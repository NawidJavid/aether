import { useState } from 'react';
import { ParticleCanvas } from './ParticleCanvas';
import { useStore } from '../store';

export function PlaybackView() {
  const ready = useStore((s) => s.ready);
  const audioElement = useStore((s) => s.audioElement);
  const [playing, setPlaying] = useState(false);

  const handlePlay = async () => {
    if (audioElement) {
      try {
        await audioElement.play();
      } catch (e) {
        console.warn('Audio play failed:', e);
      }
      setPlaying(true);
    }
  };

  return (
    <div className="relative w-full h-full">
      <ParticleCanvas />
      {ready && !playing && (
        <div className="absolute inset-0 flex items-center justify-center">
          <button
            onClick={handlePlay}
            className="w-16 h-16 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 flex items-center justify-center transition-colors"
          >
            <svg
              viewBox="0 0 24 24"
              fill="white"
              className="w-6 h-6 ml-1"
            >
              <polygon points="5,3 19,12 5,21" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
