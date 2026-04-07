from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import aether.db as db_module
from aether.db import Base


@pytest.fixture
async def tmp_data_dir(tmp_path):
    """Provides a temp data dir and patches settings + DB to use it."""
    data_dir = tmp_path / "data"
    for sub in ["cache/shapes", "cache/meshes", "cache/images", "manifests"]:
        (data_dir / sub).mkdir(parents=True)

    engine = create_async_engine(f"sqlite+aiosqlite:///{data_dir}/test.db")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch the module-level engine and session factory
    original_engine = db_module._engine
    original_factory = db_module._session_factory
    db_module._engine = engine
    db_module._session_factory = session_factory

    with patch("aether.config.settings.data_dir", data_dir):
        yield data_dir

    db_module._engine = original_engine
    db_module._session_factory = original_factory
    await engine.dispose()
