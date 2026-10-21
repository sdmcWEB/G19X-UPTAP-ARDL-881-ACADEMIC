from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config import settings

# pwdlib en lugar de passlib: passlib importa el módulo `crypt`, eliminado de
# la biblioteca estándar en Python 3.13, y lleva años sin publicar versión.
# El formato PHC de argon2 es el mismo, así que los hashes ya guardados siguen
# verificándose sin migrar ninguna contraseña.
_hasher = PasswordHash((Argon2Hasher(),))
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """False ante un hash corrupto, nunca una excepción.

    Un registro dañado en la base debe impedir ese login, no tumbar el
    endpoint para todos."""
    try:
        return _hasher.verify(plain, hashed)
    except Exception:
        return False


def create_token(subject: str, kind: Literal["access", "refresh"] = "access") -> str:
    if kind == "access":
        expires = timedelta(minutes=settings.access_token_expire_minutes)
    else:
        expires = timedelta(days=settings.refresh_token_expire_days)

    payload = {
        "sub": subject,
        "type": kind,
        "exp": datetime.now(UTC) + expires,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Levanta jwt.PyJWTError si el token es inválido o expiró."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
