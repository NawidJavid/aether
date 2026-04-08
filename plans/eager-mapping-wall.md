# Milestone 5 — Real Shape Generation

## Context

The shape generation pipeline currently uses procedural point clouds (sphere, cube, torus, helix, octahedron) as stubs. This milestone replaces the stub with the real **Flux Pro 1.1 (text-to-image) -> Trellis (image-to-3D)** pipeline via fal.ai, producing recognizable shapes from concept descriptions like "glowing human brain" or "interconnected nodes".

The orchestrator already calls `generate_shape(concept) -> Path` with the correct interface and runs all concepts in parallel. The function signature does not change — only the internal implementation.

## Plan

### Step 1: Modify `backend/src/aether/pipeline/shapes.py`

**This is the only production file that changes.** Replace the stub with the real Flux -> Trellis -> trimesh pipeline.

Changes:
- **Remove** `from aether.pipeline.pointcloud import generate_procedural`
- **Add** imports: `fal_client`, `httpx`, `trimesh`
- **Replace** the body of `generate_shape()` after the cache check: call `_generate_image()` -> `_generate_mesh()` -> `_sample_mesh()` instead of `generate_procedural()`
- **Add** three new private functions (from `.claude/rules/backend-pipeline.md` lines 324-407):
  - `_generate_image(concept, key)` — Flux Pro 1.1 via `fal_client.subscribe_async()`, saves PNG to `data/cache/images/{key}.png`
  - `_generate_mesh(image_path, key)` — uploads image via `fal_client.upload_file_async()`, Trellis via `fal_client.subscribe_async()`, saves GLB to `data/cache/meshes/{key}.glb`
  - `_sample_mesh(mesh_path, n_points)` — `trimesh.load()` + `sample_surface()` + normalize to unit sphere * 0.85

**Important detail:** The rules file shows `save_cache_entry(key, concept, str(bin_path))` with 3 args, but the actual DB function takes 4 args including `point_count`. Keep the existing 4-arg call: `save_cache_entry(key, concept, str(bin_path), POINT_COUNT)`.

**Intermediate caching:** Both `_generate_image` and `_generate_mesh` check if their output file exists on disk before calling the API, so a retry after partial failure skips already-completed steps.

### Step 2: Run existing tests

```bash
cd backend && pytest -v
```

All three test files should pass unchanged:
- `test_orchestrator.py` — mocks `generate_shape` at orchestrator import level
- `test_llm_parser.py` — independent of shapes
- `test_pointcloud.py` — tests `pointcloud.py` directly (file kept, just no longer imported by production code)

### Step 3: Manual end-to-end test (requires FAL_KEY)

1. Ensure `FAL_KEY` is set in `backend/.env`
2. Start backend: `cd backend && uvicorn aether.main:app --reload`
3. Generate: `curl -X POST http://127.0.0.1:8000/api/generate -H "Content-Type: application/json" -d '{"topic":"What is artificial intelligence?"}'`
4. Poll until completed, then verify:
   - Shapes are recognizable (brain, network, etc.)
   - `.bin` files are 360,000 bytes each (30000 * 3 * 4)
   - Intermediate `.png` and `.glb` files exist in cache dirs
5. Generate same topic again — should complete much faster (cache hits, no fal.ai calls)

## Files

| File | Action | Description |
|------|--------|-------------|
| `backend/src/aether/pipeline/shapes.py` | **Modify** | Replace procedural stub with real Flux -> Trellis pipeline |
| `backend/src/aether/pipeline/pointcloud.py` | Keep | No longer imported by production code; kept for tests |
| `backend/src/aether/pipeline/orchestrator.py` | No change | Already uses correct `generate_shape()` interface |
| `backend/src/aether/db.py` | No change | `lookup_cache` / `save_cache_entry` already work |
| `backend/src/aether/config.py` | No change | `fal_key` field exists; fal-client reads `FAL_KEY` from env |
| `backend/pyproject.toml` | No change | `fal-client`, `trimesh`, `httpx`, `numpy` already installed |

## Key reference

The exact production code is in `.claude/rules/backend-pipeline.md` lines 279-408. Follow it closely, with the one correction to `save_cache_entry` (4 args, not 3).

## Verification

1. `cd backend && pytest -v` — all existing tests pass
2. Generate "What is artificial intelligence?" via the API — shapes should be recognizable, not blobs
3. Generate same topic again — cache hit, no API calls, fast completion
4. Check `data/cache/images/`, `data/cache/meshes/`, `data/cache/shapes/` for intermediate and final artifacts
