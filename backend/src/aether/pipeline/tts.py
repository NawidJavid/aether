from __future__ import annotations

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
    return [(w["text"], int(w["start"] * 1000)) for w in words if w["text"].strip()]


def _extract_duration_ms(alignment: dict) -> int:
    """The end time of the last word, in ms."""
    words = alignment.get("words", [])
    if not words:
        return 0
    return int(words[-1]["end"] * 1000)
