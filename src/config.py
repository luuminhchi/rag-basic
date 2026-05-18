from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",         # bỏ qua các biến .env không khai báo trong Settings
    )

    # Paths
    vector_store_dir: Path = Path("storage/faiss")

    # Chunking
    chunk_size: int = Field(default=1000, ge=100)
    chunk_overlap: int = Field(default=150, ge=0)

    # Retrieval
    top_k: int = Field(default=5, ge=1, le=64)

    # Embedding
    # embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_model: str = "intfloat/multilingual-e5-base"

    # LLM
    llm_provider: str = "gemini"          # "openai" | "gemini" | "hf_local"
    llm_model: str = "gemini-2.5-flash"          #gpt-4o.mini
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2048, ge=1)

    # API keys (loaded from .env, no RAG_ prefix)
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    google_api_key: str | None = Field(default=None, validation_alias="GOOGLE_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
