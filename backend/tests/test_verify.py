"""El verificador de citas es el componente crítico del sistema.

Si deja pasar una cita inventada, la plataforma le presenta al abogado
evidencia falsa. Estos casos son la línea de defensa.
"""

import pytest

from app.ai.verify import normalizar, verificar_cita
from app.enums import VerificationStatus

CLAUSULA = (
    "DÉCIMA PRIMERA. PENA CONVENCIONAL. En caso de incumplimiento en los plazos "
    "de entrega, EL PROVEEDOR pagará a EL CLIENTE una pena convencional del 5% "
    "(cinco por ciento) del valor total del contrato por cada día natural de "
    "retraso, sin límite máximo acumulable."
)


def test_cita_literal_es_verificada():
    estado, score = verificar_cita("sin límite máximo acumulable", CLAUSULA)
    assert estado == VerificationStatus.VERIFICADA
    assert score == 100.0


def test_cita_con_espacios_distintos_sigue_verificada():
    # El extractor colapsa saltos de línea; la cita no debe romperse por eso.
    estado, _ = verificar_cita("pena  convencional\ndel 5%", CLAUSULA)
    assert estado == VerificationStatus.VERIFICADA


def test_cita_con_comillas_tipograficas():
    clausula = 'La parte acepta las condiciones "sin reserva alguna" en este acto.'
    estado, _ = verificar_cita("sin reserva alguna", clausula)
    assert estado == VerificationStatus.VERIFICADA


def test_ruido_de_ocr_no_invalida_la_cita():
    """Tesseract confunde "l" con "I" y "0" con "O": eso no es una alucinación."""
    estado, score = verificar_cita(
        "pena convenciona1 del 5% (cinco por ciento) del vaIor total", CLAUSULA
    )
    assert estado in (VerificationStatus.VERIFICADA, VerificationStatus.APROXIMADA)
    assert score >= 80.0


def test_cita_que_omite_un_fragmento_intermedio_no_se_da_por_verificada():
    """Limitación conocida y deliberada.

    Si el modelo se salta el "(cinco por ciento)" de en medio, la cita deja de
    ser literal. El verificador es conservador a propósito: preferimos mandar el
    hallazgo a revisión que presentarle al abogado una cita que no dice eso.
    """
    estado, _ = verificar_cita("pena convencional del 5% del valor total", CLAUSULA)
    assert estado != VerificationStatus.VERIFICADA


def test_cita_inventada_es_rechazada():
    estado, score = verificar_cita(
        "El proveedor no tendrá responsabilidad alguna por daños indirectos",
        CLAUSULA,
    )
    assert estado == VerificationStatus.NO_VERIFICADA
    assert score < 80.0


def test_cita_vacia_es_rechazada():
    estado, score = verificar_cita("", CLAUSULA)
    assert estado == VerificationStatus.NO_VERIFICADA
    assert score == 0.0


def test_parafraseo_es_rechazado():
    """El caso que más importa: el modelo resume en lugar de copiar."""
    estado, _ = verificar_cita(
        "se cobrará una multa diaria sin tope por demoras en la entrega",
        CLAUSULA,
    )
    assert estado == VerificationStatus.NO_VERIFICADA


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("  hola   mundo  ", "hola mundo"),
        ("PENA\nCONVENCIONAL", "pena convencional"),
        ("com­pensación", "compensación"),  # guion suave
        ("“texto”", '"texto"'),
    ],
)
def test_normalizar(entrada, esperado):
    assert normalizar(entrada) == esperado


def test_normalizar_conserva_acentos():
    # "año" y "ano" no son lo mismo: quitar acentos cambiaría el sentido.
    assert "ñ" in normalizar("AÑO")
    assert normalizar("año") != normalizar("ano")
