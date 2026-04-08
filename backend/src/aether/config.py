from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    model_config = {"extra": "ignore"}

    data_dir: Path = Field(default=Path("./data"), validation_alias="AETHER_DATA_DIR")
    host: str = Field(default="127.0.0.1", validation_alias="AETHER_HOST")
    port: int = Field(default=8000, validation_alias="AETHER_PORT")

    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    fal_key: str = ""


settings = Settings()
