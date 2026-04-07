import { useState } from 'react';
import { generateExplanation } from '../api';
import { useStore } from '../store';

export function PromptInput() {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const setJobId = useStore((s) => s.setJobId);
  const setView = useStore((s) => s.setView);
  const error = useStore((s) => s.error);
  const setError = useStore((s) => s.setError);

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

  return (
    <div className="flex flex-col items-center justify-center h-full px-4">
      <h1 className="text-4xl font-light tracking-wide mb-8 text-white/90">
        aether
      </h1>
      <form onSubmit={handleSubmit} className="w-full max-w-lg flex flex-col gap-4">
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="What do you want to understand?"
          className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/30 outline-none focus:border-white/30 transition-colors"
          autoFocus
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!topic.trim() || loading}
          className="bg-white/10 hover:bg-white/15 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg px-6 py-3 text-white/80 transition-colors"
        >
          {loading ? 'Starting...' : 'Explain'}
        </button>
      </form>
      {error && (
        <p className="mt-4 text-red-400/80 text-sm max-w-lg text-center">{error}</p>
      )}
    </div>
  );
}
