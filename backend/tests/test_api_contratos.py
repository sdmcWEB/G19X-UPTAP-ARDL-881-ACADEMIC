"""Subida de contratos, permisos y descarga del reporte."""

import uuid

import pytest

from app.enums import ContractStatus, Role

PDF_MINIMO = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def subir(client, cabeceras, nombre="contrato.pdf", contenido=PDF_MINIMO, mime="application/pdf"):
    return client.post(
        "/api/contratos",
        headers=cabeceras,
        files={"archivo": (nombre, contenido, mime)},
    )


# --- Subida ---


def test_el_juridico_puede_subir(client, juridico, autenticar):
    r = subir(client, autenticar("juridico@prueba.mx"))
    assert r.status_code == 201
    assert r.json()["status"] == "recibido"


def test_el_lector_no_puede_subir(client, lector, autenticar):
    """El rol existía en el código pero nadie lo había comprobado."""
    assert subir(client, autenticar("lector@prueba.mx")).status_code == 403


def test_sin_sesion_no_se_sube(client):
    assert subir(client, {}).status_code == 401


def test_la_subida_encola_el_analisis(client, juridico, autenticar):
    cabeceras = autenticar("juridico@prueba.mx")
    r = subir(client, cabeceras)
    assert client.encoladas == [r.json()["id"]]


@pytest.mark.parametrize(
    ("nombre", "mime"),
    [
        ("hoja.xlsx", "application/vnd.ms-excel"),
        ("notas.txt", "text/plain"),
        ("imagen.png", "image/png"),
    ],
)
def test_se_rechaza_lo_que_no_es_contrato(client, juridico, nombre, mime, autenticar):
    r = subir(client, autenticar("juridico@prueba.mx"), nombre=nombre, mime=mime)
    assert r.status_code == 415


def test_se_acepta_word(client, juridico, autenticar):
    r = subir(
        client,
        autenticar("juridico@prueba.mx"),
        nombre="c.docx",
        contenido=b"PK\x03\x04",
        mime=DOCX,
    )
    assert r.status_code == 201


def test_un_archivo_vacio_se_rechaza(client, juridico, autenticar):
    r = subir(client, autenticar("juridico@prueba.mx"), contenido=b"")
    assert r.status_code == 400


def test_un_archivo_enorme_se_rechaza(client, juridico, autenticar):
    """51 MB contra el tope de 50: el límite existe para que un PDF escaneado
    gigante no tumbe al worker."""
    r = subir(
        client,
        autenticar("juridico@prueba.mx"),
        contenido=b"%PDF" + b"0" * (51 * 1024 * 1024),
    )
    assert r.status_code == 413


def test_el_archivo_subido_se_puede_recuperar(client, juridico, autenticar):
    cabeceras = autenticar("juridico@prueba.mx")
    cid = subir(client, cabeceras).json()["id"]

    r = client.get(f"/api/contratos/{cid}/archivo", headers=cabeceras)
    assert r.status_code == 200
    assert r.content == PDF_MINIMO
    assert r.headers["content-type"] == "application/pdf"


# --- Consulta ---


def test_cualquier_rol_puede_consultar(client, contrato_listo, lector, juridico, autenticar):
    contrato_listo(juridico)
    r = client.get("/api/contratos", headers=autenticar("lector@prueba.mx"))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_el_detalle_trae_clausulas_y_hallazgos(client, contrato_listo, juridico, autenticar):
    c = contrato_listo(juridico)
    r = client.get(f"/api/contratos/{c.id}", headers=autenticar("juridico@prueba.mx"))
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo["clausulas"]) == 1
    assert len(cuerpo["hallazgos"]) == 1
    assert cuerpo["hallazgos"][0]["verificacion"] == "verificada"


def test_un_contrato_inexistente_da_404(client, juridico, autenticar):
    r = client.get(f"/api/contratos/{uuid.uuid4()}", headers=autenticar("juridico@prueba.mx"))
    assert r.status_code == 404


def test_un_id_mal_formado_da_422(client, juridico, autenticar):
    r = client.get("/api/contratos/no-es-un-uuid", headers=autenticar("juridico@prueba.mx"))
    assert r.status_code == 422


# --- Reporte ---


def test_el_reporte_sale_en_pdf(client, contrato_listo, juridico, autenticar):
    c = contrato_listo(juridico)
    r = client.get(f"/api/contratos/{c.id}/reporte.pdf", headers=autenticar("juridico@prueba.mx"))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert "attachment" in r.headers["content-disposition"]


def test_no_hay_reporte_de_un_contrato_sin_analizar(client, juridico, autenticar):
    """Un PDF con cero hallazgos porque el análisis no corrió se leería como
    'este contrato no tiene riesgos', que es una afirmación falsa."""
    cid = subir(client, autenticar("juridico@prueba.mx")).json()["id"]
    r = client.get(f"/api/contratos/{cid}/reporte.pdf", headers=autenticar("juridico@prueba.mx"))
    assert r.status_code == 409


def test_el_lector_sí_puede_descargar_el_reporte(
    client, contrato_listo, lector, juridico, autenticar
):
    c = contrato_listo(juridico)
    r = client.get(f"/api/contratos/{c.id}/reporte.pdf", headers=autenticar("lector@prueba.mx"))
    assert r.status_code == 200


# --- Reanálisis ---


def test_reanalizar_limpia_y_vuelve_a_encolar(client, contrato_listo, juridico, autenticar):
    c = contrato_listo(juridico)
    cabeceras = autenticar("juridico@prueba.mx")

    r = client.post(f"/api/contratos/{c.id}/reanalizar", headers=cabeceras)
    assert r.status_code == 200
    assert r.json()["status"] == "recibido"
    assert str(c.id) in client.encoladas

    detalle = client.get(f"/api/contratos/{c.id}", headers=cabeceras).json()
    assert detalle["hallazgos"] == []
    assert detalle["clausulas"] == []
    assert detalle["puntuacion_riesgo"] is None


def test_el_lector_no_puede_reanalizar(client, contrato_listo, lector, juridico, autenticar):
    c = contrato_listo(juridico)
    r = client.post(f"/api/contratos/{c.id}/reanalizar", headers=autenticar("lector@prueba.mx"))
    assert r.status_code == 403


def test_no_se_reanaliza_lo_que_ya_está_corriendo(client, contrato_listo, juridico, db, autenticar):
    c = contrato_listo(juridico)
    c.status = ContractStatus.ANALIZANDO
    db.commit()

    r = client.post(f"/api/contratos/{c.id}/reanalizar", headers=autenticar("juridico@prueba.mx"))
    assert r.status_code == 409


def test_queda_rastro_en_la_auditoria(client, juridico, db, autenticar):
    """El 038 pide trazabilidad; la tabla existe y hasta ahora nadie había
    comprobado que se escriba."""
    from sqlalchemy import select

    from app.models import AuditLog

    subir(client, autenticar("juridico@prueba.mx"))
    acciones = db.scalars(select(AuditLog.accion)).all()
    assert "subir_contrato" in acciones


def test_el_rol_admin_también_puede_subir(client, admin, autenticar):
    assert subir(client, autenticar("admin@prueba.mx")).status_code == 201


def test_los_roles_del_dominio_son_los_tres_esperados():
    assert {r.value for r in Role} == {"admin", "juridico", "lector"}
