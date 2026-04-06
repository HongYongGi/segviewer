from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/gpu")
async def gpu_status() -> dict:
    info: dict = {
        "gpu_name": "N/A",
        "gpu_index": settings.gpu_device_index,
        "vram_total_mb": 0,
        "vram_used_mb": 0,
        "vram_free_mb": 0,
        "gpu_utilization_percent": 0,
        "pytorch_version": "N/A",
        "cuda_version": "N/A",
        "cuda_available": False,
    }

    try:
        import torch

        info["pytorch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()

        if torch.cuda.is_available():
            idx = settings.gpu_device_index
            info["gpu_name"] = torch.cuda.get_device_name(idx)
            info["cuda_version"] = torch.version.cuda or "N/A"
            free, total = torch.cuda.mem_get_info(idx)
            info["vram_total_mb"] = total // (1024 * 1024)
            info["vram_free_mb"] = free // (1024 * 1024)
            info["vram_used_mb"] = (total - free) // (1024 * 1024)
    except ImportError:
        pass

    return info
