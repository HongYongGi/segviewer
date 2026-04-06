from fastapi import APIRouter

router = APIRouter(prefix="/api/segments", tags=["segments"])


@router.get("/")
async def list_segments() -> dict:
    return {"segments": [], "message": "Not yet implemented"}
