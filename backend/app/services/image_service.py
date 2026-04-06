from __future__ import annotations

import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from app.config import settings

logger = logging.getLogger("segviewer.image")


class ImageService:
    def __init__(self) -> None:
        self.upload_dir = Path(settings.upload_dir)

    async def upload(self, filename: str, file_bytes: bytes) -> dict[str, Any]:
        image_id = str(uuid.uuid4())
        image_dir = self.upload_dir / image_id
        image_dir.mkdir(parents=True, exist_ok=True)

        ext = _get_nifti_ext(filename)
        if ext is None:
            raise InvalidNiftiError("INVALID_NIFTI_FORMAT", f"지원하지 않는 확장자: {filename}")

        file_size = len(file_bytes)
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise FileTooLargeError(
                f"파일 크기({file_size / 1024 / 1024:.1f}MB)가 "
                f"제한({settings.max_upload_size_mb}MB)을 초과합니다."
            )

        tmp_path = image_dir / f"_tmp{ext}"
        tmp_path.write_bytes(file_bytes)

        try:
            img = nib.load(str(tmp_path))
        except Exception:
            shutil.rmtree(image_dir)
            raise InvalidNiftiError("INVALID_NIFTI_FORMAT", "NIfTI 파싱에 실패했습니다.")

        data = np.asarray(img.dataobj)
        if data.ndim != 3:
            shutil.rmtree(image_dir)
            raise InvalidNiftiError("NOT_3D_VOLUME", f"3D 볼륨이어야 합니다 (현재: {data.ndim}D)")

        original_path = image_dir / "original.nii.gz"
        nib.save(img, str(original_path))

        canonical = nib.as_closest_canonical(img)
        canonical_path = image_dir / "canonical.nii.gz"
        nib.save(canonical, str(canonical_path))

        tmp_path.unlink(missing_ok=True)

        canon_data = np.asarray(canonical.dataobj).astype(np.float32)
        metadata = _extract_metadata(filename, file_size, img, canonical, canon_data)
        meta_path = image_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2, default=str))

        logger.info("Image uploaded: %s (%s)", image_id, filename)
        return {"image_id": image_id, "filename": filename, "metadata": metadata}

    def get_metadata(self, image_id: str) -> dict[str, Any]:
        meta_path = self.upload_dir / image_id / "metadata.json"
        if not meta_path.exists():
            raise ImageNotFoundError(image_id)
        return json.loads(meta_path.read_text())

    def get_volume_bytes(self, image_id: str) -> tuple[bytes, dict[str, str]]:
        canonical_path = self.upload_dir / image_id / "canonical.nii.gz"
        if not canonical_path.exists():
            raise ImageNotFoundError(image_id)

        img = nib.load(str(canonical_path))
        data = np.asarray(img.dataobj).astype(np.float32)
        affine = img.affine

        headers = {
            "X-Image-Shape": ",".join(str(s) for s in data.shape),
            "X-Image-Dtype": "float32",
            "X-Image-Spacing": ",".join(f"{s:.6f}" for s in img.header.get_zooms()[:3]),
            "X-Image-ByteOrder": "little",
            "X-Image-Affine": ",".join(f"{v:.6f}" for v in affine.flatten()),
        }
        return data.tobytes(order="C"), headers

    def get_slice_bytes(
        self, image_id: str, axis: str, index: int
    ) -> tuple[bytes, dict[str, str]]:
        canonical_path = self.upload_dir / image_id / "canonical.nii.gz"
        if not canonical_path.exists():
            raise ImageNotFoundError(image_id)

        img = nib.load(str(canonical_path))
        data = np.asarray(img.dataobj).astype(np.float32)

        axis_map = {"axial": 2, "coronal": 1, "sagittal": 0}
        ax = axis_map.get(axis)
        if ax is None:
            raise ValueError(f"Invalid axis: {axis}")
        if index < 0 or index >= data.shape[ax]:
            raise ValueError(f"Index {index} out of range [0, {data.shape[ax]})")

        slc = np.take(data, index, axis=ax)
        headers = {
            "X-Slice-Shape": ",".join(str(s) for s in slc.shape),
            "X-Slice-Dtype": "float32",
        }
        return slc.tobytes(order="C"), headers

    def list_images(self) -> list[dict[str, Any]]:
        images = []
        if not self.upload_dir.exists():
            return images
        for d in sorted(self.upload_dir.iterdir()):
            meta_path = d / "metadata.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                images.append({"image_id": d.name, **meta})
        return images


def _get_nifti_ext(filename: str) -> str | None:
    lower = filename.lower()
    if lower.endswith(".nii.gz"):
        return ".nii.gz"
    if lower.endswith(".nii"):
        return ".nii"
    return None


def _extract_metadata(
    filename: str,
    file_size: int,
    original: nib.Nifti1Image,
    canonical: nib.Nifti1Image,
    data: np.ndarray,
) -> dict[str, Any]:
    return {
        "filename": filename,
        "shape": list(data.shape),
        "spacing": [round(float(s), 6) for s in canonical.header.get_zooms()[:3]],
        "orientation": "".join(nib.aff2axcodes(original.affine)),
        "dtype": str(data.dtype),
        "hu_range": [int(data.min()), int(data.max())],
        "file_size_bytes": file_size,
        "affine": canonical.affine.tolist(),
    }


class InvalidNiftiError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class FileTooLargeError(Exception):
    def __init__(self, message: str) -> None:
        self.code = "FILE_TOO_LARGE"
        self.message = message
        super().__init__(message)


class ImageNotFoundError(Exception):
    def __init__(self, image_id: str) -> None:
        self.code = "IMAGE_NOT_FOUND"
        self.message = f"이미지를 찾을 수 없습니다: {image_id}"
        super().__init__(self.message)
