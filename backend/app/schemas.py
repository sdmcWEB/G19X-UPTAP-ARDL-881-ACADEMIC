"""Schemas de la API (entrada/salida HTTP). No confundir con app/ai/schemas.py."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import ContractStatus, ReviewStatus, Role, Severity, VerificationStatus


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

    # Dictamen del abogado
    revision: ReviewStatus
    comentario_revision: str | None
    revisado_at: datetime | None
    revisado_por: str | None = None

    @field_validator("revisado_por", mode="before")
    @classmethod
    def _nombre_del_revisor(cls, v):
        """El cliente necesita el nombre, no el objeto usuario completo."""
        return v.nombre if hasattr(v, "nombre") else v


class RevisionIn(BaseModel):
    """Lo que manda el abogado al confirmar o descartar."""

    revision: ReviewStatus
    comentario: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _descartar_exige_motivo(self):
        """Descartar sin decir por qué deja al siguiente revisor sin nada.

        Confirmar no lo exige: el hallazgo ya trae su explicación y su cita.
        """
        if self.revision == ReviewStatus.DESCARTADO and not (self.comentario or "").strip():
            raise ValueError("Para descartar un hallazgo hay que indicar el motivo")
        return self


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
