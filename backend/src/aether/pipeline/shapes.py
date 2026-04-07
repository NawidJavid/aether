from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from aether.config import settings
from aether.db import lookup_cache, save_cache_entry
from aether.pipeline.pointcloud import generate_procedural

POINT_COUNT = 30000


def cache_key(concept: str) -> str:
    """Stable hash for a concept. Lowercased, whitespace-normalized."""
    normalized = " ".join(concept.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


async def generate_shape(concept: str) -> Path:
    """
    Returns path to a .bin file containing 30000 xyz floats (Float32).
    Stub implementation: uses procedural point clouds instead of Flux+Trellis.
    """
    key = cache_key(concept)
    bin_path = settings.data_dir / "cache" / "shapes" / f"{key}.bin"

    cached = await lookup_cache(key)
    if cached and bin_path.exists():
        return bin_path

    points = generate_procedural(concept, POINT_COUNT)

    bin_path.parent.mkdir(parents=True, exist_ok=True)
    points.astype(np.float32).tofile(bin_path)

    await save_cache_entry(key, concept, str(bin_path), POINT_COUNT)
    return bin_path
