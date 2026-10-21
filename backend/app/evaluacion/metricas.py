"""Métricas de precisión del sistema.

Responde las dos preguntas que sostienen la hipótesis del proyecto:

1. ¿Encuentra el sistema los riesgos que un abogado encuentra?
2. Cuando se equivoca, ¿el verificador de citas lo delata?

La segunda importa tanto como la primera. Un sistema que acierta el 80 % pero
presenta el 20 % restante con citas de aspecto impecable es peor que uno que
acierta menos y marca sus propios errores.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.enums import VerificationStatus


@dataclass(frozen=True)
class Esperado:
    """Un riesgo que el abogado marcó en el contrato."""

    clausula: str
    tipo_codigo: str


@dataclass(frozen=True)
class Predicho:
    """Un hallazgo que produjo el sistema."""

    clausula: str
    tipo_codigo: str
    verificacion: VerificationStatus


@dataclass
class Emparejamiento:
    """Resultado de confrontar lo predicho con lo esperado."""

    aciertos: list[Predicho] = field(default_factory=list)
    falsos_positivos: list[Predicho] = field(default_factory=list)
    falsos_negativos: list[Esperado] = field(default_factory=list)
    # Cláusula correcta, tipo de riesgo equivocado. Cuenta como error por
    # ambos lados, pero se reporta aparte: el sistema vio el problema y lo
    # clasificó mal, que no es lo mismo que no haberlo visto.
    tipo_incorrecto: list[tuple[Predicho, Esperado]] = field(default_factory=list)


def emparejar(predichos: list[Predicho], esperados: list[Esperado]) -> Emparejamiento:
    """Empareja hallazgos por (cláusula, tipo). Un esperado se consume una vez."""
    resultado = Emparejamiento()

    pendientes = list(esperados)
    sin_emparejar: list[Predicho] = []

    # Primera pasada: coincidencia exacta de cláusula y tipo.
    for p in predichos:
        exacto = next(
            (e for e in pendientes if e.clausula == p.clausula and e.tipo_codigo == p.tipo_codigo),
            None,
        )
        if exacto is not None:
            pendientes.remove(exacto)
            resultado.aciertos.append(p)
        else:
            sin_emparejar.append(p)

    # Segunda pasada: misma cláusula, otro tipo.
    for p in sin_emparejar:
        misma_clausula = next((e for e in pendientes if e.clausula == p.clausula), None)
        if misma_clausula is not None:
            pendientes.remove(misma_clausula)
            resultado.tipo_incorrecto.append((p, misma_clausula))
        else:
            resultado.falsos_positivos.append(p)

    resultado.falsos_negativos = pendientes
    return resultado


def _division(numerador: int, denominador: int) -> float | None:
    """None, no cero: sin denominador la métrica no existe, no vale 0."""
    return numerador / denominador if denominador else None


@dataclass
class Metricas:
    aciertos: int
    falsos_positivos: int
    falsos_negativos: int
    tipo_incorrecto: int

    precision: float | None
    exhaustividad: float | None
    f1: float | None

    @property
    def total_esperados(self) -> int:
        return self.aciertos + self.falsos_negativos + self.tipo_incorrecto

    @property
    def total_predichos(self) -> int:
        return self.aciertos + self.falsos_positivos + self.tipo_incorrecto


def calcular(emp: Emparejamiento) -> Metricas:
    """Un tipo mal clasificado cuenta como error por ambos lados.

    Es la lectura estricta y es la correcta: al abogado le llegó una etiqueta
    equivocada y el riesgo real quedó sin reportar con su nombre.
    """
    vp = len(emp.aciertos)
    fp = len(emp.falsos_positivos) + len(emp.tipo_incorrecto)
    fn = len(emp.falsos_negativos) + len(emp.tipo_incorrecto)

    precision = _division(vp, vp + fp)
    exhaustividad = _division(vp, vp + fn)

    if precision and exhaustividad:
        f1 = 2 * precision * exhaustividad / (precision + exhaustividad)
    else:
        f1 = None if precision is None or exhaustividad is None else 0.0

    return Metricas(
        aciertos=vp,
        falsos_positivos=len(emp.falsos_positivos),
        falsos_negativos=len(emp.falsos_negativos),
        tipo_incorrecto=len(emp.tipo_incorrecto),
        precision=precision,
        exhaustividad=exhaustividad,
        f1=f1,
    )


@dataclass
class CalidadEvidencia:
    """Qué tan bien delata el verificador los errores del modelo.

    Es la métrica propia de este proyecto. Si los falsos positivos llegan con
    cita verificada, el verificador no está protegiendo a nadie.
    """

    verificadas: int
    aproximadas: int
    no_verificadas: int

    # De los hallazgos equivocados, cuántos trae el verificador marcados.
    errores_detectados: int
    errores_totales: int

    # De los hallazgos correctos, cuántos quedaron marcados sin serlo.
    aciertos_marcados: int
    aciertos_totales: int

    @property
    def tasa_verificadas(self) -> float | None:
        total = self.verificadas + self.aproximadas + self.no_verificadas
        return _division(self.verificadas, total)

    @property
    def sensibilidad_del_verificador(self) -> float | None:
        """Proporción de hallazgos equivocados que el verificador marca."""
        return _division(self.errores_detectados, self.errores_totales)

    @property
    def falsas_alarmas(self) -> float | None:
        """Proporción de hallazgos correctos que el verificador marca de más."""
        return _division(self.aciertos_marcados, self.aciertos_totales)


def calidad_evidencia(emp: Emparejamiento) -> CalidadEvidencia:
    marcado = {VerificationStatus.APROXIMADA, VerificationStatus.NO_VERIFICADA}
    errados = emp.falsos_positivos + [p for p, _ in emp.tipo_incorrecto]
    todos = emp.aciertos + errados

    return CalidadEvidencia(
        verificadas=sum(1 for p in todos if p.verificacion == VerificationStatus.VERIFICADA),
        aproximadas=sum(1 for p in todos if p.verificacion == VerificationStatus.APROXIMADA),
        no_verificadas=sum(1 for p in todos if p.verificacion == VerificationStatus.NO_VERIFICADA),
        errores_detectados=sum(1 for p in errados if p.verificacion in marcado),
        errores_totales=len(errados),
        aciertos_marcados=sum(1 for p in emp.aciertos if p.verificacion in marcado),
        aciertos_totales=len(emp.aciertos),
    )


def por_tipo(emp: Emparejamiento) -> dict[str, Metricas]:
    """Métricas desglosadas por tipo de riesgo.

    El agregado esconde lo que importa: un sistema puede ir bien en los tipos
    frecuentes y fallar justo en los críticos, que son los que pagan el
    proyecto.
    """
    codigos = {p.tipo_codigo for p in emp.aciertos}
    codigos |= {p.tipo_codigo for p in emp.falsos_positivos}
    codigos |= {e.tipo_codigo for e in emp.falsos_negativos}
    for p, e in emp.tipo_incorrecto:
        codigos |= {p.tipo_codigo, e.tipo_codigo}

    desglose = {}
    for codigo in sorted(codigos):
        parcial = Emparejamiento(
            aciertos=[p for p in emp.aciertos if p.tipo_codigo == codigo],
            falsos_positivos=[p for p in emp.falsos_positivos if p.tipo_codigo == codigo],
            falsos_negativos=[e for e in emp.falsos_negativos if e.tipo_codigo == codigo],
            tipo_incorrecto=[
                (p, e) for p, e in emp.tipo_incorrecto if codigo in (p.tipo_codigo, e.tipo_codigo)
            ],
        )
        desglose[codigo] = calcular(parcial)
    return desglose
