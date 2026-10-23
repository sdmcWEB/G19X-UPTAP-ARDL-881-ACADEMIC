import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db import Base
from app.enums import (
    ContractStatus,
    ReviewStatus,
    Role,
    Severity,
    VerificationStatus,
)

__all__ = [
    "AuditLog",
    "Clause",
    "Contract",
    "ContractStatus",
    "Finding",
    "ReviewStatus",
    "RiskType",
    "Role",
    "Severity",
    "User",
    "VerificationStatus",
]


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.LECTOR)
    activo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    nombre_archivo: Mapped[str] = mapped_column(String(512))
    object_key: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    paginas: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.RECIBIDO, index=True
    )
    error_msg: Mapped[str | None] = mapped_column(Text)

    # True si hubo que pasar OCR: la calidad del texto es menos confiable
    ocr_aplicado: Mapped[bool] = mapped_column(default=False)
    # 0-100, agregado de los hallazgos
    puntuacion_riesgo: Mapped[float | None] = mapped_column(Float)

    subido_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    analizado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clausulas: Mapped[list["Clause"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )
    hallazgos: Mapped[list["Finding"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )


class Clause(Base):
    """Un fragmento del contrato con su ubicación física en el PDF.

    `clause_id` es el identificador estable que se le manda al modelo y que el
    modelo debe devolver; es lo que permite volver de un hallazgo a la página y
    las coordenadas exactas.
    """

    __tablename__ = "clauses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )

    clause_id: Mapped[str] = mapped_column(String(32), index=True)  # "C-001"
    orden: Mapped[int] = mapped_column(Integer)
    encabezado: Mapped[str | None] = mapped_column(String(512))
    texto: Mapped[str] = mapped_column(Text)

    pagina_inicio: Mapped[int] = mapped_column(Integer)
    pagina_fin: Mapped[int] = mapped_column(Integer)
    # [{"page": 3, "bbox": [x0, y0, x1, y1]}, ...] -> resaltado en el visor
    bboxes: Mapped[list] = mapped_column(JSON, default=list)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim))

    contrato: Mapped[Contract] = relationship(back_populates="clausulas")


class RiskType(Base):
    """Catálogo de riesgos. Lo mantiene el área jurídica, no el código."""

    __tablename__ = "risk_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    codigo: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    descripcion: Mapped[str] = mapped_column(Text)
    severidad_default: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.MEDIA)
    peso: Mapped[float] = mapped_column(Float, default=1.0)  # para la puntuación agregada
    activo: Mapped[bool] = mapped_column(default=True)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    clausula_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clauses.id"))

    tipo_codigo: Mapped[str] = mapped_column(String(64), index=True)
    severidad: Mapped[Severity] = mapped_column(Enum(Severity), index=True)
    titulo: Mapped[str] = mapped_column(String(512))
    explicacion: Mapped[str] = mapped_column(Text)
    recomendacion: Mapped[str] = mapped_column(Text)

    # Lo que el modelo dijo que decía el contrato...
    cita_textual: Mapped[str] = mapped_column(Text)
    # ...y si eso resultó cierto al confrontarlo con la cláusula
    verificacion: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.NO_VERIFICADA, index=True
    )
    score_similitud: Mapped[float | None] = mapped_column(Float)
    confianza_modelo: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # --- Revisión humana ---
    # El sistema propone; el abogado dispone. Sin este dictamen la plataforma
    # entrega una lista que nadie firma.
    revision: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDIENTE, index=True
    )
    comentario_revision: Mapped[str | None] = mapped_column(Text)
    revisado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    revisado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contrato: Mapped[Contract] = relationship(back_populates="hallazgos")
    clausula: Mapped[Clause | None] = relationship()
    revisado_por: Mapped["User | None"] = relationship(foreign_keys=[revisado_por_id])


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    accion: Mapped[str] = mapped_column(String(128), index=True)
    recurso: Mapped[str] = mapped_column(String(128))
    recurso_id: Mapped[str | None] = mapped_column(String(64))
    detalle: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
