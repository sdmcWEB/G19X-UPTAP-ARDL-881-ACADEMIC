"""Schemas de la API (entrada/salida HTTP). No confundir con app/ai/schemas.py."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import ContractStatus, Role, Severity, VerificationStatus


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UsuarioCrear(BaseModel):
    email: EmailStr
    nombre: str
    password: str
    role: Role = Role.LECTOR


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    nombre: str
    role: Role
    activo: bool


class ClausulaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clause_id: str
    orden: int
    encabezado: str | None
    texto: str
    pagina_inicio: int
    pagina_fin: int
    bboxes: list


class HallazgoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clausula_id: uuid.UUID | None
    tipo_codigo: str
    severidad: Severity
    titulo: str
    explicacion: str
    recomendacion: str
    cita_textual: str
    verificacion: VerificationStatus
    score_similitud: float | None
    confianza_modelo: float | None


class ContratoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre_archivo: str
    mime_type: str
    paginas: int | None
    status: ContractStatus
    error_msg: str | None
    ocr_aplicado: bool
    puntuacion_riesgo: float | None
    created_at: datetime
    analizado_at: datetime | None


class ContratoDetalle(ContratoOut):
    hallazgos: list[HallazgoOut] = []
    clausulas: list[ClausulaOut] = []
