"""Envoltura delgada sobre el modelo de lenguaje.

Se aísla aquí a propósito: si el proyecto cambia de proveedor de modelo, este
es el único archivo que se toca. Groq expone una API compatible con OpenAI, por
eso se usa el SDK de `openai` apuntando a su URL base.
"""

from __future__ import annotations

from functools import lru_cache

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.config import settings

# Una respuesta que no cumple el schema se pide de nuevo antes de rendirse: los
# modelos abiertos fallan el formato de vez en cuando, sobre todo en lotes largos.
INTENTOS = 3


@lru_cache
def llm() -> OpenAI:
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY no está configurada. Ponla en .env antes de analizar contratos."
        )
    # El plan gratuito de Groq limita los tokens por minuto (429): el SDK espera
    # y reintenta, pero con sus 2 intentos por defecto se rinde en lotes seguidos.
    return OpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        max_retries=8,
        timeout=120,
    )


def parsear[T: BaseModel](system_prompt: str, user_prompt: str, esquema: type[T]) -> T:
    """Una consulta al modelo cuya respuesta se valida contra `esquema`."""
    ultimo_error: ValidationError | None = None
    for _ in range(INTENTOS):
        respuesta = llm().chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": esquema.__name__,
                    "schema": esquema.model_json_schema(),
                },
            },
        )
        contenido = respuesta.choices[0].message.content or ""
        try:
            return esquema.model_validate_json(contenido)
        except ValidationError as exc:
            ultimo_error = exc
    raise RuntimeError(
        f"El modelo no devolvió una respuesta válida tras {INTENTOS} intentos."
    ) from ultimo_error
