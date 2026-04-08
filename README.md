# Aether

A generative cinematic explainer. Type a topic, wait a minute, watch 30,000 glowing particles morph through recognizable 3D shapes in perfect sync with a narrated explanation.

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/4f479c1a-9812-4578-8409-6a61faf92a37" />

## Try it instantly

A built-in demo ships with the repo — no API keys needed. Clone, install, start the servers, and click **demo** in the bottom-left corner. You'll see a full "How does the human body work?" generation with real audio, particle morphs, and subtitles.

## How it works

1. You type a topic — anything from "What is quantum computing?" to "How do vaccines work?"
2. **Claude Opus 4.6** writes a narration script with interleaved shape cues, rewriting every abstract concept into a concrete physical object ("recursion" becomes "russian nesting dolls")
3. **ElevenLabs** renders the narration with word-level timestamps via Forced Alignment
4. Each shape cue becomes a 3D point cloud: **Flux Pro 1.1** generates an image, **Trellis** converts it to a mesh, and **trimesh** samples 30,000 surface points
5. A manifest maps each shape morph to the exact millisecond in the audio where the corresponding concept is spoken
6. The frontend plays it all back deterministically — particles explode and reform through curl noise turbulence, pulsing with the audio, while subtitles appear in sync

The whole pipeline is pre-rendered. By the time playback starts, every point cloud is loaded, every word timestamp is known, and sync is just a scheduling problem.

## The aesthetic

The particle cloud uses custom GLSL shaders with 3D simplex curl noise, per-particle staggered morphing, additive blending, and UnrealBloomPass post-processing. Particles don't slide between shapes — they explode and reform. The cloud breathes at rest and pulses with the narrator's voice.

Move your cursor over the particles and see what happens.

## Tech stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.x async, SQLite |
| **Frontend** | React 18, TypeScript, vanilla Three.js, Tailwind CSS, Zustand |
| **LLM** | Anthropic Claude Opus 4.6 |
| **Voice** | ElevenLabs `eleven_multilingual_v2` + Forced Alignment |
| **3D pipeline** | fal.ai Flux Pro 1.1 (text-to-image) + Trellis (image-to-3D) |

## Prerequisites

- Python 3.11+
- Node.js 18+
- API keys for [Anthropic](https://console.anthropic.com), [ElevenLabs](https://elevenlabs.io), and [fal.ai](https://fal.ai) (only needed for generating new topics — the demo works without them)

## Setup

### Backend

```bash
cd backend
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -e ".[dev]"
mkdir -p data/cache/{shapes,meshes,images} data/manifests
```

Create a `.env` file in the `backend/` directory:

```env
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
FAL_KEY=...
```

### Frontend

```bash
cd frontend
npm install
```

## Running

**Quick start** (Windows): double-click `dev.bat`

**Manual start** — two terminals:

```bash
# Terminal 1 — backend
cd backend && source .venv/bin/activate
uvicorn aether.main:app --reload --host 127.0.0.1 --port 8080

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Testing

```bash
cd backend && pytest -v
```

## Cost per generation

| Service | Cost |
|---------|------|
| Claude Opus 4.6 | ~$0.05 |
| Flux Pro 1.1 (5-10 images) | ~$0.28 |
| Trellis (5-10 meshes) | ~$0.14 |
| ElevenLabs (~250 words) | ~$0.30 |
| **Total** | **~$0.75** |

Cached concepts are free on repeat generations.

## License

MIT
