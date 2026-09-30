from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    """El engine se crea al primer uso, no al importar.

    Así se puede importar cualquier modelo (y correr los tests de lógica pura)
    sin el driver de Postgres instalado ni una base de datos levantada.
    """
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def SessionLocal() -> Session:  # noqa: N802  -- se conserva el nombre convencional
    return _session_factory()()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
