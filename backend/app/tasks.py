"""Pipeline de análisis de un contrato.

Corre en Celery, no en el request: entre el OCR y varias llamadas al modelo,
un contrato largo tarda minutos.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import structlog
from sqlalchemy import select

from app import storage
from app.ai.analyze import analizar_lote, lotes, puntuacion_riesgo
from app.ai.embeddings import embed
from app.celery_app import celery
from app.db import SessionLocal
from app.ingest.clauses import segmentar
from app.ingest.extract import extraer
from app.models import Clause, Contract, ContractStatus, Finding, RiskType

log = structlog.get_logger()

_SEED_CATALOGO = Path(__file__).parent.parent / "seeds" / "risk_types.json"


def _catalogo(db) -> list[dict]:
    """Catálogo de riesgos desde la BD, con el seed como respaldo."""
    tipos = db.scalars(select(RiskType).where(RiskType.activo.is_(True))).all()
    if tipos:
        return [
            {
                "codigo": t.codigo,
                "nombre": t.nombre,
                "descripcion": t.descripcion,
                "activo": t.activo,
            }
            for t in tipos
        ]
    log.warning("catalogo_vacio_usando_seed")
    return json.loads(_SEED_CATALOGO.read_text(encoding="utf-8"))


@celery.task(name="app.tasks.analizar_contrato", bind=True, max_retries=2)
def analizar_contrato(self, contrato_id: str) -> dict:
    db = SessionLocal()
    try:
        contrato = db.get(Contract, contrato_id)
        if contrato is None:
            raise ValueError(f"Contrato {contrato_id} no existe")

        # --- 1. Extracción (+ OCR si hace falta) ---
        contrato.status = ContractStatus.EXTRAYENDO
        db.commit()

        contenido = storage.get(contrato.object_key)
        doc = extraer(contenido, contrato.mime_type)

        contrato.paginas = doc.paginas
        contrato.ocr_aplicado = doc.ocr_aplicado
        db.commit()

        if not doc.bloques:
            raise ValueError(
                "No se extrajo texto del documento. "
                "Si es un escaneo, revisa la calidad de la imagen."
            )

        # --- 2. Segmentación en cláusulas ---
        clausulas = segmentar(doc)
        log.info(
            "contrato_segmentado",
            contrato_id=contrato_id,
            clausulas=len(clausulas),
            paginas=doc.paginas,
            ocr=doc.ocr_aplicado,
        )

        vectores = embed([c.texto for c in clausulas])
        filas_clausulas = {}
        for c, vector in zip(clausulas, vectores, strict=True):
            fila = Clause(
                contrato_id=contrato.id,
                clause_id=c.clause_id,
                orden=c.orden,
                encabezado=c.encabezado,
                texto=c.texto,
                pagina_inicio=c.pagina_inicio,
                pagina_fin=c.pagina_fin,
                bboxes=c.bboxes,
                embedding=vector,
            )
            db.add(fila)
            filas_clausulas[c.clause_id] = fila
        db.commit()

        # --- 3. Análisis por lotes ---
        contrato.status = ContractStatus.ANALIZANDO
        db.commit()

        catalogo = _catalogo(db)
        todos = []
        for lote in lotes(clausulas):
            verificados, _ = analizar_lote(lote, catalogo, doc.ocr_aplicado)
            todos.extend(verificados)

            for h in verificados:
                fila = filas_clausulas.get(h.clausula.clause_id) if h.clausula else None
                db.add(
                    Finding(
                        contrato_id=contrato.id,
                        clausula_id=fila.id if fila else None,
                        tipo_codigo=h.llm.tipo_codigo,
                        severidad=h.llm.severidad,
                        titulo=h.llm.titulo[:512],
                        explicacion=h.llm.explicacion,
                        recomendacion=h.llm.recomendacion,
                        cita_textual=h.llm.cita_textual,
                        verificacion=h.verificacion,
                        score_similitud=h.score_similitud,
                        confianza_modelo=h.llm.confianza,
                    )
                )
            db.commit()

        # --- 4. Cierre ---
        contrato.puntuacion_riesgo = puntuacion_riesgo(todos)
        contrato.status = ContractStatus.LISTO
        contrato.analizado_at = datetime.now(UTC)
        db.commit()

        no_verificados = sum(1 for h in todos if h.verificacion.value == "no_verificada")
        log.info(
            "contrato_analizado",
            contrato_id=contrato_id,
            hallazgos=len(todos),
            no_verificados=no_verificados,
            puntuacion=contrato.puntuacion_riesgo,
        )
        return {
            "contrato_id": contrato_id,
            "hallazgos": len(todos),
            "no_verificados": no_verificados,
            "puntuacion_riesgo": contrato.puntuacion_riesgo,
        }

    except Exception as exc:
        db.rollback()
        contrato = db.get(Contract, contrato_id)
        if contrato is not None:
            contrato.status = ContractStatus.ERROR
            contrato.error_msg = str(exc)[:2000]
            db.commit()
        log.error("analisis_fallido", contrato_id=contrato_id, error=str(exc))
        raise
    finally:
        db.close()
