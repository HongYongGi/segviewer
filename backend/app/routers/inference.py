from __future__ import annotations

import asyncio
import re

from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.services.inference_service import InferenceJob, InferenceService, QueueFullError

router = APIRouter(prefix="/api/inference", tags=["inference"])
service = InferenceService()

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


class InferenceRequest(BaseModel):
    image_id: str = Field(..., description="업로드된 이미지의 UUID")
    dataset_id: int = Field(..., description="nnUNet 데이터셋 ID")
    full_dataset_name: str = Field(..., description="전체 데이터셋 이름 (예: Dataset302_Segmentation)")
    trainer: str = Field(default="nnUNetTrainer", description="트레이너 이름")
    plans: str = Field(default="nnUNetResEncUNetMPlans", description="플랜 이름")
    configuration: str = Field(default="3d_fullres", description="설정")
    folds: list[int] = Field(default=[0, 1, 2, 3, 4], description="사용할 fold 목록")
    labels: dict[str, int] = Field(default_factory=dict, description="레이블 매핑")


@router.on_event("startup")
async def startup() -> None:
    service.start_worker()


@router.post("/run")
async def run_inference(body: InferenceRequest) -> dict:
    if not _UUID_RE.match(body.image_id):
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_ID_FORMAT", "message": "잘못된 image_id 형식입니다. UUID가 필요합니다.", "detail": {}},
        )

    image_path = str(
        Path(settings.upload_dir) / body.image_id / "canonical.nii.gz"
    )
    if not Path(image_path).exists():
        return JSONResponse(
            status_code=404,
            content={"error": "IMAGE_NOT_FOUND", "message": f"이미지를 찾을 수 없습니다: {body.image_id}", "detail": {}},
        )

    import uuid

    job = InferenceJob(
        job_id=str(uuid.uuid4()),
        image_id=body.image_id,
        image_path=image_path,
        model_config=body.model_dump(),
    )

    try:
        await service.submit(job)
    except QueueFullError:
        return JSONResponse(
            status_code=429,
            content={"error": "INFERENCE_QUEUE_FULL", "message": "현재 대기열이 가득 찼습니다.", "detail": {}},
        )

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job.job_id,
            "status": "queued",
            "websocket_url": f"/ws/inference/{job.job_id}",
        },
    )


@router.get("/{job_id}/status")
async def get_status(job_id: str) -> dict:
    if not _UUID_RE.match(job_id):
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_ID_FORMAT", "message": "잘못된 job_id 형식입니다.", "detail": {}},
        )
    job = service.get_job(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"error": "JOB_NOT_FOUND", "message": f"작업을 찾을 수 없습니다: {job_id}", "detail": {}},
        )
    return job.to_dict()


@router.get("/cache")
async def get_cache() -> dict:
    return service.get_cache_info()


@router.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    job = service.get_job(job_id)
    if not job:
        await websocket.send_json({"error": "JOB_NOT_FOUND"})
        await websocket.close()
        return

    queue: asyncio.Queue[dict] = asyncio.Queue()

    def on_update(data: dict) -> None:
        queue.put_nowait(data)

    job._listeners.append(on_update)

    try:
        await websocket.send_json(job.to_dict())

        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json(data)
                if data.get("status") in ("completed", "failed"):
                    break
            except asyncio.TimeoutError:
                if job.status in ("completed", "failed"):
                    await websocket.send_json(job.to_dict())
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if on_update in job._listeners:
            job._listeners.remove(on_update)
