from __future__ import annotations

import re

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.services.image_service import (
    FileTooLargeError,
    ImageNotFoundError,
    ImageService,
    InvalidNiftiError,
)

router = APIRouter(prefix="/api/images", tags=["images"])
service = ImageService()

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def _validate_id(value: str, name: str = "id") -> JSONResponse | None:
    if not _UUID_RE.match(value):
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_ID_FORMAT", "message": f"잘못된 {name} 형식입니다. UUID가 필요합니다.", "detail": {}},
        )
    return None


@router.get("/")
async def list_images() -> dict:
    return {"images": service.list_images()}


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)) -> dict:
    try:
        file_bytes = await file.read()
        result = await service.upload(file.filename or "unknown.nii.gz", file_bytes)
        return result
    except InvalidNiftiError as e:
        return JSONResponse(
            status_code=400,
            content={"error": e.code, "message": e.message, "detail": {}},
        )
    except FileTooLargeError as e:
        return JSONResponse(
            status_code=413,
            content={"error": e.code, "message": e.message, "detail": {}},
        )


@router.get("/{image_id}/metadata")
async def get_metadata(image_id: str) -> dict:
    err = _validate_id(image_id, "image_id")
    if err:
        return err
    try:
        return service.get_metadata(image_id)
    except ImageNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"error": e.code, "message": e.message, "detail": {}},
        )


@router.get("/{image_id}/volume")
async def get_volume(image_id: str) -> Response:
    err = _validate_id(image_id, "image_id")
    if err:
        return err
    try:
        data_bytes, headers = service.get_volume_bytes(image_id)
        return Response(
            content=data_bytes,
            media_type="application/octet-stream",
            headers=headers,
        )
    except ImageNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"error": e.code, "message": e.message, "detail": {}},
        )


@router.get("/{image_id}/slice")
async def get_slice(
    image_id: str,
    axis: str = Query(..., pattern="^(axial|coronal|sagittal)$"),
    index: int = Query(..., ge=0),
) -> Response:
    err = _validate_id(image_id, "image_id")
    if err:
        return err
    try:
        data_bytes, headers = service.get_slice_bytes(image_id, axis, index)
        return Response(
            content=data_bytes,
            media_type="application/octet-stream",
            headers=headers,
        )
    except ImageNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"error": e.code, "message": e.message, "detail": {}},
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_PARAMETER", "message": str(e), "detail": {}},
        )
