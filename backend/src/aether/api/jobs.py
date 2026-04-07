from fastapi import APIRouter

router = APIRouter()


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    return {
        "job_id": job_id,
        "status": "pending",
        "progress_message": "",
        "manifest": None,
        "error": None,
    }
