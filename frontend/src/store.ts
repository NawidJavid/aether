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
