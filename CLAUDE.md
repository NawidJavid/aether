# CLAUDE.md — Aether

> A generative cinematic explainer. Type a topic, wait ~60 seconds, watch a 3D particle cloud morph through visual concepts in perfect sync with a narrated explanation.

This file is the project overview and the source of truth for what Aether is and how to build it. **Detailed implementation guidance lives in `.claude/rules/` and loads automatically when you work on files in matching directories.** Start here, follow the build order, let the rules attach themselves to the right phases.

## What we're building

A web app where the user types a topic into a single input box, waits 30–90 seconds while a "thinking" loader plays, then watches a black canvas filled with ~30,000 glowing blue particles morph through 5–10 recognizable shapes (a glowing brain, interconnected nodes, a layered geometric mesh, and so on), perfectly synchronized with a high-quality voice narration that explains the topic in 60–90 seconds. The particles breathe and pulse with the audio. When the explanation ends, the cloud settles into a final memorable form.

The bar is **"people see this and screenshot it,"** not "it works." This is meant to be portfolio-quality and shareable.

## What this is NOT (out of scope for v1)

- Real-time voice loop / live conversation
- Multi-user / accounts / auth
- Sharing URLs or gallery features
- Local model inference (we use APIs only)
- Mobile / responsive UI
- Multiple voice options or settings panels
- Export to MP4 / embed widgets

Resist these mercilessly. Every one of them will tempt you. Ship v1 first.

## Non-negotiable design principles

1. **Quality over speed.** Pre-rendered batch pipeline, not real-time. Take 90 seconds to make something stunning rather than 10 to make something mid.
2. **The aesthetic is the product.** A perfect pipeline producing ugly visuals is a failed project. Gate ruthlessly on Milestone 1.
3. **Concrete over abstract.** The LLM rewrites every abstract concept into a physical, photographable object *before* it hits the shape generator. "Recursion" → "russian nesting dolls". No exceptions.
4. **Pre-render everything.** Audio rendered in one shot with timestamps. Shapes generated in parallel ahead of time. Playback is deterministic scheduling, not a live pipeline.
5. **Cache aggressively.** Same concept hash = no regeneration.
6. **No infrastructure.** SQLite + filesystem. Zero servers, zero containers in v1.
7. **One provider per concern.** One LLM, one TTS, one shape generator. Clean function boundaries, not provider abstractions.
8. **Ship the thing.** No accounts, settings, themes, i18n, telemetry. The "Out of scope" list above is non-negotiable.

## Tech stack

**Backend:** Python 3.11+, FastAPI, `anthropic`, `elevenlabs`, `fal-client`, `trimesh`, `numpy`, SQLAlchemy 2.x async + `aiosqlite`, Pydantic v2, `structlog`, `pytest`.

**Frontend:** Vite, React 18, TypeScript strict, Three.js (vanilla — NOT React Three Fiber), Tailwind CSS, Zustand. No UI library (no shadcn, no Material).

**External services:**
- Anthropic API — model `claude-opus-4-6`
- ElevenLabs — model `eleven_multilingual_v2`, streaming-with-timestamps endpoint
- fal.ai — `fal-ai/flux-pro/v1.1` (text→image) and `fal-ai/trellis` (image→3D)

**Storage:** SQLite for metadata, local filesystem for blobs.

## Architecture flow

```
User submits topic
        │
        ▼
┌─────────────────┐
│ Claude Opus 4.6 │  →  interleaved <say>/<shape> script
└────────┬────────┘
         │
   Parse script
         │
         ├─────────────────────┐
         ▼                     ▼
┌────────────────┐   ┌──────────────────────┐
│  ElevenLabs    │   │  Per concept (parallel):
│  full audio +  │   │   1. Cache check
│  timestamps    │   │   2. Flux Pro 1.1 → image
└───────┬────────┘   │   3. Trellis → mesh
        │            │   4. trimesh sample → point cloud
        │            │   5. Save .bin
        │            └──────────┬───────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
         Assemble manifest:
         - audio_url
         - shapes[]: { url, trigger_time_ms }
         - script
                    │
                    ▼
         Frontend polls, downloads,
         plays it back deterministically
```

**Key insight:** shape morphs trigger at exact word timestamps from the pre-rendered TTS. Each `<shape>` cue in the parsed script is positioned between two `<say>` blocks; we map it to the start time of the next word in the audio. Sync is a scheduling problem, not a live loop.

## Build order — DO IT IN THIS ORDER

The order is intentional. It front-loads the highest-risk task (visual aesthetic) so we discover failure early instead of after building the whole pipeline.

| # | Milestone | Evenings | Gate |
|---|---|---|---|
| 0 | Project skeleton | 1 | Both dev servers running |
| 1 | **PARTICLE AESTHETIC GATE** ⚠️ | 2-3 | Does the morph make you feel something? |
| 2 | Backend pipeline with stubs | 1-2 | Manifest returns valid shape count + timing |
| 3 | Frontend e2e with stub backend | 1-2 | Stub shapes morph in time with stub audio |
| 4 | Real TTS | 1 | Shapes land on the right spoken words |
| 5 | Real shape generation | 2-3 | Shapes recognizable, cache hits work |
| 6 | Polish + README | open | Hero GIF recorded |

**Milestone 1 is the project's go/no-go moment.** Do not proceed past it until the particle aesthetic looks beautiful. If it doesn't after 3 evenings of tuning, stop and reassess — the project is in trouble.

Use the `/milestone N` slash command to plan and execute each milestone in turn. See `.claude/commands/milestone.md`.

## Key technical decisions

### Why text → image → 3D, not text → 3D directly
Text-to-image models (Flux Pro 1.1) are vastly more capable than direct text-to-3D models. Generating a clean isolated image with a carefully crafted prompt template gives much higher quality 3D output from Trellis than any direct text-to-3D pipeline. The image step is 1-2 seconds and well worth it.

### Why concrete visual metaphors are non-negotiable
3D generators have no concept of abstraction. "Recursion" produces a blob. "Russian nesting dolls" produces nesting dolls. The LLM system prompt enforces this rewriting at script generation time. **If shapes come out blob-shaped, the first thing to check is whether the LLM is actually rewriting abstract concepts.** This is the single most common failure mode.

### Why random correspondence in morphs, not optimal transport
Optimal transport between two point clouds is mathematically "correct" but visually boring. Random correspondence with strong curl noise looks like the cloud explodes and reforms — the actual Jarvis aesthetic. **Use random.**

### Why pre-render everything
Streaming would let playback start faster but makes word-level shape sync nearly impossible. Pre-rendering means by the time playback starts, we have the complete audio file, all word timings, and every point cloud loaded into memory. The scheduler is purely deterministic. This is what makes the sync feel magical.

### Why first shape always triggers at t=0
So the cloud forms into the topic's iconic shape *before* the voice begins speaking. Without this, the user sees a generic blob for the first second. Always force `trigger_time_ms = 0` for the first scheduled shape.

### Why vanilla Three.js, not React Three Fiber
R3F's reconciler abstracts away the GPU-level control we need. The particle system uses custom shaders, custom buffer attributes updated 60 times per second, and direct uniform writes. Vanilla Three.js inside a React `useEffect` is the right call.

### Why SQLite + filesystem, not Postgres / Redis / S3
Single-user local app. SQLite has zero setup, the data is portable as a single file, can be deleted to fully reset state. Use the `aiosqlite` driver to keep all DB calls async.

### Why FastAPI BackgroundTasks, not Celery / ARQ
The pipeline is bottlenecked entirely on external API calls, which are async-friendly. Single in-process worker is sufficient for v1.

### Per-generation cost estimate
~$0.75 per fresh explanation: Trellis $0.14 + Flux Pro $0.28 + ElevenLabs $0.30 + Claude Opus $0.05. Cached repeats are essentially free. Iterate freely.

## Commands cheat sheet

```bash
# Backend dev
cd backend && source .venv/bin/activate && uvicorn aether.main:app --reload

# Frontend dev
cd frontend && npm run dev

# Backend tests
cd backend && pytest -v

# Backend lint + format
cd backend && ruff check . && ruff format .

# Frontend lint + format
cd frontend && npm run lint && npm run format

# Full reset (delete all generated data)
rm -rf backend/data && mkdir -p backend/data/cache/{shapes,meshes,images} backend/data/manifests
```

## Where to find detailed guidance

This file is a lean overview. Detailed implementation guidance lives in `.claude/rules/` and **loads automatically** when you read files in matching directories — you don't have to point at the rules manually.

| Working on... | Auto-loads |
|---|---|
| Anything in `backend/` | `.claude/rules/backend.md` — directory structure, env setup, data models, API endpoints, DB schema |
| Files in `backend/src/aether/pipeline/**` | `.claude/rules/backend-pipeline.md` — Claude system prompt, LLM/TTS/shapes/orchestrator implementations |
| Files in `frontend/src/particle/**` | `.claude/rules/frontend-particle.md` — particle system, GLSL shaders, renderer, audio analyzer |
| Files in `frontend/src/components/**` or `frontend/src/playback/**` | `.claude/rules/frontend-app.md` — components, Zustand store, playback scheduler |

The path-scoped rule mechanism is documented at https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/. Trust it — when Claude Code reads a backend file, the backend rules appear in context. When it reads a particle file, the particle rules appear. You just follow the build order and let the rules attach themselves to the right phases.

If you ever need to check what's loaded in a given session, run `/memory` inside Claude Code.
