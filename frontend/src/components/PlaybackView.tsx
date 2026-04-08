import { useEffect, useState } from 'react';
import { ParticleCanvas } from './ParticleCanvas';
import { Subtitles } from './Subtitles';
import { useStore } from '../store';

export function PlaybackView() {
  const ready = useStore((s) => s.ready);
  const audioElement = useStore((s) => s.audioElement);
  const scheduler = useStore((s) => s.scheduler);
  const [playing, setPlaying] = useState(false);
  const [ended, setEnded] = useState(false);

  useEffect(() => {
    if (!audioElement) return;
    const onEnded = () => {
      setPlaying(false);
      setEnded(true);
    };
    audioElement.addEventListener('ended', onEnded);
    return () => audioElement.removeEventListener('ended', onEnded);
  }, [audioElement]);

  const handlePlay = async () => {
    if (audioElement) {
      try {
        await audioElement.play();
      } catch (e) {
        console.warn('Audio play failed:', e);
      }
      setPlaying(true);
      setEnded(false);
    }
  };

  const handleReplay = async () => {
    if (audioElement) {
      audioElement.currentTime = 0;
      scheduler?.reset();
      await handlePlay();
    }
  };

  const showButton = ready && !playing;

  return (
    <div className="relative w-full h-full">
      <ParticleCanvas />
      {playing && <Subtitles />}
      {showButton && (
        <div className="absolute inset-0 flex items-center justify-center">
          <button
            onClick={ended ? handleReplay : handlePlay}
            className="w-16 h-16 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 flex items-center justify-center transition-colors"
          >
            {ended ? (
              <svg viewBox="0 0 24 24" fill="white" className="w-6 h-6">
                <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="white" className="w-6 h-6 ml-1">
                <polygon points="5,3 19,12 5,21" />
              </svg>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
