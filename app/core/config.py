from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CA Agentic AI RAG"
    environment: str = "local"
    data_dir: Path = Path("data")
    ocr_provider: str = "local"
    llm_provider: str = "offline"
    openai_api_key: str | None = None
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

