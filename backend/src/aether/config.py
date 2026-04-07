from __future__ import annotations

import os
from pathlib import Path

from pydantic import model_validator
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

    @model_validator(mode="after")
    def _fallback_to_standard_env_vars(self) -> Settings:
        """Fall back to standard env var names if AETHER_-prefixed ones aren't set."""
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.elevenlabs_api_key:
            self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not self.fal_key:
            self.fal_key = os.environ.get("FAL_KEY", "")
        return self


settings = Settings()
