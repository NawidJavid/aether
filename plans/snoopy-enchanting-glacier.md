# Milestone 3 — Frontend E2E with Stub Backend

## Context

Milestones 1 and 2 are complete. The particle system renders 30K particles with morphing, curl noise, and bloom (M1). The backend pipeline works end-to-end with stub TTS (silent MP3 + fake word timing at 250ms/word) and stub shapes (procedural sphere/cube/torus/helix/octahedron as `.bin` files). The backend serves a complete manifest with shape trigger times synced to (fake) word timestamps.

**This milestone wires the frontend to the backend**, turning the standalone particle demo into a full app: type a topic, watch generation progress, then play back shapes morphing in sync with audio timestamps. The point is to validate the **timing/sync architecture** before paying for real generation.

## Current frontend state

- `App.tsx` — renders only `<ParticleCanvas />` in a black div (no views)
- `ParticleCanvas.tsx` — standalone demo: morphs between sphere/cube on a 3s timer with sine-wave amplitude stub
- `particleSystem.ts` — fully implemented, uses `position` attribute (not `currentPos`), has `morphTo()` and `update()` methods
- `renderer.ts` — Three.js scene + UnrealBloomPass, returns `{ renderer, scene, camera, composer, dispose }`
- Shaders — complete with Ashima simplex noise
- **Missing:** store, api client, types, audioAnalyzer, scheduler, PromptInput, GenerationProgress, PlaybackView
- Zustand is installed but unused
- Vite proxy already configured: `/api` and `/assets` → `http://127.0.0.1:8000`

## Plan

### 1. Create `frontend/.env`
- Set `VITE_API_BASE_URL=` (empty string) so fetch URLs resolve to same origin, picked up by Vite proxy

### 2. Create `src/types.ts`
- Mirror backend `models.py` exactly: `JobStatus`, `ScheduledShape`, `Manifest`, `Job`
- Reference: `backend/src/aether/models.py` (lines 11-64)

### 3. Create `src/api.ts`
- Two functions: `generateExplanation(topic)` and `getJob(jobId)`
- Uses `import.meta.env.VITE_API_BASE_URL` as base URL (will be empty → relative URLs → proxied)
- Follows the exact pattern from `.claude/rules/frontend-app.md` lines 149-169

### 4. Create `src/store.ts`
- Zustand store with: `view` ('input'|'generating'|'playback'), `jobId`, `manifest`, `audioElement`, `ready`, `progressMessage`, `error`
- Setters + `reset()` action
- Follows exact pattern from `.claude/rules/frontend-app.md` lines 91-143

### 5. Create `src/particle/audioAnalyzer.ts`
- Wraps `AnalyserNode` with `getAmplitude()` → 0-1 float
- FFT size 256, smoothing 0.6
- Follows exact pattern from `.claude/rules/frontend-particle.md` lines 289-312

### 6. Create `src/playback/scheduler.ts`
- `PlaybackScheduler` class: `preload()` fetches all `.bin` files, `tick(audioCurrentTimeMs)` fires morphs at trigger times
- Uses `firedIndices` Set to avoid double-firing
- Follows exact pattern from `.claude/rules/frontend-app.md` lines 172-222

### 7. Create `src/components/PromptInput.tsx`
- Single input box + generate button
- On submit: calls `generateExplanation()`, stores `jobId`, switches view to `'generating'`
- Minimal styling — dark theme, centered, no validation beyond non-empty

### 8. Create `src/components/GenerationProgress.tsx`
- On mount: polls `getJob(jobId)` every 1000ms
- Shows `progress_message` from job
- On `completed`: sets manifest, creates `new Audio(audioUrl)`, sets audioElement, switches to `'playback'`
- On `failed`: shows error, returns to `'input'`
- Follows pattern from `.claude/rules/frontend-app.md` lines 232-261

### 9. Create `src/components/PlaybackView.tsx`
- Renders `<ParticleCanvas />` filling viewport
- Overlays a play button when `ready === true`
- On click: calls `audioElement.play()` (required for AudioContext user gesture)
- Play button disappears after click

### 10. Rewrite `src/components/ParticleCanvas.tsx`
- Remove the standalone demo logic (timer-based morphing, sine-wave stub)
- Integrate with Zustand store: read `manifest` and `audioElement`
- When manifest + audioElement present:
  - Create `AudioContext` + `createMediaElementSource` + `AudioAnalyzer`
  - Create `PlaybackScheduler`, call `preload()`, set `ready: true` when done
- Render loop: `particles.update(elapsed, analyzer.getAmplitude())` + `scheduler.tick(audioElement.currentTime * 1000)`
- Proper cleanup on unmount (cancel RAF, close AudioContext, dispose renderer)
- Follows pattern from `.claude/rules/frontend-app.md` lines 270-332

### 11. Rewrite `src/App.tsx`
- View state machine: `input` → `generating` → `playback`
- Full-screen black container with `overflow-hidden`
- Conditionally renders one of: `PromptInput`, `GenerationProgress`, `PlaybackView`

### 12. Update `src/styles/globals.css` (if needed)
- Minimal additions for input/button styling if Tailwind utility classes aren't sufficient

## File creation order

1. `frontend/.env` (config)
2. `src/types.ts` (no deps)
3. `src/api.ts` (depends on types)
4. `src/store.ts` (depends on types)
5. `src/particle/audioAnalyzer.ts` (no deps)
6. `src/playback/scheduler.ts` (depends on types, particleSystem)
7. `src/components/PromptInput.tsx` (depends on api, store)
8. `src/components/GenerationProgress.tsx` (depends on api, store)
9. `src/components/PlaybackView.tsx` (depends on store, ParticleCanvas)
10. `src/components/ParticleCanvas.tsx` (rewrite — depends on store, audioAnalyzer, scheduler, renderer, particleSystem)
11. `src/App.tsx` (rewrite — depends on store, all components)

## Key technical notes

- **Attribute name:** The existing `ParticleSystem` uses `position` (Three.js default), not `currentPos` as in the rules reference. The code will work with this as-is.
- **Stub audio is silent:** The 417-byte silent MP3 from stub TTS means `getAmplitude()` will return ~0. That's fine — the goal is validating sync architecture, not audio reactivity.
- **`audioPlayer.ts`:** Listed in directory structure but has no reference implementation and isn't needed. Audio is handled via `<audio>` element + `AudioContext` in `ParticleCanvas`.
- **No new dependencies needed.** React, Three.js, Zustand, and Tailwind are already installed.

## Verification

1. Start backend: `cd backend && .venv/Scripts/activate && uvicorn aether.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173` — should see the input box
4. Type a topic (e.g., "What is AI?"), click generate
5. Should see progress messages updating as backend processes
6. When complete, should see a play button
7. Click play — stub shapes should morph at the trigger times from the manifest
8. Verify: shapes morph in sequence (first at t=0, rest at their scheduled times)
9. Run `npm run build` to verify TypeScript compiles cleanly
