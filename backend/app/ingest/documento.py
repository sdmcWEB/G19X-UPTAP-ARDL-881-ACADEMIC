"""Estructuras de datos del documento extraído.

Separadas de `extract.py` porque ese módulo importa PyMuPDF: el segmentador
trabaja sobre estos datos y no tiene por qué depender de una librería de PDF.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Block:
    """Un bloque de texto con su caja en la página."""

    texto: str
    pagina: int  # 1-indexado, como lo ve el usuario
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1 en puntos PDF


@dataclass
class Documento:
    bloques: list[Block] = field(default_factory=list)
    paginas: int = 0
    ocr_aplicado: bool = False
    # ancho/alto por página: el frontend necesita esto para escalar el resaltado
    dimensiones: dict[int, tuple[float, float]] = field(default_factory=dict)

    @property
    def texto_plano(self) -> str:
        return "\n".join(b.texto for b in self.bloques)
