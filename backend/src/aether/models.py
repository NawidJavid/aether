from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_ASSETS = "generating_assets"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=500)


class ScriptElement(BaseModel):
    """One element of the parsed script — either spoken text or a shape cue."""
    kind: Literal["say", "shape"]
    text: str | None = None
    concept: str | None = None


class ParsedScript(BaseModel):
    elements: list[ScriptElement]
    full_text: str
    unique_concepts: list[str]


class ScheduledShape(BaseModel):
    """A shape positioned in the playback timeline."""
    concept: str
    point_cloud_url: str
    point_count: int
    trigger_time_ms: int
    morph_duration_ms: int = 1500


class Manifest(BaseModel):
    manifest_id: UUID
    topic: str
    audio_url: str
    audio_duration_ms: int
    shapes: list[ScheduledShape]
    full_text: str
    created_at: datetime


class Job(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    topic: str
    status: JobStatus = JobStatus.PENDING
    progress_message: str = ""
    manifest: Manifest | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
