import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import images, inference, models, segments

logger = logging.getLogger("segviewer")


def create_app() -> FastAPI:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    application = FastAPI(title="SegViewer", version="0.1.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Image-Shape",
            "X-Image-Dtype",
            "X-Image-Spacing",
            "X-Image-ByteOrder",
            "X-Image-Affine",
            "X-Seg-Shape",
            "X-Seg-Dtype",
            "X-Seg-Num-Classes",
            "X-Seg-Labels",
            "X-Slice-Shape",
            "X-Slice-Dtype",
            "X-Mesh-Vertices-Count",
            "X-Mesh-Faces-Count",
            "X-Mesh-Format",
        ],
    )

    application.include_router(images.router)
    application.include_router(models.router)
    application.include_router(inference.router)
    application.include_router(segments.router)

    @application.on_event("startup")
    async def startup() -> None:
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.results_dir).mkdir(parents=True, exist_ok=True)

        if settings.nnunet_results_path:
            p = Path(settings.nnunet_results_path)
            if not p.exists():
                logger.warning("nnUNet_results path does not exist: %s", p)
            else:
                logger.info("nnUNet_results path: %s", p)
        else:
            logger.warning(
                "nnunet_results_path not set. "
                "Model listing and inference will be unavailable."
            )

    @application.get("/api/health")
    async def health_check() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    return application


app = create_app()
