"""Subida de contratos, permisos y descarga del reporte."""

import uuid

import pytest

from app.enums import ContractStatus, Role, Severity, VerificationStatus
from app.models import Clause, Contract, Finding
from tests.conftest import autenticar

PDF_MINIMO = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def subir(client, cabeceras, nombre="contrato.pdf", contenido=PDF_MINIMO, mime="application/pdf"):
    return client.post(
        "/api/contratos",
        headers=cabeceras,
        files={"archivo": (nombre, contenido, mime)},
    )


def contrato_listo(db, usuario, con_hallazgo=True) -> Contract:
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


# --- Subida ---


def test_el_juridico_puede_subir(client, juridico):
    r = subir(client, autenticar(client, "juridico@prueba.mx"))
    assert r.status_code == 201
    assert r.json()["status"] == "recibido"


def test_el_lector_no_puede_subir(client, lector):
    """El rol existía en el código pero nadie lo había comprobado."""
    assert subir(client, autenticar(client, "lector@prueba.mx")).status_code == 403


def test_sin_sesion_no_se_sube(client):
    assert subir(client, {}).status_code == 401


def test_la_subida_encola_el_analisis(client, juridico):
    cabeceras = autenticar(client, "juridico@prueba.mx")
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
def test_se_rechaza_lo_que_no_es_contrato(client, juridico, nombre, mime):
    r = subir(client, autenticar(client, "juridico@prueba.mx"), nombre=nombre, mime=mime)
    assert r.status_code == 415


def test_se_acepta_word(client, juridico):
    r = subir(
        client,
        autenticar(client, "juridico@prueba.mx"),
        nombre="c.docx",
        contenido=b"PK\x03\x04",
        mime=DOCX,
    )
    assert r.status_code == 201


def test_un_archivo_vacio_se_rechaza(client, juridico):
    r = subir(client, autenticar(client, "juridico@prueba.mx"), contenido=b"")
    assert r.status_code == 400


def test_un_archivo_enorme_se_rechaza(client, juridico):
    """51 MB contra el tope de 50: el límite existe para que un PDF escaneado
    gigante no tumbe al worker."""
    r = subir(
        client,
        autenticar(client, "juridico@prueba.mx"),
        contenido=b"%PDF" + b"0" * (51 * 1024 * 1024),
    )
    assert r.status_code == 413


def test_el_archivo_subido_se_puede_recuperar(client, juridico):
    cabeceras = autenticar(client, "juridico@prueba.mx")
    cid = subir(client, cabeceras).json()["id"]

    r = client.get(f"/api/contratos/{cid}/archivo", headers=cabeceras)
    assert r.status_code == 200
    assert r.content == PDF_MINIMO
    assert r.headers["content-type"] == "application/pdf"


# --- Consulta ---


def test_cualquier_rol_puede_consultar(client, lector, juridico, db):
    contrato_listo(db, juridico)
    r = client.get("/api/contratos", headers=autenticar(client, "lector@prueba.mx"))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_el_detalle_trae_clausulas_y_hallazgos(client, juridico, db):
    c = contrato_listo(db, juridico)
    r = client.get(f"/api/contratos/{c.id}", headers=autenticar(client, "juridico@prueba.mx"))
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo["clausulas"]) == 1
    assert len(cuerpo["hallazgos"]) == 1
    assert cuerpo["hallazgos"][0]["verificacion"] == "verificada"


def test_un_contrato_inexistente_da_404(client, juridico):
    r = client.get(
        f"/api/contratos/{uuid.uuid4()}", headers=autenticar(client, "juridico@prueba.mx")
    )
    assert r.status_code == 404


def test_un_id_mal_formado_da_422(client, juridico):
    r = client.get("/api/contratos/no-es-un-uuid", headers=autenticar(client, "juridico@prueba.mx"))
    assert r.status_code == 422


# --- Reporte ---


def test_el_reporte_sale_en_pdf(client, juridico, db):
    c = contrato_listo(db, juridico)
    r = client.get(
        f"/api/contratos/{c.id}/reporte.pdf", headers=autenticar(client, "juridico@prueba.mx")
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert "attachment" in r.headers["content-disposition"]


def test_no_hay_reporte_de_un_contrato_sin_analizar(client, juridico):
    """Un PDF con cero hallazgos porque el análisis no corrió se leería como
    'este contrato no tiene riesgos', que es una afirmación falsa."""
    cid = subir(client, autenticar(client, "juridico@prueba.mx")).json()["id"]
    r = client.get(
        f"/api/contratos/{cid}/reporte.pdf", headers=autenticar(client, "juridico@prueba.mx")
    )
    assert r.status_code == 409


def test_el_lector_sí_puede_descargar_el_reporte(client, lector, juridico, db):
    c = contrato_listo(db, juridico)
    r = client.get(
        f"/api/contratos/{c.id}/reporte.pdf", headers=autenticar(client, "lector@prueba.mx")
    )
    assert r.status_code == 200


# --- Reanálisis ---


def test_reanalizar_limpia_y_vuelve_a_encolar(client, juridico, db):
    c = contrato_listo(db, juridico)
    cabeceras = autenticar(client, "juridico@prueba.mx")

    r = client.post(f"/api/contratos/{c.id}/reanalizar", headers=cabeceras)
    assert r.status_code == 200
    assert r.json()["status"] == "recibido"
    assert str(c.id) in client.encoladas

    detalle = client.get(f"/api/contratos/{c.id}", headers=cabeceras).json()
    assert detalle["hallazgos"] == []
    assert detalle["clausulas"] == []
    assert detalle["puntuacion_riesgo"] is None


def test_el_lector_no_puede_reanalizar(client, lector, juridico, db):
    c = contrato_listo(db, juridico)
    r = client.post(
        f"/api/contratos/{c.id}/reanalizar", headers=autenticar(client, "lector@prueba.mx")
    )
    assert r.status_code == 403


def test_no_se_reanaliza_lo_que_ya_está_corriendo(client, juridico, db):
    c = contrato_listo(db, juridico)
    c.status = ContractStatus.ANALIZANDO
    db.commit()

    r = client.post(
        f"/api/contratos/{c.id}/reanalizar", headers=autenticar(client, "juridico@prueba.mx")
    )
    assert r.status_code == 409


def test_queda_rastro_en_la_auditoria(client, juridico, db):
    """El 038 pide trazabilidad; la tabla existe y hasta ahora nadie había
    comprobado que se escriba."""
    from sqlalchemy import select

    from app.models import AuditLog

    subir(client, autenticar(client, "juridico@prueba.mx"))
    acciones = db.scalars(select(AuditLog.accion)).all()
    assert "subir_contrato" in acciones


def test_el_rol_admin_también_puede_subir(client, admin):
    assert subir(client, autenticar(client, "admin@prueba.mx")).status_code == 201


def test_los_roles_del_dominio_son_los_tres_esperados():
    assert {r.value for r in Role} == {"admin", "juridico", "lector"}
