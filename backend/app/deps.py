import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_CREDENCIALES_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)


def current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise _CREDENCIALES_INVALIDAS from None

    if payload.get("type") != "access":
        raise _CREDENCIALES_INVALIDAS

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise _CREDENCIALES_INVALIDAS from None

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.activo:
        raise _CREDENCIALES_INVALIDAS
    return user


def require_roles(*roles: Role):
    """Dependencia de autorización: `Depends(require_roles(Role.ADMIN))`."""

    def _check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta operación",
            )
        return user

    return _check
