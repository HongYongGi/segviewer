from fastapi import APIRouter

from app.services.model_service import ModelService

router = APIRouter(prefix="/api/models", tags=["models"])
service = ModelService()


@router.get("/")
async def list_models() -> dict:
    return service.get_models()


@router.get("/refresh")
async def refresh_models() -> dict:
    return service.refresh()
