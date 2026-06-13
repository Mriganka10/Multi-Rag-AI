from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CA Agentic AI RAG"
    environment: str = "local"
    data_dir: Path = Path("data")
    ocr_provider: str = "local"
    llm_provider: str = "openai"
    openai_model: str = "gpt-4.1-mini"
    rag_learning_enabled: bool = True
    rag_learning_default_consent: bool = False
    openai_api_key: str | None = None
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    rag_provider: str = "local"
    qdrant_collection_prefix: str = "ca"
    openai_embedding_model: str = "text-embedding-3-small"
    auth_enabled: bool = False
    auth_username: str = "admin"
    auth_password: str | None = None
    auth_default_role: str = "admin"
    database_url: str | None = None
    audit_enabled: bool = True
    storage_provider: str = "local"
    s3_bucket: str | None = None
    s3_prefix: str = "ca-agentic-ai"
    s3_kms_key_id: str | None = None
    aws_region: str = "ap-south-1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
