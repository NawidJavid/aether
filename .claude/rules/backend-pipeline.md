---
paths:
  - "backend/src/aether/pipeline/**"
  - "backend/src/aether/prompts/**"
---

# Aether — Pipeline implementation rules

These rules load automatically when you work on any file in `backend/src/aether/pipeline/` or `backend/src/aether/prompts/`. They cover the LLM call (with the full Claude system prompt), the TTS pipeline, the shape generation pipeline, and the orchestrator.

## The Claude system prompt — `prompts/script_writer.txt`

**THIS IS THE SINGLE MOST IMPORTANT ARTIFACT IN THE ENTIRE PROJECT.** Get this right and everything downstream works. Copy the text below verbatim into `backend/src/aether/prompts/script_writer.txt`. Do not paraphrase, do not "improve", do not summarize.

```
You are the script writer for Aether, a generative cinematic explainer that turns any topic into a 60-90 second voice narration synchronized with morphing 3D particle visuals.

## Your task

Given a topic the user wants to learn about, write a clear, engaging 200-300 word explanation, with shape cues marking exactly when the visual particle cloud should morph into a new form.

## Output format

You output a structured script with two interleaved element types:

<shape concept="..."/>     — a cue for the particles to morph into a new shape
<say>...</say>             — text the narrator will speak aloud

Example output for the topic "What is artificial intelligence?":

<shape concept="glowing human brain"/>
<say>Artificial intelligence is the field of building machines that can think, reason, and learn from experience.</say>
<shape concept="interconnected glowing nodes"/>
<say>At the heart of modern AI are neural networks: vast webs of simple computing units that pass signals to each other, much like the neurons in your own mind.</say>
<shape concept="layered geometric mesh"/>
<say>These networks learn by adjusting the strength of their connections, slowly tuning themselves to recognize patterns hidden in mountains of data.</say>
<shape concept="robotic humanoid figure"/>
<say>The result is software that can recognize faces, translate languages, drive cars, and even hold conversations like this one.</say>
<shape concept="glowing crystal sphere"/>
<say>And we are still only at the beginning of understanding what these systems can ultimately become.</say>

## HARD RULES — VIOLATING ANY OF THESE BREAKS THE PIPELINE

### 1. CONCRETE VISUAL METAPHORS ONLY

Each shape concept MUST describe a physical, photographable object. The downstream pipeline turns this concept into a 3D model. If the concept is abstract, the model will fail and the user will see a blob.

EXAMPLES:
- "consciousness"        BAD  →  "glowing human brain"        GOOD
- "recursion"            BAD  →  "russian nesting dolls"      GOOD
- "love"                 BAD  →  "anatomical heart"           GOOD
- "time"                 BAD  →  "antique pocket watch"       GOOD
- "freedom"              BAD  →  "soaring eagle"              GOOD
- "infinity"             BAD  →  "ouroboros snake ring"       GOOD
- "the economy"          BAD  →  "stack of gold coins"        GOOD

If you can't take a photograph of it with a camera, it's not a valid concept.

### 2. PACING

One shape change per 12-20 spoken words (roughly every 5-8 seconds of speech). Never change shapes mid-sentence — always at sentence boundaries.

### 3. LENGTH

Total spoken text: 200-300 words. (This produces a 60-90 second audio file.)

### 4. SHAPE COUNT

5-10 shape cues total, including the opening one.

### 5. STRUCTURE

- ALWAYS begin with a `<shape>` cue before the first `<say>`. The opening shape should be the most iconic visual representation of the topic.
- ALWAYS end with a final `<shape>` cue followed by a final `<say>` that lands the explanation memorably.

### 6. SHAPE DESCRIPTIONS

2-5 words. One clear physical object with one or two adjectives. Examples: "glowing brain", "interconnected nodes", "DNA double helix", "antique pocket watch", "burning candle", "robotic humanoid figure". Never describe scenes, multiple objects, or backgrounds.

### 7. TONE

Conversational but precise, like Brian Cox or 3Blue1Brown narration. Avoid jargon unless you immediately explain it. Flowing prose only — no bullet points, no lists, no headers.

### 8. OUTPUT ONLY THE STRUCTURED SCRIPT

No preamble. No closing remarks. No markdown headers. No explanation of your process. The first character of your output must be `<` and the last character must be `>`.

## Topic

{topic}
```

The orchestrator loads this file at module-import time and substitutes `{topic}` at call time. If the prompt is ever modified, it should be done by editing this file directly, not by string-replacing in code.

## LLM call (`pipeline/llm.py`)

```python
import re
from pathlib import Path

from anthropic import AsyncAnthropic

from aether.config import settings
from aether.models import ParsedScript, ScriptElement

_PROMPT_TEMPLATE = (Path(__file__).parent.parent / "prompts" / "script_writer.txt").read_text()

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

# Captures interleaved <shape concept="..."/> and <say>...</say>
_ELEMENT_RE = re.compile(
    r'<shape\s+concept="([^"]+)"\s*/>|<say>(.*?)</say>',
    re.DOTALL,
)


async def generate_script(topic: str) -> ParsedScript:
    prompt = _PROMPT_TEMPLATE.replace("{topic}", topic)

    # Use streaming because Opus 4.6 with reasonable max_tokens benefits from it
    # and the SDK requires streaming for large max_tokens to avoid HTTP timeouts.
    async with _client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = await stream.get_final_message()

    raw = message.content[0].text.strip()
    return _parse_script(raw)


def _parse_script(raw: str) -> ParsedScript:
    elements: list[ScriptElement] = []
    say_chunks: list[str] = []
    seen_concepts: list[str] = []

    for match in _ELEMENT_RE.finditer(raw):
        shape_concept, say_text = match.group(1), match.group(2)
        if shape_concept is not None:
            concept = shape_concept.strip()
            elements.append(ScriptElement(kind="shape", concept=concept))
            if concept not in seen_concepts:
                seen_concepts.append(concept)
        elif say_text is not None:
            cleaned = " ".join(say_text.split())
            elements.append(ScriptElement(kind="say", text=cleaned))
            say_chunks.append(cleaned)

    if not elements or elements[0].kind != "shape":
        raise ValueError("Script must start with a <shape> cue")
    if not any(e.kind == "say" for e in elements):
        raise ValueError("Script has no <say> elements")

    return ParsedScript(
        elements=elements,
        full_text=" ".join(say_chunks),
        unique_concepts=seen_concepts,
    )
```

## TTS pipeline (`pipeline/tts.py`)

ElevenLabs has two endpoints we use together:

1. **Text to Speech** (`/v1/text-to-speech/{voice_id}`) — generates the MP3 audio
2. **Forced Alignment** (`/v1/forced-alignment`) — takes the finished audio + original text, returns precise word-level and character-level timestamps

We use both because Forced Alignment gives noticeably more accurate word timings than the inline timestamps the TTS-with-timestamps endpoint returns. Since the entire architectural premise of Aether is "pre-render so we can achieve word-perfect sync," we use the dedicated alignment tool. The two calls run sequentially inside `render_audio()` (alignment depends on the audio existing), but the whole sequence runs in parallel with shape generation in the orchestrator, so it doesn't slow the overall pipeline.

Required ElevenLabs permissions for your API key: Text to Speech (Access), Forced Alignment (Access), Voices (Read).

import base64
from dataclasses import dataclass
from pathlib import Path

import httpx

from aether.config import settings


@dataclass
class TTSResult:
    audio_path: Path
    duration_ms: int
    word_starts_ms: list[tuple[str, int]]


async def render_audio(text: str, output_dir: Path) -> TTSResult:
    """
    Two-step pipeline:
      1. Generate audio with the regular TTS endpoint
      2. Run Forced Alignment over the finished audio + original text
         to get precise word-level timestamps
    """
    audio_path = output_dir / "audio.mp3"
    audio_bytes = await _synthesize(text)
    audio_path.write_bytes(audio_bytes)

    alignment = await _force_align(audio_bytes, text)
    word_starts_ms = _extract_word_starts(alignment)
    duration_ms = _extract_duration_ms(alignment)

    return TTSResult(
        audio_path=audio_path,
        duration_ms=duration_ms,
        word_starts_ms=word_starts_ms,
    )


async def _synthesize(text: str) -> bytes:
    """Step 1: Generate the audio. We discard ElevenLabs' inline timestamps."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.content


async def _force_align(audio_bytes: bytes, text: str) -> dict:
    """
    Step 2: Get precise word/character timing from Forced Alignment.

    Endpoint: POST /v1/forced-alignment
    Format: multipart/form-data with `file` (audio) and `text` (plain string).
    """
    url = "https://api.elevenlabs.io/v1/forced-alignment"
    headers = {"xi-api-key": settings.elevenlabs_api_key}
    files = {"file": ("audio.mp3", audio_bytes, "audio/mpeg")}
    data = {"text": text}

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        return response.json()


def _extract_word_starts(alignment: dict) -> list[tuple[str, int]]:
    """
    Forced Alignment returns a `words` array with start/end times in seconds.
    We convert to (word, start_ms) tuples — same shape the scheduler expects.
    """
    words = alignment.get("words", [])
    return [(w["text"], int(w["start"] * 1000)) for w in words]


def _extract_duration_ms(alignment: dict) -> int:
    """The end time of the last word, in ms."""
    words = alignment.get("words", [])
    if not words:
        return 0
    return int(words[-1]["end"] * 1000)

```

## Shape generation (`pipeline/shapes.py`)

The most expensive part of the pipeline. Runs in parallel with TTS, and parallel across concepts within itself.

Use `fal_client.subscribe_async()` — NOT the older `submit_async` + `handler.get()` pattern. The Trellis schema is confirmed: takes `image_url`, returns `model_mesh.url` pointing at a GLB. Pricing is $0.02 per generation. The fal docs example response sometimes shows `content_type: "image/png"` for the mesh — that's a docs copy-paste error from another model, the actual file is a GLB.

```python
import hashlib
from pathlib import Path

import fal_client
import httpx
import numpy as np
import trimesh

from aether.config import settings
from aether.db import lookup_cache, save_cache_entry


POINT_COUNT = 30000


def cache_key(concept: str) -> str:
    """Stable hash for a concept. Lowercased, whitespace-normalized."""
    normalized = " ".join(concept.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


async def generate_shape(concept: str) -> Path:
    """
    Returns the path to a .bin file containing 30000 xyz floats (Float32).
    Cache hit: returns immediately. Cache miss: runs full Flux → Trellis pipeline.
    """
    key = cache_key(concept)
    bin_path = settings.data_dir / "cache" / "shapes" / f"{key}.bin"

    cached = await lookup_cache(key)
    if cached and bin_path.exists():
        return bin_path

    image_path = await _generate_image(concept, key)
    mesh_path = await _generate_mesh(image_path, key)
    points = _sample_mesh(mesh_path, POINT_COUNT)

    bin_path.parent.mkdir(parents=True, exist_ok=True)
    points.astype(np.float32).tofile(bin_path)

    await save_cache_entry(key, concept, str(bin_path))
    return bin_path


async def _generate_image(concept: str, key: str) -> Path:
    image_path = settings.data_dir / "cache" / "images" / f"{key}.png"
    if image_path.exists():
        return image_path

    # Carefully crafted prompt for clean 3D-friendly silhouettes
    prompt = (
        f"A {concept}, isolated centered single object, "
        "pure black background, dramatic studio lighting, "
        "sharp clear silhouette, simple iconic form, "
        "no text, no shadows, photographic"
    )

    result = await fal_client.subscribe_async(
        "fal-ai/flux-pro/v1.1",
        arguments={
            "prompt": prompt,
            "image_size": "square_hd",
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 1,
        },
    )
    image_url = result["images"][0]["url"]

    image_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient() as client:
        resp = await client.get(image_url)
        resp.raise_for_status()
        image_path.write_bytes(resp.content)

    return image_path


async def _generate_mesh(image_path: Path, key: str) -> Path:
    mesh_path = settings.data_dir / "cache" / "meshes" / f"{key}.glb"
    if mesh_path.exists():
        return mesh_path

    image_url = await fal_client.upload_file_async(str(image_path))

    # NOTE: Trellis returns a GLB mesh in model_mesh.url despite what
    # the fal docs example response sometimes claims (it's a docs bug).
    result = await fal_client.subscribe_async(
        "fal-ai/trellis",
        arguments={
            "image_url": image_url,
            "ss_guidance_strength": 7.5,
            "ss_sampling_steps": 12,
            "slat_guidance_strength": 3.0,
            "slat_sampling_steps": 12,
            "mesh_simplify": 0.95,
            "texture_size": 1024,
        },
    )
    glb_url = result["model_mesh"]["url"]

    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient() as client:
        resp = await client.get(glb_url)
        resp.raise_for_status()
        mesh_path.write_bytes(resp.content)

    return mesh_path


def _sample_mesh(mesh_path: Path, n_points: int) -> np.ndarray:
    """Uniform surface sampling, normalized to fit in a unit sphere centered at origin."""
    mesh = trimesh.load(mesh_path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)

    points, _ = trimesh.sample.sample_surface(mesh, n_points)

    # Center
    points = points - points.mean(axis=0)
    # Scale to unit sphere
    max_dist = np.max(np.linalg.norm(points, axis=1))
    if max_dist > 0:
        points = points / max_dist
    # Slight scale-down so the cloud doesn't fill the whole viewport
    points = points * 0.85

    return points
```

## Orchestrator (`pipeline/orchestrator.py`)

Ties everything together. Catches exceptions and marks job as FAILED. Updates job status at each phase so the frontend can poll for progress.

```python
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import structlog

from aether.config import settings
from aether.db import update_job_status, save_job_manifest
from aether.models import (
    JobStatus, Manifest, ParsedScript, ScheduledShape
)
from aether.pipeline.llm import generate_script
from aether.pipeline.shapes import generate_shape, cache_key
from aether.pipeline.tts import render_audio, TTSResult

log = structlog.get_logger()


async def run_pipeline(job_id: UUID, topic: str) -> None:
    try:
        await update_job_status(job_id, JobStatus.GENERATING_SCRIPT, "Writing the script...")
        script = await generate_script(topic)
        log.info("script_generated", job_id=str(job_id),
                 element_count=len(script.elements),
                 concepts=script.unique_concepts)

        await update_job_status(job_id, JobStatus.GENERATING_ASSETS,
                                "Generating shapes and voice...")

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

    for element in script.elements:
        if element.kind == "shape":
            assert element.concept is not None
            trigger_ms = word_starts[word_index][1] if word_index < len(word_starts) else 0
            if not scheduled:
                trigger_ms = 0  # First shape ALWAYS at t=0

            key = cache_key(element.concept)
            scheduled.append(ScheduledShape(
                concept=element.concept,
                point_cloud_url=f"/assets/cache/shapes/{key}.bin",
                point_count=30000,
                trigger_time_ms=trigger_ms,
                morph_duration_ms=1500,
            ))
        elif element.kind == "say":
            assert element.text is not None
            word_index += len(element.text.split())

    return scheduled
```

## Pipeline gotchas

- The Anthropic SDK requires streaming for reasonable `max_tokens` to avoid HTTP timeouts. Use `messages.stream()` + `get_final_message()`.
- Adaptive thinking (`thinking={"type": "adaptive"}`) is the recommended mode for Opus 4.6 — it lets the model decide how much to reason.
- When parsing the script, if the regex doesn't find ANY elements, the LLM probably wrapped the output in markdown or added preamble. The system prompt is explicit about not doing this; if it happens, log the raw output and inspect.
- Trellis output is a GLB even though fal docs sometimes show png content_type — that's a docs bug.
- Always force `trigger_time_ms = 0` for the first scheduled shape so the cloud forms before the voice begins.
- TTS now happens in two phases: synthesis (returns raw MP3) followed by Forced Alignment (returns word/character timings). Both use the same xi-api-key header, but Forced Alignment is multipart/form-data while synthesis is JSON. Don't accidentally send the alignment text wrapped in JSON — the docs are explicit that it must be a plain form field.

