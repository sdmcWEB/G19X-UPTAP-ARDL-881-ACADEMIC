"""Infraestructura para las pruebas de la API.

Corren contra Postgres real, no SQLite: los modelos usan `UUID` y `Vector`,
que son tipos del dialecto de Postgres. Una prueba sobre un motor distinto al
de producción verifica un sistema que no existe.

Cada prueba se ejecuta dentro de una transacción que se revierte al terminar,
así que el orden entre pruebas no importa y ninguna deja residuo.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base, get_db
from app.enums import ContractStatus, Role, Severity, VerificationStatus
from app.main import app
from app.models import Clause, Contract, Finding, User
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
        # Se recrea desde cero en cada corrida: `create_all` no altera tablas
        # que ya existen, así que una base de pruebas vieja seguiría sin las
        # columnas de una migración reciente y las pruebas fallarían por el
        # esquema, no por el código.
        Base.metadata.drop_all(motor)
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

    # TestClient dispara el ciclo de vida de la app, que precalienta bge-m3.
    # En las pruebas eso sería una descarga de 2 GB y una dependencia de red
    # que no aporta nada: ninguna prueba de API vectoriza.
    monkeypatch.setattr("app.ai.embeddings.embed", lambda textos: [[0.0] * 1024 for _ in textos])

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


@pytest.fixture
def crear_usuario(db):
    """Fábrica de usuarios. Es fixture y no función importable: importar entre
    módulos de prueba depende de que el directorio esté en sys.path, y eso
    cambia entre `pytest` y `python -m pytest`."""

    def _crear(email: str, role: Role, password: str = "Prueba123!", activo: bool = True):
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

    return _crear


@pytest.fixture
def admin(crear_usuario):
    return crear_usuario("admin@prueba.mx", Role.ADMIN)


@pytest.fixture
def juridico(crear_usuario):
    return crear_usuario("juridico@prueba.mx", Role.JURIDICO)


@pytest.fixture
def lector(crear_usuario):
    return crear_usuario("lector@prueba.mx", Role.LECTOR)


@pytest.fixture
def autenticar(client):
    """Devuelve la cabecera de autorización de ese usuario."""

    def _autenticar(email: str, password: str = "Prueba123!") -> dict[str, str]:
        r = client.post("/api/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _autenticar


@pytest.fixture
def contrato_listo(db):
    """Un contrato ya analizado, con una cláusula y un hallazgo verificado."""

    def _crear(usuario, con_hallazgo: bool = True) -> Contract:
        c = Contract(
            nombre_archivo="analizado.pdf",
            object_key=f"{uuid.uuid4()}/analizado.pdf",
            mime_type="application/pdf",
            paginas=4,
            status=ContractStatus.LISTO,
            puntuacion_riesgo=61.0,
            subido_por_id=usuario.id,
        )
        db.add(c)
        db.flush()

        if con_hallazgo:
            cl = Clause(
                contrato_id=c.id,
                clause_id="C-001",
                orden=1,
                encabezado="PRIMERA",
                texto="El proveedor pagará una pena sin tope.",
                pagina_inicio=2,
                pagina_fin=2,
                bboxes=[{"page": 2, "bbox": [10, 20, 300, 40]}],
            )
            db.add(cl)
            db.flush()
            db.add(
                Finding(
                    contrato_id=c.id,
                    clausula_id=cl.id,
                    tipo_codigo="PENALIZACION_DESPROPORCIONADA",
                    severidad=Severity.ALTA,
                    titulo="Pena sin tope",
                    explicacion="No hay límite acumulable.",
                    recomendacion="Negociar un tope.",
                    cita_textual="una pena sin tope",
                    verificacion=VerificationStatus.VERIFICADA,
                    score_similitud=100.0,
                    confianza_modelo=0.93,
                )
            )
        db.commit()
        return c

    return _crear
