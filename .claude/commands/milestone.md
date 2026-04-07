---
description: Plan and execute a specific Aether milestone (use as /milestone 0, /milestone 1, etc.)
---

# Aether Milestone $ARGUMENTS

You are working on the **Aether** project — a generative cinematic explainer that turns text prompts into 3D particle morphing visualizations synced to TTS narration.

## Required reading

If you have not already read it this session, read `CLAUDE.md` in the project root **end to end** before doing anything else. It contains the project overview, design principles, build order, and key technical decisions.

**Detailed implementation guidance lives in `.claude/rules/`**, organized by area:
- `.claude/rules/backend.md` — backend directory structure, models, API, DB
- `.claude/rules/backend-pipeline.md` — Claude system prompt, LLM/TTS/shapes/orchestrator code
- `.claude/rules/frontend-particle.md` — particle system, GLSL shaders, renderer
- `.claude/rules/frontend-app.md` — components, store, playback scheduler

These rule files **load automatically** when you read files in matching directories. For Milestones 1+ where you'll be reading existing project files during planning, the relevant rules will appear in your context as soon as you start reading. **For Milestone 0 (where there are no files yet), you should manually read the relevant rule files during the planning phase.**

## The milestone you are working on: **$ARGUMENTS**

If the user typed `/milestone` without a number, ask them which milestone they want and stop.

### Milestone 0 — Project skeleton

**Manually read:** `.claude/rules/backend.md` and `.claude/rules/frontend-app.md` (no project files exist yet to trigger auto-loading).

**Goal:** Both directories created, dependencies installed, FastAPI hello world responding on port 8000, Vite React-TS template responding on port 5173. No business logic yet.

**Deliverable check:** I should be able to run `uvicorn aether.main:app --reload` in one terminal and `npm run dev` in another, hit both URLs, and see the hello world / black screen.

### Milestone 1 — PARTICLE AESTHETIC GATE ⚠️ ULTRATHINK ⚠️

**This is the highest-stakes design moment in the entire project. Ultrathink during the planning phase.**

**Manually read:** `.claude/rules/frontend-particle.md` carefully. This rule contains the particle system class, GLSL shaders, renderer setup, audio analyzer, and the aesthetic tuning checklist.

**Goal:** A standalone Three.js particle system rendering 30,000 particles morphing between two procedurally generated point clouds (sphere and cube) on a 3-second loop. Curl noise turbulence, UnrealBloomPass, soft circular point sprites, audio-reactive amplitude pulse stub (sine wave input). NO backend integration. NO React UI beyond a single canvas.

**Critical constraints:**
- Vanilla Three.js inside a React `useEffect`, NOT R3F
- Random correspondence between particles, NOT optimal transport
- The simplex noise function in the vertex shader needs the standard Ashima Arts implementation pasted in — don't leave it as a stub
- Stagger morph progress per particle via the jitter attribute so particles don't move in sync
- Tune curl noise strength, point size, color, and bloom params until it looks alive

**Deliverable check:** I need to look at the running canvas and feel something. If it looks like points sliding between positions in straight lines, it has failed. It should look like the cloud explodes and reforms with breathing motion. Stop and show me before proceeding.

### Milestone 2 — Backend pipeline with stubs

**Auto-loads when you read backend files:** `backend.md` and `backend-pipeline.md`. Read at least one file in `backend/src/aether/` early in your planning to trigger them.

**Goal:** Full backend pipeline working end-to-end with stub external services. Real Claude Opus 4.6 call using the system prompt from `prompts/script_writer.txt`. Stub TTS that returns a hardcoded MP3 file with fake word timestamps. Stub shape generator that returns one of 5 procedural point clouds (sphere, cube, torus, helix, octahedron) saved as `.bin` files. Real orchestrator, real job lifecycle, real SQLite, real manifest assembly.

**Important:** The `backend-pipeline.md` rule contains the exact system prompt — copy it verbatim into `prompts/script_writer.txt`. Do not paraphrase or "improve" it.

**Deliverable check:** I should be able to `curl -X POST http://127.0.0.1:8000/api/generate -d '{"topic":"What is AI?"}'`, get a job_id, poll `/api/jobs/{id}`, and eventually see a complete manifest with the right structure. The audio is fake but the manifest is real.

### Milestone 3 — Frontend e2e with stub backend

**Auto-loads when you read frontend files:** `frontend-app.md` and `frontend-particle.md`.

**Goal:** Complete frontend wired to the stub backend from Milestone 2. Zustand store, all 4 components (PromptInput, GenerationProgress, PlaybackView, ParticleCanvas), audio playback with AudioContext + AnalyserNode + AudioBufferSourceNode, the timeline scheduler firing morphs at the right timestamps.

**Deliverable check:** I type a topic in the input box, see progress messages, see a play button when ready, click it, watch the stub procedural shapes morph in time with the stub audio. The point of this milestone is to validate the **timing/sync architecture** before paying for real generation.

### Milestone 4 — Real TTS

**Auto-loads:** `backend-pipeline.md`.

**Goal:** Replace the stub TTS in `pipeline/tts.py` with the real ElevenLabs streaming-with-timestamps call. Verify character timestamps come back, verify the word-bucketing logic in `_chars_to_word_starts` works, verify shape trigger times now actually align with spoken words in the playback.

**Deliverable check:** Generate an explanation, play it back, listen carefully — the shape morphs should land on the words you'd expect.

### Milestone 5 — Real shape generation

**Auto-loads:** `backend-pipeline.md`.

**Goal:** Replace the shape stub with the real `Flux Pro 1.1 → Trellis` pipeline via fal.ai. Implement the SQLite cache lookup and save logic. Test with 3-5 distinct topics. The fal-client SDK uses `fal_client.subscribe_async()` (NOT the older pattern).

**If shapes come out looking like blobs, the first thing to check is whether the LLM is rewriting abstract concepts into concrete visual metaphors** — see the system prompt in `backend-pipeline.md`.

**Deliverable check:** Generate "What is artificial intelligence?" — the shapes should be recognizable (a brain, a network, etc.), and the second time you generate the same topic the shapes should come from cache (no fal.ai calls, much faster).

### Milestone 6 — Polish

**Goal:** Error handling and retry logic for external API calls. Better progress messages during generation. Loading state polish. README.md with installation instructions and a placeholder for the hero GIF (the user will record it themselves).

---

## Workflow (applies to EVERY milestone)

You are running inside Plan Mode. **Do not write or edit any files yet.**

1. Read CLAUDE.md if you haven't this session.
2. Read the relevant rule file(s) listed for this milestone — manually for Milestones 0 and 1 since the project may not have files yet to trigger auto-loading.
3. Examine any existing project files to understand the current state (this also auto-loads any matching rules).
4. Ask any clarifying questions if something is genuinely ambiguous (rare — CLAUDE.md and the rules are comprehensive).
5. Produce a structured plan listing:
   - Every file to be created or modified
   - The order of creation
   - A 1-2 sentence description of what each file will contain
   - Any commands that will be run (install, init, etc.)
6. **Stop and wait for me to approve the plan.**
7. After approval, I will exit plan mode and you will execute the plan.
8. After execution, run the deliverable check above and report status.
9. **Stop. Do not start the next milestone. I will start a new session for that.**

Begin now: read CLAUDE.md, read the relevant rule(s) for Milestone $ARGUMENTS, examine the project state, and produce the plan.
