"""El cliente del modelo reintenta cuando la respuesta no cumple el schema."""

from types import SimpleNamespace

import pytest

from app.ai import client
from app.ai.schemas import AnalisisLLM


class _FalsoLLM:
    def __init__(self, respuestas: list[str]):
        self.respuestas = list(respuestas)
        self.llamadas = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **_kwargs):
        self.llamadas += 1
        contenido = self.respuestas.pop(0)
        mensaje = SimpleNamespace(content=contenido)
        return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


def test_reintenta_hasta_obtener_una_respuesta_valida(monkeypatch):
    falso = _FalsoLLM(["no es json", '{"hallazgos": [], "resumen": "Sin riesgos."}'])
    monkeypatch.setattr(client, "llm", lambda: falso)

    analisis = client.parsear("sistema", "usuario", AnalisisLLM)

    assert analisis.hallazgos == []
    assert falso.llamadas == 2


def test_se_rinde_tras_los_intentos_permitidos(monkeypatch):
    falso = _FalsoLLM(["basura"] * client.INTENTOS)
    monkeypatch.setattr(client, "llm", lambda: falso)

    with pytest.raises(RuntimeError, match="respuesta válida"):
        client.parsear("sistema", "usuario", AnalisisLLM)

    assert falso.llamadas == client.INTENTOS
