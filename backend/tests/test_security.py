"""Hasheo de contraseñas y tokens. No tenía pruebas propias hasta ahora."""

import time

import jwt
import pytest

from app.config import settings
from app.security import (
    ALGORITHM,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

# Hash real generado con passlib 1.7.4, la librería anterior. Vive aquí para
# que el día que alguien cambie de hasher se note si rompe los logins
# existentes en lugar de descubrirlo en producción.
HASH_DE_PASSLIB = (
    "$argon2id$v=19$m=65536,t=3,p=4$WcuZU6o1xnhPiRGi9H4vZ"
    "Q$rt4IagU6OXw8L2f1g68dzjRCGd/nrFhflHdjvGX9xyw"
)


def test_los_hashes_de_passlib_siguen_verificándose():
    """La razón de ser de este archivo.

    El proyecto cambió de passlib a pwdlib porque passlib importa el módulo
    `crypt`, eliminado en Python 3.13. Ambos usan el formato PHC de argon2, así
    que las contraseñas guardadas antes del cambio siguen sirviendo y no hubo
    que migrar a nadie. Si alguien vuelve a cambiar de hasher, esta prueba
    falla antes de que fallen los logins reales.
    """
    assert verify_password("Estadia2026!", HASH_DE_PASSLIB)
    assert not verify_password("otra-cosa", HASH_DE_PASSLIB)


def test_el_hash_no_es_la_contraseña():
    h = hash_password("Estadia2026!")
    assert "Estadia2026!" not in h
    assert h.startswith("$argon2")


def test_dos_hashes_de_la_misma_contraseña_difieren():
    """Con sal; si coincidieran, dos usuarios con la misma contraseña serían
    identificables mirando la tabla."""
    assert hash_password("misma") != hash_password("misma")


def test_verifica_la_correcta_y_rechaza_la_demás():
    h = hash_password("Estadia2026!")
    assert verify_password("Estadia2026!", h)
    assert not verify_password("estadia2026!", h)
    assert not verify_password("", h)
    assert not verify_password("Estadia2026", h)


@pytest.mark.parametrize("corrupto", ["", "no-es-un-hash", "$argon2id$roto", "$2b$12$otroformato"])
def test_un_hash_corrupto_devuelve_falso_sin_reventar(corrupto):
    """Un registro dañado debe impedir ese login, no tumbar el endpoint."""
    assert verify_password("loquesea", corrupto) is False


def test_las_contraseñas_largas_y_con_unicode_funcionan():
    clave = "contraseñaMUYlarga✓" * 10
    assert verify_password(clave, hash_password(clave))


# --- Tokens ---


def test_el_token_de_acceso_lleva_su_tipo_y_sujeto():
    datos = decode_token(create_token("usuario-123", "access"))
    assert datos["sub"] == "usuario-123"
    assert datos["type"] == "access"


def test_el_refresh_dura_más_que_el_de_acceso():
    acceso = decode_token(create_token("u", "access"))
    refresh = decode_token(create_token("u", "refresh"))
    assert refresh["exp"] > acceso["exp"]


def test_un_token_firmado_con_otra_llave_no_pasa():
    ajeno = jwt.encode({"sub": "u", "type": "access"}, "otra-llave", algorithm=ALGORITHM)
    with pytest.raises(jwt.PyJWTError):
        decode_token(ajeno)


def test_un_token_vencido_no_pasa():
    vencido = jwt.encode(
        {"sub": "u", "type": "access", "exp": int(time.time()) - 60},
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(vencido)


def test_un_token_manipulado_no_pasa():
    token = create_token("usuario-123", "access")
    cabecera, carga, firma = token.split(".")
    with pytest.raises(jwt.PyJWTError):
        decode_token(f"{cabecera}.{carga}.{firma[:-4]}xxxx")
