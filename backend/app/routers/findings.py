import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.models import Contract, Finding, Severity, User, VerificationStatus
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


@router.get("/resumen/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(current_user)):
    """Cifras para el tablero: por severidad, por tipo y calidad de la evidencia."""
    por_severidad = dict(
        db.execute(select(Finding.severidad, func.count()).group_by(Finding.severidad)).all()
    )
    por_tipo = dict(
        db.execute(
            select(Finding.tipo_codigo, func.count())
            .group_by(Finding.tipo_codigo)
            .order_by(func.count().desc())
            .limit(10)
        ).all()
    )
    por_verificacion = dict(
        db.execute(select(Finding.verificacion, func.count()).group_by(Finding.verificacion)).all()
    )

    return {
        "contratos_totales": db.scalar(select(func.count()).select_from(Contract)),
        "hallazgos_totales": db.scalar(select(func.count()).select_from(Finding)),
        "riesgo_promedio": db.scalar(select(func.avg(Contract.puntuacion_riesgo))),
        "por_severidad": {k.value: v for k, v in por_severidad.items()},
        "por_tipo": por_tipo,
        "por_verificacion": {k.value: v for k, v in por_verificacion.items()},
    }
