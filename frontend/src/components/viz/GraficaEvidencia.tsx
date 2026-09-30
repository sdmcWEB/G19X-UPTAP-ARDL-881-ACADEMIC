import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Conteo } from "../../lib/tipos";
import { VizTooltip } from "./Tooltip";

/* Calidad de la evidencia: parte-todo sobre tres clases con polaridad
   (buena → mala), así que va en barra apilada horizontal con la paleta de
   estado. Es estado real —qué tan confiable es la cita—, no identidad de
   series, y por eso puede usar esos tonos reservados.

   En superficie clara el amarillo queda bajo 3:1. La mitigación que exige el
   sistema va incluida: etiquetas visibles, leyenda y gemela en tabla. */
const TONO: Record<string, string> = {
  verificada: "var(--estado-bueno)",
  aproximada: "var(--estado-advertencia)",
  no_verificada: "var(--estado-critico)",
};

/** Una etiqueta dentro del segmento solo se dibuja si cabe con holgura.
 *  Si no, se cae al tooltip y a la tabla en lugar de recortarse. */
const MINIMO_PARA_ETIQUETA_INTERNA = 0.1;

export function GraficaEvidencia({ datos }: { datos: Conteo[] }) {
  const total = datos.reduce((s, d) => s + d.total, 0);

  if (total === 0) {
    return (
      <p className="py-10 text-center text-sm text-[var(--text-muted)]">
        Todavía no hay hallazgos que evaluar.
      </p>
    );
  }

  // Una sola fila apilada: el eje y no lleva categorías.
  const fila = Object.fromEntries(datos.map((d) => [d.clave, d.total]));

  return (
    <div>
      <ResponsiveContainer width="100%" height={72}>
        <BarChart data={[fila]} layout="vertical" margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <XAxis type="number" hide domain={[0, total]} />
          <YAxis type="category" hide />
          <Tooltip content={<VizTooltip />} cursor={{ fill: "transparent" }} />

          {datos.map((d, i) => (
            <Bar
              key={d.clave}
              dataKey={d.clave}
              name={d.etiqueta}
              stackId="evidencia"
              maxBarSize={28}
              /* El trazo del color de la superficie ES el separador de 2px, no
                 un borde: cada segmento lo pinta hacia adentro y entre dos
                 vecinos el hueco queda del ancho justo. */
              stroke="var(--surface-1)"
              strokeWidth={2}
              isAnimationActive={false}
              radius={
                i === 0
                  ? [4, 0, 0, 4]
                  : i === datos.length - 1
                    ? [0, 4, 4, 0]
                    : [0, 0, 0, 0]
              }
            >
              <Cell fill={TONO[d.clave]} />
              {d.total / total >= MINIMO_PARA_ETIQUETA_INTERNA && (
                <LabelList
                  dataKey={d.clave}
                  position="center"
                  /* Dentro de un relleno de color la etiqueta se pinta blanca o
                     en ink según la luminancia del segmento. */
                  fill={d.clave === "aproximada" ? "#0b0b0b" : "#ffffff"}
                  fontSize={12}
                  fontWeight={600}
                />
              )}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Tres series: la leyenda siempre está presente. */}
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-sm">
        {datos.map((d) => (
          <li key={d.clave} className="flex items-center gap-2">
            <span
              aria-hidden
              className="inline-block size-2.5 shrink-0 rounded-sm"
              style={{ background: TONO[d.clave] }}
            />
            <span className="text-[var(--text-secondary)]">{d.etiqueta}</span>
            <span className="font-medium tabular-nums text-[var(--text-primary)]">
              {((d.total / total) * 100).toFixed(0)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
