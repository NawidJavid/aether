from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import structlog

from aether.config import settings
from aether.db import update_job_status, save_job_manifest
from aether.models import JobStatus, Manifest, ParsedScript, ScheduledShape
from aether.pipeline.llm import generate_script
from aether.pipeline.shapes import generate_shape, cache_key
from aether.pipeline.tts import render_audio, TTSResult

log = structlog.get_logger()


async def run_pipeline(job_id: UUID, topic: str) -> None:
    try:
        await update_job_status(job_id, JobStatus.GENERATING_SCRIPT, "Writing the script...")
        script = await generate_script(topic)
        log.info(
            "script_generated",
            job_id=str(job_id),
            element_count=len(script.elements),
            concepts=script.unique_concepts,
        )

        await update_job_status(
            job_id, JobStatus.GENERATING_ASSETS, "Generating shapes and voice..."
        )

        manifest_id = uuid4()
        manifest_dir = settings.data_dir / "manifests" / str(manifest_id)
        manifest_dir.mkdir(parents=True, exist_ok=True)

        # Run TTS and shape generation concurrently
        tts_task = asyncio.create_task(render_audio(script.full_text, manifest_dir))
        shape_tasks = {
            concept: asyncio.create_task(generate_shape(concept))
            for concept in script.unique_concepts
        }

        tts_result: TTSResult = await tts_task
        shape_paths = {c: await t for c, t in shape_tasks.items()}

        await update_job_status(job_id, JobStatus.ASSEMBLING, "Assembling...")

        scheduled_shapes = _schedule_shapes(script, tts_result, shape_paths)

        manifest = Manifest(
            manifest_id=manifest_id,
            topic=topic,
            audio_url=f"/assets/manifests/{manifest_id}/audio.mp3",
            audio_duration_ms=tts_result.duration_ms,
            shapes=scheduled_shapes,
            full_text=script.full_text,
            created_at=datetime.now(timezone.utc),
        )

        (manifest_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2))

        await save_job_manifest(job_id, manifest)
        await update_job_status(job_id, JobStatus.COMPLETED, "Ready")

    except Exception as exc:
        log.exception("pipeline_failed", job_id=str(job_id))
        await update_job_status(job_id, JobStatus.FAILED, "", error=str(exc))


def _schedule_shapes(
    script: ParsedScript,
    tts: TTSResult,
    shape_paths: dict[str, Path],
) -> list[ScheduledShape]:
    """
    Walks the script in order. Each shape cue gets a trigger time corresponding
    to the START of the next spoken word after it in the audio. The first shape
    triggers at t=0 so the cloud forms the topic shape BEFORE the voice begins.
    """
    word_index = 0
    word_starts = tts.word_starts_ms
    scheduled: list[ScheduledShape] = []
    pending_say: list[str] = []

    for element in script.elements:
        if element.kind == "shape":
            # Attach accumulated say text to the previous shape
            if scheduled and pending_say:
                scheduled[-1].subtitle = " ".join(pending_say)
                pending_say = []

            assert element.concept is not None
            trigger_ms = word_starts[word_index][1] if word_index < len(word_starts) else 0
            if not scheduled:
                trigger_ms = 0  # First shape ALWAYS at t=0

            key = cache_key(element.concept)
            scheduled.append(
                ScheduledShape(
                    concept=element.concept,
                    point_cloud_url=f"/assets/cache/shapes/{key}.bin",
                    point_count=30000,
                    trigger_time_ms=trigger_ms,
                    morph_duration_ms=1500,
                )
            )
        elif element.kind == "say":
            assert element.text is not None
            pending_say.append(element.text)
            word_index += len(element.text.split())

    # Attach remaining say text to the last shape
    if scheduled and pending_say:
        scheduled[-1].subtitle = " ".join(pending_say)

    return scheduled
