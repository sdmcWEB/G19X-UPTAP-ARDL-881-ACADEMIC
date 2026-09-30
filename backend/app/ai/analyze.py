"""Orquestación del análisis: prompt, llamada al modelo y anclaje de citas."""

from __future__ import annotations

from dataclasses import dataclass

from xai_sdk.chat import system, user

from app.ai.client import nuevo_chat
from app.ai.schemas import AnalisisLLM, HallazgoLLM
from app.ai.verify import verificar_cita
from app.enums import VerificationStatus
from app.ingest.clauses import Clausula, formatear_para_prompt

# Cuántas cláusulas van por llamada. Grok 4.7 tiene 500k de contexto, así que
# el límite no es técnico: lotes chicos dan citas más precisas y aíslan fallas.
CLAUSULAS_POR_LOTE = 12

SYSTEM_PROMPT = """\
Eres un analista de riesgos contractuales. Revisas contratos bajo derecho \
mexicano para el equipo jurídico y tu trabajo es señalar riesgos reales, no \
producir volumen.

Reglas que no se negocian:

1. Solo reportas riesgos que estén sustentados en el texto que recibiste. Si una \
cláusula no tiene riesgo relevante, no la reportas.
2. `cita_textual` se copia palabra por palabra del contrato. No la parafraseas, \
no le corriges la ortografía, no la completas. Cada cita se valida contra el \
documento y una que no exista invalida el hallazgo completo.
3. `clause_id` es uno de los identificadores que recibiste entre corchetes. \
Jamás lo inventas.
4. `tipo_codigo` sale del catálogo de riesgos que se te entregó. Si un riesgo \
real no encaja en ningún código, usa `OTRO` y explícalo.
5. Si el texto viene de un escaneo puede traer errores de OCR. Cuando una \
cláusula sea ilegible, dilo en la explicación en lugar de adivinar qué decía.

Escribes en español, en tono profesional y directo."""


@dataclass
class HallazgoVerificado:
    """Un hallazgo del modelo ya confrontado contra el documento."""

    llm: HallazgoLLM
    clausula: Clausula | None
    verificacion: VerificationStatus
    score_similitud: float


def _prompt_catalogo(catalogo: list[dict]) -> str:
    lineas = [
        f"- `{r['codigo']}` — {r['nombre']}: {r['descripcion']}"
        for r in catalogo
        if r.get("activo", True)
    ]
    lineas.append("- `OTRO` — Otro riesgo relevante que no encaja en los códigos anteriores.")
    return "CATÁLOGO DE TIPOS DE RIESGO:\n" + "\n".join(lineas)


def analizar_lote(
    clausulas: list[Clausula],
    catalogo: list[dict],
    ocr_aplicado: bool,
) -> tuple[list[HallazgoVerificado], str]:
    """Analiza un lote de cláusulas y ancla cada cita al documento."""
    indice = {c.clause_id: c for c in clausulas}

    aviso_ocr = (
        "\n\nATENCIÓN: este documento se procesó con OCR. Puede haber palabras "
        "mal reconocidas. No corrijas las citas para compensarlo.\n"
        if ocr_aplicado
        else ""
    )

    chat = nuevo_chat()
    chat.append(system(SYSTEM_PROMPT))
    chat.append(
        user(
            f"{_prompt_catalogo(catalogo)}{aviso_ocr}\n\n"
            f"CLÁUSULAS A ANALIZAR:\n\n{formatear_para_prompt(clausulas)}"
        )
    )

    _, analisis = chat.parse(AnalisisLLM)

    verificados: list[HallazgoVerificado] = []
    for h in analisis.hallazgos:
        clausula = indice.get(h.clause_id)
        if clausula is None:
            # El modelo citó una cláusula que no existe en este lote: se
            # conserva el hallazgo pero sin evidencia anclada.
            verificados.append(HallazgoVerificado(h, None, VerificationStatus.NO_VERIFICADA, 0.0))
            continue

        estado, score = verificar_cita(h.cita_textual, clausula.texto)
        verificados.append(HallazgoVerificado(h, clausula, estado, score))

    return verificados, analisis.resumen


def lotes(clausulas: list[Clausula], tamano: int = CLAUSULAS_POR_LOTE):
    for i in range(0, len(clausulas), tamano):
        yield clausulas[i : i + tamano]


# Pesos para la puntuación agregada de riesgo del contrato (0-100).
_PESO_SEVERIDAD = {
    "critica": 100.0,
    "alta": 70.0,
    "media": 40.0,
    "baja": 15.0,
    "informativa": 5.0,
}


def puntuacion_riesgo(hallazgos: list[HallazgoVerificado]) -> float:
    """Puntuación 0-100 del contrato.

    Manda el hallazgo más grave, no el promedio: un contrato con una cláusula
    crítica es un contrato riesgoso aunque las otras cuarenta estén limpias.
    Los hallazgos no verificados pesan la mitad, porque su evidencia no se pudo
    confirmar contra el documento.
    """
    if not hallazgos:
        return 0.0

    valores = []
    for h in hallazgos:
        base = _PESO_SEVERIDAD.get(h.llm.severidad.value, 20.0)
        if h.verificacion == VerificationStatus.NO_VERIFICADA:
            base *= 0.5
        elif h.verificacion == VerificationStatus.APROXIMADA:
            base *= 0.85
        valores.append(base * h.llm.confianza)

    maximo = max(valores)
    # Un pequeño empujón por acumulación, con techo en 100.
    extra = min(sum(sorted(valores, reverse=True)[1:]) * 0.05, 100.0 - maximo)
    return round(min(maximo + extra, 100.0), 1)
