import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Conteo } from "../../lib/tipos";
import { VizTooltip } from "./Tooltip";

/* Los tipos de riesgo son categorías *nominales*: no tienen orden natural, así
   que van todas del mismo color. Oscurecer la barra más grande doblaría en el
   color lo que el largo ya dice y gastaría el único canal libre.

   Horizontal porque los nombres son largos: "Responsabilidad ilimitada" no
   cabe bajo una columna. */
export function GraficaTipos({ datos }: { datos: Conteo[] }) {
  if (datos.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-[var(--text-muted)]">
        Todavía no hay hallazgos clasificados.
      </p>
    );
  }

  // 34px por fila más la banda del eje: el contenedor crece con los datos en
  // lugar de fijar una altura que recorte el eje y genere un scroll anidado.
  const altura = datos.length * 34 + 24;

  return (
    <ResponsiveContainer width="100%" height={altura}>
      <BarChart
        data={datos}
        layout="vertical"
        margin={{ top: 0, right: 44, bottom: 0, left: 0 }}
      >
        <CartesianGrid stroke="var(--grid)" strokeDasharray="0" horizontal={false} />
        <XAxis type="number" hide allowDecimals={false} />
        <YAxis
          type="category"
          dataKey="etiqueta"
          tickLine={false}
          axisLine={false}
          width={190}
          tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
        />
        <Tooltip content={<VizTooltip />} cursor={{ fill: "var(--plane)" }} />
        <Bar
          dataKey="total"
          name="Hallazgos"
          fill="var(--series-1)"
          maxBarSize={20}
          radius={[0, 4, 4, 0]}
          isAnimationActive={false}
        >
          {/* Barras → el valor en la punta. */}
          <LabelList
            dataKey="total"
            position="right"
            offset={8}
            fill="var(--text-secondary)"
            fontSize={12}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
