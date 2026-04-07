# Aether

A generative cinematic explainer. Type a topic, wait a minute, watch 30,000 glowing particles morph through recognizable 3D shapes in perfect sync with a narrated explanation.

<!-- Replace with your recorded hero GIF -->
![Hero GIF placeholder](https://placehold.co/800x400/000000/88bbff?text=hero+gif+goes+here)

## How it works

1. You type a topic — anything from "What is quantum computing?" to "How do vaccines work?"
2. Claude Opus writes a narration script with interleaved shape cues, rewriting every abstract concept into a concrete, photographable object ("recursion" becomes "russian nesting dolls")
3. ElevenLabs renders the narration with word-level timestamps
4. Each shape cue is turned into a 3D point cloud: Flux Pro generates an image, Trellis converts it to a mesh, and trimesh samples 30,000 surface points
5. A manifest maps each shape morph to the exact millisecond in the audio where the corresponding concept is spoken
6. The frontend plays it all back deterministically — particles explode and reform through curl noise turbulence, pulsing with the audio, while the voice explains

The whole pipeline is pre-rendered. By the time playback starts, every point cloud is loaded, every word timestamp is known, and sync is just a scheduling problem.

## The aesthetic

This is a portfolio piece, not a demo. The particle cloud uses custom GLSL shaders with 3D simplex curl noise, per-particle staggered morphing, additive blending, and UnrealBloomPass post-processing. Particles don't slide between shapes — they explode and reform. The cloud breathes at rest and pulses with the narrator's voice.

## Tech stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.x async, SQLite |
| **Frontend** | React 18, TypeScript, vanilla Three.js, Tailwind CSS, Zustand |
| **LLM** | Anthropic Claude Opus 4.6 |
| **Voice** | ElevenLabs `eleven_multilingual_v2` with word timestamps |
| **3D pipeline** | fal.ai Flux Pro 1.1 (text-to-image) + Trellis (image-to-3D) |

## Prerequisites

- Python 3.11+
- Node.js 18+
- API keys for [Anthropic](https://console.anthropic.com), [ElevenLabs](https://elevenlabs.io), and [fal.ai](https://fal.ai)

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

Create a `.env` file in the `backend/` directory (or set these as environment variables):

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

Start both servers in separate terminals:

```bash
# Terminal 1 — backend on :8000
cd backend && source .venv/bin/activate
uvicorn aether.main:app --reload

# Terminal 2 — frontend on :5173
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## API

The backend exposes three endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate` | Submit a topic. Returns `{ "job_id": "..." }` |
| `GET` | `/api/jobs/{id}` | Poll job status. Returns manifest when complete |
| `GET` | `/assets/{path}` | Serves audio files and point cloud binaries |

### Example

```bash
# Start a generation
curl -X POST http://127.0.0.1:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "What is artificial intelligence?"}'

# Poll until status is "completed"
curl http://127.0.0.1:8000/api/jobs/{job_id}
```

## Testing

```bash
cd backend
pytest -v
```

## Project structure

```
aether/
├── backend/
│   ├── src/aether/
│   │   ├── main.py                  # FastAPI app, CORS, static mounts
│   │   ├── config.py                # Pydantic Settings, env vars
│   │   ├── models.py                # Pydantic data models
│   │   ├── db.py                    # SQLAlchemy async, SQLite
│   │   ├── api/
│   │   │   ├── generate.py          # POST /api/generate
│   │   │   └── jobs.py              # GET /api/jobs/{id}
│   │   ├── pipeline/
│   │   │   ├── orchestrator.py      # Ties LLM → TTS → shapes → manifest
│   │   │   ├── llm.py               # Claude script generation + parser
│   │   │   ├── tts.py               # ElevenLabs with word timestamps
│   │   │   ├── shapes.py            # Flux → Trellis → point cloud
│   │   │   └── pointcloud.py        # Procedural shape generators
│   │   └── prompts/
│   │       └── script_writer.txt    # The Claude system prompt
│   ├── tests/
│   └── data/                        # Runtime data (gitignored)
├── frontend/
│   └── src/
│       ├── particle/
│       │   ├── particleSystem.ts     # 30K-particle Points mesh + morphing
│       │   ├── renderer.ts           # Three.js scene + bloom post-processing
│       │   └── shaders/              # Custom GLSL vertex + fragment shaders
│       └── components/
│           └── ParticleCanvas.tsx     # React wrapper for the Three.js canvas
└── CLAUDE.md                         # Project spec and build instructions
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
