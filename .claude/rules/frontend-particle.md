---
paths:
  - "frontend/src/particle/**"
---

# Aether — Particle renderer rules

These rules load automatically when you work on any file in `frontend/src/particle/`. **This is the project's highest-stakes area — Milestone 1 lives or dies here.** Read these rules carefully before touching shader code.

## Why vanilla Three.js, not React Three Fiber

R3F is great for declarative scene graphs but adds reconciliation overhead and abstracts away exactly the GPU-level control we need. The particle system uses custom shaders, custom buffer attributes updated every frame, and direct uniform writes 60 times per second. Doing that through R3F's reconciler is fighting the framework. Write a `<ParticleCanvas>` React component that owns the Three.js renderer in a `useEffect`, and inside that effect have full vanilla control.

## The particle system at a glance

- **30,000 particles**, rendered as a single `THREE.Points` mesh with a custom `ShaderMaterial`
- Each particle has two position attributes: `currentPos` and `targetPos`. The vertex shader interpolates between them based on a `u_morphProgress` uniform
- Each particle has a `jitter` attribute (random 0–1) so the morph is staggered, not synchronized
- A 3D **curl noise** field perturbs each particle every frame so the cloud breathes even at rest
- An **AnalyserNode** reads playing audio amplitude and feeds it as `u_audioAmplitude` so the cloud pulses radially with the voice
- **UnrealBloomPass** post-processing adds soft glow

## Particle correspondence: USE RANDOM, not optimal transport

When morphing between two point clouds with different point distributions, the mathematically "correct" approach is optimal transport — find the assignment that minimizes total movement. It looks smooth and dignified, and **boring**. Random correspondence with strong curl noise looks like the cloud explodes and reforms, which is the actual Jarvis aesthetic. Always use random.

## `particle/particleSystem.ts`

```typescript
import * as THREE from 'three';
import vertexShader from './shaders/particle.vert.glsl?raw';
import fragmentShader from './shaders/particle.frag.glsl?raw';

export class ParticleSystem {
  readonly mesh: THREE.Points;
  private geometry: THREE.BufferGeometry;
  private material: THREE.ShaderMaterial;
  private currentPositions: Float32Array;
  private targetPositions: Float32Array;
  private morphStartTime = 0;
  private morphDuration = 1500;
  private isMorphing = false;

  constructor(public readonly pointCount: number = 30000) {
    this.geometry = new THREE.BufferGeometry();
    this.currentPositions = this._randomSphere(pointCount, 1.0);
    this.targetPositions = new Float32Array(this.currentPositions);

    const jitter = new Float32Array(pointCount);
    for (let i = 0; i < pointCount; i++) jitter[i] = Math.random();

    this.geometry.setAttribute(
      'currentPos',
      new THREE.BufferAttribute(this.currentPositions, 3)
    );
    this.geometry.setAttribute(
      'targetPos',
      new THREE.BufferAttribute(this.targetPositions, 3)
    );
    this.geometry.setAttribute(
      'jitter',
      new THREE.BufferAttribute(jitter, 1)
    );

    this.material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        u_time: { value: 0 },
        u_morphProgress: { value: 1.0 },
        u_audioAmplitude: { value: 0.0 },
        u_pointSize: { value: 4.5 },
        u_color: { value: new THREE.Color(0x88bbff) },
      },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    this.mesh = new THREE.Points(this.geometry, this.material);
  }

  /**
   * Load a new target point cloud from a fetched .bin file.
   * Triggers a morph from current → target.
   */
  morphTo(newTargetPositions: Float32Array, durationMs: number = 1500): void {
    // Snapshot current positions
    this.currentPositions.set(this.targetPositions);

    // Match length: if new array is different length, resample randomly
    if (newTargetPositions.length !== this.targetPositions.length) {
      this.targetPositions = this._resampleToLength(newTargetPositions, this.pointCount);
    } else {
      this.targetPositions.set(newTargetPositions);
    }

    (this.geometry.attributes.currentPos as THREE.BufferAttribute).needsUpdate = true;
    (this.geometry.attributes.targetPos as THREE.BufferAttribute).needsUpdate = true;
    this.geometry.attributes.targetPos.array = this.targetPositions;

    this.morphStartTime = performance.now();
    this.morphDuration = durationMs;
    this.isMorphing = true;
  }

  update(elapsedSeconds: number, audioAmplitude: number): void {
    this.material.uniforms.u_time.value = elapsedSeconds;
    this.material.uniforms.u_audioAmplitude.value = audioAmplitude;

    if (this.isMorphing) {
      const t = (performance.now() - this.morphStartTime) / this.morphDuration;
      this.material.uniforms.u_morphProgress.value = Math.min(1.0, t);
      if (t >= 1.0) this.isMorphing = false;
    }
  }

  private _randomSphere(n: number, radius: number): Float32Array {
    const out = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = 2 * Math.PI * u;
      const phi = Math.acos(2 * v - 1);
      const r = radius * Math.cbrt(Math.random());
      out[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      out[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      out[i * 3 + 2] = r * Math.cos(phi);
    }
    return out;
  }

  private _resampleToLength(input: Float32Array, targetLength: number): Float32Array {
    const inputCount = input.length / 3;
    const out = new Float32Array(targetLength * 3);
    for (let i = 0; i < targetLength; i++) {
      const srcIdx = Math.floor(Math.random() * inputCount);
      out[i * 3] = input[srcIdx * 3];
      out[i * 3 + 1] = input[srcIdx * 3 + 1];
      out[i * 3 + 2] = input[srcIdx * 3 + 2];
    }
    return out;
  }
}
```

## `particle/shaders/particle.vert.glsl`

The simplex noise function below is a stub. **Paste in the standard 3D simplex noise implementation from Ashima Arts** (https://github.com/ashima/webgl-noise) — it's ~50 lines of well-known boilerplate. Don't try to write it yourself.

```glsl
attribute vec3 currentPos;
attribute vec3 targetPos;
attribute float jitter;

uniform float u_time;
uniform float u_morphProgress;
uniform float u_audioAmplitude;
uniform float u_pointSize;

varying float v_intensity;

// PASTE STANDARD ASHIMA ARTS 3D SIMPLEX NOISE HERE
// https://github.com/ashima/webgl-noise/blob/master/src/noise3D.glsl
// You need: vec3 mod289(vec3), vec4 mod289(vec4), vec4 permute(vec4),
//           vec4 taylorInvSqrt(vec4), float snoise(vec3 v)
float snoise(vec3 v) {
    // PLACEHOLDER — replace with the real implementation
    return 0.0;
}

// Curl of a noise field — divergence-free vector field for organic motion
vec3 curlNoise(vec3 p) {
    const float e = 0.1;
    vec3 dx = vec3(e, 0.0, 0.0);
    vec3 dy = vec3(0.0, e, 0.0);
    vec3 dz = vec3(0.0, 0.0, e);

    float x = snoise(p + dy) - snoise(p - dy) - snoise(p + dz) + snoise(p - dz);
    float y = snoise(p + dz) - snoise(p - dz) - snoise(p + dx) + snoise(p - dx);
    float z = snoise(p + dx) - snoise(p - dx) - snoise(p + dy) + snoise(p - dy);

    return normalize(vec3(x, y, z) / (2.0 * e));
}

void main() {
    // Stagger morph progress per particle so they don't move in sync
    float t = clamp((u_morphProgress - jitter * 0.4) / 0.6, 0.0, 1.0);
    // Smoothstep easing
    float eased = t * t * (3.0 - 2.0 * t);

    vec3 morphed = mix(currentPos, targetPos, eased);

    // Curl noise turbulence — stronger mid-morph, gentle at rest
    float noiseStrength = 0.05 + (1.0 - eased) * 0.15;
    vec3 noiseOffset = curlNoise(morphed * 1.5 + u_time * 0.15) * noiseStrength;

    // Audio-reactive radial pulse
    vec3 dir = length(morphed) > 0.001 ? normalize(morphed) : vec3(0.0);
    float pulse = u_audioAmplitude * 0.12;

    vec3 finalPos = morphed + noiseOffset + dir * pulse;

    vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
    gl_Position = projectionMatrix * mvPosition;

    gl_PointSize = u_pointSize * (300.0 / -mvPosition.z);

    v_intensity = 0.55 + u_audioAmplitude * 0.45 + jitter * 0.1;
}
```

## `particle/shaders/particle.frag.glsl`

```glsl
varying float v_intensity;
uniform vec3 u_color;

void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv);
    if (dist > 0.5) discard;

    // Smooth alpha falloff with strong center
    float alpha = pow(1.0 - dist * 2.0, 2.5);

    vec3 color = u_color * v_intensity;
    gl_FragColor = vec4(color, alpha);
}
```

## `particle/renderer.ts` — Three.js scene + bloom

```typescript
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';

export function createRenderer(canvas: HTMLCanvasElement) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 1);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
  camera.position.set(0, 0, 3.5);
  camera.lookAt(0, 0, 0);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));

  const bloom = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    0.85,    // strength
    0.6,     // radius
    0.05,    // threshold
  );
  composer.addPass(bloom);

  const resize = () => {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    composer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  resize();
  window.addEventListener('resize', resize);

  return {
    renderer, scene, camera, composer,
    dispose: () => {
      window.removeEventListener('resize', resize);
      renderer.dispose();
    }
  };
}
```

## `particle/audioAnalyzer.ts`

```typescript
export class AudioAnalyzer {
  private analyser: AnalyserNode;
  private dataArray: Uint8Array;

  constructor(audioContext: AudioContext, source: AudioNode) {
    this.analyser = audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.analyser.smoothingTimeConstant = 0.6;
    source.connect(this.analyser);
    this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
  }

  /** Returns 0–1 amplitude representing current audio loudness. */
  getAmplitude(): number {
    this.analyser.getByteFrequencyData(this.dataArray);
    let sum = 0;
    for (let i = 0; i < this.dataArray.length; i++) sum += this.dataArray[i];
    const avg = sum / this.dataArray.length / 255;
    // Slight curve for snappier visual response
    return Math.pow(avg, 0.7);
  }
}
```

## Aesthetic tuning checklist

After getting the basic morph working, these are the knobs that determine whether it looks alive or dead. Tune them in this order:

1. **Bloom strength** — start at 0.85, increase if particles look flat. Too high washes everything out.
2. **Point size** — 4.5 default. Smaller looks more elegant, larger looks more substantial.
3. **Curl noise strength at rest** — the `0.05` constant in the vertex shader. Controls the "breathing" amplitude when the cloud isn't morphing. If it looks static, increase. If it looks chaotic, decrease.
4. **Curl noise strength mid-morph** — the `(1.0 - eased) * 0.15` term. Controls the explosion amplitude during morphs. Higher = more chaos during transition.
5. **Jitter spread** — the `0.4` and `0.6` constants in the eased calculation. Controls how staggered the per-particle morph is. Higher spread = more "wave" feeling.
6. **Camera distance** — `position.set(0, 0, 3.5)`. Closer feels more immersive, farther feels more cinematic.
7. **Color** — `0x88bbff` is a cool blue-white. Stays close to the reference image.

**The Milestone 1 gate is binary:** does the morph make you feel something? If after 3 evenings of tuning these knobs the answer is still no, the project is in trouble — escalate before continuing.
