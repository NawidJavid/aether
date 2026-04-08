from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import numpy as np
import pytest

from aether.db import create_job, get_job
from aether.models import JobStatus, ParsedScript, ScriptElement
from aether.pipeline.orchestrator import run_pipeline
from aether.pipeline.tts import TTSResult


def _make_script() -> ParsedScript:
    return ParsedScript(
        elements=[
            ScriptElement(kind="shape", concept="glowing brain"),
            ScriptElement(kind="say", text="AI is the field of building machines that think."),
            ScriptElement(kind="shape", concept="interconnected nodes"),
            ScriptElement(kind="say", text="Neural networks pass signals like neurons."),
            ScriptElement(kind="shape", concept="crystal sphere"),
            ScriptElement(kind="say", text="We are only at the beginning."),
        ],
        full_text=(
            "AI is the field of building machines that think. "
            "Neural networks pass signals like neurons. "
            "We are only at the beginning."
        ),
        unique_concepts=["glowing brain", "interconnected nodes", "crystal sphere"],
    )


def _make_tts_result(text: str, output_dir: Path) -> TTSResult:
    """Simulate ElevenLabs Forced Alignment tokenization: punctuation becomes separate tokens."""
    import re

    audio_path = output_dir / "audio.mp3"
    audio_path.write_bytes(b"\xff\xfb\x90\x00" * 10)  # minimal bytes
    # Split words and separate trailing/leading punctuation (mimics ElevenLabs)
    tokens: list[str] = []
    for word in text.split():
        parts = re.findall(r"[A-Za-z0-9']+|[^\s\w]", word)
        tokens.extend(parts)
    return TTSResult(
        audio_path=audio_path,
        duration_ms=len(tokens) * 200,
        word_starts_ms=[(t, i * 200) for i, t in enumerate(tokens)],
    )


def _make_shape_bin(data_dir: Path, concept: str) -> Path:
    from aether.pipeline.shapes import cache_key

    key = cache_key(concept)
    bin_path = data_dir / "cache" / "shapes" / f"{key}.bin"
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    pts = np.random.default_rng(42).random((30000, 3)).astype(np.float32)
    pts.tofile(bin_path)
    return bin_path


@pytest.mark.asyncio
async def test_full_pipeline(tmp_data_dir):
    """Run the full pipeline with mocked LLM and verify manifest output."""
    data_dir = tmp_data_dir
    script = _make_script()

    job = await create_job("What is AI?")

    async def mock_generate_script(topic):
        return script

    async def mock_render_audio(text, output_dir):
        return _make_tts_result(text, output_dir)

    async def mock_generate_shape(concept):
        return _make_shape_bin(data_dir, concept)

    with (
        patch("aether.pipeline.orchestrator.generate_script", side_effect=mock_generate_script),
        patch("aether.pipeline.orchestrator.render_audio", side_effect=mock_render_audio),
        patch("aether.pipeline.orchestrator.generate_shape", side_effect=mock_generate_shape),
    ):
        await run_pipeline(job.job_id, "What is AI?")

    result = await get_job(job.job_id)
    assert result is not None
    assert result.status == JobStatus.COMPLETED
    assert result.manifest is not None

    manifest = result.manifest
    assert manifest.topic == "What is AI?"
    assert len(manifest.shapes) == 3
    assert manifest.shapes[0].trigger_time_ms == 0  # First shape always at t=0
    assert manifest.shapes[0].concept == "glowing brain"
    assert manifest.shapes[1].concept == "interconnected nodes"
    assert manifest.shapes[2].concept == "crystal sphere"
    assert manifest.audio_duration_ms > 0

    # Verify manifest.json was written to disk
    manifest_dir = data_dir / "manifests" / str(manifest.manifest_id)
    manifest_json_path = manifest_dir / "manifest.json"
    assert manifest_json_path.exists()
    disk_manifest = json.loads(manifest_json_path.read_text())
    assert disk_manifest["topic"] == "What is AI?"
    assert len(disk_manifest["shapes"]) == 3


@pytest.mark.asyncio
async def test_pipeline_failure_marks_job_failed(tmp_data_dir):
    """If the LLM call fails, the job should be marked FAILED."""
    job = await create_job("failing topic")

    async def mock_generate_script(topic):
        raise RuntimeError("LLM unavailable")

    with patch("aether.pipeline.orchestrator.generate_script", side_effect=mock_generate_script):
        await run_pipeline(job.job_id, "failing topic")

    result = await get_job(job.job_id)
    assert result is not None
    assert result.status == JobStatus.FAILED
    assert "LLM unavailable" in result.error
