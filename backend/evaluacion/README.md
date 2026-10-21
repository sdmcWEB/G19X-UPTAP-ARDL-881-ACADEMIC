# Conjunto de evaluación

Aquí vive la medición de precisión del sistema. Es el objetivo específico que
sostiene la hipótesis del proyecto: sin estas cifras, "funciona" es una
impresión.

## Qué mide

**Detección** — ¿encuentra el sistema los riesgos que encuentra un abogado?

| Métrica | Pregunta que responde |
|---|---|
| Precisión | De lo que el sistema reporta, cuánto es real |
| Exhaustividad | De los riesgos que hay, cuántos encuentra |
| F1 | Las dos anteriores en un solo número |

**Calidad de la evidencia** — cuando el sistema se equivoca, ¿lo delata?

| Métrica | Por qué importa |
|---|---|
| Citas verificadas | Qué proporción de los hallazgos trae evidencia confirmada |
| Errores que el verificador marca | **La métrica central del proyecto.** Un falso positivo con cita impecable es exactamente lo que este sistema existe para evitar |
| Aciertos marcados de más | Si el verificador rechaza demasiadas citas buenas, el abogado deja de confiar en él y revisa todo igual |

El desglose por tipo de riesgo también se reporta: el agregado esconde que un
sistema puede ir perfecto en lo frecuente y fallar justo en lo crítico.

## Cómo etiquetar un contrato

El etiquetado va **después** de que el sistema ingiere el contrato, porque las
etiquetas se anclan a las cláusulas que el segmentador produjo.

1. **Sube el contrato** a la plataforma y espera a que termine de procesarse.
2. **Abre el contrato** y revisa la lista de cláusulas con sus identificadores
   (`C-001`, `C-002`, …). Son los que el sistema asignó al segmentar.
3. **El abogado marca** qué cláusulas tienen riesgo y de qué tipo, usando los
   códigos del catálogo (`GET /api/dashboard` los lista, o la tabla
   `risk_types`).
4. **Crea un archivo** `evaluacion/etiquetas/<nombre>.json` con ese contenido.

Mira `_ejemplo.json` para el formato. Los archivos que empiezan con guion bajo
se ignoran.

```json
{
  "archivo": "nombre exacto del archivo subido.pdf",
  "etiquetado_por": "quién revisó",
  "fecha": "2026-10-20",
  "hallazgos_esperados": [
    { "clausula": "C-014", "tipo_codigo": "PENALIZACION_DESPROPORCIONADA" }
  ]
}
```

El campo `nota` de cada hallazgo es opcional y solo sirve para que otra persona
entienda el criterio después.

## Cómo correr la evaluación

```bash
docker compose exec api python scripts/evaluar.py
```

Para guardar el resultado y poder comparar entre versiones:

```bash
docker compose exec api python scripts/evaluar.py --json evaluacion/reporte.json
```

Los contratos etiquetados que no estén analizados en el sistema se reportan
como omitidos en lugar de contarse como fallas.

## Cuántos contratos hacen falta

Con menos de 10 contratos las cifras se mueven demasiado con cada caso
particular y no sostienen una afirmación. Entre 20 y 30, con los tipos de
riesgo críticos representados al menos tres veces cada uno, da una medición
defendible para la estadía.

Importa también que haya **escaneados** en la muestra: el OCR degrada el texto
y ese efecto solo se ve midiéndolo por separado.

## Cómo leer el resultado

Una precisión alta con exhaustividad baja significa que el sistema es
conservador: lo que dice es cierto, pero se le escapan riesgos. Al revés
significa que reporta de más y le hace perder tiempo al abogado.

Para este proyecto importa más la **sensibilidad del verificador** que
cualquiera de las dos. Si esa cifra es alta, los errores del modelo llegan
marcados y el abogado sabe en cuáles no apoyarse. Si es baja, el sistema está
entregando afirmaciones disfrazadas de evidencia, que es justo el problema que
el proyecto planteó resolver.
