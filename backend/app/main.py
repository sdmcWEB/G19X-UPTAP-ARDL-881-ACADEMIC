import logging
import threading
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, contracts, dashboard, findings, search

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Carga bge-m3 en segundo plano al arrancar.

    Son ~20 s de carga desde el volumen. En un hilo aparte para que la API
    quede sana de inmediato y la primera búsqueda no se los coma; si alguien
    busca antes de que termine, `embed` espera a que el lru_cache resuelva.
    """

    def precalentar():
        try:
            from app.ai.embeddings import embed

            embed(["precalentamiento"])
            structlog.get_logger().info("modelo_de_embeddings_listo")
        except Exception as exc:  # el worker es quien lo necesita de verdad
            structlog.get_logger().warning("precalentamiento_fallido", error=str(exc))

    threading.Thread(target=precalentar, daemon=True).start()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Plataforma de Identificación de Riesgos Contractuales",
    description=(
        "Análisis de contratos con IA: detecta cláusulas de riesgo y ancla cada "
        "hallazgo a su ubicación exacta en el documento."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(findings.router)
app.include_router(dashboard.router)
app.include_router(search.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
