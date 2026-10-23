"""Reporte de revisión en PDF: lo que el abogado se lleva.

Recibe datos planos, no objetos de la base, para poder construirse y probarse
sin una sesión abierta.

La decisión de diseño que manda sobre todas: **un hallazgo cuya cita no se
pudo confirmar se ve distinto**. Si en el papel un hallazgo verificado y uno
inventado se leen igual, el documento traiciona el propósito del sistema.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.enums import ReviewStatus, Severity, VerificationStatus

TINTA = colors.HexColor("#0b0b0b")
TENUE = colors.HexColor("#52514e")
APAGADO = colors.HexColor("#898781")
LINEA = colors.HexColor("#e1e0d9")

COLOR_SEVERIDAD = {
    Severity.CRITICA: colors.HexColor("#d03b3b"),
    Severity.ALTA: colors.HexColor("#ec835a"),
    Severity.MEDIA: colors.HexColor("#fab219"),
    Severity.BAJA: colors.HexColor("#898781"),
    Severity.INFORMATIVA: colors.HexColor("#c3c2b7"),
}

ETIQUETA_SEVERIDAD = {
    Severity.CRITICA: "CRÍTICA",
    Severity.ALTA: "ALTA",
    Severity.MEDIA: "MEDIA",
    Severity.BAJA: "BAJA",
    Severity.INFORMATIVA: "INFORMATIVA",
}

ORDEN_SEVERIDAD = {
    Severity.CRITICA: 0,
    Severity.ALTA: 1,
    Severity.MEDIA: 2,
    Severity.BAJA: 3,
    Severity.INFORMATIVA: 4,
}

ETIQUETA_VERIFICACION = {
    VerificationStatus.VERIFICADA: "Cita verificada contra el documento",
    VerificationStatus.APROXIMADA: "Cita aproximada — revisar contra el original",
    VerificationStatus.NO_VERIFICADA: "CITA NO VERIFICADA — no usar como evidencia",
}

ETIQUETA_REVISION = {
    ReviewStatus.CONFIRMADO: "Confirmado por",
    ReviewStatus.DESCARTADO: "Descartado por",
    ReviewStatus.PENDIENTE: "Sin revisar",
}

COLOR_REVISION = {
    ReviewStatus.CONFIRMADO: colors.HexColor("#0ca30c"),
    ReviewStatus.DESCARTADO: APAGADO,
    ReviewStatus.PENDIENTE: colors.HexColor("#b07c0a"),
}

COLOR_VERIFICACION = {
    VerificationStatus.VERIFICADA: colors.HexColor("#0ca30c"),
    VerificationStatus.APROXIMADA: colors.HexColor("#b07c0a"),
    VerificationStatus.NO_VERIFICADA: colors.HexColor("#d03b3b"),
}


def _estilos() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo",
            parent=base["Title"],
            fontSize=16,
            leading=20,
            alignment=0,
            textColor=TINTA,
            spaceAfter=2,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo",
            parent=base["Normal"],
            fontSize=9,
            leading=13,
            textColor=APAGADO,
        ),
        "seccion": ParagraphStyle(
            "seccion",
            parent=base["Heading2"],
            fontSize=11,
            leading=14,
            textColor=TINTA,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo",
            parent=base["Normal"],
            fontSize=9.5,
            leading=13.5,
            textColor=TINTA,
            alignment=TA_JUSTIFY,
        ),
        "tenue": ParagraphStyle(
            "tenue",
            parent=base["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=TENUE,
        ),
        "cita": ParagraphStyle(
            "cita",
            parent=base["Normal"],
            fontSize=9,
            leading=13,
            textColor=TENUE,
            leftIndent=8,
            fontName="Helvetica-Oblique",
        ),
        "hallazgo": ParagraphStyle(
            "hallazgo",
            parent=base["Normal"],
            fontSize=10.5,
            leading=14,
            textColor=TINTA,
            fontName="Helvetica-Bold",
        ),
    }


def _escapar(texto: str) -> str:
    """ReportLab interpreta marcado en los párrafos; el texto del contrato no
    es marcado y un `<` suelto reventaría el documento."""
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _encabezado_y_pie(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(APAGADO)
    canvas.drawString(20 * mm, 12 * mm, "Plataforma de Identificación de Riesgos Contractuales")
    canvas.drawRightString(196 * mm, 12 * mm, f"Página {doc.page}")
    canvas.setStrokeColor(LINEA)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 15 * mm, 196 * mm, 15 * mm)
    canvas.restoreState()


def _resumen(hallazgos: list[dict[str, Any]], st: dict) -> Table:
    por_sev: dict[Severity, int] = {}
    for h in hallazgos:
        por_sev[h["severidad"]] = por_sev.get(h["severidad"], 0) + 1

    filas = [["Severidad", "Hallazgos"]]
    for sev in sorted(por_sev, key=lambda s: ORDEN_SEVERIDAD[s]):
        filas.append([ETIQUETA_SEVERIDAD[sev], str(por_sev[sev])])

    t = Table(filas, colWidths=[90 * mm, 30 * mm], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                ("TEXTCOLOR", (0, 0), (-1, 0), APAGADO),
                ("TEXTCOLOR", (0, 1), (-1, -1), TINTA),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINEA),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _bloque_hallazgo(h: dict[str, Any], n: int, st: dict, ultimo: bool) -> KeepTogether:
    sev = h["severidad"]
    ver = h["verificacion"]
    partes = []

    cabecera = Table(
        [
            [
                Paragraph(f"{n}. {_escapar(h['titulo'])}", st["hallazgo"]),
                Paragraph(
                    f'<font color="#{COLOR_SEVERIDAD[sev].hexval()[2:]}">'
                    f"<b>{ETIQUETA_SEVERIDAD[sev]}</b></font>",
                    st["tenue"],
                ),
            ]
        ],
        colWidths=[140 * mm, 36 * mm],
    )
    cabecera.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    partes.append(cabecera)

    ubicacion = f"Cláusula {h['clausula']}" if h.get("clausula") else "Sin cláusula asociada"
    if h.get("pagina"):
        ubicacion += f" · página {h['pagina']}"
    partes.append(Paragraph(f"{_escapar(ubicacion)} · {_escapar(h['tipo_codigo'])}", st["tenue"]))
    partes.append(Spacer(1, 5))

    partes.append(Paragraph(_escapar(h["explicacion"]), st["cuerpo"]))
    partes.append(Spacer(1, 6))

    partes.append(Paragraph(f'"{_escapar(h["cita_textual"])}"', st["cita"]))
    partes.append(Spacer(1, 4))

    # El estado de la cita va junto a la cita, no al pie del hallazgo: quien
    # lee la cita tiene que ver ahí mismo si puede apoyarse en ella.
    sello = ETIQUETA_VERIFICACION[ver]
    if h.get("score_similitud") is not None and ver != VerificationStatus.NO_VERIFICADA:
        sello += f" ({h['score_similitud']:.0f}%)"
    partes.append(
        Paragraph(
            f'<font color="#{COLOR_VERIFICACION[ver].hexval()[2:]}">{_escapar(sello)}</font>',
            st["tenue"],
        )
    )
    partes.append(Spacer(1, 6))

    partes.append(Paragraph(f"<b>Recomendación:</b> {_escapar(h['recomendacion'])}", st["cuerpo"]))

    # El dictamen cierra el hallazgo: es la última palabra, y la humana.
    revision = h.get("revision", ReviewStatus.PENDIENTE)
    sello_revision = ETIQUETA_REVISION[revision]
    if revision != ReviewStatus.PENDIENTE and h.get("revisado_por"):
        sello_revision += f" {h['revisado_por']}"
        if h.get("revisado_at"):
            sello_revision += f" el {h['revisado_at'].strftime('%d/%m/%Y')}"
    if h.get("comentario_revision"):
        sello_revision += f" — {h['comentario_revision']}"

    partes.append(Spacer(1, 4))
    partes.append(
        Paragraph(
            f'<font color="#{COLOR_REVISION[revision].hexval()[2:]}">'
            f"<b>{_escapar(sello_revision)}</b></font>",
            st["tenue"],
        )
    )

    if not ultimo:
        partes.append(Spacer(1, 10))
        partes.append(HRFlowable(width="100%", thickness=0.4, color=LINEA, spaceAfter=10))

    # KeepTogether evita que un hallazgo se parta entre páginas y deje la
    # recomendación huérfana de su cita.
    return KeepTogether(partes)


def construir_reporte(contrato: dict[str, Any], hallazgos: list[dict[str, Any]]) -> bytes:
    """Devuelve el PDF del reporte de revisión."""
    st = _estilos()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=20 * mm,
        rightMargin=19 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=f"Reporte de revisión — {contrato['nombre_archivo']}",
        author="Plataforma de Identificación de Riesgos Contractuales",
    )

    flujo: list[Any] = [
        Paragraph("Reporte de revisión contractual", st["titulo"]),
        Paragraph(_escapar(contrato["nombre_archivo"]), st["subtitulo"]),
        Spacer(1, 10),
    ]

    generado = datetime.now().strftime("%d/%m/%Y %H:%M")
    meta = [f"Generado el {generado}", f"{contrato.get('paginas') or '—'} páginas"]
    if contrato.get("puntuacion_riesgo") is not None:
        meta.append(f"Puntuación de riesgo {contrato['puntuacion_riesgo']:.0f}/100")
    meta.append(f"{len(hallazgos)} hallazgos")
    flujo.append(Paragraph(" · ".join(meta), st["tenue"]))

    if contrato.get("ocr_aplicado"):
        flujo.append(Spacer(1, 6))
        flujo.append(
            Paragraph(
                "<b>Documento procesado con OCR.</b> El texto se obtuvo por reconocimiento "
                "óptico y puede contener errores de lectura que afectan la precisión de las "
                "citas.",
                st["tenue"],
            )
        )

    flujo.append(Spacer(1, 8))
    flujo.append(HRFlowable(width="100%", thickness=0.6, color=LINEA))

    no_verificados = sum(
        1 for h in hallazgos if h["verificacion"] == VerificationStatus.NO_VERIFICADA
    )
    sin_revisar = sum(
        1 for h in hallazgos if h.get("revision", ReviewStatus.PENDIENTE) == ReviewStatus.PENDIENTE
    )

    flujo.append(Paragraph("Resumen", st["seccion"]))
    if hallazgos:
        flujo.append(_resumen(hallazgos, st))
        flujo.append(Spacer(1, 8))
    flujo.append(
        Paragraph(
            "Cada hallazgo incluye la cita del contrato que lo sustenta y el resultado de "
            "confrontarla automáticamente contra el documento original. "
            + (
                f"<b>{no_verificados} de {len(hallazgos)} citas no pudieron confirmarse</b> y "
                "están marcadas como tales: requieren verificación humana antes de "
                "considerarse evidencia."
                if no_verificados
                else "Todas las citas de este reporte se confirmaron contra el documento."
            ),
            st["cuerpo"],
        )
    )

    if hallazgos:
        flujo.append(Spacer(1, 6))
        flujo.append(
            Paragraph(
                (
                    f"<b>{sin_revisar} de {len(hallazgos)} hallazgos siguen sin revisión "
                    "humana</b> y aparecen marcados como tales."
                    if sin_revisar
                    else "Todos los hallazgos de este reporte fueron revisados por el área "
                    "jurídica."
                ),
                st["cuerpo"],
            )
        )

    flujo.append(Paragraph("Hallazgos", st["seccion"]))

    if not hallazgos:
        flujo.append(
            Paragraph("No se identificaron cláusulas de riesgo en este contrato.", st["cuerpo"])
        )
    else:
        ordenados = sorted(
            hallazgos,
            key=lambda h: (ORDEN_SEVERIDAD[h["severidad"]], h.get("pagina") or 0),
        )
        for i, h in enumerate(ordenados, start=1):
            flujo.append(_bloque_hallazgo(h, i, st, ultimo=i == len(ordenados)))

    flujo.append(Spacer(1, 6))
    flujo.append(
        Paragraph(
            "Este reporte lo genera un sistema automatizado y no sustituye la revisión "
            "jurídica. Las citas marcadas como no verificadas no fueron localizadas en el "
            "documento y no deben tomarse como evidencia.",
            st["tenue"],
        )
    )

    doc.build(flujo, onFirstPage=_encabezado_y_pie, onLaterPages=_encabezado_y_pie)
    return buffer.getvalue()
