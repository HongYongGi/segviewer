from fastapi import APIRouter

router = APIRouter(prefix="/api/inference", tags=["inference"])


@router.get("/")
async def inference_status() -> dict:
    return {"status": "idle", "message": "Not yet implemented"}
