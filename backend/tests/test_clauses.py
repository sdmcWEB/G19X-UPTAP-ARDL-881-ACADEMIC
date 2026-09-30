from app.ingest.clauses import MAX_CARACTERES_CLAUSULA, formatear_para_prompt, segmentar
from app.ingest.documento import Block, Documento


def _doc(*textos: str) -> Documento:
    return Documento(
        bloques=[
            Block(texto=t, pagina=1, bbox=(0, i * 20, 500, i * 20 + 15))
            for i, t in enumerate(textos)
        ],
        paginas=1,
    )


def test_cada_clausula_abre_con_su_encabezado():
    doc = _doc(
        "PRIMERA. OBJETO",
        "El proveedor se obliga a prestar los servicios descritos en el Anexo A.",
        "SEGUNDA. VIGENCIA",
        "El presente contrato tendrá una vigencia de doce meses.",
    )
    clausulas = segmentar(doc)
    assert len(clausulas) == 2
    assert clausulas[0].encabezado == "PRIMERA"
    assert "Anexo A" in clausulas[0].texto
    assert clausulas[1].encabezado == "SEGUNDA"


def test_los_ids_son_estables_y_ordenados():
    doc = _doc("CLÁUSULA I. UNO", "texto", "CLÁUSULA II. DOS", "texto")
    ids = [c.clause_id for c in segmentar(doc)]
    assert ids == ["C-001", "C-002"]


def test_reconoce_numerales_y_articulos():
    doc = _doc("1.1 Definiciones", "Para efectos de este contrato...")
    assert segmentar(doc)[0].encabezado == "1.1"


def test_parrafo_que_empieza_con_cifra_no_es_encabezado():
    """Un párrafo que abre con una cifra es texto corrido, no un encabezado."""
    doc = _doc("PRIMERA. OBJETO", "5 días naturales contados a partir de la firma.")
    assert len(segmentar(doc)) == 1

    doc = _doc("ARTÍCULO 5.- Obligaciones", "Las partes convienen...")
    assert segmentar(doc)[0].encabezado == "ARTÍCULO 5"


def test_un_parrafo_largo_no_se_confunde_con_encabezado():
    parrafo = "El presente instrumento se celebra entre las partes " * 5
    clausulas = segmentar(_doc("PRIMERA. OBJETO", parrafo))
    assert len(clausulas) == 1


def test_clausula_gigante_se_parte():
    gigante = "x" * (MAX_CARACTERES_CLAUSULA + 500)
    clausulas = segmentar(_doc("PRIMERA. OBJETO", gigante, gigante))
    assert len(clausulas) > 1
    assert "cont." in clausulas[1].encabezado


def test_se_conservan_pagina_y_coordenadas():
    doc = Documento(
        bloques=[
            Block("PRIMERA. OBJETO", pagina=2, bbox=(10, 20, 300, 35)),
            Block("El proveedor se obliga.", pagina=3, bbox=(10, 40, 300, 55)),
        ],
        paginas=3,
    )
    c = segmentar(doc)[0]
    assert c.pagina_inicio == 2
    assert c.pagina_fin == 3
    assert c.bboxes[0] == {"page": 2, "bbox": [10, 20, 300, 35]}


def test_el_prompt_lleva_los_ids_visibles():
    """Sin los ids en el prompt, el modelo no puede citar cláusulas."""
    salida = formatear_para_prompt(segmentar(_doc("PRIMERA. OBJETO", "texto")))
    assert "[C-001]" in salida
