from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    secret_key: str = "dev-insecure"
    # Orígenes permitidos, separados por coma. Con el proxy de Vite el
    # navegador nunca llama a la API directo, así que esto solo hace falta si
    # alguien expone la API por su cuenta.
    cors_origins: str = "http://localhost:5173"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Postgres
    database_url: str = "postgresql+psycopg://riesgos:riesgos@localhost:5432/riesgos"

    # Celery
    redis_url: str = "redis://localhost:6379/0"

    # Almacenamiento de archivos (volumen en disco)
    storage_dir: str = "/data/contratos"

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
