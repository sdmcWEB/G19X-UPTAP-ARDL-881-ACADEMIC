import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, contracts, findings

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

app = FastAPI(
    title="Plataforma de Identificación de Riesgos Contractuales",
    description=(
        "Análisis de contratos con IA: detecta cláusulas de riesgo y ancla cada "
        "hallazgo a su ubicación exacta en el documento."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(findings.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
