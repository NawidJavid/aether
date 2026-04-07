from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from aether.api import generate, jobs
from aether.config import settings
from aether.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data directories exist
    data = Path(settings.data_dir)
    for sub in ["cache/shapes", "cache/meshes", "cache/images", "manifests"]:
        (data / sub).mkdir(parents=True, exist_ok=True)
    await init_db()
    yield


app = FastAPI(title="Aether", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router)
app.include_router(jobs.router)
app.mount("/assets", StaticFiles(directory=str(settings.data_dir)), name="assets")


@app.get("/")
async def root():
    return {"status": "ok", "name": "aether"}
