from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TTSResult:
    audio_path: Path
    duration_ms: int
    word_starts_ms: list[tuple[str, int]]


# Minimal valid MPEG1 Layer3 frame header (128kbps, 44100Hz, stereo)
# followed by zero-padded frame data. This is a single valid silent MP3 frame.
_SILENT_MP3 = (
    b"\xff\xfb\x90\x00" + b"\x00" * 413  # 417 bytes = one MPEG1 L3 128kbps frame
)


async def render_audio(text: str, output_dir: Path) -> TTSResult:
    """
    Stub TTS: writes a silent MP3 and generates fake word timestamps.
    Words are spaced at ~250ms intervals (4 words/sec).
    """
    audio_path = output_dir / "audio.mp3"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(_SILENT_MP3)

    words = text.split()
    word_starts_ms: list[tuple[str, int]] = [
        (word, i * 250) for i, word in enumerate(words)
    ]
    duration_ms = len(words) * 250

    return TTSResult(
        audio_path=audio_path,
        duration_ms=duration_ms,
        word_starts_ms=word_starts_ms,
    )
