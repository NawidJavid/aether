from __future__ import annotations

import numpy as np

from aether.pipeline.pointcloud import (
    sphere,
    cube,
    torus,
    helix,
    octahedron,
    generate_procedural,
    _normalize,
)

N = 1000


def test_sphere_shape():
    rng = np.random.default_rng(42)
    pts = _normalize(sphere(N, rng))
    assert pts.shape == (N, 3)
    assert np.max(np.linalg.norm(pts, axis=1)) <= 1.0 + 1e-6


def test_cube_shape():
    rng = np.random.default_rng(42)
    pts = _normalize(cube(N, rng))
    assert pts.shape == (N, 3)
    assert np.max(np.linalg.norm(pts, axis=1)) <= 1.0 + 1e-6


def test_torus_shape():
    rng = np.random.default_rng(42)
    pts = _normalize(torus(N, rng))
    assert pts.shape == (N, 3)
    assert np.max(np.linalg.norm(pts, axis=1)) <= 1.0 + 1e-6


def test_helix_shape():
    rng = np.random.default_rng(42)
    pts = _normalize(helix(N, rng))
    assert pts.shape == (N, 3)
    assert np.max(np.linalg.norm(pts, axis=1)) <= 1.0 + 1e-6


def test_octahedron_shape():
    rng = np.random.default_rng(42)
    pts = _normalize(octahedron(N, rng))
    assert pts.shape == (N, 3)
    assert np.max(np.linalg.norm(pts, axis=1)) <= 1.0 + 1e-6


def test_generate_procedural_deterministic():
    pts1 = generate_procedural("glowing brain", N)
    pts2 = generate_procedural("glowing brain", N)
    np.testing.assert_array_equal(pts1, pts2)


def test_generate_procedural_different_concepts():
    pts1 = generate_procedural("glowing brain", N)
    pts2 = generate_procedural("crystal sphere", N)
    # Different concepts may (but aren't guaranteed to) produce different shapes
    # At minimum, verify both produce valid output
    assert pts1.shape == (N, 3)
    assert pts2.shape == (N, 3)


def test_points_centered():
    pts = generate_procedural("test concept", N)
    center = pts.mean(axis=0)
    assert np.allclose(center, 0, atol=0.05)
