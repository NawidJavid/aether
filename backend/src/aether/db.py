from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from aether.config import settings
from aether.models import Job, JobStatus, Manifest


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


async def create_job(topic: str) -> Job:
    now = datetime.now(timezone.utc)
    job_id = uuid4()
    row = JobRow(
        job_id=str(job_id),
        topic=topic,
        status=JobStatus.PENDING.value,
        progress_message="",
        manifest_json=None,
        error=None,
        created_at=now,
        updated_at=now,
    )
    async with _session_factory() as session:
        session.add(row)
        await session.commit()
    return Job(
        job_id=job_id,
        topic=topic,
        status=JobStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


async def get_job(job_id: UUID) -> Job | None:
    async with _session_factory() as session:
        row = await session.get(JobRow, str(job_id))
        if row is None:
            return None
        manifest = None
        if row.manifest_json:
            manifest = Manifest.model_validate_json(row.manifest_json)
        return Job(
            job_id=UUID(row.job_id),
            topic=row.topic,
            status=JobStatus(row.status),
            progress_message=row.progress_message,
            manifest=manifest,
            error=row.error,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


async def update_job_status(
    job_id: UUID,
    status: JobStatus,
    progress_message: str,
    error: str | None = None,
) -> None:
    async with _session_factory() as session:
        row = await session.get(JobRow, str(job_id))
        if row is None:
            return
        row.status = status.value
        row.progress_message = progress_message
        row.updated_at = datetime.now(timezone.utc)
        if error is not None:
            row.error = error
        await session.commit()


async def save_job_manifest(job_id: UUID, manifest: Manifest) -> None:
    async with _session_factory() as session:
        row = await session.get(JobRow, str(job_id))
        if row is None:
            return
        row.manifest_json = manifest.model_dump_json()
        row.status = JobStatus.COMPLETED.value
        row.progress_message = "Ready"
        row.updated_at = datetime.now(timezone.utc)
        await session.commit()


async def lookup_cache(key: str) -> ShapeCacheRow | None:
    async with _session_factory() as session:
        return await session.get(ShapeCacheRow, key)


async def save_cache_entry(
    key: str, concept: str, bin_path: str, point_count: int
) -> None:
    async with _session_factory() as session:
        existing = await session.get(ShapeCacheRow, key)
        if existing:
            return
        row = ShapeCacheRow(
            cache_key=key,
            concept=concept,
            bin_path=bin_path,
            point_count=point_count,
            created_at=datetime.now(timezone.utc),
        )
        session.add(row)
        await session.commit()
