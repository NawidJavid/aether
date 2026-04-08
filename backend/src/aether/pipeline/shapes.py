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
    Cache hit: returns immediately. Cache miss: runs full Flux -> Trellis pipeline.
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

    await save_cache_entry(key, concept, str(bin_path), POINT_COUNT)
    return bin_path


async def _generate_image(concept: str, key: str) -> Path:
    image_path = settings.data_dir / "cache" / "images" / f"{key}.png"
    if image_path.exists():
        return image_path

    # Prompt engineered for Trellis 3D conversion: light object, black bg, 3D render
    prompt = (
        f"A {concept}, single solid object, white and light gray color, "
        "pure black background, three-quarter view angle, "
        "matte clay-like surface, soft studio lighting, "
        "clear strong silhouette, high contrast, "
        "no glow, no transparency, no particles, no text, no ground plane, "
        "clean 3D render, simple geometry"
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
