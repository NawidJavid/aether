from uuid import UUID

from fastapi import APIRouter, HTTPException

from aether.db import get_job
from aether.models import Job

router = APIRouter()


@router.get("/api/jobs/{job_id}")
async def get_job_status(job_id: UUID) -> Job:
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
