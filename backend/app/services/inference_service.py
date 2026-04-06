from __future__ import annotations

import asyncio
import gc
import json
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

from app.config import settings

logger = logging.getLogger("segviewer.inference")

JOB_TTL_SECONDS = 3600  # completed/failed jobs are cleaned up after 1 hour

try:
    import torch
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    NNUNET_AVAILABLE = True
except ImportError:
    NNUNET_AVAILABLE = False
    logger.warning("nnUNet/PyTorch not available. Inference will be disabled.")


@dataclass
class InferenceJob:
    job_id: str
    image_id: str
    image_path: str
    model_config: dict[str, Any]
    status: str = "queued"
    progress: int = 0
    stage: str = ""
    stage_detail: str = ""
    result_id: str | None = None
    error: str | None = None
    error_message: str | None = None
    started_at: float | None = None
    elapsed_seconds: float = 0
    labels: dict[str, int] = field(default_factory=dict)
    _listeners: list[Callable] = field(default_factory=list, repr=False)

    def update(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.started_at:
            self.elapsed_seconds = time.time() - self.started_at
        for listener in self._listeners:
            try:
                listener(self.to_dict())
            except Exception:
                pass

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "image_id": self.image_id,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "stage_detail": self.stage_detail,
            "result_id": self.result_id,
            "error": self.error,
            "error_message": self.error_message,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "labels": self.labels,
        }


class InferenceService:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[InferenceJob] = asyncio.Queue(maxsize=5)
        self._jobs: dict[str, InferenceJob] = {}
        self._current_job: InferenceJob | None = None
        self._predictors: dict[str, Any] = {}
        self._predictor_lru: list[str] = []
        self._worker_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

    def start_worker(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Inference worker started")

    async def submit(self, job: InferenceJob) -> None:
        if self._queue.full():
            raise QueueFullError()
        self._jobs[job.job_id] = job
        await self._queue.put(job)

    def get_job(self, job_id: str) -> InferenceJob | None:
        return self._jobs.get(job_id)

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            self._current_job = job
            try:
                await self._run_inference(job)
            except Exception as e:
                logger.exception("Inference failed: %s", e)
                job.update(status="failed", progress=-1, error="INFERENCE_FAILED", error_message=str(e))
            finally:
                self._current_job = None
                self._queue.task_done()

    async def _run_inference(self, job: InferenceJob) -> None:
        if not NNUNET_AVAILABLE:
            job.update(status="failed", progress=-1, error="NNUNET_NOT_AVAILABLE",
                       error_message="nnUNet/PyTorch가 설치되지 않았습니다.")
            return

        job.update(status="running", started_at=time.time(), progress=0, stage="preparing")

        mc = job.model_config
        cache_key = f"{mc['dataset_id']}_{mc['trainer']}_{mc['plans']}_{mc['configuration']}"
        results_path = settings.nnunet_results_path
        model_dir = (
            Path(results_path)
            / mc["full_dataset_name"]
            / f"{mc['trainer']}__{mc['plans']}__{mc['configuration']}"
        )

        job.update(progress=5, stage="loading_model", stage_detail="모델 로딩 중...")
        predictor = await asyncio.to_thread(
            self._get_or_load_predictor, cache_key, str(model_dir), mc.get("folds", (0, 1, 2, 3, 4))
        )

        job.update(progress=15, stage="preprocessing", stage_detail="전처리 중...")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            src = Path(job.image_path)
            link = input_dir / f"{job.image_id}_0000.nii.gz"
            os.symlink(src.resolve(), link)

            folds = mc.get("folds", (0, 1, 2, 3, 4))
            num_folds = len(folds) if isinstance(folds, (list, tuple)) else 1

            job.update(progress=20, stage="inference", stage_detail=f"추론 중... (0/{num_folds} folds)")

            await asyncio.to_thread(
                predictor.predict_from_files,
                str(input_dir),
                str(output_dir),
                save_probabilities=False,
                overwrite=True,
                num_processes_preprocessing=1,
                num_processes_segmentation_export=1,
            )

            job.update(progress=90, stage="postprocessing", stage_detail="후처리 중...")

            output_files = list(output_dir.glob("*.nii.gz"))
            if not output_files:
                raise RuntimeError("Inference 결과 파일이 생성되지 않았습니다.")

            result_id = str(uuid.uuid4())
            result_dir = Path(settings.results_dir) / job.image_id
            result_dir.mkdir(parents=True, exist_ok=True)
            result_path = result_dir / f"{result_id}.nii.gz"

            import shutil
            shutil.copy2(str(output_files[0]), str(result_path))

        job.update(progress=95, stage="saving", stage_detail="결과 저장 중...")

        import nibabel as nib
        seg_img = nib.load(str(result_path))
        seg_data = np.asarray(seg_img.dataobj)

        labels = mc.get("labels", {"background": 0})
        meta = {
            "result_id": result_id,
            "image_id": job.image_id,
            "model": {
                "dataset": mc.get("full_dataset_name", ""),
                "configuration": mc.get("configuration", ""),
                "folds": list(folds) if isinstance(folds, (list, tuple)) else [folds],
            },
            "labels": labels,
            "shape": list(seg_data.shape),
            "num_classes": len(labels),
            "inference_time_seconds": round(time.time() - job.started_at, 1),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "edited": False,
        }
        meta_path = result_dir / f"{result_id}_meta.json"
        meta_path.write_text(json.dumps(meta, indent=2, default=str))

        job.update(
            status="completed", progress=100, stage="completed",
            stage_detail="완료!", result_id=result_id, labels=labels,
        )
        logger.info("Inference completed: job=%s result=%s", job.job_id, result_id)

    def _get_or_load_predictor(self, cache_key: str, model_dir: str, folds: tuple) -> Any:
        if cache_key in self._predictors:
            self._predictor_lru.remove(cache_key)
            self._predictor_lru.append(cache_key)
            return self._predictors[cache_key]

        while len(self._predictors) >= settings.max_cached_models:
            oldest = self._predictor_lru.pop(0)
            self._release_predictor(oldest)

        predictor = nnUNetPredictor(
            tile_step_size=0.5,
            use_gaussian=True,
            use_mirroring=True,
            perform_everything_on_device=True,
            device=torch.device("cuda", settings.gpu_device_index),
            verbose=False,
            verbose_preprocessing=False,
            allow_tqdm=False,
        )
        predictor.initialize_from_trained_model_folder(
            model_training_output_dir=model_dir,
            use_folds=tuple(folds) if isinstance(folds, list) else folds,
            checkpoint_name="checkpoint_best.pth",
        )

        self._predictors[cache_key] = predictor
        self._predictor_lru.append(cache_key)
        logger.info("Model loaded: %s", cache_key)
        return predictor

    def _release_predictor(self, cache_key: str) -> None:
        predictor = self._predictors.pop(cache_key, None)
        if predictor is None:
            return
        try:
            if hasattr(predictor, "network"):
                predictor.network.cpu()
            del predictor
            gc.collect()
            if NNUNET_AVAILABLE:
                torch.cuda.empty_cache()
            logger.info("Model released: %s", cache_key)
        except Exception:
            logger.exception("Failed to release model: %s", cache_key)

    async def _cleanup_loop(self) -> None:
        """Periodically remove completed/failed jobs older than JOB_TTL_SECONDS."""
        while True:
            await asyncio.sleep(300)  # check every 5 minutes
            now = time.time()
            expired = [
                jid for jid, job in self._jobs.items()
                if job.status in ("completed", "failed")
                and job.started_at
                and (now - job.started_at) > JOB_TTL_SECONDS
            ]
            for jid in expired:
                del self._jobs[jid]
            if expired:
                logger.info("Cleaned up %d expired jobs", len(expired))

    def get_cache_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "cached_models": list(self._predictors.keys()),
            "max_cached": settings.max_cached_models,
            "queue_length": self._queue.qsize(),
            "current_job": self._current_job.to_dict() if self._current_job else None,
        }
        if NNUNET_AVAILABLE:
            try:
                free, total = torch.cuda.mem_get_info(settings.gpu_device_index)
                info["gpu_total_mb"] = total // (1024 * 1024)
                info["gpu_free_mb"] = free // (1024 * 1024)
                info["gpu_name"] = torch.cuda.get_device_name(settings.gpu_device_index)
            except Exception:
                pass
        return info


class QueueFullError(Exception):
    pass
