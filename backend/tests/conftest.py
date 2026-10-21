"""Infraestructura para las pruebas de la API.

Corren contra Postgres real, no SQLite: los modelos usan `UUID` y `Vector`,
que son tipos del dialecto de Postgres. Una prueba sobre un motor distinto al
de producción verifica un sistema que no existe.

Cada prueba se ejecuta dentro de una transacción que se revierte al terminar,
así que el orden entre pruebas no importa y ninguna deja residuo.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base, get_db
from app.enums import Role
from app.main import app
from app.models import User
from app.security import hash_password

# Base aparte para no tocar los datos de desarrollo.
URL_PRUEBAS = os.getenv(
    "TEST_DATABASE_URL",
    settings.database_url.rsplit("/", 1)[0] + "/riesgos_test",
)

SIN_BASE = (
    "No hay Postgres disponible para las pruebas de la API. "
    "Córrelas con `docker compose exec api pytest`, o define TEST_DATABASE_URL."
)


def _crear_base_si_falta() -> None:
    """`CREATE DATABASE` no admite transacción, de ahí el AUTOCOMMIT."""
    url_admin, nombre = URL_PRUEBAS.rsplit("/", 1)
    motor = create_engine(f"{url_admin}/postgres", isolation_level="AUTOCOMMIT")
    with motor.connect() as conn:
        existe = conn.execute(
            text("select 1 from pg_database where datname = :n"), {"n": nombre}
        ).scalar()
        if not existe:
            conn.execute(text(f'create database "{nombre}"'))
    motor.dispose()


@pytest.fixture(scope="session")
def engine():
    try:
        _crear_base_si_falta()
        motor = create_engine(URL_PRUEBAS)
        with motor.begin() as conn:
            conn.execute(text("create extension if not exists vector"))
        Base.metadata.create_all(motor)
    except OperationalError:
        pytest.skip(SIN_BASE, allow_module_level=True)

    yield motor
    motor.dispose()


@pytest.fixture
def conexion(engine):
    """Una transacción por prueba, revertida al terminar.

    El código de la aplicación llama a `commit()`; SQLAlchemy 2.0 lo resuelve
    con un savepoint dentro de esta transacción, así que el rollback final
    sigue limpiando todo.
    """
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
    finally:
        trans.rollback()
        conn.close()


@pytest.fixture
def db(conexion):
    """Sesión para que la prueba prepare datos y revise resultados."""
    sesion = sessionmaker(bind=conexion, expire_on_commit=False)()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture
def client(conexion, tmp_path, monkeypatch):
    """Cliente HTTP con la base de pruebas, el almacén en disco temporal y
    Celery desactivado: subir un contrato no debe disparar el worker."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "archivos"))

    encoladas: list[str] = []
    monkeypatch.setattr(
        "app.routers.contracts.analizar_contrato.delay",
        lambda contrato_id: encoladas.append(contrato_id),
    )

    # Una sesión NUEVA por petición, como en producción. Compartir una sola
    # entre peticiones deja objetos cacheados en el mapa de identidad y hace
    # que una prueba vea datos que ya se borraron.
    fabrica_sesion = sessionmaker(bind=conexion, expire_on_commit=False)

    def sesion_por_peticion():
        s = fabrica_sesion()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = sesion_por_peticion
    with TestClient(app) as c:
        c.encoladas = encoladas  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


def _usuario(db, email: str, role: Role, password: str = "Prueba123!", activo: bool = True):
    u = User(
        email=email,
        nombre=email.split("@")[0],
        password_hash=hash_password(password),
        role=role,
        activo=activo,
    )
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def admin(db):
    return _usuario(db, "admin@prueba.mx", Role.ADMIN)


@pytest.fixture
def juridico(db):
    return _usuario(db, "juridico@prueba.mx", Role.JURIDICO)


@pytest.fixture
def lector(db):
    return _usuario(db, "lector@prueba.mx", Role.LECTOR)


def autenticar(client: TestClient, email: str, password: str = "Prueba123!") -> dict[str, str]:
    """Devuelve la cabecera de autorización para ese usuario."""
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
