"""Las métricas son lo que se reporta en la defensa.

Si están mal calculadas, el proyecto afirma un número que no es cierto, y eso
es peor que no reportar ninguno.
"""

import pytest

from app.enums import VerificationStatus as V
from app.evaluacion.metricas import (
    Esperado,
    Predicho,
    calcular,
    calidad_evidencia,
    emparejar,
    por_tipo,
)


def p(clausula, tipo, verificacion=V.VERIFICADA):
    return Predicho(clausula=clausula, tipo_codigo=tipo, verificacion=verificacion)


def e(clausula, tipo):
    return Esperado(clausula=clausula, tipo_codigo=tipo)


# --- Emparejamiento ---


def test_coincidencia_exacta_es_acierto():
    emp = emparejar([p("C-001", "PENALIZACION")], [e("C-001", "PENALIZACION")])
    assert len(emp.aciertos) == 1
    assert not emp.falsos_positivos and not emp.falsos_negativos


def test_cláusula_que_nadie_marcó_es_falso_positivo():
    emp = emparejar([p("C-009", "PENALIZACION")], [])
    assert len(emp.falsos_positivos) == 1


def test_riesgo_que_el_sistema_no_vio_es_falso_negativo():
    emp = emparejar([], [e("C-003", "RESPONSABILIDAD")])
    assert len(emp.falsos_negativos) == 1


def test_misma_cláusula_otro_tipo_se_reporta_aparte():
    """Ver el problema y clasificarlo mal no es lo mismo que no verlo."""
    emp = emparejar([p("C-005", "PENALIZACION")], [e("C-005", "RESPONSABILIDAD")])
    assert len(emp.tipo_incorrecto) == 1
    assert not emp.falsos_positivos and not emp.falsos_negativos


def test_un_esperado_se_consume_una_sola_vez():
    """Dos hallazgos sobre la misma cláusula no pueden acertarle al mismo."""
    emp = emparejar(
        [p("C-002", "PENALIZACION"), p("C-002", "PENALIZACION")],
        [e("C-002", "PENALIZACION")],
    )
    assert len(emp.aciertos) == 1
    assert len(emp.falsos_positivos) == 1


def test_la_coincidencia_exacta_gana_sobre_la_parcial():
    """Sin esto, un hallazgo con el tipo equivocado podría robarse el esperado
    que le corresponde al hallazgo correcto."""
    emp = emparejar(
        [p("C-007", "OTRO"), p("C-007", "PENALIZACION")],
        [e("C-007", "PENALIZACION")],
    )
    assert len(emp.aciertos) == 1
    assert emp.aciertos[0].tipo_codigo == "PENALIZACION"
    assert len(emp.falsos_positivos) == 1


# --- Métricas ---


def test_sistema_perfecto():
    m = calcular(emparejar([p("C-1", "A"), p("C-2", "B")], [e("C-1", "A"), e("C-2", "B")]))
    assert m.precision == 1.0
    assert m.exhaustividad == 1.0
    assert m.f1 == 1.0


def test_mitad_de_los_hallazgos_correctos():
    m = calcular(emparejar([p("C-1", "A"), p("C-9", "A")], [e("C-1", "A")]))
    assert m.precision == 0.5
    assert m.exhaustividad == 1.0


def test_el_tipo_incorrecto_penaliza_por_ambos_lados():
    m = calcular(emparejar([p("C-1", "A")], [e("C-1", "B")]))
    assert m.precision == 0.0
    assert m.exhaustividad == 0.0
    assert m.tipo_incorrecto == 1


def test_sin_predicciones_la_precision_no_existe():
    """No es cero: una métrica sin denominador no tiene valor, y reportarla
    como 0 % hace ver al sistema peor de lo que se midió."""
    m = calcular(emparejar([], [e("C-1", "A")]))
    assert m.precision is None
    assert m.exhaustividad == 0.0


def test_contrato_sin_riesgos_y_sistema_que_no_inventa():
    m = calcular(emparejar([], []))
    assert m.precision is None
    assert m.exhaustividad is None
    assert m.f1 is None


def test_los_totales_cuadran():
    emp = emparejar(
        [p("C-1", "A"), p("C-2", "B"), p("C-3", "C")],
        [e("C-1", "A"), e("C-2", "X"), e("C-8", "D")],
    )
    m = calcular(emp)
    assert m.total_predichos == 3
    assert m.total_esperados == 3


# --- Calidad de la evidencia ---


def test_el_verificador_delata_los_errores():
    """El caso que valida la hipótesis: el modelo se equivoca y lo marca."""
    emp = emparejar(
        [p("C-1", "A", V.VERIFICADA), p("C-9", "A", V.NO_VERIFICADA)],
        [e("C-1", "A")],
    )
    c = calidad_evidencia(emp)
    assert c.sensibilidad_del_verificador == 1.0
    assert c.falsas_alarmas == 0.0


def test_el_peor_caso_un_error_con_cita_verificada():
    """Un falso positivo que llega con cita impecable es lo que el proyecto
    existe para evitar."""
    emp = emparejar([p("C-9", "A", V.VERIFICADA)], [])
    c = calidad_evidencia(emp)
    assert c.sensibilidad_del_verificador == 0.0
    assert c.errores_totales == 1


def test_un_acierto_marcado_de_más_es_falsa_alarma():
    emp = emparejar([p("C-1", "A", V.NO_VERIFICADA)], [e("C-1", "A")])
    c = calidad_evidencia(emp)
    assert c.falsas_alarmas == 1.0


def test_sin_hallazgos_las_tasas_no_existen():
    c = calidad_evidencia(emparejar([], []))
    assert c.tasa_verificadas is None
    assert c.sensibilidad_del_verificador is None


def test_el_tipo_incorrecto_cuenta_como_error_para_el_verificador():
    emp = emparejar([p("C-1", "A", V.NO_VERIFICADA)], [e("C-1", "B")])
    c = calidad_evidencia(emp)
    assert c.errores_totales == 1
    assert c.sensibilidad_del_verificador == 1.0


# --- Desglose por tipo ---


def test_el_agregado_esconde_el_tipo_que_falla():
    """Un sistema puede ir perfecto en lo frecuente y fallar en lo crítico."""
    emp = emparejar(
        [p("C-1", "PAGO"), p("C-2", "PAGO"), p("C-7", "RESPONSABILIDAD")],
        [e("C-1", "PAGO"), e("C-2", "PAGO"), e("C-3", "RESPONSABILIDAD")],
    )
    desglose = por_tipo(emp)
    assert desglose["PAGO"].precision == 1.0
    assert desglose["RESPONSABILIDAD"].precision == 0.0
    assert desglose["RESPONSABILIDAD"].exhaustividad == 0.0


def test_el_desglose_cubre_los_tipos_que_solo_aparecen_como_omision():
    emp = emparejar([], [e("C-1", "DATOS_PERSONALES")])
    assert "DATOS_PERSONALES" in por_tipo(emp)


@pytest.mark.parametrize("tipo", ["PAGO", "RESPONSABILIDAD"])
def test_un_tipo_mal_clasificado_aparece_en_ambos_codigos(tipo):
    emp = emparejar([p("C-1", "PAGO")], [e("C-1", "RESPONSABILIDAD")])
    assert tipo in por_tipo(emp)
