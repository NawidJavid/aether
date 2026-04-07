from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "AETHER_", "env_file": ".env", "extra": "ignore"}

    data_dir: Path = Path("./data")
    host: str = "127.0.0.1"
    port: int = 8000

    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    fal_key: str = ""


settings = Settings()
