from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    secret_key: str = "dev-insecure"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Postgres
    database_url: str = "postgresql+psycopg://riesgos:riesgos@localhost:5432/riesgos"

    # Celery
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "contratos"
    minio_secure: bool = False

    # xAI / Grok
    xai_api_key: str = ""
    xai_model: str = "grok-4.7"

    # Embeddings
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # OCR
    ocr_lang: str = "spa"
    ocr_min_chars_per_page: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
