from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TTSResult:
    audio_path: Path
    duration_ms: int
    word_starts_ms: list[tuple[str, int]]


def _generate_silent_wav(duration_ms: int) -> bytes:
    """Generate a valid silent WAV file of the given duration."""
    sample_rate = 44100
    channels = 1
    bits_per_sample = 16
    num_samples = int(sample_rate * duration_ms / 1000)
    data_size = num_samples * channels * (bits_per_sample // 8)

    header = struct.pack('<4sI4s', b'RIFF', 36 + data_size, b'WAVE')
    fmt = struct.pack('<4sIHHIIHH', b'fmt ', 16, 1, channels, sample_rate,
                      sample_rate * channels * (bits_per_sample // 8),
                      channels * (bits_per_sample // 8), bits_per_sample)
    data = struct.pack('<4sI', b'data', data_size)

    return header + fmt + data + b'\x00' * data_size


async def render_audio(text: str, output_dir: Path) -> TTSResult:
    """
    Stub TTS: writes a silent WAV and generates fake word timestamps.
    Words are spaced at ~250ms intervals (4 words/sec).
    """
    audio_path = output_dir / "audio.mp3"
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    words = text.split()
    duration_ms = len(words) * 250

    audio_path.write_bytes(_generate_silent_wav(duration_ms))

    word_starts_ms: list[tuple[str, int]] = [
        (word, i * 250) for i, word in enumerate(words)
    ]

    return TTSResult(
        audio_path=audio_path,
        duration_ms=duration_ms,
        word_starts_ms=word_starts_ms,
    )
