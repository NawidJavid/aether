import { useEffect, useRef, useState } from 'react';
import { useStore } from '../store';

export function Subtitles() {
  const manifest = useStore((s) => s.manifest);
  const audioElement = useStore((s) => s.audioElement);
  const [text, setText] = useState('');
  const [visible, setVisible] = useState(false);
  const prevIndexRef = useRef(-1);

  useEffect(() => {
    if (!audioElement || !manifest) return;

    const shapes = manifest.shapes;

    const onTimeUpdate = () => {
      const ms = audioElement.currentTime * 1000;

      let idx = -1;
      for (let i = shapes.length - 1; i >= 0; i--) {
        if (ms >= shapes[i].trigger_time_ms) {
          idx = i;
          break;
        }
      }

      if (idx !== prevIndexRef.current) {
        prevIndexRef.current = idx;
        const newText = idx >= 0 ? shapes[idx].subtitle || '' : '';
        if (newText) {
          // Fade out, swap text, fade in
          setVisible(false);
          setTimeout(() => {
            setText(newText);
            setVisible(true);
          }, 300);
        } else {
          setVisible(false);
        }
      }
    };

    audioElement.addEventListener('timeupdate', onTimeUpdate);
    return () => audioElement.removeEventListener('timeupdate', onTimeUpdate);
  }, [audioElement, manifest]);

  if (!text) return null;

  return (
    <div className="absolute bottom-16 left-0 right-0 flex justify-center pointer-events-none px-12">
      <p
        className="text-white/70 text-xl font-extralight tracking-wide leading-relaxed text-center max-w-2xl transition-opacity duration-300"
        style={{
          opacity: visible ? 1 : 0,
          textShadow: '0 0 12px rgba(0,0,0,0.8), 0 0 4px rgba(0,0,0,0.9)',
        }}
      >
        {text}
      </p>
    </div>
  );
}
