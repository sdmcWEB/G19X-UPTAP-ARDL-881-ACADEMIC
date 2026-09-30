from datetime import date

from app.routers.dashboard import ORDEN_SEVERIDAD, ORDEN_VERIFICACION, rellenar_dias

HOY = date(2026, 9, 30)


def test_serie_vacia_no_inventa_puntos():
    assert rellenar_dias({}, {}, dias=30, hoy=HOY) == []


def test_dias_sin_actividad_se_rellenan_con_cero():
    """Una línea con huecos insinúa una caída que nunca ocurrió."""
    puntos = rellenar_dias(
        contratos={date(2026, 9, 28): 2, date(2026, 9, 30): 1},
        hallazgos={date(2026, 9, 28): 14},
        dias=3,
        hoy=HOY,
    )
    assert [(p.fecha.day, p.contratos, p.hallazgos) for p in puntos] == [
        (28, 2, 14),
        (29, 0, 0),
        (30, 1, 0),
    ]


def test_el_periodo_incluye_hoy():
    """dias=30 es hoy más los 29 anteriores: 30 puntos, no 31."""
    puntos = rellenar_dias({HOY: 1}, {}, dias=30, hoy=HOY)
    assert len(puntos) == 30
    assert puntos[0].fecha == date(2026, 9, 1)
    assert puntos[-1].fecha == HOY


def test_sin_periodo_la_serie_arranca_en_el_primer_dato():
    puntos = rellenar_dias(
        contratos={date(2026, 8, 15): 1},
        hallazgos={date(2026, 9, 30): 3},
        dias=None,
        hoy=HOY,
    )
    assert puntos[0].fecha == date(2026, 8, 15)
    assert puntos[-1].fecha == HOY


def test_un_solo_dia():
    puntos = rellenar_dias({HOY: 4}, {HOY: 20}, dias=1, hoy=HOY)
    assert len(puntos) == 1
    assert puntos[0].contratos == 4


def test_la_severidad_va_de_mayor_a_menor():
    """La gráfica recibe el orden del dominio ya resuelto, no alfabético."""
    assert [s.value for s in ORDEN_SEVERIDAD] == [
        "critica",
        "alta",
        "media",
        "baja",
        "informativa",
    ]


def test_la_verificacion_va_de_mejor_a_peor_evidencia():
    assert [v.value for v in ORDEN_VERIFICACION] == [
        "verificada",
        "aproximada",
        "no_verificada",
    ]
