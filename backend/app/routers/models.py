from fastapi import APIRouter

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/")
async def list_models() -> dict:
    return {"models": [], "message": "Not yet implemented"}
