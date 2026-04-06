from fastapi import APIRouter

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/")
async def list_images() -> dict:
    return {"images": [], "message": "Not yet implemented"}
