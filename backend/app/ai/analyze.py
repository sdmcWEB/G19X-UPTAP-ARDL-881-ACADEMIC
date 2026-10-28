"""Orquestación del análisis: prompt, llamada al modelo y anclaje de citas."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.client import parsear
from app.ai.schemas import AnalisisLLM, HallazgoLLM
from app.ai.verify import verificar_cita
from app.enums import VerificationStatus
from app.ingest.clauses import Clausula, formatear_para_prompt

# Cuántas cláusulas van por llamada. El contexto del modelo alcanza para
# mucho más: lotes chicos dan citas más precisas, aíslan fallas y caben en los
# límites de tokens por minuto del plan gratuito.
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


def _buscar_cita(
    cita: str, clausulas: list[Clausula]
) -> tuple[Clausula | None, VerificationStatus, float]:
    """La cláusula del lote donde mejor aparece la cita, si aparece de verdad."""
    mejor: tuple[Clausula | None, VerificationStatus, float] = (
        None,
        VerificationStatus.NO_VERIFICADA,
        0.0,
    )
    for c in clausulas:
        estado, score = verificar_cita(cita, c.texto)
        if estado != VerificationStatus.NO_VERIFICADA and score > mejor[2]:
            mejor = (c, estado, score)
    return mejor


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

    analisis = parsear(
        SYSTEM_PROMPT,
        f"{_prompt_catalogo(catalogo)}{aviso_ocr}\n\n"
        f"CLÁUSULAS A ANALIZAR:\n\n{formatear_para_prompt(clausulas)}",
        AnalisisLLM,
    )

    verificados: list[HallazgoVerificado] = []
    for h in analisis.hallazgos:
        clausula = indice.get(h.clause_id)
        estado, score = (
            verificar_cita(h.cita_textual, clausula.texto)
            if clausula
            else (VerificationStatus.NO_VERIFICADA, 0.0)
        )

        if estado == VerificationStatus.NO_VERIFICADA:
            # El modelo suele acertar la cita y errar el número de cláusula. Si
            # el texto citado aparece en otra cláusula del lote, la evidencia es
            # real y solo estaba mal ubicada; si no aparece en ninguna, el
            # hallazgo se conserva sin evidencia anclada.
            otra, otro_estado, otro_score = _buscar_cita(h.cita_textual, clausulas)
            if otra is not None:
                clausula, estado, score = otra, otro_estado, otro_score
            elif clausula is None:
                verificados.append(
                    HallazgoVerificado(h, None, VerificationStatus.NO_VERIFICADA, 0.0)
                )
                continue

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
