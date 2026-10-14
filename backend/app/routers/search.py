"""Búsqueda semántica sobre las cláusulas.

Responde "¿qué contratos tienen algo parecido a esto?" sin depender de que
coincidan las palabras: el abogado busca *penalización por retraso* y
encuentra una cláusula que dice *pena convencional por demora en la entrega*.

La consulta se vectoriza en la API y pgvector ordena por distancia coseno.
Vectorizar aquí mantiene el modelo cargado en el proceso que responde —cuesta
memoria residente, pero evita un viaje de ida y vuelta por Celery para una
consulta que debe sentirse inmediata.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.ai.embeddings import embed
from app.db import get_db
from app.deps import current_user
from app.models import Clause, Contract, User

router = APIRouter(prefix="/api/busqueda", tags=["búsqueda"])

# Piso absoluto: por debajo de esto la cláusula no tiene nada que ver con la
# consulta. La distancia coseno va de 0 (idéntico) a 2 (opuesto).
DISTANCIA_MAXIMA = 0.75

# Corte relativo al mejor resultado. Hace el trabajo que el piso absoluto no
# puede: dentro de un mismo contrato todas las cláusulas se parecen un poco
# entre sí, así que un umbral fijo deja pasar el documento entero. Lo que
# importa no es cuánto se parece una cláusula en abstracto, sino cuánto se
# parece comparada con la mejor.
#
# Calibrado contra un solo documento: hay que reajustarlo con un corpus real
# de contratos distintos.
RATIO_RESPECTO_AL_MEJOR = 0.75


class Coincidencia(BaseModel):
    clausula_id: uuid.UUID
    clause_id: str
    encabezado: str | None
    fragmento: str
    pagina_inicio: int
    similitud: float  # 0-1, más alto es más parecido

    contrato_id: uuid.UUID
    nombre_archivo: str


class Resultados(BaseModel):
    consulta: str
    total: int
    coincidencias: list[Coincidencia]


def _recortar(texto: str, maximo: int = 320) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= maximo else texto[: maximo - 1].rstrip() + "…"


def _acotar_a_contrato(q: Select, contrato_id: uuid.UUID | None) -> Select:
    return q if contrato_id is None else q.where(Clause.contrato_id == contrato_id)


@router.get("", response_model=Resultados)
def buscar(
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
    q: str = Query(
        ..., min_length=3, max_length=500, description="Qué buscar, en lenguaje natural"
    ),
    contrato_id: uuid.UUID | None = Query(None, description="Limitar a un solo contrato"),
    limite: int = Query(20, ge=1, le=100),
):
    vector = embed([q])[0]

    # `<=>` es distancia coseno en pgvector. Los embeddings se guardan
    # normalizados, así que la similitud es 1 - distancia.
    distancia = Clause.embedding.cosine_distance(vector).label("distancia")

    consulta = (
        select(Clause, Contract.nombre_archivo, distancia)
        .join(Contract, Contract.id == Clause.contrato_id)
        .where(Clause.embedding.is_not(None))
        .where(distancia < DISTANCIA_MAXIMA)
        .order_by(distancia)
        .limit(limite)
    )
    filas = db.execute(_acotar_a_contrato(consulta, contrato_id)).all()

    if not filas:
        return Resultados(consulta=q, total=0, coincidencias=[])

    # Las filas vienen ordenadas por distancia: la primera es la mejor.
    mejor_similitud = 1 - filas[0][2]
    piso = mejor_similitud * RATIO_RESPECTO_AL_MEJOR

    coincidencias = [
        Coincidencia(
            clausula_id=clausula.id,
            clause_id=clausula.clause_id,
            encabezado=clausula.encabezado,
            fragmento=_recortar(clausula.texto),
            pagina_inicio=clausula.pagina_inicio,
            similitud=round(1 - dist, 4),
            contrato_id=clausula.contrato_id,
            nombre_archivo=nombre,
        )
        for clausula, nombre, dist in filas
        if (1 - dist) >= piso
    ]

    return Resultados(consulta=q, total=len(coincidencias), coincidencias=coincidencias)
