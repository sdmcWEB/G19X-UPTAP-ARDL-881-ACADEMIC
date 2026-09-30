import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.models import Finding, Severity, User, VerificationStatus
from app.schemas import HallazgoOut

router = APIRouter(prefix="/api/hallazgos", tags=["hallazgos"])


@router.get("", response_model=list[HallazgoOut])
def listar(
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
    contrato_id: uuid.UUID | None = None,
    severidad: Severity | None = None,
    verificacion: VerificationStatus | None = None,
    limite: int = Query(100, le=500),
):
    q = select(Finding).limit(limite)
    if contrato_id is not None:
        q = q.where(Finding.contrato_id == contrato_id)
    if severidad is not None:
        q = q.where(Finding.severidad == severidad)
    if verificacion is not None:
        q = q.where(Finding.verificacion == verificacion)
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
