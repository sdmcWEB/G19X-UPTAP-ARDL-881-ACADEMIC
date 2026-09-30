import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PuntoTendencia } from "../../lib/tipos";
import { VizTooltip } from "./Tooltip";

/* Contratos y hallazgos viven en escalas muy distintas: un día son 3 contratos
   y 40 hallazgos. Ponerlos en un mismo plot exigiría dos ejes y, con dos
   escalas, la alineación entre ambas es arbitraria e inventa una correlación
   que no está en los datos.

   La salida correcta son múltiplos pequeños: dos gráficas apiladas que
   comparten el eje x, cada una con su propia escala. */

function fecha(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
  });
}

interface PanelProps {
  datos: PuntoTendencia[];
  clave: "contratos" | "hallazgos";
  nombre: string;
  ejeVisible: boolean;
}

function Panel({ datos, clave, nombre, ejeVisible }: PanelProps) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium text-[var(--text-secondary)]">{nombre}</p>
      <ResponsiveContainer width="100%" height={ejeVisible ? 132 : 108}>
        <AreaChart data={datos} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" strokeDasharray="0" vertical={false} />
          <XAxis
            dataKey="fecha"
            hide={!ejeVisible}
            tickFormatter={fecha}
            tickLine={false}
            axisLine={{ stroke: "var(--axis)" }}
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            minTickGap={28}
          />
          <YAxis
            allowDecimals={false}
            tickLine={false}
            axisLine={false}
            width={32}
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          />
          <Tooltip
            content={<VizTooltip />}
            labelFormatter={(v) => fecha(String(v))}
            /* Cruceta de una hairline: en una serie temporal el lector necesita
               ver a qué día corresponde el valor. */
            cursor={{ stroke: "var(--axis)", strokeWidth: 1 }}
          />
          <Area
            type="monotone"
            dataKey={clave}
            name={nombre}
            stroke="var(--series-1)"
            strokeWidth={2}
            /* El relleno es un lavado al 10%, nunca un bloque saturado. */
            fill="var(--series-1)"
            fillOpacity={0.1}
            dot={false}
            /* Anillo de 2px del color de la superficie, para que el punto activo
               se lea donde cruza la línea. */
            activeDot={{ r: 4, stroke: "var(--surface-1)", strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function GraficaActividad({ datos }: { datos: PuntoTendencia[] }) {
  if (datos.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-[var(--text-muted)]">
        Sin actividad en el periodo.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <Panel datos={datos} clave="contratos" nombre="Contratos subidos" ejeVisible={false} />
      <Panel datos={datos} clave="hallazgos" nombre="Hallazgos generados" ejeVisible />
    </div>
  );
}
