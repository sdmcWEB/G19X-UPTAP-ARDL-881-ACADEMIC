"""Registro de auditoría.

El 038 pide trazabilidad de las decisiones del sistema. Esta tabla cubre el
lado de las acciones humanas; las llamadas al modelo las traza Langfuse.
"""

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def registrar(
    db: Session,
    usuario: User | None,
    accion: str,
    recurso: str,
    recurso_id: str | None = None,
    detalle: dict | None = None,
) -> None:
    """Agrega el registro a la sesión. El commit lo hace quien llama."""
    db.add(
        AuditLog(
            usuario_id=usuario.id if usuario else None,
            accion=accion,
            recurso=recurso,
            recurso_id=recurso_id,
            detalle=detalle or {},
        )
    )
