"""Revisión humana de hallazgos.

El sistema propone y el abogado dispone. Sin este paso la plataforma entrega
una lista que nadie firma.
"""

import uuid

import pytest
from sqlalchemy import select

from app.models import AuditLog, Finding


def un_hallazgo(db, juridico, contrato_listo) -> Finding:
    contrato_listo(juridico)
    return db.scalars(select(Finding)).one()


def test_nace_pendiente(client, juridico, db, contrato_listo, autenticar):
    """Mientras nadie lo revise, el estado honesto es pendiente."""
    h = un_hallazgo(db, juridico, contrato_listo)
    r = client.get(f"/api/hallazgos/{h.id}", headers=autenticar("juridico@prueba.mx"))
    assert r.json()["revision"] == "pendiente"
    assert r.json()["revisado_por"] is None
    assert r.json()["revisado_at"] is None


def test_confirmar_registra_quién_y_cuándo(client, juridico, db, contrato_listo, autenticar):
    h = un_hallazgo(db, juridico, contrato_listo)
    r = client.patch(
        f"/api/hallazgos/{h.id}",
        headers=autenticar("juridico@prueba.mx"),
        json={"revision": "confirmado", "comentario": "Riesgo real, hay que negociarlo."},
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["revision"] == "confirmado"
    assert cuerpo["comentario_revision"] == "Riesgo real, hay que negociarlo."
    assert cuerpo["revisado_por"] == "juridico"
    assert cuerpo["revisado_at"] is not None


def test_confirmar_no_exige_comentario(client, juridico, db, contrato_listo, autenticar):
    """El hallazgo ya trae su explicación y su cita; confirmar es estar de
    acuerdo con lo que ya está escrito."""
    h = un_hallazgo(db, juridico, contrato_listo)
    r = client.patch(
        f"/api/hallazgos/{h.id}",
        headers=autenticar("juridico@prueba.mx"),
        json={"revision": "confirmado"},
    )
    assert r.status_code == 200


def test_descartar_sin_motivo_se_rechaza(client, juridico, db, contrato_listo, autenticar):
    """Descartar sin decir por qué deja al siguiente revisor sin nada: no
    sabe si el riesgo no aplica o si alguien se equivocó al cerrarlo."""
    h = un_hallazgo(db, juridico, contrato_listo)
    r = client.patch(
        f"/api/hallazgos/{h.id}",
        headers=autenticar("juridico@prueba.mx"),
        json={"revision": "descartado"},
    )
    assert r.status_code == 422


@pytest.mark.parametrize("vacío", ["", "   ", "\n\t "])
def test_un_motivo_en_blanco_no_cuenta_como_motivo(
    client, juridico, db, contrato_listo, autenticar, vacío
):
    h = un_hallazgo(db, juridico, contrato_listo)
    r = client.patch(
        f"/api/hallazgos/{h.id}",
        headers=autenticar("juridico@prueba.mx"),
        json={"revision": "descartado", "comentario": vacío},
    )
    assert r.status_code == 422


def test_descartar_con_motivo_funciona(client, juridico, db, contrato_listo, autenticar):
    h = un_hallazgo(db, juridico, contrato_listo)
    r = client.patch(
        f"/api/hallazgos/{h.id}",
        headers=autenticar("juridico@prueba.mx"),
        json={"revision": "descartado", "comentario": "La cláusula ya está acotada en el anexo B."},
    )
    assert r.status_code == 200
    assert r.json()["revision"] == "descartado"


def test_volver_a_pendiente_borra_la_firma(client, juridico, db, contrato_listo, autenticar):
    """Deshacer un dictamen no puede dejar firmado a quien se arrepintió."""
    h = un_hallazgo(db, juridico, contrato_listo)
    cabeceras = autenticar("juridico@prueba.mx")

    client.patch(f"/api/hallazgos/{h.id}", headers=cabeceras, json={"revision": "confirmado"})
    r = client.patch(f"/api/hallazgos/{h.id}", headers=cabeceras, json={"revision": "pendiente"})

    assert r.json()["revision"] == "pendiente"
    assert r.json()["revisado_por"] is None
    assert r.json()["revisado_at"] is None


def test_el_lector_no_dictamina(client, lector, juridico, db, contrato_listo, autenticar):
    h = un_hallazgo(db, juridico, contrato_listo)
    r = client.patch(
        f"/api/hallazgos/{h.id}",
        headers=autenticar("lector@prueba.mx"),
        json={"revision": "confirmado"},
    )
    assert r.status_code == 403


def test_sin_sesion_no_se_dictamina(client, juridico, db, contrato_listo):
    h = un_hallazgo(db, juridico, contrato_listo)
    assert (
        client.patch(f"/api/hallazgos/{h.id}", json={"revision": "confirmado"}).status_code == 401
    )


def test_un_hallazgo_inexistente_da_404(client, juridico, autenticar):
    r = client.patch(
        f"/api/hallazgos/{uuid.uuid4()}",
        headers=autenticar("juridico@prueba.mx"),
        json={"revision": "confirmado"},
    )
    assert r.status_code == 404


def test_un_dictamen_inventado_se_rechaza(client, juridico, db, contrato_listo, autenticar):
    h = un_hallazgo(db, juridico, contrato_listo)
    r = client.patch(
        f"/api/hallazgos/{h.id}",
        headers=autenticar("juridico@prueba.mx"),
        json={"revision": "archivado"},
    )
    assert r.status_code == 422


def test_queda_rastro_en_la_auditoria(client, juridico, db, contrato_listo, autenticar):
    """El 038 pide trazabilidad de las decisiones; un dictamen es una."""
    h = un_hallazgo(db, juridico, contrato_listo)
    client.patch(
        f"/api/hallazgos/{h.id}",
        headers=autenticar("juridico@prueba.mx"),
        json={"revision": "confirmado"},
    )
    registro = db.scalars(select(AuditLog).where(AuditLog.accion == "dictaminar_hallazgo")).one()
    assert registro.recurso_id == str(h.id)
    assert registro.detalle == {"de": "pendiente", "a": "confirmado"}


def test_se_pueden_filtrar_los_pendientes(client, juridico, db, contrato_listo, autenticar):
    """Es lo que permite al abogado retomar donde se quedó."""
    h = un_hallazgo(db, juridico, contrato_listo)
    cabeceras = autenticar("juridico@prueba.mx")

    assert (
        len(
            client.get("/api/hallazgos", params={"revision": "pendiente"}, headers=cabeceras).json()
        )
        == 1
    )

    client.patch(f"/api/hallazgos/{h.id}", headers=cabeceras, json={"revision": "confirmado"})

    assert (
        client.get("/api/hallazgos", params={"revision": "pendiente"}, headers=cabeceras).json()
        == []
    )
    assert (
        len(
            client.get(
                "/api/hallazgos", params={"revision": "confirmado"}, headers=cabeceras
            ).json()
        )
        == 1
    )
