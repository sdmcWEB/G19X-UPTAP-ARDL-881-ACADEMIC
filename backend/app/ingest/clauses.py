"""Segmentación del contrato en cláusulas con identificador estable.

El `clause_id` viaja al modelo y regresa en cada hallazgo. Es la bisagra de
toda la trazabilidad: sin él no se puede volver del hallazgo a la página.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ingest.documento import Block, Documento

# Encabezados típicos en contratos mexicanos. El orden importa: el primero que
# coincide gana, así que los patrones más específicos van antes.
#
# El grupo capturado es solo la etiqueta; la puntuación final se recorta después
# para que "PRIMERA.", "PRIMERA -" y "PRIMERA:" produzcan el mismo encabezado.
_PATRONES_ENCABEZADO = [
    re.compile(r"^(CL[ÁA]USULA\s+[A-ZÁÉÍÓÚÑ0-9]+)", re.IGNORECASE),
    re.compile(r"^(ART[ÍI]CULO\s+[A-ZÁÉÍÓÚÑ0-9]+)", re.IGNORECASE),
    re.compile(
        r"^(D[ÉE]CIMA?\s+[A-ZÁÉÍÓÚÑ]+"
        r"|PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[ÉE]PTIMA|OCTAVA|NOVENA"
        r"|D[ÉE]CIMA|UND[ÉE]CIMA|DUOD[ÉE]CIMA)[.\-–—:)]",
        re.IGNORECASE,
    ),
    # Numeral tipo "1.", "3.2" o "1.1 Definiciones". La puntuación es opcional,
    # así que se exige que lo que sigue empiece en mayúscula: sin eso, un párrafo
    # que arranca con una cifra ("5 días naturales...") se leería como encabezado.
    re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)[.\-–—:)]*\s+[A-ZÁÉÍÓÚÑ]"),
    # Romanos: aquí sí se exige puntuación. Una "I" o una "V" suelta es ambigua.
    re.compile(r"^([IVXLC]{1,6})[.\-–—:)]\s+\S"),
]

# Puntuación que se recorta del final de un encabezado detectado.
_PUNTUACION_FINAL = ".-–—:)  "

# Una cláusula más larga que esto se parte: si un bloque gigante entra al
# prompt, el modelo pierde precisión y la cita se vuelve imposible de anclar.
MAX_CARACTERES_CLAUSULA = 4000


@dataclass
class Clausula:
    clause_id: str
    orden: int
    encabezado: str | None
    texto: str
    bloques: list[Block] = field(default_factory=list)

    @property
    def pagina_inicio(self) -> int:
        return min(b.pagina for b in self.bloques) if self.bloques else 1

    @property
    def pagina_fin(self) -> int:
        return max(b.pagina for b in self.bloques) if self.bloques else 1

    @property
    def bboxes(self) -> list[dict]:
        return [{"page": b.pagina, "bbox": list(b.bbox)} for b in self.bloques]


def _detectar_encabezado(texto: str) -> str | None:
    primera_linea = texto.split("\n", 1)[0].strip()
    if len(primera_linea) > 120:  # un párrafo, no un encabezado
        return None
    for patron in _PATRONES_ENCABEZADO:
        if m := patron.match(primera_linea):
            return m.group(1).strip().rstrip(_PUNTUACION_FINAL) or None
    return None


def segmentar(doc: Documento) -> list[Clausula]:
    """Agrupa bloques en cláusulas. Cada encabezado abre una nueva."""
    grupos: list[list[Block]] = []
    encabezados: list[str | None] = []

    for bloque in doc.bloques:
        encabezado = _detectar_encabezado(bloque.texto)
        abre_nueva = encabezado is not None or not grupos

        if not abre_nueva:
            actual = sum(len(b.texto) for b in grupos[-1])
            if actual + len(bloque.texto) > MAX_CARACTERES_CLAUSULA:
                abre_nueva = True
                encabezado = f"{encabezados[-1] or 'Fragmento'} (cont.)"

        if abre_nueva:
            grupos.append([bloque])
            encabezados.append(encabezado)
        else:
            grupos[-1].append(bloque)

    clausulas: list[Clausula] = []
    for i, (bloques, encabezado) in enumerate(zip(grupos, encabezados, strict=True), start=1):
        clausulas.append(
            Clausula(
                clause_id=f"C-{i:03d}",
                orden=i,
                encabezado=encabezado,
                texto="\n".join(b.texto for b in bloques).strip(),
                bloques=bloques,
            )
        )
    return clausulas


def formatear_para_prompt(clausulas: list[Clausula]) -> str:
    """Serializa las cláusulas con su id para que el modelo pueda citarlas."""
    partes = []
    for c in clausulas:
        titulo = c.encabezado or f"Cláusula {c.orden}"
        partes.append(f"[{c.clause_id}] {titulo}\n{c.texto}")
    return "\n\n---\n\n".join(partes)
