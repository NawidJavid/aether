# Milestone 1 — Particle Aesthetic Gate

## Context

This is the highest-stakes milestone in the Aether project. The goal is a standalone Three.js particle demo: 30,000 glowing blue particles morphing between a sphere and a cube on a 3-second loop, with curl noise turbulence, bloom post-processing, and a sine-wave audio amplitude stub. No backend, no UI beyond a full-screen canvas. The deliverable is binary: does the morph make you feel something?

The particle system rules (`.claude/rules/frontend-particle.md`) provide near-complete reference implementations for every file. The work is transcribing them faithfully, filling in the Ashima Arts simplex noise (the rules explicitly say to paste it in, not stub it), adding a procedural cube generator, wiring up a 3-second auto-morph loop, and tuning the aesthetic knobs.

## Files to create/modify (in order)

### 1. `frontend/src/particle/shaders/particle.vert.glsl` (NEW)

Vertex shader from the rules, with the full Ashima Arts 3D simplex noise implementation (~60 lines) replacing the placeholder. Contains:
- `mod289`, `permute`, `taylorInvSqrt`, `snoise(vec3)` — standard Ashima Arts functions
- `curlNoise(vec3)` — divergence-free vector field for organic motion
- `main()` — staggered morph via jitter, curl noise perturbation, audio-reactive radial pulse, point size attenuation

### 2. `frontend/src/particle/shaders/particle.frag.glsl` (NEW)

Fragment shader from the rules. Soft circular point sprite with `pow()` alpha falloff, discards pixels outside radius 0.5. ~10 lines.

### 3. `frontend/src/particle/particleSystem.ts` (NEW)

`ParticleSystem` class from the rules verbatim, plus one addition: a `_randomCube(n, size)` static method that generates `n` random points uniformly distributed within a cube. The constructor initializes 30,000 particles in a sphere. Exposes `morphTo()` and `update()`.

### 4. `frontend/src/particle/renderer.ts` (NEW)

`createRenderer()` function from the rules verbatim. Sets up WebGLRenderer, PerspectiveCamera at z=3.5, EffectComposer with RenderPass + UnrealBloomPass (strength 0.85, radius 0.6, threshold 0.05). Handles resize. Returns `{ renderer, scene, camera, composer, dispose }`.

### 5. `frontend/src/components/ParticleCanvas.tsx` (NEW)

Standalone demo component for Milestone 1. Simplified version of the full ParticleCanvas — no store, no scheduler, no audio. Contains:
- `useRef<HTMLCanvasElement>` for the canvas
- `useEffect` that:
  - Creates renderer via `createRenderer()`
  - Creates `ParticleSystem(30000)`
  - Adds mesh to scene
  - Pre-generates a sphere cloud and a cube cloud (each 30,000 points)
  - Runs a `requestAnimationFrame` loop that:
    - Computes sine-wave amplitude: `Math.sin(elapsed * 2.0) * 0.5 + 0.5`
    - Calls `particles.update(elapsed, amplitude)`
    - Every 3 seconds, triggers `particles.morphTo()` alternating between sphere and cube
    - Calls `composer.render()`
  - Cleanup: `cancelAnimationFrame`, `dispose()`
- Returns a full-screen `<canvas>`

### 6. `frontend/src/App.tsx` (MODIFY)

Replace the current placeholder text with just `<ParticleCanvas />`. Full-screen black canvas, nothing else.

## Commands to run after implementation

```bash
cd frontend && npm run dev
```

Then open `http://localhost:5173` and visually inspect. No tests to run — this milestone is a visual gate.

## Verification

- Canvas fills the viewport, black background
- ~30,000 soft glowing blue particles visible with bloom halo
- Particles start as a sphere, morph to a cube after 3s, back to sphere after 6s, looping
- During morph: particles stagger (not all moving at once), curl noise makes the cloud "explode and reform"
- At rest: particles gently breathe/drift from curl noise
- Sine-wave amplitude causes subtle radial pulsing
- No console errors, no WebGL warnings
- Resize the window — particles and bloom adapt

## Aesthetic tuning knobs (if needed post-implementation)

Per the rules, tune in this order:
1. Bloom strength (start 0.85)
2. Point size (start 4.5)
3. Curl noise at rest (the `0.05` constant)
4. Curl noise mid-morph (the `0.15` multiplier)
5. Jitter spread (`0.4` / `0.6` constants)
6. Camera distance (z=3.5)
7. Color (`0x88bbff`)
