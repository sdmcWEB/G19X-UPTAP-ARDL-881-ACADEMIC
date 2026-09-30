import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { GraficaActividad } from "../components/viz/GraficaActividad";
import { GraficaEvidencia } from "../components/viz/GraficaEvidencia";
import { GraficaSeveridad } from "../components/viz/GraficaSeveridad";
import { GraficaTipos } from "../components/viz/GraficaTipos";
import { Medidor } from "../components/viz/Medidor";
import { StatTile } from "../components/viz/StatTile";
import { TarjetaGrafica } from "../components/viz/TarjetaGrafica";
import { api } from "../lib/api";
import { PERIODOS } from "../lib/tipos";

function fechaCorta(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
  });
}

export function Dashboard() {
  const [dias, setDias] = useState<number | null>(30);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["dashboard", dias],
    queryFn: () => api.dashboard(dias),
    // Al cambiar el periodo se conserva la vista anterior atenuada, en lugar
    // de parpadear un esqueleto y brincar el layout.
    placeholderData: (previa) => previa,
  });

  if (isLoading && !data) {
    return <p className="p-6 text-sm text-neutral-500">Cargando tablero…</p>;
  }
  if (!data) {
    return <p className="p-6 text-sm text-red-700">No se pudo cargar el tablero.</p>;
  }

  const recargando = isFetching && !isLoading;
  const sinDatos = data.contratos_totales === 0;

  return (
    <div className="viz-root mx-auto max-w-[1400px] p-6">
      <h1 className="text-xl font-semibold text-[var(--text-primary)]">Tablero de riesgo</h1>

      {/* Una sola fila de filtros arriba de todo lo que acota: las cinco
          tarjetas se recalculan contra la misma rebanada. */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-sm text-[var(--text-secondary)]">Periodo:</span>
        {PERIODOS.map((p) => (
          <button
            key={p.etiqueta}
            onClick={() => setDias(p.dias)}
            aria-pressed={dias === p.dias}
            className={`rounded-lg border px-3 py-1 text-sm transition ${
              dias === p.dias
                ? "border-transparent bg-[var(--text-primary)] text-[var(--surface-1)]"
                : "border-[var(--hairline)] text-[var(--text-secondary)] hover:bg-[var(--plane)]"
            }`}
          >
            {p.etiqueta}
          </button>
        ))}
      </div>

      {sinDatos ? (
        <p className="mt-6 rounded-xl border border-dashed border-[var(--axis)] p-12 text-center text-sm text-[var(--text-muted)]">
          No hay contratos en este periodo.{" "}
          <Link to="/contratos" className="underline">
            Sube uno
          </Link>{" "}
          para empezar a ver cifras.
        </p>
      ) : (
        <div className={`transition-opacity ${recargando ? "opacity-60" : ""}`}>
          {/* El número que encabeza el tablero es el riesgo promedio: una sola
              figura destacada por vista. */}
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile
              etiqueta="Riesgo promedio"
              valor={data.riesgo_promedio !== null ? data.riesgo_promedio.toFixed(0) : "—"}
              pie={`de 100 · ${data.contratos_analizados} contratos analizados`}
              destacado
            />
            <StatTile
              etiqueta="Contratos"
              valor={data.contratos_totales.toLocaleString("es-MX")}
              pie={
                data.pct_con_ocr !== null
                  ? `${data.pct_con_ocr.toFixed(0)}% requirió OCR`
                  : undefined
              }
            />
            <StatTile
              etiqueta="Hallazgos"
              valor={data.hallazgos_totales.toLocaleString("es-MX")}
              pie="cláusulas de riesgo detectadas"
            />
            <StatTile
              etiqueta="Citas verificadas"
              valor={
                data.pct_citas_verificadas !== null
                  ? `${data.pct_citas_verificadas.toFixed(0)}%`
                  : "—"
              }
              pie="confirmadas contra el documento"
            />
          </div>

          {/* La calidad de la evidencia va a todo lo ancho: es la métrica que
              distingue a este sistema y su barra es horizontal. */}
          <div className="mt-4">
            <TarjetaGrafica
              titulo="Calidad de la evidencia"
              subtitulo="Qué proporción de las citas se confirmó palabra por palabra contra el contrato"
              nota="Un hallazgo con cita no verificada no debe presentarse como evidencia sin revisión humana."
              recargando={recargando}
              grafica={<GraficaEvidencia datos={data.por_verificacion} />}
              filas={data.por_verificacion}
              columnas={[
                { encabezado: "Estado de la cita", valor: (f) => f.etiqueta },
                { encabezado: "Hallazgos", valor: (f) => f.total, numerica: true },
              ]}
            />
          </div>

          {/* items-start: cada tarjeta toma su altura natural en lugar de
              estirarse a la más alta y dejar un hueco muerto. */}
          <div className="mt-4 grid items-start gap-4 lg:grid-cols-2">
            <TarjetaGrafica
              titulo="Hallazgos por severidad"
              subtitulo="Distribución de los riesgos detectados en el periodo"
              recargando={recargando}
              grafica={<GraficaSeveridad datos={data.por_severidad} />}
              filas={data.por_severidad}
              columnas={[
                { encabezado: "Severidad", valor: (f) => f.etiqueta },
                { encabezado: "Hallazgos", valor: (f) => f.total, numerica: true },
              ]}
            />

            <TarjetaGrafica
              titulo="Tipos de riesgo más frecuentes"
              subtitulo="Los diez códigos del catálogo con más hallazgos"
              recargando={recargando}
              grafica={<GraficaTipos datos={data.por_tipo} />}
              filas={data.por_tipo}
              columnas={[
                { encabezado: "Tipo de riesgo", valor: (f) => f.etiqueta },
                { encabezado: "Hallazgos", valor: (f) => f.total, numerica: true },
              ]}
            />
          </div>

          <div className="mt-4">
            <TarjetaGrafica
              titulo="Actividad"
              subtitulo="Contratos subidos y hallazgos generados por día"
              nota="Dos escalas distintas, dos gráficas: compartir un eje inventaría una relación entre ellas."
              recargando={recargando}
              grafica={<GraficaActividad datos={data.tendencia} />}
              filas={data.tendencia}
              columnas={[
                { encabezado: "Fecha", valor: (f) => fechaCorta(f.fecha) },
                { encabezado: "Contratos", valor: (f) => f.contratos, numerica: true },
                { encabezado: "Hallazgos", valor: (f) => f.hallazgos, numerica: true },
              ]}
            />
          </div>

          <section className="viz-root mt-4 rounded-xl border border-[var(--hairline)] bg-[var(--surface-1)] p-5">
            <h2 className="font-semibold text-[var(--text-primary)]">
              Contratos de mayor riesgo
            </h2>
            <p className="mt-0.5 text-sm text-[var(--text-secondary)]">
              Los cinco con la puntuación más alta. La puntuación la manda el hallazgo
              más grave, no el promedio.
            </p>

            {data.contratos_riesgosos.length === 0 ? (
              <p className="py-8 text-center text-sm text-[var(--text-muted)]">
                Ningún contrato del periodo terminó de analizarse.
              </p>
            ) : (
              <table className="mt-4 w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--grid)] text-left text-[var(--text-muted)]">
                    <th className="py-1.5 font-normal">Contrato</th>
                    <th className="py-1.5 text-right font-normal">Hallazgos</th>
                    <th className="py-1.5 pl-6 font-normal">Riesgo</th>
                  </tr>
                </thead>
                <tbody>
                  {data.contratos_riesgosos.map((c) => (
                    <tr key={c.id} className="border-b border-[var(--grid)] last:border-0">
                      <td className="py-2">
                        <Link
                          to={`/contratos/${c.id}`}
                          className="font-medium text-[var(--text-primary)] hover:underline"
                        >
                          {c.nombre_archivo}
                        </Link>
                        {c.ocr_aplicado && (
                          <span
                            className="ml-2 rounded bg-[var(--plane)] px-1.5 py-0.5 text-xs text-[var(--text-secondary)]"
                            title="El texto se obtuvo por OCR: puede tener errores de reconocimiento"
                          >
                            OCR
                          </span>
                        )}
                      </td>
                      <td className="py-2 text-right tabular-nums text-[var(--text-secondary)]">
                        {c.hallazgos}
                      </td>
                      <td className="py-2 pl-6">
                        <Medidor valor={c.puntuacion_riesgo} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
