import { useState, useEffect, useRef } from 'react';
import { generateExplanation } from '../api';
import { useStore } from '../store';

const SUGGESTIONS = [
  'How does the human body work?',
  'What is quantum mechanics?',
  'How do black holes form?',
  'What is consciousness?',
  'How does DNA store information?',
  'What causes the northern lights?',
  'How does evolution work?',
  'What is the theory of relativity?',
];

export function PromptInput() {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [placeholder, setPlaceholder] = useState('');
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const setJobId = useStore((s) => s.setJobId);
  const setView = useStore((s) => s.setView);
  const error = useStore((s) => s.error);
  const setError = useStore((s) => s.setError);
  const inputRef = useRef<HTMLInputElement>(null);

  // Cycle through suggestions as animated placeholder
  useEffect(() => {
    if (topic) return; // Stop cycling when user is typing

    let charIdx = 0;
    let deleting = false;
    const target = SUGGESTIONS[placeholderIdx];
    let timeout: ReturnType<typeof setTimeout>;

    const tick = () => {
      if (!deleting) {
        charIdx++;
        setPlaceholder(target.slice(0, charIdx));
        if (charIdx === target.length) {
          // Pause at full text, then start deleting
          timeout = setTimeout(() => {
            deleting = true;
            tick();
          }, 2500);
          return;
        }
        timeout = setTimeout(tick, 50 + Math.random() * 30);
      } else {
        charIdx--;
        setPlaceholder(target.slice(0, charIdx));
        if (charIdx === 0) {
          // Move to next suggestion
          setPlaceholderIdx((i) => (i + 1) % SUGGESTIONS.length);
          return;
        }
        timeout = setTimeout(tick, 25);
      }
    };

    timeout = setTimeout(tick, 400);
    return () => clearTimeout(timeout);
  }, [placeholderIdx, topic]);

  const handleTest = async () => {
    const TEST_MANIFEST_ID = 'f024cdab-4161-414f-a0fe-870030326303';
    try {
      const resp = await fetch(`/assets/manifests/${TEST_MANIFEST_ID}/manifest.json`);
      const manifest = await resp.json();
      useStore.getState().setManifest(manifest);
      const audio = new Audio(manifest.audio_url);
      audio.preload = 'auto';
      useStore.getState().setAudioElement(audio);
      setView('playback');
    } catch (err) {
      setError(String(err));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || loading) return;

    setLoading(true);
    setError(null);
    try {
      const { job_id } = await generateExplanation(topic.trim());
      setJobId(job_id);
      setView('generating');
    } catch (err) {
      setError(String(err));
      setLoading(false);
    }
  };

  // Click on placeholder suggestion to use it
  const handlePlaceholderClick = () => {
    if (!topic && placeholder) {
      const full = SUGGESTIONS[placeholderIdx];
      setTopic(full);
      inputRef.current?.focus();
    }
  };

  return (
    <div
      className="flex flex-col items-center justify-center h-full px-4"
      style={{ background: 'radial-gradient(ellipse at center, #0a0a12 0%, #000000 70%)' }}
    >
      <h1 className="text-5xl font-extralight tracking-[0.2em] mb-2 text-white/90">
        aether
      </h1>
      <p className="text-white/20 text-xs font-light tracking-widest mb-12">
        understand anything
      </p>
      <form onSubmit={handleSubmit} className="w-full max-w-lg">
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full bg-transparent border-b border-white/15 px-1 py-3 text-white text-lg font-light outline-none focus:border-white/30 transition-colors placeholder-transparent"
            autoFocus
            disabled={loading}
          />
          {/* Custom animated placeholder */}
          {!topic && (
            <span
              onClick={handlePlaceholderClick}
              className="absolute left-1 top-3 text-white/20 text-lg font-light pointer-events-auto cursor-text"
            >
              {placeholder}
              <span className="inline-block w-[1px] h-5 bg-white/30 ml-[1px] align-text-bottom animate-pulse" />
            </span>
          )}
        </div>
        <div className="flex justify-end mt-4">
          <button
            type="submit"
            disabled={!topic.trim() || loading}
            className="text-white/40 hover:text-white/70 disabled:opacity-0 text-sm font-light tracking-wider transition-all"
          >
            {loading ? 'starting...' : 'explain \u2192'}
          </button>
        </div>
      </form>
      <button
        onClick={handleTest}
        className="absolute bottom-6 left-6 text-white/15 hover:text-white/40 text-xs font-light tracking-wider transition-colors"
      >
        demo
      </button>
      {error && (
        <p className="mt-6 text-red-400/60 text-sm font-light max-w-lg text-center">{error}</p>
      )}
    </div>
  );
}
