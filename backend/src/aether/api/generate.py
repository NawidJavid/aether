from fastapi import APIRouter

router = APIRouter()


@router.post("/api/generate")
async def generate() -> dict:
    return {"job_id": "stub"}
