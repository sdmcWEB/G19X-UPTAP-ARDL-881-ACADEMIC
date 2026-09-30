import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require_roles
from app.models import Role, User
from app.schemas import Token, UsuarioCrear, UsuarioOut
from app.security import create_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    return Token(
        access_token=create_token(str(user.id), "access"),
        refresh_token=create_token(str(user.id), "refresh"),
    )


@router.post("/refresh", response_model=Token)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido") from None

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Se esperaba un refresh token")

    return Token(
        access_token=create_token(payload["sub"], "access"),
        refresh_token=create_token(payload["sub"], "refresh"),
    )


@router.get("/yo", response_model=UsuarioOut)
def yo(user: User = Depends(current_user)):
    return user


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
def crear_usuario(
    datos: UsuarioCrear,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    if db.scalar(select(User).where(User.email == datos.email.lower())):
        raise HTTPException(status_code=409, detail="Ese correo ya está registrado")

    user = User(
        email=datos.email.lower(),
        nombre=datos.nombre,
        password_hash=hash_password(datos.password),
        role=datos.role,
    )
    db.add(user)
    db.commit()
    return user
