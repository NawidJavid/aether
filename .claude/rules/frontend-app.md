---
paths:
  - "frontend/src/components/**"
  - "frontend/src/playback/**"
  - "frontend/src/store.ts"
  - "frontend/src/api.ts"
  - "frontend/src/types.ts"
  - "frontend/src/App.tsx"
---

# Aether — Frontend application rules

These rules load when you work on React components, the Zustand store, the API client, or the playback scheduler. They cover the wiring that connects the particle renderer (see `frontend-particle.md`) to the backend manifest.

## Frontend directory structure

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api.ts                   # Backend API client
    ├── store.ts                 # Zustand store
    ├── types.ts                 # Mirrors Pydantic models
    ├── components/
    │   ├── PromptInput.tsx
    │   ├── GenerationProgress.tsx
    │   ├── PlaybackView.tsx
    │   └── ParticleCanvas.tsx
    ├── particle/                # see frontend-particle.md rule
    ├── playback/
    │   ├── scheduler.ts
    │   └── audioPlayer.ts
    └── styles/
        └── globals.css
```

## TypeScript types (`src/types.ts`)

Mirror the Pydantic models from `backend/src/aether/models.py` exactly. If a field changes there, update it here too.

```typescript
export type JobStatus =
  | 'pending'
  | 'generating_script'
  | 'generating_assets'
  | 'assembling'
  | 'completed'
  | 'failed';

export interface ScheduledShape {
  concept: string;
  point_cloud_url: string;
  point_count: number;
  trigger_time_ms: number;
  morph_duration_ms: number;
}

export interface Manifest {
  manifest_id: string;
  topic: string;
  audio_url: string;
  audio_duration_ms: number;
  shapes: ScheduledShape[];
  full_text: string;
  created_at: string;
}

export interface Job {
  job_id: string;
  topic: string;
  status: JobStatus;
  progress_message: string;
  manifest: Manifest | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}
```

## Zustand store (`src/store.ts`)

Single source of truth for the app's view state and the current manifest. Don't sprawl into multiple stores.

```typescript
import { create } from 'zustand';
import type { Manifest } from './types';

type View = 'input' | 'generating' | 'playback';

interface AetherStore {
  view: View;
  jobId: string | null;
  manifest: Manifest | null;
  audioElement: HTMLAudioElement | null;
  ready: boolean;
  progressMessage: string;
  error: string | null;

  setView: (v: View) => void;
  setJobId: (id: string | null) => void;
  setManifest: (m: Manifest | null) => void;
  setAudioElement: (el: HTMLAudioElement | null) => void;
  setReady: (r: boolean) => void;
  setProgressMessage: (m: string) => void;
  setError: (e: string | null) => void;
  reset: () => void;
}

export const useStore = create<AetherStore>((set) => ({
  view: 'input',
  jobId: null,
  manifest: null,
  audioElement: null,
  ready: false,
  progressMessage: '',
  error: null,

  setView: (v) => set({ view: v }),
  setJobId: (id) => set({ jobId: id }),
  setManifest: (m) => set({ manifest: m }),
  setAudioElement: (el) => set({ audioElement: el }),
  setReady: (r) => set({ ready: r }),
  setProgressMessage: (m) => set({ progressMessage: m }),
  setError: (e) => set({ error: e }),

  reset: () => set({
    view: 'input',
    jobId: null,
    manifest: null,
    audioElement: null,
    ready: false,
    progressMessage: '',
    error: null,
  }),
}));
```

## API client (`src/api.ts`)

Thin wrapper over fetch. No fancy client library.

```typescript
import type { Job } from './types';

const BASE = import.meta.env.VITE_API_BASE_URL;

export async function generateExplanation(topic: string): Promise<{ job_id: string }> {
  const resp = await fetch(`${BASE}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  });
  if (!resp.ok) throw new Error(`Generate failed: ${resp.status}`);
  return resp.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const resp = await fetch(`${BASE}/api/jobs/${jobId}`);
  if (!resp.ok) throw new Error(`Job fetch failed: ${resp.status}`);
  return resp.json();
}
```

## Playback scheduler (`src/playback/scheduler.ts`)

The scheduler runs inside the requestAnimationFrame loop and triggers shape morphs at exact audio timestamps. **It must be deterministic** — the playback experience depends on this.

```typescript
import type { Manifest, ScheduledShape } from '../types';
import { ParticleSystem } from '../particle/particleSystem';

export class PlaybackScheduler {
  private firedIndices = new Set<number>();
  private shapes: ScheduledShape[];
  private pointClouds = new Map<string, Float32Array>();

  constructor(
    private particleSystem: ParticleSystem,
    private manifest: Manifest,
  ) {
    this.shapes = manifest.shapes;
  }

  /** Pre-fetches all .bin files into memory before playback starts. */
  async preload(apiBaseUrl: string): Promise<void> {
    await Promise.all(
      this.shapes.map(async (s) => {
        const url = `${apiBaseUrl}${s.point_cloud_url}`;
        const resp = await fetch(url);
        const buf = await resp.arrayBuffer();
        this.pointClouds.set(s.point_cloud_url, new Float32Array(buf));
      }),
    );
  }

  /** Called every frame from the render loop. */
  tick(audioCurrentTimeMs: number): void {
    for (let i = 0; i < this.shapes.length; i++) {
      if (this.firedIndices.has(i)) continue;
      const shape = this.shapes[i];
      if (audioCurrentTimeMs >= shape.trigger_time_ms) {
        const cloud = this.pointClouds.get(shape.point_cloud_url);
        if (cloud) {
          this.particleSystem.morphTo(cloud, shape.morph_duration_ms);
          this.firedIndices.add(i); // Inside cloud check so it retries if cloud not loaded yet
        }
      }
    }
  }

  reset(): void {
    this.firedIndices.clear();
  }
}
```

## Components

### `components/PromptInput.tsx`

Single input box, generate button, calls `generateExplanation()`, stores `job_id`, switches view to `generating`. Keep it minimal — no validation beyond required-non-empty, no character counter, no examples panel.

### `components/GenerationProgress.tsx`

On mount, polls `getJob(jobId)` every 1000ms via `setInterval`. Displays the `progress_message` from the job. When status flips to `completed`, sets the manifest in the store, creates a hidden `<audio>` element pointing at the manifest's audio URL, sets it in the store, switches view to `playback`. On status `failed`, switches back to `input` with the error displayed.

```typescript
useEffect(() => {
  if (!jobId) return;
  const interval = setInterval(async () => {
    try {
      const job = await getJob(jobId);
      setProgressMessage(job.progress_message);
      if (job.status === 'completed' && job.manifest) {
        clearInterval(interval);
        setManifest(job.manifest);
        const audio = new Audio(`${import.meta.env.VITE_API_BASE_URL}${job.manifest.audio_url}`);
        audio.preload = 'auto';
        setAudioElement(audio);
        setView('playback');
      } else if (job.status === 'failed') {
        clearInterval(interval);
        setError(job.error || 'Generation failed');
        setView('input');
      }
    } catch (e) {
      clearInterval(interval);
      setError(String(e));
      setView('input');
    }
  }, 1000);
  return () => clearInterval(interval);
}, [jobId]);
```

### `components/PlaybackView.tsx`

Renders `<ParticleCanvas>` filling the viewport. Overlay a play button when `ready === true`. When clicked, calls `audioElement.play()`. The scheduler is owned by ParticleCanvas; this component just provides the play trigger.

### `components/ParticleCanvas.tsx`

This is where Three.js + the scheduler meet React. Owns the renderer in a `useEffect`.

```tsx
import { useEffect, useRef } from 'react';
import { createRenderer } from '../particle/renderer';
import { ParticleSystem } from '../particle/particleSystem';
import { AudioAnalyzer } from '../particle/audioAnalyzer';
import { PlaybackScheduler } from '../playback/scheduler';
import { useStore } from '../store';

export function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const manifest = useStore((s) => s.manifest);
  const audioElement = useStore((s) => s.audioElement);

  useEffect(() => {
    if (!canvasRef.current) return;

    const { renderer, scene, camera, composer, dispose } = createRenderer(canvasRef.current);
    const particles = new ParticleSystem(30000);
    scene.add(particles.mesh);

    let analyzer: AudioAnalyzer | null = null;
    let scheduler: PlaybackScheduler | null = null;
    let audioContext: AudioContext | null = null;

    if (audioElement && manifest) {
      audioContext = new AudioContext();
      const source = audioContext.createMediaElementSource(audioElement);
      source.connect(audioContext.destination);
      analyzer = new AudioAnalyzer(audioContext, source);

      scheduler = new PlaybackScheduler(particles, manifest);
      scheduler.preload(import.meta.env.VITE_API_BASE_URL).then(() => {
        useStore.setState({ ready: true });
      });
    }

    let frameId = 0;
    const startTime = performance.now();
    const render = () => {
      const elapsed = (performance.now() - startTime) / 1000;
      const amplitude = analyzer?.getAmplitude() ?? 0;
      particles.update(elapsed, amplitude);

      if (scheduler && audioElement) {
        scheduler.tick(audioElement.currentTime * 1000);
      }

      composer.render();
      frameId = requestAnimationFrame(render);
    };
    render();

    return () => {
      cancelAnimationFrame(frameId);
      audioContext?.close();
      dispose();
    };
  }, [manifest, audioElement]);

  return <canvas ref={canvasRef} className="w-full h-full block" />;
}
```

### `App.tsx`

A single state machine driven by the `view` value in the store. No router, no nested layouts.

```tsx
import { useStore } from './store';
import { PromptInput } from './components/PromptInput';
import { GenerationProgress } from './components/GenerationProgress';
import { PlaybackView } from './components/PlaybackView';

export default function App() {
  const view = useStore((s) => s.view);

  return (
    <div className="w-screen h-screen bg-black text-white overflow-hidden">
      {view === 'input' && <PromptInput />}
      {view === 'generating' && <GenerationProgress />}
      {view === 'playback' && <PlaybackView />}
    </div>
  );
}
```

## Frontend gotchas

- **AudioContext requires user gesture.** The `play()` call must happen inside a click handler — that's why the play button exists. Don't try to autoplay.
- **`createMediaElementSource` can only be called once per `<audio>` element.** If you create the audio element fresh on each generation (which we do), this is fine. Don't reuse audio elements.
- **The scheduler's `tick` reads `audioElement.currentTime` directly**, not from the AudioContext. This is intentional — `currentTime` on the HTMLAudioElement is the canonical playback position, and is what ElevenLabs' timestamps are measured against.
- **`useEffect` cleanup matters.** When the component unmounts (or when manifest/audioElement changes), the AudioContext and renderer must be properly disposed or you'll leak GPU resources and audio nodes.
- **Don't add a router or nested routing.** The view state machine is three states — input, generating, playback — and that's it.
