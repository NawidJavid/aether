from fastapi import APIRouter, BackgroundTasks

from aether.db import create_job
from aether.models import GenerationRequest
from aether.pipeline.orchestrator import run_pipeline

router = APIRouter()


@router.post("/api/generate")
async def generate(req: GenerationRequest, bg: BackgroundTasks) -> dict:
    job = await create_job(req.topic)
    bg.add_task(run_pipeline, job.job_id, req.topic)
    return {"job_id": str(job.job_id)}
