"""Autenticación y control de acceso por rol.

Estaba escrito pero nunca probado: hasta aquí nadie había verificado que un
lector no pueda hacer lo que solo le toca a un administrador.
"""


def test_login_con_credenciales_correctas(client, admin):
    r = client.post(
        "/api/auth/login", data={"username": "admin@prueba.mx", "password": "Prueba123!"}
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["access_token"] and cuerpo["refresh_token"]


def test_la_contraseña_incorrecta_no_distingue_del_correo_inexistente(client, admin):
    """Dos mensajes distintos le dirían a un atacante qué correos existen."""
    mala = client.post(
        "/api/auth/login", data={"username": "admin@prueba.mx", "password": "incorrecta"}
    )
    inexistente = client.post(
        "/api/auth/login", data={"username": "nadie@prueba.mx", "password": "Prueba123!"}
    )
    assert mala.status_code == inexistente.status_code == 401
    assert mala.json()["detail"] == inexistente.json()["detail"]


def test_el_correo_no_distingue_mayusculas(client, admin):
    r = client.post(
        "/api/auth/login", data={"username": "ADMIN@PRUEBA.MX", "password": "Prueba123!"}
    )
    assert r.status_code == 200


def test_un_usuario_inactivo_no_entra(client, crear_usuario):
    from app.enums import Role

    crear_usuario("baja@prueba.mx", Role.LECTOR, activo=False)
    r = client.post(
        "/api/auth/login", data={"username": "baja@prueba.mx", "password": "Prueba123!"}
    )
    assert r.status_code == 403


def test_sin_token_no_se_pasa(client):
    assert client.get("/api/auth/yo").status_code == 401


def test_un_token_inventado_no_se_pasa(client):
    r = client.get("/api/auth/yo", headers={"Authorization": "Bearer esto.no.es-un-token"})
    assert r.status_code == 401


def test_el_refresh_token_no_sirve_como_token_de_acceso(client, admin):
    """Son de distinta vida y distinto propósito; confundirlos alargaría una
    sesión mucho más de lo previsto."""
    r = client.post(
        "/api/auth/login", data={"username": "admin@prueba.mx", "password": "Prueba123!"}
    )
    refresh = r.json()["refresh_token"]
    assert (
        client.get("/api/auth/yo", headers={"Authorization": f"Bearer {refresh}"}).status_code
        == 401
    )


def test_refresh_entrega_un_token_nuevo(client, admin):
    r = client.post(
        "/api/auth/login", data={"username": "admin@prueba.mx", "password": "Prueba123!"}
    )
    refresh = r.json()["refresh_token"]

    nuevo = client.post("/api/auth/refresh", params={"refresh_token": refresh})
    assert nuevo.status_code == 200
    assert (
        client.get(
            "/api/auth/yo", headers={"Authorization": f"Bearer {nuevo.json()['access_token']}"}
        ).status_code
        == 200
    )


def test_un_token_de_acceso_no_sirve_para_refrescar(client, admin, autenticar):
    cabeceras = autenticar("admin@prueba.mx")
    acceso = cabeceras["Authorization"].removeprefix("Bearer ")
    assert client.post("/api/auth/refresh", params={"refresh_token": acceso}).status_code == 401


def test_yo_devuelve_al_usuario_autenticado(client, juridico, autenticar):
    r = client.get("/api/auth/yo", headers=autenticar("juridico@prueba.mx"))
    assert r.status_code == 200
    assert r.json()["email"] == "juridico@prueba.mx"
    assert r.json()["role"] == "juridico"


# --- Control de acceso por rol ---


def test_solo_el_admin_crea_usuarios(client, admin, autenticar):
    r = client.post(
        "/api/auth/usuarios",
        headers=autenticar("admin@prueba.mx"),
        json={"email": "nuevo@prueba.mx", "nombre": "Nuevo", "password": "x" * 12},
    )
    assert r.status_code == 201


def test_el_juridico_no_crea_usuarios(client, juridico, autenticar):
    r = client.post(
        "/api/auth/usuarios",
        headers=autenticar("juridico@prueba.mx"),
        json={"email": "nuevo@prueba.mx", "nombre": "Nuevo", "password": "x" * 12},
    )
    assert r.status_code == 403


def test_el_lector_no_crea_usuarios(client, lector, autenticar):
    r = client.post(
        "/api/auth/usuarios",
        headers=autenticar("lector@prueba.mx"),
        json={"email": "nuevo@prueba.mx", "nombre": "Nuevo", "password": "x" * 12},
    )
    assert r.status_code == 403


def test_no_se_puede_repetir_un_correo(client, admin, autenticar):
    cabeceras = autenticar("admin@prueba.mx")
    datos = {"email": "repetido@prueba.mx", "nombre": "Uno", "password": "x" * 12}
    assert client.post("/api/auth/usuarios", headers=cabeceras, json=datos).status_code == 201
    assert client.post("/api/auth/usuarios", headers=cabeceras, json=datos).status_code == 409
