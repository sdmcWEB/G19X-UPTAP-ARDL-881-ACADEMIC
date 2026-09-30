import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Conteo } from "../../lib/tipos";
import { VizTooltip } from "./Tooltip";

/* La severidad es una categoría *ordenada*, así que lleva rampa ordinal de un
   solo tono: más severo = más oscuro. No es una rampa sobre categorías
   nominales —eso doblaría el largo de la barra en el color— sino el orden
   propio de la escala. Validada con --ordinal en ambos modos. */
const TONO: Record<string, string> = {
  critica: "var(--sev-critica)",
  alta: "var(--sev-alta)",
  media: "var(--sev-media)",
  baja: "var(--sev-baja)",
  informativa: "var(--sev-informativa)",
};

export function GraficaSeveridad({ datos }: { datos: Conteo[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={datos} margin={{ top: 20, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid stroke="var(--grid)" strokeDasharray="0" vertical={false} />
        <XAxis
          dataKey="etiqueta"
          tickLine={false}
          axisLine={{ stroke: "var(--axis)" }}
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
        />
        <YAxis
          allowDecimals={false}
          tickLine={false}
          axisLine={false}
          width={36}
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
        />
        <Tooltip content={<VizTooltip />} cursor={{ fill: "var(--plane)" }} />
        {/* 24px de tope: la barra nunca llena su banda, el resto es aire.
            Extremo redondeado arriba, escuadra en la línea base. */}
        <Bar
          dataKey="total"
          name="Hallazgos"
          maxBarSize={24}
          radius={[4, 4, 0, 0]}
          isAnimationActive={false}
        >
          {datos.map((d) => (
            <Cell key={d.clave} fill={TONO[d.clave]} />
          ))}
          {/* Serie única: el valor va en la tapa y el eje x carga la identidad,
              así que no hace falta caja de leyenda. */}
          <LabelList
            dataKey="total"
            position="top"
            offset={8}
            fill="var(--text-secondary)"
            fontSize={12}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
