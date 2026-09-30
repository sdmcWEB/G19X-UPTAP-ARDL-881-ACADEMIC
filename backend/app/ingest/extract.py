"""Extracción de texto con coordenadas.

Las coordenadas son el punto de todo este módulo: sin ellas no se puede
resaltar la cláusula de riesgo sobre el documento en el visor.

Grok no acepta PDF como entrada ni tiene visión en sus modelos de texto, así
que el OCR aquí no es una comodidad: es el único camino para un escaneo. Si
Tesseract falla, no hay plan B de "mandarle la imagen al modelo".
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

from app.config import settings
from app.ingest.documento import Block, Documento

__all__ = ["Block", "Documento", "extraer", "extraer_docx", "extraer_pdf"]


def _necesita_ocr(doc: fitz.Document) -> bool:
    """¿Hay suficiente texto extraíble, o es un escaneo?

    Se decide por página: un PDF mixto (portada digital + anexos escaneados)
    también necesita OCR.
    """
    return any(len(page.get_text("text").strip()) < settings.ocr_min_chars_per_page for page in doc)


def _aplicar_ocr(pdf_bytes: bytes) -> bytes:
    """Corre OCRmyPDF y devuelve el PDF con capa de texto.

    `--skip-text` deja intactas las páginas que ya tienen texto en lugar de
    fallar, que es lo que pasa con los PDF mixtos.
    """
    with tempfile.TemporaryDirectory() as tmp:
        entrada = Path(tmp) / "in.pdf"
        salida = Path(tmp) / "out.pdf"
        entrada.write_bytes(pdf_bytes)

        subprocess.run(
            [
                "ocrmypdf",
                "--language",
                settings.ocr_lang,
                "--skip-text",
                "--deskew",
                "--clean",
                "--optimize",
                "1",
                "--quiet",
                str(entrada),
                str(salida),
            ],
            check=True,
            capture_output=True,
        )
        return salida.read_bytes()


def extraer_pdf(pdf_bytes: bytes) -> Documento:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    ocr = False

    if _necesita_ocr(doc):
        doc.close()
        pdf_bytes = _aplicar_ocr(pdf_bytes)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        ocr = True

    resultado = Documento(paginas=doc.page_count, ocr_aplicado=ocr)

    for i, page in enumerate(doc, start=1):
        resultado.dimensiones[i] = (page.rect.width, page.rect.height)
        # sort=True los devuelve en orden de lectura, no de creación
        for x0, y0, x1, y1, texto, *_ in page.get_text("blocks", sort=True):
            texto = texto.strip()
            if texto:
                resultado.bloques.append(Block(texto=texto, pagina=i, bbox=(x0, y0, x1, y1)))

    doc.close()
    return resultado


def extraer_docx(docx_bytes: bytes) -> Documento:
    """Word no tiene geometría de página: los bboxes quedan vacíos.

    El hallazgo se podrá ubicar por cláusula, pero no resaltar sobre la página.
    """
    import docx

    with tempfile.NamedTemporaryFile(suffix=".docx") as tmp:
        tmp.write(docx_bytes)
        tmp.flush()
        d = docx.Document(tmp.name)

    resultado = Documento(paginas=1)
    for p in d.paragraphs:
        texto = p.text.strip()
        if texto:
            resultado.bloques.append(Block(texto=texto, pagina=1, bbox=(0, 0, 0, 0)))
    return resultado


def extraer(contenido: bytes, mime_type: str) -> Documento:
    if mime_type == "application/pdf":
        return extraer_pdf(contenido)
    if mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return extraer_docx(contenido)
    raise ValueError(f"Tipo de archivo no soportado: {mime_type}")
