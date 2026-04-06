from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response

from app.services.segment_service import (
    InvalidLabelError,
    ResultNotFoundError,
    SegmentService,
    ShapeMismatchError,
)

router = APIRouter(prefix="/api/segments", tags=["segments"])
service = SegmentService()


@router.get("/{result_id}/volume")
async def get_volume(result_id: str) -> Response:
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
    try:
        return service.get_metadata(result_id)
    except ResultNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"error": e.code, "message": e.message, "detail": {}},
        )


@router.put("/{result_id}")
async def save_edited(result_id: str, request: Request) -> dict:
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


@router.get("/history")
async def get_history(image_id: str = Query(...)) -> dict:
    return {"results": service.list_results(image_id)}


@router.get("/{result_id}/download")
async def download_segment(
    result_id: str, class_id: Optional[int] = Query(default=None)
) -> Response:
    try:
        nifti_path, meta = service._find_result(result_id)

        import nibabel as nib
        import numpy as np

        img = nib.load(str(nifti_path))
        data = np.asarray(img.dataobj)

        if class_id is not None:
            data = (data == class_id).astype(np.uint8)

        import io
        import gzip

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
