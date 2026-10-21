"""Tablero, hallazgos y búsqueda a nivel HTTP."""

import uuid

from app.enums import Severity, VerificationStatus


def test_el_tablero_exige_sesion(client):
    assert client.get("/api/dashboard").status_code == 401


def test_la_busqueda_exige_sesion(client):
    assert client.get("/api/busqueda", params={"q": "penalización"}).status_code == 401


def test_los_hallazgos_exigen_sesion(client):
    assert client.get("/api/hallazgos").status_code == 401


def test_una_consulta_demasiado_corta_se_rechaza(client, lector, autenticar):
    """Dos letras no identifican nada y cuestan una vectorización."""
    r = client.get("/api/busqueda", params={"q": "ab"}, headers=autenticar("lector@prueba.mx"))
    assert r.status_code == 422


def test_el_tablero_vacio_no_inventa_cifras(client, lector, autenticar):
    r = client.get("/api/dashboard", headers=autenticar("lector@prueba.mx"))
    assert r.status_code == 200
    d = r.json()
    assert d["contratos_totales"] == 0
    assert d["riesgo_promedio"] is None
    assert d["pct_citas_verificadas"] is None
    assert d["tendencia"] == []


def test_el_tablero_cuenta_lo_que_hay(client, contrato_listo, juridico, autenticar):
    contrato_listo(juridico)
    r = client.get("/api/dashboard", headers=autenticar("juridico@prueba.mx"))
    d = r.json()
    assert d["contratos_totales"] == 1
    assert d["contratos_analizados"] == 1
    assert d["hallazgos_totales"] == 1
    assert d["riesgo_promedio"] == 61.0
    assert d["pct_citas_verificadas"] == 100.0


def test_las_severidades_vienen_completas_y_en_orden(client, contrato_listo, juridico, autenticar):
    """La gráfica recibe las cinco, aunque alguna esté en cero: un eje al que
    le faltan categorías cambia de forma entre periodos."""
    contrato_listo(juridico)
    d = client.get("/api/dashboard", headers=autenticar("juridico@prueba.mx")).json()
    assert [s["clave"] for s in d["por_severidad"]] == [
        "critica",
        "alta",
        "media",
        "baja",
        "informativa",
    ]
    assert sum(s["total"] for s in d["por_severidad"]) == 1


def test_el_periodo_cero_es_todo_el_historico(client, contrato_listo, juridico, autenticar):
    contrato_listo(juridico)
    cabeceras = autenticar("juridico@prueba.mx")
    r = client.get("/api/dashboard", params={"dias": 0}, headers=cabeceras)
    assert r.status_code == 200
    assert r.json()["dias"] is None


def test_el_periodo_tiene_tope(client, lector, autenticar):
    r = client.get("/api/dashboard", params={"dias": 5000}, headers=autenticar("lector@prueba.mx"))
    assert r.status_code == 422


def test_los_hallazgos_se_filtran_por_contrato(client, contrato_listo, juridico, autenticar):
    c = contrato_listo(juridico)
    cabeceras = autenticar("juridico@prueba.mx")

    propios = client.get("/api/hallazgos", params={"contrato_id": str(c.id)}, headers=cabeceras)
    assert len(propios.json()) == 1

    ajenos = client.get(
        "/api/hallazgos", params={"contrato_id": str(uuid.uuid4())}, headers=cabeceras
    )
    assert ajenos.json() == []


def test_los_hallazgos_se_filtran_por_severidad_y_verificacion(
    client, contrato_listo, juridico, autenticar
):
    contrato_listo(juridico)
    cabeceras = autenticar("juridico@prueba.mx")

    assert (
        len(
            client.get(
                "/api/hallazgos", params={"severidad": Severity.ALTA.value}, headers=cabeceras
            ).json()
        )
        == 1
    )
    assert (
        client.get(
            "/api/hallazgos", params={"severidad": Severity.CRITICA.value}, headers=cabeceras
        ).json()
        == []
    )
    assert (
        len(
            client.get(
                "/api/hallazgos",
                params={"verificacion": VerificationStatus.VERIFICADA.value},
                headers=cabeceras,
            ).json()
        )
        == 1
    )


def test_un_hallazgo_inexistente_da_404(client, lector, autenticar):
    r = client.get(f"/api/hallazgos/{uuid.uuid4()}", headers=autenticar("lector@prueba.mx"))
    assert r.status_code == 404
