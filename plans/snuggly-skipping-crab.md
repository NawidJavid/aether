# Plan: Fix particle aesthetics — curl noise expression + point-size audio pulse

## Context

The particle-aesthetics critique found two issues before milestone commit:

1. **CRITICAL — No physical audio response.** The radial positional pulse was intentionally removed (it distorted recognizable shapes like a balloon). But brightness-only response is too subtle. The agreed fix is to move audio reactivity to **point size** instead of position — the shape stays intact but the cloud visually swells with the voice.

2. **HIGH — Curl noise expression wrong.** Uses `sin(u_morphProgress * PI) * 0.15` (global, peaks mid-morph) instead of `(1.0 - eased) * 0.18` (per-particle, peaks at morph start). This eliminates the "explosion and reform" effect and removes per-particle noise variation.

## File to modify

`frontend/src/particle/shaders/particle.vert.glsl` — lines 115–135 (the `main()` function)

## Changes

### Change 1: Curl noise expression (line 124)

**Before:**
```glsl
float noiseStrength = 0.05 + sin(u_morphProgress * 3.14159) * 0.15;
```

**After:**
```glsl
float noiseStrength = 0.05 + (1.0 - eased) * 0.18;
```

This fixes both issues:
- Uses per-particle `eased` value instead of global `u_morphProgress` — each particle gets noise proportional to its own morph state, creating visual variety across the staggered wave
- Uses `(1.0 - eased)` which peaks at morph START (explosion) and decays to rest as particles arrive (reform), instead of sin() which peaks mid-morph
- Bumps multiplier from 0.15 to 0.18 (centered value from tuning reference)

### Change 2: Point-size audio pulse (line 132)

**Before:**
```glsl
gl_PointSize = u_pointSize * (2.0 / -mvPosition.z);
```

**After:**
```glsl
gl_PointSize = u_pointSize * (2.0 / -mvPosition.z) * (1.0 + u_audioAmplitude * 0.3);
```

Each particle sprite grows slightly during loud moments. The shape silhouette stays intact, but the cloud swells in density/luminosity with the narration. Combined with the existing brightness modulation in `v_intensity`, this sells "alive" without the balloon distortion.

## What is NOT changing

- No changes to `particleSystem.ts`, `renderer.ts`, `audioAnalyzer.ts`, or `particle.frag.glsl`
- No changes to bloom, camera, jitter spread, or any other parameters (all at centered values)
- The removed radial positional pulse stays removed — point-size pulse replaces it

## Verification

1. `cd frontend && npm run dev` — confirm no shader compile errors
2. Visual check: trigger a morph and confirm particles explode outward from starting positions (not calm-start wobble)
3. Visual check: play audio and confirm the cloud visibly swells with voice without shape distortion
4. Visual check: at rest (between morphs), confirm gentle drift (rest noise 0.05 still present)
