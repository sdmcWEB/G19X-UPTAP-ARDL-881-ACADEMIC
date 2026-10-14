from app.routers.search import DISTANCIA_MAXIMA, _recortar


def test_colapsa_espacios_y_saltos():
    """El texto viene del extractor con saltos de línea del PDF."""
    assert _recortar("CLÁUSULA\n  PRIMERA.\tObjeto") == "CLÁUSULA PRIMERA. Objeto"


def test_un_texto_corto_pasa_intacto():
    assert _recortar("Pena convencional del 5%.") == "Pena convencional del 5%."


def test_un_texto_largo_se_recorta_con_puntos_suspensivos():
    recortado = _recortar("x" * 500, maximo=50)
    assert len(recortado) == 50
    assert recortado.endswith("…")


def test_el_recorte_no_deja_un_espacio_colgando():
    texto = "palabra " * 60
    recortado = _recortar(texto, maximo=40)
    assert not recortado[:-1].endswith(" ")


def test_el_umbral_deja_fuera_lo_que_no_se_parece():
    """La distancia coseno va de 0 (idéntico) a 2 (opuesto).

    Un umbral de 1.0 o más dejaría pasar cláusulas ortogonales a la consulta,
    que es ruido puro en una lista de resultados.
    """
    assert 0 < DISTANCIA_MAXIMA < 1.0
