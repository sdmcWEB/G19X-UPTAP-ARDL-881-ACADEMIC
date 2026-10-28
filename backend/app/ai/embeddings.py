"""Embeddings locales con bge-m3.

Groq no expone un endpoint de embeddings, así que esto corre en el worker. El
modelo pesa ~2 GB y se descarga en el primer uso: por eso el volumen
`hfcache` en docker-compose, para no re-descargarlo en cada build.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings


@lru_cache
def _modelo():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            "sentence-transformers no está instalado. Es el extra `ml`: "
            'pip install -e ".[ml]". El worker lo necesita; la API y los tests no.'
        ) from exc

    return SentenceTransformer(settings.embedding_model)


def embed(textos: list[str]) -> list[list[float]]:
    if not textos:
        return []
    vectores = _modelo().encode(
        textos,
        normalize_embeddings=True,  # permite usar distancia coseno en pgvector
        show_progress_bar=False,
    )
    return [v.tolist() for v in vectores]
