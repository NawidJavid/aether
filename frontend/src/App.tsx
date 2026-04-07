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
