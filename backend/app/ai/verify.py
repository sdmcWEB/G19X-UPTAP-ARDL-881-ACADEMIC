"""Verificación de citas: el paso que separa un dato de una afirmación.

El modelo devuelve la cita que supuestamente sustenta cada hallazgo. Aquí se
confronta contra el texto real de la cláusula. Una cita que no aparece en el
documento no se le muestra al abogado como evidencia.
"""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

from app.enums import VerificationStatus

# Coincidencia casi exacta: se acepta como evidencia.
UMBRAL_VERIFICADA = 95.0
# Coincidencia parcial: probablemente el OCR alteró caracteres. Se marca para revisión.
UMBRAL_APROXIMADA = 80.0


def normalizar(texto: str) -> str:
    """Quita el ruido que no cambia el sentido legal del texto.

    Se conservan los acentos: en español distinguen palabras. Sí se normaliza
    la forma Unicode, porque el OCR mezcla composiciones NFC y NFD para la
    misma letra acentuada.
    """
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("­", "")  # guion suave del OCR
    texto = re.sub(r"[“”«»]", '"', texto)
    texto = re.sub(r"[‘’]", "'", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip().lower()


def verificar_cita(cita: str, texto_clausula: str) -> tuple[VerificationStatus, float]:
    """Devuelve el estado de la cita y su score de similitud (0-100)."""
    cita_n = normalizar(cita)
    clausula_n = normalizar(texto_clausula)

    if not cita_n or not clausula_n:
        return VerificationStatus.NO_VERIFICADA, 0.0

    # Coincidencia literal: el caso bueno, sin costo de fuzzy matching.
    if cita_n in clausula_n:
        return VerificationStatus.VERIFICADA, 100.0

    # partial_ratio busca la mejor subcadena, que es exactamente el problema:
    # una cita corta dentro de una cláusula larga.
    score = fuzz.partial_ratio(cita_n, clausula_n)

    if score >= UMBRAL_VERIFICADA:
        return VerificationStatus.VERIFICADA, score
    if score >= UMBRAL_APROXIMADA:
        return VerificationStatus.APROXIMADA, score
    return VerificationStatus.NO_VERIFICADA, score
