import { useEffect, useState, useRef } from 'react';
import { ParticleCanvas } from './ParticleCanvas';
import { Subtitles } from './Subtitles';
import { useStore } from '../store';
import { generateExplanation } from '../api';

export function PlaybackView() {
  const ready = useStore((s) => s.ready);
  const audioElement = useStore((s) => s.audioElement);
  const scheduler = useStore((s) => s.scheduler);
  const setJobId = useStore((s) => s.setJobId);
  const setView = useStore((s) => s.setView);
  const setError = useStore((s) => s.setError);
  const [phase, setPhase] = useState<'waiting' | 'playing' | 'ended'>('waiting');
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!audioElement) return;
    const onEnded = () => setPhase('ended');
    audioElement.addEventListener('ended', onEnded);
    return () => audioElement.removeEventListener('ended', onEnded);
  }, [audioElement]);

  const handleStart = async () => {
    if (phase !== 'waiting' || !audioElement) return;
    try {
      await audioElement.play();
    } catch (e) {
      console.warn('Audio play failed:', e);
    }
    setPhase('playing');
  };

  const handleReplay = async () => {
    if (!audioElement) return;
    audioElement.currentTime = 0;
    scheduler?.reset();
    try {
      await audioElement.play();
    } catch (e) {
      console.warn('Audio play failed:', e);
    }
    setPhase('playing');
  };

  const handleNewTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || loading) return;
    setLoading(true);
    try {
      const { job_id } = await generateExplanation(topic.trim());
      setJobId(job_id);
      setView('generating');
    } catch (err) {
      setError(String(err));
      setLoading(false);
    }
  };

  // Focus input when ended
  useEffect(() => {
    if (phase === 'ended') {
      setTimeout(() => inputRef.current?.focus(), 600);
    }
  }, [phase]);

  return (
    <div className="relative w-full h-full">
      <ParticleCanvas />

      {phase === 'playing' && <Subtitles />}

      {/* Click anywhere to begin */}
      {phase === 'waiting' && ready && (
        <div
          className="absolute inset-0 flex items-end justify-center pb-20 cursor-pointer"
          onClick={handleStart}
        >
          <p className="text-white/50 text-sm font-light tracking-widest animate-pulse">
            click anywhere to begin
          </p>
        </div>
      )}

      {/* End state: again + new topic input */}
      {phase === 'ended' && (
        <div className="absolute bottom-16 left-0 right-0 flex flex-col items-center gap-6 pointer-events-auto px-8">
          <button
            onClick={handleReplay}
            className="text-white/30 hover:text-white/60 text-sm font-extralight tracking-widest transition-colors"
          >
            again
          </button>
          <form onSubmit={handleNewTopic} className="w-full max-w-md">
            <input
              ref={inputRef}
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="explore another topic..."
              disabled={loading}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white text-sm font-light placeholder-white/20 outline-none focus:border-white/20 transition-colors"
            />
          </form>
        </div>
      )}
    </div>
  );
}
