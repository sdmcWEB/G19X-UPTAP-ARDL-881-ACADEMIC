"""Mide la precisión del sistema contra contratos etiquetados por un abogado.

    docker compose exec api python scripts/evaluar.py
    docker compose exec api python scripts/evaluar.py --json reporte.json

Lee los archivos de `evaluacion/etiquetas/`, busca cada contrato en la base por
su nombre de archivo, confronta los hallazgos del sistema con los que marcó el
abogado e imprime el reporte.

Los contratos deben estar ya analizados en el sistema: este script mide, no
ejecuta el pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db import SessionLocal
from app.evaluacion.metricas import (
    Emparejamiento,
    Esperado,
    Predicho,
    calcular,
    calidad_evidencia,
    emparejar,
    por_tipo,
)
from app.models import Clause, Contract, ContractStatus, Finding

ETIQUETAS = Path(__file__).parent.parent / "evaluacion" / "etiquetas"


def pct(valor: float | None) -> str:
    """Una métrica sin denominador se imprime como tal, no como 0 %."""
    return "—" if valor is None else f"{valor * 100:5.1f}%"


def cargar_etiquetas() -> list[dict]:
    archivos = sorted(ETIQUETAS.glob("*.json"))
    archivos = [a for a in archivos if not a.name.startswith("_")]
    if not archivos:
        print(f"No hay etiquetas en {ETIQUETAS}. Lee evaluacion/README.md.", file=sys.stderr)
        raise SystemExit(1)
    return [json.loads(a.read_text(encoding="utf-8")) for a in archivos]


def predichos_de(db, contrato: Contract) -> list[Predicho]:
    filas = db.execute(
        select(Finding, Clause.clause_id)
        .join(Clause, Clause.id == Finding.clausula_id)
        .where(Finding.contrato_id == contrato.id)
    ).all()
    return [
        Predicho(clausula=clause_id, tipo_codigo=f.tipo_codigo, verificacion=f.verificacion)
        for f, clause_id in filas
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description="Evalúa la precisión del sistema.")
    ap.add_argument("--json", type=Path, help="Guarda el reporte en este archivo")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        global_emp = Emparejamiento()
        por_contrato = []
        omitidos = []

        for etiqueta in cargar_etiquetas():
            nombre = etiqueta["archivo"]
            contrato = db.scalar(select(Contract).where(Contract.nombre_archivo == nombre))

            if contrato is None:
                omitidos.append((nombre, "no está en el sistema"))
                continue
            if contrato.status != ContractStatus.LISTO:
                omitidos.append((nombre, f"estado {contrato.status.value}"))
                continue

            esperados = [
                Esperado(clausula=h["clausula"], tipo_codigo=h["tipo_codigo"])
                for h in etiqueta["hallazgos_esperados"]
            ]
            emp = emparejar(predichos_de(db, contrato), esperados)
            por_contrato.append((nombre, calcular(emp)))

            global_emp.aciertos += emp.aciertos
            global_emp.falsos_positivos += emp.falsos_positivos
            global_emp.falsos_negativos += emp.falsos_negativos
            global_emp.tipo_incorrecto += emp.tipo_incorrecto

        if not por_contrato:
            print("Ningún contrato etiquetado está analizado en el sistema.", file=sys.stderr)
            for nombre, motivo in omitidos:
                print(f"  {nombre}: {motivo}", file=sys.stderr)
            raise SystemExit(1)

        total = calcular(global_emp)
        evidencia = calidad_evidencia(global_emp)
        desglose = por_tipo(global_emp)

        n = len(por_contrato)
        print(f"\n{'=' * 64}")
        print(
            f"EVALUACIÓN · {n} {'contrato' if n == 1 else 'contratos'} · "
            f"{total.total_esperados} riesgos marcados"
        )
        print("=" * 64)

        print("\nDETECCIÓN")
        print(f"  Precisión        {pct(total.precision)}   de lo que reporta, cuánto es real")
        print(f"  Exhaustividad    {pct(total.exhaustividad)}   de lo que hay, cuánto encuentra")
        print(f"  F1               {pct(total.f1)}")
        print(
            f"\n  {total.aciertos} aciertos · {total.falsos_positivos} falsos positivos · "
            f"{total.falsos_negativos} omitidos · {total.tipo_incorrecto} mal clasificados"
        )

        print("\nCALIDAD DE LA EVIDENCIA")
        print(f"  Citas verificadas              {pct(evidencia.tasa_verificadas)}")
        print(
            f"  Errores que el verificador marca {pct(evidencia.sensibilidad_del_verificador)}"
            f"   ({evidencia.errores_detectados}/{evidencia.errores_totales})"
        )
        print(
            f"  Aciertos marcados de más       {pct(evidencia.falsas_alarmas)}"
            f"   ({evidencia.aciertos_marcados}/{evidencia.aciertos_totales})"
        )

        print("\nPOR TIPO DE RIESGO")
        print(f"  {'código':<34} {'prec.':>7} {'exh.':>7} {'esp.':>5}")
        for codigo, m in sorted(desglose.items(), key=lambda kv: -kv[1].total_esperados):
            print(
                f"  {codigo:<34} {pct(m.precision):>7} {pct(m.exhaustividad):>7} "
                f"{m.total_esperados:>5}"
            )

        print("\nPOR CONTRATO")
        for nombre, m in por_contrato:
            corto = nombre if len(nombre) <= 44 else nombre[:41] + "..."
            print(f"  {corto:<44} {pct(m.precision):>7} {pct(m.exhaustividad):>7}")

        if omitidos:
            print("\nOMITIDOS")
            for nombre, motivo in omitidos:
                print(f"  {nombre}: {motivo}")

        print()

        if args.json:
            args.json.write_text(
                json.dumps(
                    {
                        "contratos": len(por_contrato),
                        "deteccion": asdict(total),
                        "evidencia": {
                            **asdict(evidencia),
                            "tasa_verificadas": evidencia.tasa_verificadas,
                            "sensibilidad_del_verificador": (
                                evidencia.sensibilidad_del_verificador
                            ),
                            "falsas_alarmas": evidencia.falsas_alarmas,
                        },
                        "por_tipo": {k: asdict(v) for k, v in desglose.items()},
                        "omitidos": dict(omitidos),
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            print(f"Reporte guardado en {args.json}\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
