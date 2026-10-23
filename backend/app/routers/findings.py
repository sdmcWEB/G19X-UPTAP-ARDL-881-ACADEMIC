import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import registrar
from app.db import get_db
from app.deps import current_user, require_roles
from app.models import Finding, ReviewStatus, Role, Severity, User, VerificationStatus
from app.schemas import HallazgoOut, RevisionIn

router = APIRouter(prefix="/api/hallazgos", tags=["hallazgos"])


@router.get("", response_model=list[HallazgoOut])
def listar(
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
    contrato_id: uuid.UUID | None = None,
    severidad: Severity | None = None,
    verificacion: VerificationStatus | None = None,
    revision: ReviewStatus | None = None,
    limite: int = Query(100, le=500),
):
    q = select(Finding).limit(limite)
    if contrato_id is not None:
        q = q.where(Finding.contrato_id == contrato_id)
    if severidad is not None:
        q = q.where(Finding.severidad == severidad)
    if verificacion is not None:
        q = q.where(Finding.verificacion == verificacion)
    if revision is not None:
        q = q.where(Finding.revision == revision)
    return db.scalars(q).all()


@router.get("/{hallazgo_id}", response_model=HallazgoOut)
def detalle(
    hallazgo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    hallazgo = db.get(Finding, hallazgo_id)
    if hallazgo is None:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")
    return hallazgo


@router.patch("/{hallazgo_id}", response_model=HallazgoOut)
def dictaminar(
    hallazgo_id: uuid.UUID,
    datos: RevisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ADMIN, Role.JURIDICO)),
):
    """El abogado confirma o descarta un hallazgo.

    El sistema propone; esto es lo que lo convierte en una revisión que
    alguien firma. Queda registrado quién dictaminó y cuándo, porque de eso
    depende que el reporte pueda presentarse como trabajo revisado.
    """
    hallazgo = db.get(Finding, hallazgo_id)
    if hallazgo is None:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")

    anterior = hallazgo.revision

    hallazgo.revision = datos.revision
    hallazgo.comentario_revision = (datos.comentario or "").strip() or None

    if datos.revision == ReviewStatus.PENDIENTE:
        # Volver a pendiente es deshacer: el dictamen anterior ya no vale y
        # dejar firmado a quien se arrepintió sería falsear el registro.
        hallazgo.revisado_por_id = None
        hallazgo.revisado_at = None
    else:
        hallazgo.revisado_por_id = user.id
        hallazgo.revisado_at = datetime.now(UTC)

    registrar(
        db,
        user,
        "dictaminar_hallazgo",
        "hallazgo",
        str(hallazgo_id),
        {"de": anterior.value, "a": datos.revision.value},
    )
    db.commit()
    db.refresh(hallazgo)
    return hallazgo
