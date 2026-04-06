from __future__ import annotations

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
    try:
        return service.get_metadata(image_id)
    except ImageNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"error": e.code, "message": e.message, "detail": {}},
        )


@router.get("/{image_id}/volume")
async def get_volume(image_id: str) -> Response:
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
