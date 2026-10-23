"""El reporte es el documento que sale del sistema y llega a un abogado.

Las pruebas lo generan y luego lo abren con PyMuPDF para leer lo que quedó
impreso: no basta con que el PDF se construya sin reventar, tiene que decir lo
que debe decir.
"""

import fitz
import pytest

from app.enums import ReviewStatus, Severity, VerificationStatus
from app.reportes.pdf import construir_reporte

CONTRATO = {
    "nombre_archivo": "Contrato_Servicios_Acme.pdf",
    "paginas": 12,
    "ocr_aplicado": False,
    "puntuacion_riesgo": 78.4,
}


def hallazgo(**cambios):
    base = {
        "titulo": "Pena convencional sin tope acumulable",
        "tipo_codigo": "PENALIZACION_DESPROPORCIONADA",
        "severidad": Severity.ALTA,
        "explicacion": "La cláusula fija una pena diaria sin límite máximo.",
        "recomendacion": "Negociar un tope equivalente al 20% del valor del contrato.",
        "cita_textual": "sin límite máximo acumulable",
        "verificacion": VerificationStatus.VERIFICADA,
        "score_similitud": 100.0,
        "clausula": "DÉCIMA PRIMERA",
        "pagina": 7,
        "revision": ReviewStatus.PENDIENTE,
        "comentario_revision": None,
        "revisado_por": None,
        "revisado_at": None,
    }
    return {**base, **cambios}


def texto_de(pdf: bytes) -> str:
    with fitz.open(stream=pdf, filetype="pdf") as d:
        return "\n".join(p.get_text() for p in d)


def test_produce_un_pdf_valido():
    pdf = construir_reporte(CONTRATO, [hallazgo()])
    assert pdf.startswith(b"%PDF")
    with fitz.open(stream=pdf, filetype="pdf") as d:
        assert d.page_count >= 1


def test_imprime_los_datos_del_contrato():
    t = texto_de(construir_reporte(CONTRATO, [hallazgo()]))
    assert "Contrato_Servicios_Acme.pdf" in t
    assert "12 páginas" in t
    assert "78/100" in t


def test_imprime_el_hallazgo_completo():
    t = texto_de(construir_reporte(CONTRATO, [hallazgo()]))
    assert "Pena convencional sin tope acumulable" in t
    assert "PENALIZACION_DESPROPORCIONADA" in t
    assert "DÉCIMA PRIMERA" in t
    assert "página 7" in t
    assert "sin límite máximo acumulable" in t
    assert "Negociar un tope" in t


def test_una_cita_no_verificada_se_marca_sin_ambigüedad():
    """El punto entero del sistema: en el papel no puede leerse igual que una
    verificada."""
    pdf = construir_reporte(CONTRATO, [hallazgo(verificacion=VerificationStatus.NO_VERIFICADA)])
    t = texto_de(pdf)
    assert "NO VERIFICADA" in t
    assert "no usar como evidencia" in t.lower()


def test_el_resumen_cuenta_las_citas_sin_confirmar():
    pdf = construir_reporte(
        CONTRATO,
        [
            hallazgo(),
            hallazgo(verificacion=VerificationStatus.NO_VERIFICADA),
            hallazgo(verificacion=VerificationStatus.NO_VERIFICADA),
        ],
    )
    t = texto_de(pdf)
    assert "2 de 3 citas no pudieron confirmarse" in t


def test_cuando_todo_está_verificado_lo_dice():
    t = texto_de(construir_reporte(CONTRATO, [hallazgo(), hallazgo()]))
    assert "Todas las citas de este reporte se confirmaron" in t


def test_los_hallazgos_van_de_mayor_a_menor_severidad():
    pdf = construir_reporte(
        CONTRATO,
        [
            hallazgo(titulo="El leve", severidad=Severity.BAJA),
            hallazgo(titulo="El grave", severidad=Severity.CRITICA),
            hallazgo(titulo="El medio", severidad=Severity.MEDIA),
        ],
    )
    t = texto_de(pdf)
    assert t.index("El grave") < t.index("El medio") < t.index("El leve")


def test_un_contrato_sin_hallazgos_no_queda_en_blanco():
    t = texto_de(construir_reporte(CONTRATO, []))
    assert "No se identificaron cláusulas de riesgo" in t


def test_el_aviso_de_ocr_solo_aparece_si_hubo_ocr():
    con = texto_de(construir_reporte({**CONTRATO, "ocr_aplicado": True}, [hallazgo()]))
    sin = texto_de(construir_reporte(CONTRATO, [hallazgo()]))
    assert "procesado con OCR" in con
    assert "procesado con OCR" not in sin


def test_lleva_el_descargo_de_responsabilidad():
    t = texto_de(construir_reporte(CONTRATO, [hallazgo()]))
    assert "no sustituye la revisión jurídica" in t


@pytest.mark.parametrize(
    "peligroso",
    [
        "El proveedor <b>no</b> responderá por daños & perjuicios",
        "Cláusula con <script>alert(1)</script> dentro",
        "Condición: a < b y c > d",
    ],
)
def test_el_texto_del_contrato_no_se_interpreta_como_marcado(peligroso):
    """ReportLab lee marcado en los párrafos. Un `<` suelto en un contrato
    real rompería el documento entero."""
    pdf = construir_reporte(CONTRATO, [hallazgo(explicacion=peligroso)])
    assert pdf.startswith(b"%PDF")
    assert texto_de(pdf).count("Pena convencional") >= 1


def test_un_contrato_largo_pagina_sin_perder_hallazgos():
    pdf = construir_reporte(CONTRATO, [hallazgo(titulo=f"Riesgo {i}") for i in range(25)])
    t = texto_de(pdf)
    with fitz.open(stream=pdf, filetype="pdf") as d:
        assert d.page_count > 1
    for i in range(25):
        assert f"Riesgo {i}" in t


def test_sin_puntuacion_de_riesgo_no_imprime_una_inventada():
    t = texto_de(construir_reporte({**CONTRATO, "puntuacion_riesgo": None}, [hallazgo()]))
    assert "/100" not in t


def test_la_cláusula_se_nombra_como_tal():
    """Un encabezado numérico suelto ("4 · página 2") se lee como un número
    perdido, no como la ubicación del hallazgo."""
    t = texto_de(construir_reporte(CONTRATO, [hallazgo(clausula="4", pagina=2)]))
    assert "Cláusula 4 · página 2" in t


def test_un_hallazgo_sin_cláusula_lo_dice():
    t = texto_de(construir_reporte(CONTRATO, [hallazgo(clausula=None, pagina=None)]))
    assert "Sin cláusula asociada" in t


# --- Dictamen del abogado ---


def test_un_hallazgo_confirmado_lleva_quién_y_cuándo():
    from datetime import datetime

    from app.enums import ReviewStatus

    t = texto_de(
        construir_reporte(
            CONTRATO,
            [
                hallazgo(
                    revision=ReviewStatus.CONFIRMADO,
                    revisado_por="Lic. Hannia Nájera",
                    revisado_at=datetime(2026, 10, 23, 11, 30),
                    comentario_revision="Hay que negociar el tope antes de firmar.",
                )
            ],
        )
    )
    assert "Confirmado por Lic. Hannia Nájera el 23/10/2026" in t
    assert "Hay que negociar el tope" in t


def test_un_hallazgo_descartado_dice_el_motivo():
    from app.enums import ReviewStatus

    t = texto_de(
        construir_reporte(
            CONTRATO,
            [
                hallazgo(
                    revision=ReviewStatus.DESCARTADO,
                    revisado_por="Lic. Hannia Nájera",
                    comentario_revision="El anexo B ya acota la pena.",
                )
            ],
        )
    )
    assert "Descartado por" in t
    assert "El anexo B ya acota la pena" in t


def test_lo_no_revisado_se_marca_como_tal():
    """Un hallazgo sin revisar no puede leerse como si alguien lo respaldara."""
    t = texto_de(construir_reporte(CONTRATO, [hallazgo()]))
    assert "Sin revisar" in t
    assert "1 de 1 hallazgos siguen sin revisión humana" in t


def test_cuando_todo_está_revisado_lo_dice():
    from app.enums import ReviewStatus

    t = texto_de(
        construir_reporte(
            CONTRATO,
            [hallazgo(revision=ReviewStatus.CONFIRMADO, revisado_por="Ana")],
        )
    )
    assert "Todos los hallazgos de este reporte fueron revisados" in t
