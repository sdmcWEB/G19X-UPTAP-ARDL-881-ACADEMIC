"""Agregados para el tablero.

Vive en su propio router porque cruza contratos y hallazgos: no es un
sub-recurso de ninguno de los dos.

Todas las cifras respetan el mismo filtro de periodo, para que el tablero
entero hable de la misma rebanada de datos.
"""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.enums import ContractStatus, Severity, VerificationStatus
from app.models import Contract, Finding, RiskType, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# El orden de severidad es del dominio, no alfabético: la gráfica lo recibe ya
# ordenado para no reimplementar el criterio en el frontend.
ORDEN_SEVERIDAD = [
    Severity.CRITICA,
    Severity.ALTA,
    Severity.MEDIA,
    Severity.BAJA,
    Severity.INFORMATIVA,
]

# De mejor a peor evidencia: así se apila la barra de calidad de citas.
ORDEN_VERIFICACION = [
    VerificationStatus.VERIFICADA,
    VerificationStatus.APROXIMADA,
    VerificationStatus.NO_VERIFICADA,
]


class Conteo(BaseModel):
    clave: str
    etiqueta: str
    total: int


class PuntoTendencia(BaseModel):
    fecha: date
    contratos: int
    hallazgos: int


class ContratoRiesgoso(BaseModel):
    id: str
    nombre_archivo: str
    puntuacion_riesgo: float
    hallazgos: int
    ocr_aplicado: bool


class Resumen(BaseModel):
    dias: int | None
    contratos_totales: int
    contratos_analizados: int
    hallazgos_totales: int
    riesgo_promedio: float | None
    pct_citas_verificadas: float | None
    pct_con_ocr: float | None
    por_severidad: list[Conteo]
    por_verificacion: list[Conteo]
    por_tipo: list[Conteo]
    tendencia: list[PuntoTendencia]
    contratos_riesgosos: list[ContratoRiesgoso]


ETIQUETA_SEVERIDAD = {
    Severity.CRITICA: "Crítica",
    Severity.ALTA: "Alta",
    Severity.MEDIA: "Media",
    Severity.BAJA: "Baja",
    Severity.INFORMATIVA: "Informativa",
}

ETIQUETA_VERIFICACION = {
    VerificationStatus.VERIFICADA: "Verificada",
    VerificationStatus.APROXIMADA: "Aproximada",
    VerificationStatus.NO_VERIFICADA: "No verificada",
}


def _desde(dias: int | None) -> datetime | None:
    if dias is None:
        return None
    return datetime.now(UTC) - timedelta(days=dias)


def _acotar_contratos(q: Select, desde: datetime | None) -> Select:
    return q if desde is None else q.where(Contract.created_at >= desde)


def _como_fecha(valor) -> date:
    """`date()` regresa `date` en Postgres y `str` en SQLite."""
    return valor if isinstance(valor, date) else date.fromisoformat(str(valor))


def _tendencia(db: Session, desde: datetime | None, dias: int | None) -> list[PuntoTendencia]:
    """Serie diaria de contratos subidos y hallazgos generados.

    Los días sin actividad se rellenan con ceros: una línea con huecos
    insinúa una caída que no ocurrió, solo no se midió.
    """
    dia = func.date(Contract.created_at).label("dia")

    contratos = {
        _como_fecha(d): n
        for d, n in db.execute(
            _acotar_contratos(select(dia, func.count()).group_by(dia), desde)
        ).all()
    }
    hallazgos = {
        _como_fecha(d): n
        for d, n in db.execute(
            _acotar_contratos(
                select(dia, func.count(Finding.id))
                .select_from(Contract)
                .join(Finding, Finding.contrato_id == Contract.id)
                .group_by(dia),
                desde,
            )
        ).all()
    }

    return rellenar_dias(contratos, hallazgos, dias)


def rellenar_dias(
    contratos: dict[date, int],
    hallazgos: dict[date, int],
    dias: int | None,
    hoy: date | None = None,
) -> list[PuntoTendencia]:
    """Completa la serie con ceros en los días sin actividad.

    Separada de la consulta para poder probarla: el cálculo del día inicial
    es justo donde se cuela un off-by-one.
    """
    if not contratos and not hallazgos:
        return []

    fin = hoy or date.today()
    # `dias=30` significa hoy más los 29 anteriores, no 30 anteriores.
    inicio = (fin - timedelta(days=dias - 1)) if dias else min(contratos | hallazgos)

    puntos = []
    cursor = inicio
    while cursor <= fin:
        puntos.append(
            PuntoTendencia(
                fecha=cursor,
                contratos=contratos.get(cursor, 0),
                hallazgos=hallazgos.get(cursor, 0),
            )
        )
        cursor += timedelta(days=1)
    return puntos


@router.get("", response_model=Resumen)
def resumen(
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
    dias: int = Query(
        30,
        ge=0,
        le=730,
        description="Periodo en días hacia atrás, incluyendo hoy. 0 = todo el histórico.",
    ),
):
    periodo = dias or None  # 0 llega como "todo el histórico"
    desde = _desde(periodo)

    contratos_totales = db.scalar(
        _acotar_contratos(select(func.count()).select_from(Contract), desde)
    )
    contratos_analizados = db.scalar(
        _acotar_contratos(
            select(func.count())
            .select_from(Contract)
            .where(Contract.status == ContractStatus.LISTO),
            desde,
        )
    )
    con_ocr = db.scalar(
        _acotar_contratos(
            select(func.count()).select_from(Contract).where(Contract.ocr_aplicado.is_(True)),
            desde,
        )
    )
    riesgo_promedio = db.scalar(
        _acotar_contratos(select(func.avg(Contract.puntuacion_riesgo)).select_from(Contract), desde)
    )

    # Los hallazgos se acotan por la fecha de su contrato: así el periodo
    # significa lo mismo en todas las cifras del tablero.
    base_hallazgos = (
        select(func.count()).select_from(Finding).join(Contract, Contract.id == Finding.contrato_id)
    )
    hallazgos_totales = db.scalar(_acotar_contratos(base_hallazgos, desde))

    severidades = dict(
        db.execute(
            _acotar_contratos(
                select(Finding.severidad, func.count())
                .select_from(Finding)
                .join(Contract, Contract.id == Finding.contrato_id)
                .group_by(Finding.severidad),
                desde,
            )
        ).all()
    )
    verificaciones = dict(
        db.execute(
            _acotar_contratos(
                select(Finding.verificacion, func.count())
                .select_from(Finding)
                .join(Contract, Contract.id == Finding.contrato_id)
                .group_by(Finding.verificacion),
                desde,
            )
        ).all()
    )

    verificadas = verificaciones.get(VerificationStatus.VERIFICADA, 0)

    # El nombre legible sale del catálogo; si un código ya no existe en él, se
    # muestra el código crudo en lugar de perder la fila.
    nombres = dict(db.execute(select(RiskType.codigo, RiskType.nombre)).all())
    tipos = db.execute(
        _acotar_contratos(
            select(Finding.tipo_codigo, func.count())
            .select_from(Finding)
            .join(Contract, Contract.id == Finding.contrato_id)
            .group_by(Finding.tipo_codigo)
            .order_by(func.count().desc())
            .limit(10),
            desde,
        )
    ).all()

    riesgosos = db.execute(
        _acotar_contratos(
            select(
                Contract.id,
                Contract.nombre_archivo,
                Contract.puntuacion_riesgo,
                Contract.ocr_aplicado,
                func.count(Finding.id),
            )
            .select_from(Contract)
            .outerjoin(Finding, Finding.contrato_id == Contract.id)
            .where(Contract.puntuacion_riesgo.is_not(None))
            .group_by(Contract.id)
            .order_by(Contract.puntuacion_riesgo.desc())
            .limit(5),
            desde,
        )
    ).all()

    return Resumen(
        dias=periodo,
        contratos_totales=contratos_totales or 0,
        contratos_analizados=contratos_analizados or 0,
        hallazgos_totales=hallazgos_totales or 0,
        riesgo_promedio=round(riesgo_promedio, 1) if riesgo_promedio is not None else None,
        pct_citas_verificadas=(
            round(verificadas / hallazgos_totales * 100, 1) if hallazgos_totales else None
        ),
        pct_con_ocr=(
            round((con_ocr or 0) / contratos_totales * 100, 1) if contratos_totales else None
        ),
        por_severidad=[
            Conteo(clave=s.value, etiqueta=ETIQUETA_SEVERIDAD[s], total=severidades.get(s, 0))
            for s in ORDEN_SEVERIDAD
        ],
        por_verificacion=[
            Conteo(clave=v.value, etiqueta=ETIQUETA_VERIFICACION[v], total=verificaciones.get(v, 0))
            for v in ORDEN_VERIFICACION
        ],
        por_tipo=[
            Conteo(clave=codigo, etiqueta=nombres.get(codigo, codigo), total=total)
            for codigo, total in tipos
        ],
        tendencia=_tendencia(db, desde, periodo),
        contratos_riesgosos=[
            ContratoRiesgoso(
                id=str(cid),
                nombre_archivo=nombre,
                puntuacion_riesgo=puntuacion,
                hallazgos=n,
                ocr_aplicado=ocr,
            )
            for cid, nombre, puntuacion, ocr, n in riesgosos
        ],
    )
