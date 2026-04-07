from __future__ import annotations

import hashlib

import numpy as np


def sphere(n: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform points inside a unit sphere."""
    # Rejection sampling
    points = []
    total = 0
    while total < n:
        batch = rng.uniform(-1, 1, size=(n * 2, 3))
        inside = batch[np.linalg.norm(batch, axis=1) <= 1.0]
        points.append(inside)
        total += len(inside)
    return np.concatenate(points)[:n]


def cube(n: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform points inside a unit cube centered at origin."""
    return rng.uniform(-1, 1, size=(n, 3))


def torus(n: int, rng: np.random.Generator) -> np.ndarray:
    """Points on a torus surface. R=0.6 (major), r=0.25 (minor)."""
    R, r = 0.6, 0.25
    theta = rng.uniform(0, 2 * np.pi, n)
    phi = rng.uniform(0, 2 * np.pi, n)
    x = (R + r * np.cos(phi)) * np.cos(theta)
    y = (R + r * np.cos(phi)) * np.sin(theta)
    z = r * np.sin(phi)
    return np.column_stack([x, y, z])


def helix(n: int, rng: np.random.Generator) -> np.ndarray:
    """Points along a double helix with slight radial noise."""
    t = np.linspace(0, 6 * np.pi, n // 2)
    noise = rng.normal(0, 0.03, size=(n // 2, 3))
    # Strand 1
    x1 = 0.4 * np.cos(t)
    y1 = np.linspace(-1, 1, n // 2)
    z1 = 0.4 * np.sin(t)
    strand1 = np.column_stack([x1, y1, z1]) + noise
    # Strand 2 (offset by pi)
    x2 = 0.4 * np.cos(t + np.pi)
    y2 = np.linspace(-1, 1, n // 2)
    z2 = 0.4 * np.sin(t + np.pi)
    strand2 = np.column_stack([x2, y2, z2]) + noise
    points = np.concatenate([strand1, strand2])
    # Pad if n is odd
    if len(points) < n:
        points = np.concatenate([points, points[:n - len(points)]])
    return points[:n]


def octahedron(n: int, rng: np.random.Generator) -> np.ndarray:
    """Points on the surface of a regular octahedron."""
    # 8 triangular faces with vertices at (+-1,0,0), (0,+-1,0), (0,0,+-1)
    verts = np.array([
        [1, 0, 0], [-1, 0, 0],
        [0, 1, 0], [0, -1, 0],
        [0, 0, 1], [0, 0, -1],
    ], dtype=np.float64)
    faces = [
        (0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2),
        (1, 2, 5), (1, 5, 3), (1, 3, 4), (1, 4, 2),
    ]
    per_face = n // len(faces)
    remainder = n - per_face * len(faces)
    points = []
    for i, (a, b, c) in enumerate(faces):
        count = per_face + (1 if i < remainder else 0)
        # Random barycentric coords
        r1 = rng.random(count)
        r2 = rng.random(count)
        mask = r1 + r2 > 1
        r1[mask] = 1 - r1[mask]
        r2[mask] = 1 - r2[mask]
        pts = (
            (1 - r1 - r2)[:, None] * verts[a]
            + r1[:, None] * verts[b]
            + r2[:, None] * verts[c]
        )
        points.append(pts)
    return np.concatenate(points)[:n]


_GENERATORS = [sphere, cube, torus, helix, octahedron]


def _normalize(points: np.ndarray) -> np.ndarray:
    """Center and scale to fit within unit sphere * 0.85."""
    points = points - points.mean(axis=0)
    max_dist = np.max(np.linalg.norm(points, axis=1))
    if max_dist > 0:
        points = points / max_dist
    return points * 0.85


def generate_procedural(concept: str, n_points: int) -> np.ndarray:
    """Pick a shape deterministically based on concept hash, return normalized points."""
    h = hashlib.sha256(concept.lower().encode()).hexdigest()
    idx = int(h, 16) % len(_GENERATORS)
    rng = np.random.default_rng(seed=int(h[:8], 16))
    points = _GENERATORS[idx](n_points, rng)
    return _normalize(points)
