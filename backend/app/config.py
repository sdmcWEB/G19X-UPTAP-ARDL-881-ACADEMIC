from functools import lru_cache

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    #
    # Sin valor por defecto a propósito: firma los tokens de sesión, y uno
    # predecible deja que cualquiera se fabrique un token de administrador.
    # El largo mínimo es el de `openssl rand -hex 32`; una llave corta no
    # protege más que ninguna.
    secret_key: str = Field(min_length=32)
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

    # Groq (API compatible con OpenAI)
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Embeddings
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # OCR
    ocr_lang: str = "spa"
    ocr_min_chars_per_page: int = 100


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        if any(e["loc"] == ("secret_key",) for e in exc.errors()):
            raise RuntimeError(
                "Falta SECRET_KEY, o es demasiado corta (mínimo 32 caracteres).\n"
                "Genera una con:  openssl rand -hex 32\n"
                "y ponla en .env antes de arrancar."
            ) from exc
        raise


settings = get_settings()
