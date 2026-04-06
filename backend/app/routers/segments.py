from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response

from app.services.mesh_service import MeshService
from app.services.segment_service import (
    InvalidLabelError,
    ResultNotFoundError,
    SegmentService,
    ShapeMismatchError,
)

router = APIRouter(prefix="/api/segments", tags=["segments"])
service = SegmentService()
mesh_service = MeshService()

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def _validate_id(value: str, name: str = "id") -> JSONResponse | None:
    if not _UUID_RE.match(value):
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_ID_FORMAT", "message": f"잘못된 {name} 형식입니다. UUID가 필요합니다.", "detail": {}},
        )
    return None


@router.get("/{result_id}/volume")
async def get_volume(result_id: str) -> Response:
    err = _validate_id(result_id, "result_id")
    if err:
        return err
    try:
        data_bytes, headers = service.get_volume_bytes(result_id)
        return Response(
            content=data_bytes,
            media_type="application/octet-stream",
            headers=headers,
        )
    except ResultNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"error": e.code, "message": e.message, "detail": {}},
        )


@router.get("/{result_id}/metadata")
async def get_metadata(result_id: str) -> dict:
    err = _validate_id(result_id, "result_id")
    if err:
        return err
    try:
        return service.get_metadata(result_id)
    except ResultNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"error": e.code, "message": e.message, "detail": {}},
        )


@router.put("/{result_id}")
async def save_edited(result_id: str, request: Request) -> dict:
    err = _validate_id(result_id, "result_id")
    if err:
        return err
    try:
        seg_bytes = await request.body()
        shape_str = request.headers.get("X-Seg-Shape", "")
        dtype = request.headers.get("X-Seg-Dtype", "uint8")

        shape = tuple(int(s) for s in shape_str.split(",") if s)
        if not shape:
            return JSONResponse(
                status_code=400,
                content={"error": "INVALID_PARAMETER", "message": "X-Seg-Shape 헤더가 필요합니다.", "detail": {}},
            )

        result = service.save_edited(result_id, seg_bytes, shape, dtype)
        return result
    except ResultNotFoundError as e:
        return JSONResponse(status_code=404, content={"error": e.code, "message": e.message, "detail": {}})
    except ShapeMismatchError as e:
        return JSONResponse(status_code=400, content={"error": e.code, "message": e.message, "detail": {}})
    except InvalidLabelError as e:
        return JSONResponse(status_code=400, content={"error": e.code, "message": e.message, "detail": {}})


@router.get("/{result_id}/mesh")
async def get_mesh(result_id: str, class_id: int = Query(...)) -> Response:
    err = _validate_id(result_id, "result_id")
    if err:
        return err
    try:
        nifti_path, _ = service.find_result(result_id)
        data_bytes, headers = mesh_service.generate_mesh(str(nifti_path), class_id)
        return Response(
            content=data_bytes,
            media_type="application/octet-stream",
            headers=headers,
        )
    except ResultNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"error": e.code, "message": e.message, "detail": {}},
        )


@router.get("/history")
async def get_history(image_id: str = Query(...)) -> dict:
    if not _UUID_RE.match(image_id):
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_ID_FORMAT", "message": "잘못된 image_id 형식입니다.", "detail": {}},
        )
    return {"results": service.list_results(image_id)}


@router.get("/{result_id}/download")
async def download_segment(
    result_id: str, class_id: Optional[int] = Query(default=None)
) -> Response:
    err = _validate_id(result_id, "result_id")
    if err:
        return err
    try:
        nifti_path, meta = service.find_result(result_id)

        import nibabel as nib
        import numpy as np

        img = nib.load(str(nifti_path))
        data = np.asarray(img.dataobj)

        if class_id is not None:
            data = (data == class_id).astype(np.uint8)

        import io

        out_img = nib.Nifti1Image(data, img.affine, img.header)
        bio = io.BytesIO()
        nib.save(out_img, bio)
        bio.seek(0)

        model_name = meta.get("model", {}).get("dataset", "unknown")
        filename = f"segmentation_{model_name}_{result_id[:8]}.nii.gz"

        return Response(
            content=bio.read(),
            media_type="application/gzip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ResultNotFoundError as e:
        return JSONResponse(status_code=404, content={"error": e.code, "message": e.message, "detail": {}})
