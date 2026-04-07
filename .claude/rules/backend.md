---
paths:
  - "backend/**"
---

# Aether — Backend implementation rules

These rules load automatically when you work on any file in `backend/`. They cover directory structure, environment setup, Pydantic models, FastAPI endpoints, and the database layer.

For pipeline-specific code (LLM, TTS, shapes, orchestrator), see `.claude/rules/backend-pipeline.md` which loads when you work in `backend/src/aether/pipeline/`.

## Backend directory structure

```
backend/
├── pyproject.toml               # Dependencies and tool config
├── .python-version              # 3.11 or higher
├── data/                        # GITIGNORED — runtime data
│   ├── aether.db                # SQLite database
│   ├── cache/
│   │   ├── shapes/              # {hash}.bin point clouds
│   │   ├── meshes/              # {hash}.glb intermediate meshes
│   │   └── images/              # {hash}.png intermediate images
│   └── manifests/
│       └── {manifest_id}/
│           ├── manifest.json
│           └── audio.mp3
├── src/
│   └── aether/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry, CORS, static mounts, lifespan
│       ├── config.py            # Pydantic Settings
│       ├── models.py            # Pydantic data models (see below)
│       ├── db.py                # SQLAlchemy setup, table defs, helper functions
│       ├── api/
│       │   ├── __init__.py
│       │   ├── generate.py      # POST /api/generate
│       │   └── jobs.py          # GET /api/jobs/{id}
│       ├── pipeline/            # see backend-pipeline.md rule
│       │   ├── __init__.py
│       │   ├── orchestrator.py
│       │   ├── llm.py
│       │   ├── tts.py
│       │   ├── shapes.py
│       │   ├── pointcloud.py
│       │   └── manifest.py
│       └── prompts/
│           └── script_writer.txt   # The Claude system prompt
└── tests/
    ├── conftest.py
    ├── test_llm_parser.py
    ├── test_pointcloud.py
    └── test_orchestrator.py
```

## Environment variables (`.env.example`)

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# ElevenLabs
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM   # Rachel by default

# fal.ai
FAL_KEY=...

# Backend config
AETHER_DATA_DIR=./data
AETHER_HOST=127.0.0.1
AETHER_PORT=8000
```

## Setup commands

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
mkdir -p data/cache/{shapes,meshes,images} data/manifests
uvicorn aether.main:app --reload --host 127.0.0.1 --port 8000
```

## Data models (`src/aether/models.py`)

Use Pydantic v2 patterns. Add `from __future__ import annotations` at the top for cleaner type hints. The TypeScript versions in `frontend/src/types.ts` should mirror these exactly.

```python
from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_ASSETS = "generating_assets"   # audio + shapes in parallel
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=500)


class ScriptElement(BaseModel):
    """One element of the parsed script — either spoken text or a shape cue."""
    kind: Literal["say", "shape"]
    text: str | None = None       # for kind == "say"
    concept: str | None = None    # for kind == "shape"


class ParsedScript(BaseModel):
    elements: list[ScriptElement]
    full_text: str                # concatenated say text, used for TTS input
    unique_concepts: list[str]    # deduped, in order of first appearance


class ScheduledShape(BaseModel):
    """A shape positioned in the playback timeline."""
    concept: str
    point_cloud_url: str          # /assets/cache/shapes/{hash}.bin
    point_count: int
    trigger_time_ms: int          # when in audio.mp3 to start morphing
    morph_duration_ms: int = 1500


class Manifest(BaseModel):
    manifest_id: UUID
    topic: str
    audio_url: str                # /assets/manifests/{id}/audio.mp3
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
```

## API endpoints

The entire HTTP surface is three endpoints. Don't add health checks, metrics, or separate manifest endpoints — the Job response carries the manifest inline once complete.

### `POST /api/generate`

```python
# api/generate.py
from fastapi import APIRouter, BackgroundTasks
from aether.models import GenerationRequest, Job
from aether.pipeline.orchestrator import run_pipeline

router = APIRouter()

@router.post("/api/generate")
async def generate(req: GenerationRequest, bg: BackgroundTasks) -> dict:
    job = await create_job(req.topic)
    bg.add_task(run_pipeline, job.job_id, req.topic)
    return {"job_id": str(job.job_id)}
```

### `GET /api/jobs/{job_id}`

Returns the full `Job` object including the inline `Manifest` if completed. Frontend polls every 1000ms.

### `GET /assets/{path}`

FastAPI `StaticFiles` mount serving everything under `data/`. Frontend fetches `audio.mp3` and `*.bin` files via this mount.

```python
# main.py — relevant pieces
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from aether.config import settings
from aether.db import init_db
from aether.api import generate, jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router)
app.include_router(jobs.router)
app.mount("/assets", StaticFiles(directory=settings.data_dir), name="assets")
```

## Database layer (`src/aether/db.py`)

Use SQLAlchemy 2.x async style with `aiosqlite`. The schema is intentionally minimal — two tables.

```python
from datetime import datetime
from uuid import UUID

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from aether.config import settings


class Base(DeclarativeBase):
    pass


class JobRow(Base):
    __tablename__ = "jobs"
    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    topic: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    progress_message: Mapped[str] = mapped_column(Text, default="")
    manifest_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class ShapeCacheRow(Base):
    __tablename__ = "shape_cache"
    cache_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    concept: Mapped[str] = mapped_column(Text)
    bin_path: Mapped[str] = mapped_column(Text)
    point_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


_engine = create_async_engine(f"sqlite+aiosqlite:///{settings.data_dir}/aether.db")
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def init_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

Add thin async helper functions for `lookup_cache(key)`, `save_cache_entry(key, concept, bin_path)`, `update_job_status(job_id, status, progress, error=None)`, `save_job_manifest(job_id, manifest)`, and `get_job(job_id)`. Each is a few lines wrapping `_session_factory()`. Keep them simple.

## Backend tests

`pytest` + `pytest-asyncio`. Three test files matter:

- `test_llm_parser.py` — feed mocked Claude responses to the script parser, verify it correctly extracts elements and unique concepts. Test failure modes (no opening shape, no say elements).
- `test_pointcloud.py` — load a known mesh from `tests/fixtures/`, sample it, verify output shape `(N, 3)` and that points are normalized (centered, max distance ≤ 1).
- `test_orchestrator.py` — mock all three external services (Claude, ElevenLabs, fal), run the full pipeline, verify a manifest is produced with correct shape count and timing.

Run with: `cd backend && pytest -v`
