import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app import storage
from app.audit import registrar
from app.db import get_db
from app.deps import current_user, require_roles
from app.models import Contract, ContractStatus, Role, User
from app.schemas import ContratoDetalle, ContratoOut
from app.tasks import analizar_contrato

router = APIRouter(prefix="/api/contratos", tags=["contratos"])

MIMES_PERMITIDOS = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("", response_model=ContratoOut, status_code=201)
async def subir(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ADMIN, Role.JURIDICO)),
):
    if archivo.content_type not in MIMES_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Solo se aceptan archivos PDF o Word (.docx)",
        )

    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo excede 50 MB")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    contrato_id = uuid.uuid4()
    object_key = f"{contrato_id}/{archivo.filename}"
    storage.put(object_key, contenido, archivo.content_type)

    contrato = Contract(
        id=contrato_id,
        nombre_archivo=archivo.filename or "sin-nombre",
        object_key=object_key,
        mime_type=archivo.content_type,
        subido_por_id=user.id,
        status=ContractStatus.RECIBIDO,
    )
    db.add(contrato)
    registrar(
        db,
        user,
        "subir_contrato",
        "contrato",
        str(contrato_id),
        {"archivo": archivo.filename, "bytes": len(contenido)},
    )
    db.commit()

    analizar_contrato.delay(str(contrato_id))
    return contrato


@router.get("", response_model=list[ContratoOut])
def listar(
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
    status_filtro: ContractStatus | None = Query(None, alias="status"),
    limite: int = Query(50, le=200),
    offset: int = 0,
):
    q = select(Contract).order_by(desc(Contract.created_at)).limit(limite).offset(offset)
    if status_filtro is not None:
        q = q.where(Contract.status == status_filtro)
    return db.scalars(q).all()


@router.get("/{contrato_id}", response_model=ContratoDetalle)
def detalle(
    contrato_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    contrato = db.scalar(
        select(Contract)
        .where(Contract.id == contrato_id)
        .options(selectinload(Contract.hallazgos), selectinload(Contract.clausulas))
    )
    if contrato is None:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    return contrato


@router.get("/{contrato_id}/archivo")
def descargar(
    contrato_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    """Sirve el PDF original para el visor del frontend."""
    contrato = db.get(Contract, contrato_id)
    if contrato is None:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")

    return Response(
        content=storage.get(contrato.object_key),
        media_type=contrato.mime_type,
        headers={"Content-Disposition": f'inline; filename="{contrato.nombre_archivo}"'},
    )


@router.post("/{contrato_id}/reanalizar", response_model=ContratoOut)
def reanalizar(
    contrato_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ADMIN, Role.JURIDICO)),
):
    """Vuelve a correr el pipeline. Útil tras cambiar el catálogo de riesgos."""
    contrato = db.get(Contract, contrato_id)
    if contrato is None:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    if contrato.status in (ContractStatus.EXTRAYENDO, ContractStatus.ANALIZANDO):
        raise HTTPException(status_code=409, detail="Ese contrato ya se está analizando")

    # El pipeline reinserta cláusulas y hallazgos: hay que limpiar los previos.
    for h in contrato.hallazgos:
        db.delete(h)
    for c in contrato.clausulas:
        db.delete(c)
    contrato.status = ContractStatus.RECIBIDO
    contrato.error_msg = None
    contrato.puntuacion_riesgo = None
    registrar(db, user, "reanalizar_contrato", "contrato", str(contrato_id))
    db.commit()

    analizar_contrato.delay(str(contrato_id))
    return contrato
