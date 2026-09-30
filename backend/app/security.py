from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


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
