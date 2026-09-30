"""Schema de salida que el modelo está obligado a respetar.

Lo usa `chat.parse()` del SDK de xAI, que valida la respuesta contra el modelo
Pydantic. Los `description` no son documentación: son parte del prompt efectivo.
"""

from pydantic import BaseModel, Field

from app.enums import Severity


class HallazgoLLM(BaseModel):
    clause_id: str = Field(
        description="El identificador exacto de la cláusula analizada, tal como "
        "aparece entre corchetes en el documento (ejemplo: C-007). "
        "Nunca lo inventes: debe ser uno de los que recibiste."
    )
    tipo_codigo: str = Field(
        description="El código del tipo de riesgo, tomado del catálogo que se te entregó."
    )
    severidad: Severity = Field(description="Severidad del riesgo identificado.")
    titulo: str = Field(description="Resumen del riesgo en una línea, máximo 120 caracteres.")
    explicacion: str = Field(
        description="Por qué esta cláusula representa un riesgo, en 2 a 4 oraciones. "
        "Redacta para un abogado: concreto, sin relleno."
    )
    recomendacion: str = Field(
        description="Acción concreta sugerida: qué renegociar, qué agregar o qué verificar."
    )
    cita_textual: str = Field(
        description="Fragmento COPIADO PALABRA POR PALABRA de la cláusula que sustenta "
        "este hallazgo, entre 10 y 300 caracteres. No lo parafrasees, no lo corrijas, "
        "no lo completes: cópialo literal. Se valida automáticamente contra el "
        "documento y un fragmento que no exista invalida el hallazgo."
    )
    confianza: float = Field(
        ge=0.0, le=1.0, description="Qué tan seguro estás de este hallazgo, de 0 a 1."
    )


class AnalisisLLM(BaseModel):
    hallazgos: list[HallazgoLLM] = Field(
        description="Todos los riesgos encontrados. Lista vacía si la sección no tiene riesgos: "
        "no rellenes con hallazgos débiles para parecer exhaustivo."
    )
    resumen: str = Field(
        description="Panorama del riesgo de las cláusulas revisadas, máximo 3 oraciones."
    )
