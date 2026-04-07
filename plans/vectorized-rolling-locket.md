# Milestone 0 — Project Skeleton

## Context
Aether has no application code yet — only `CLAUDE.md`, `.gitignore`, and `.claude/` config. This milestone creates the backend (FastAPI) and frontend (Vite + React + TypeScript) scaffolding so both dev servers run and respond.

## Environment
- Python 3.14.3, Node 24.14.0, npm 11.9.0
- Windows 11, bash shell

---

## Backend (`backend/`)

### 1. `backend/pyproject.toml`
Project metadata, dependencies, and tool config. Dependencies for M0: `fastapi`, `uvicorn[standard]`, `aiosqlite`, `sqlalchemy[asyncio]`, `pydantic`, `pydantic-settings`, `structlog`, `python-dotenv`. Dev extras: `pytest`, `pytest-asyncio`, `ruff`, `httpx` (for test client). Also: `anthropic`, `elevenlabs`, `fal-client`, `trimesh`, `numpy` (needed later but install now to avoid churn).

### 2. `backend/.python-version`
Single line: `3.14`

### 3. `backend/src/aether/__init__.py`
Empty init file.

### 4. `backend/src/aether/config.py`
Pydantic `BaseSettings` loading from `.env`. Fields: `data_dir`, `host`, `port`, API keys (with defaults/optional for M0).

### 5. `backend/src/aether/main.py`
Minimal FastAPI app with CORS middleware (allowing `localhost:5173`), a lifespan that creates data directories, and a single `GET /` returning `{"status": "ok", "name": "aether"}`. Static files mount for `data/` under `/assets`. Include router stubs for `api/generate` and `api/jobs`.

### 6. `backend/src/aether/api/__init__.py`
Empty init.

### 7. `backend/src/aether/api/generate.py`
Stub router with `POST /api/generate` returning `{"job_id": "stub"}`.

### 8. `backend/src/aether/api/jobs.py`
Stub router with `GET /api/jobs/{job_id}` returning a minimal stub job JSON.

### 9. `backend/.env.example`
Template env file with placeholder API keys (per backend.md rule).

### 10. Setup commands
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev]"
mkdir -p data/cache/{shapes,meshes,images} data/manifests
```

### 11. Verify
```bash
uvicorn aether.main:app --reload --host 127.0.0.1 --port 8000
# curl http://127.0.0.1:8000/ → {"status":"ok","name":"aether"}
```

---

## Frontend (`frontend/`)

### 1. Scaffold with Vite
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### 2. Install additional deps
```bash
npm install three zustand tailwindcss @tailwindcss/vite
npm install -D @types/three
```

### 3. `frontend/vite.config.ts`
Add Tailwind plugin, set dev server port to 5173 (default), add proxy for `/api` and `/assets` to `http://127.0.0.1:8000` so frontend can reach backend without CORS issues in dev.

### 4. `frontend/src/styles/globals.css`
Tailwind v4 import (`@import "tailwindcss"`). Set body/html to black background, full height.

### 5. `frontend/src/main.tsx`
Import `globals.css`, render `<App />`.

### 6. `frontend/src/App.tsx`
Minimal: full-screen black div with centered white text "aether" — proves Tailwind + React work.

### 7. `frontend/.env`
```
VITE_API_BASE_URL=http://localhost:8000
```

### 8. Clean up Vite template
Remove default Vite boilerplate files: `App.css`, `index.css`, default `assets/`, counter logic.

### 9. Verify
```bash
cd frontend && npm run dev
# Browser → http://localhost:5173 → black screen with "aether" text
```

---

## File creation order

1. `backend/pyproject.toml`
2. `backend/.python-version`
3. `backend/.env.example`
4. `backend/src/aether/__init__.py`
5. `backend/src/aether/config.py`
6. `backend/src/aether/main.py`
7. `backend/src/aether/api/__init__.py`
8. `backend/src/aether/api/generate.py`
9. `backend/src/aether/api/jobs.py`
10. Run backend setup commands (venv, install, mkdir)
11. Verify backend starts
12. Scaffold frontend with Vite
13. Install frontend deps
14. Edit `vite.config.ts` (Tailwind plugin + proxy)
15. Create `src/styles/globals.css`
16. Edit `src/main.tsx` (use globals.css)
17. Replace `src/App.tsx` (black screen)
18. Create `frontend/.env`
19. Clean up Vite boilerplate
20. Verify frontend starts

## Deliverable check
- `uvicorn aether.main:app --reload` responds on port 8000 with JSON
- `npm run dev` responds on port 5173 with a black screen showing "aether"
- Both can run simultaneously
