from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from app.config import settings

logger = logging.getLogger("segviewer.segment")


class SegmentService:
    def __init__(self) -> None:
        self.results_dir = Path(settings.results_dir)

    def get_volume_bytes(self, result_id: str) -> tuple[bytes, dict[str, str]]:
        nifti_path, meta = self._find_result(result_id)
        img = nib.load(str(nifti_path))
        data = np.asarray(img.dataobj).astype(np.uint8)

        labels_str = ",".join(f"{k}:{v}" for k, v in meta.get("labels", {}).items())
        headers = {
            "X-Seg-Shape": ",".join(str(s) for s in data.shape),
            "X-Seg-Dtype": "uint8",
            "X-Seg-Num-Classes": str(meta.get("num_classes", 0)),
            "X-Seg-Labels": labels_str,
        }
        return data.tobytes(order="C"), headers

    def get_metadata(self, result_id: str) -> dict[str, Any]:
        nifti_path, meta = self._find_result(result_id)
        img = nib.load(str(nifti_path))
        data = np.asarray(img.dataobj).astype(np.uint8)

        voxel_counts: dict[str, int] = {}
        for label_name, label_id in meta.get("labels", {}).items():
            voxel_counts[str(label_id)] = int(np.sum(data == label_id))

        meta["voxel_counts"] = voxel_counts
        return meta

    def save_edited(
        self, result_id: str, seg_bytes: bytes, shape: tuple[int, ...], dtype: str
    ) -> dict[str, Any]:
        nifti_path, meta = self._find_result(result_id)

        original_img = nib.load(str(nifti_path))
        original_shape = original_img.shape

        np_dtype = np.uint8 if dtype == "uint8" else np.uint16
        data = np.frombuffer(seg_bytes, dtype=np_dtype).reshape(shape, order="C")

        if data.shape != original_shape:
            raise ShapeMismatchError(
                f"Shape 불일치: 원본={original_shape}, 수신={data.shape}"
            )

        labels = meta.get("labels", {})
        max_label = max(labels.values()) if labels else 0
        if data.max() > max_label:
            raise InvalidLabelError(
                f"유효하지 않은 레이블 값: max={data.max()}, expected<={max_label}"
            )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        backup_path = nifti_path.with_name(
            f"{result_id}_backup_{timestamp}.nii.gz"
        )
        shutil.copy2(str(nifti_path), str(backup_path))

        self._cleanup_backups(nifti_path.parent, result_id, max_backups=5)

        new_img = nib.Nifti1Image(data, original_img.affine, original_img.header)
        nib.save(new_img, str(nifti_path))

        meta["edited"] = True
        meta["edited_at"] = datetime.now(timezone.utc).isoformat()
        meta_path = nifti_path.with_name(f"{result_id}_meta.json")
        meta_path.write_text(json.dumps(meta, indent=2, default=str))

        logger.info("Segment saved: %s (backup: %s)", result_id, backup_path.name)
        return {
            "result_id": result_id,
            "updated_at": meta["edited_at"],
            "edited": True,
            "backup_path": str(backup_path),
        }

    def list_results(self, image_id: str) -> list[dict[str, Any]]:
        results = []
        image_dir = self.results_dir / image_id
        if not image_dir.exists():
            return results
        for meta_file in sorted(image_dir.glob("*_meta.json")):
            meta = json.loads(meta_file.read_text())
            results.append(meta)
        return results

    def _find_result(self, result_id: str) -> tuple[Path, dict[str, Any]]:
        for image_dir in self.results_dir.iterdir():
            if not image_dir.is_dir():
                continue
            nifti_path = image_dir / f"{result_id}.nii.gz"
            meta_path = image_dir / f"{result_id}_meta.json"
            if nifti_path.exists() and meta_path.exists():
                meta = json.loads(meta_path.read_text())
                return nifti_path, meta
        raise ResultNotFoundError(result_id)

    def _cleanup_backups(self, directory: Path, result_id: str, max_backups: int) -> None:
        backups = sorted(directory.glob(f"{result_id}_backup_*.nii.gz"))
        while len(backups) > max_backups:
            oldest = backups.pop(0)
            oldest.unlink()
            logger.info("Removed old backup: %s", oldest.name)


class ResultNotFoundError(Exception):
    def __init__(self, result_id: str) -> None:
        self.code = "RESULT_NOT_FOUND"
        self.message = f"결과를 찾을 수 없습니다: {result_id}"
        super().__init__(self.message)


class ShapeMismatchError(Exception):
    def __init__(self, message: str) -> None:
        self.code = "SHAPE_MISMATCH"
        self.message = message
        super().__init__(message)


class InvalidLabelError(Exception):
    def __init__(self, message: str) -> None:
        self.code = "INVALID_LABEL_VALUE"
        self.message = message
        super().__init__(message)
