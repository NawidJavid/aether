import { useEffect } from 'react';
import { getJob } from '../api';
import { useStore } from '../store';

export function GenerationProgress() {
  const jobId = useStore((s) => s.jobId);
  const progressMessage = useStore((s) => s.progressMessage);
  const setProgressMessage = useStore((s) => s.setProgressMessage);
  const setManifest = useStore((s) => s.setManifest);
  const setAudioElement = useStore((s) => s.setAudioElement);
  const setView = useStore((s) => s.setView);
  const setError = useStore((s) => s.setError);

  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      try {
        const job = await getJob(jobId);
        setProgressMessage(job.progress_message);
        if (job.status === 'completed' && job.manifest) {
          clearInterval(interval);
          setManifest(job.manifest);
          const audio = new Audio(job.manifest.audio_url);
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
  }, [jobId, setProgressMessage, setManifest, setAudioElement, setView, setError]);

  return (
    <div className="flex flex-col items-center justify-center h-full px-4">
      <div className="w-8 h-8 border-2 border-white/20 border-t-white/60 rounded-full animate-spin mb-6" />
      <p className="text-white/60 text-sm">
        {progressMessage || 'Starting generation...'}
      </p>
    </div>
  );
}
