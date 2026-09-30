"""Envoltura delgada sobre el SDK de xAI.

Se aísla aquí a propósito: si el proyecto cambia de proveedor de modelo, este
es el único archivo que se toca.
"""

from __future__ import annotations

from functools import lru_cache

from xai_sdk import Client

from app.config import settings


@lru_cache
def xai() -> Client:
    if not settings.xai_api_key:
        raise RuntimeError(
            "XAI_API_KEY no está configurada. Ponla en .env antes de analizar contratos."
        )
    return Client(api_key=settings.xai_api_key)


def nuevo_chat():
    """Una conversación nueva contra el modelo configurado."""
    return xai().chat.create(model=settings.xai_model)
