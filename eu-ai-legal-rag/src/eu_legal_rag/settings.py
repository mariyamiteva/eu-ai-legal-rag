from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "eu_ai_legal_docs"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_api_key: str | None = None
    llm_model: str | None = None
    user_agent: str = "eu-ai-legal-rag/0.1"
    request_timeout_seconds: int = 45
    chunk_size_chars: int = 2800
    chunk_overlap_chars: int = 350


@lru_cache
def get_settings() -> Settings:
    return Settings()
