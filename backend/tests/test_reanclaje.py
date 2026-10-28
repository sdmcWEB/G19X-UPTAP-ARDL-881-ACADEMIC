"""Si el modelo cita bien pero se equivoca de número de cláusula, la evidencia no se pierde."""

from app.ai import analyze
from app.ai.schemas import AnalisisLLM, HallazgoLLM
from app.enums import Severity, VerificationStatus
from app.ingest.clauses import Clausula

C1 = Clausula(
    "C-001", 1, "PRIMERA", "El PRESTADOR entregará el sistema en ciento veinte días naturales."
)
C2 = Clausula(
    "C-002",
    2,
    "SEGUNDA",
    "El PRESTADOR responderá de manera ilimitada por todos los daños y perjuicios.",
)


def _hallazgo(clause_id: str, cita: str) -> HallazgoLLM:
    return HallazgoLLM(
        clause_id=clause_id,
        tipo_codigo="RESPONSABILIDAD_ILIMITADA",
        severidad=Severity.CRITICA,
        titulo="Responsabilidad sin tope",
        explicacion="No hay límite.",
        recomendacion="Fijar un tope.",
        cita_textual=cita,
        confianza=0.9,
    )


def _analizar(monkeypatch, hallazgo: HallazgoLLM):
    respuesta = AnalisisLLM(hallazgos=[hallazgo], resumen="Resumen.")
    monkeypatch.setattr(analyze, "parsear", lambda *_a, **_k: respuesta)
    verificados, _ = analyze.analizar_lote([C1, C2], [], ocr_aplicado=False)
    return verificados[0]


def test_cita_correcta_con_cláusula_equivocada_se_reancla(monkeypatch):
    h = _analizar(
        monkeypatch, _hallazgo("C-001", "responderá de manera ilimitada por todos los daños")
    )
    assert h.clausula is C2
    assert h.verificacion == VerificationStatus.VERIFICADA


def test_cita_con_cláusula_inexistente_se_reancla(monkeypatch):
    h = _analizar(
        monkeypatch, _hallazgo("C-099", "responderá de manera ilimitada por todos los daños")
    )
    assert h.clausula is C2
    assert h.verificacion == VerificationStatus.VERIFICADA


def test_cita_que_no_existe_en_ninguna_cláusula_sigue_sin_verificar(monkeypatch):
    h = _analizar(
        monkeypatch, _hallazgo("C-002", "El CLIENTE pagará una penalización del 40% diario")
    )
    assert h.verificacion == VerificationStatus.NO_VERIFICADA


def test_cita_inventada_con_cláusula_inexistente_queda_sin_cláusula(monkeypatch):
    h = _analizar(
        monkeypatch, _hallazgo("C-099", "El CLIENTE pagará una penalización del 40% diario")
    )
    assert h.clausula is None
    assert h.verificacion == VerificationStatus.NO_VERIFICADA
