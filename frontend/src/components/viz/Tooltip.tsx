// En Recharts 3 el contenido personalizado recibe TooltipContentProps;
// TooltipProps pasó a ser el tipo del componente <Tooltip>, sin payload.
import type { TooltipContentProps } from "recharts";

/** Tooltip compartido. Los valores viajan en ink de texto, no en el color de
 *  la serie: la identidad la carga el punto de color a su lado. */
export function VizTooltip({
  active,
  payload,
  label,
}: Partial<TooltipContentProps<number, string>>) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-[var(--hairline)] bg-[var(--surface-1)] px-3 py-2 text-xs shadow-sm">
      {label !== undefined && (
        <p className="mb-1 font-medium text-[var(--text-primary)]">{String(label)}</p>
      )}
      {payload.map((p) => (
        <p key={String(p.dataKey)} className="flex items-center gap-2 text-[var(--text-secondary)]">
          <span
            aria-hidden
            className="inline-block size-2 shrink-0 rounded-full"
            style={{ background: p.color }}
          />
          <span>{p.name}</span>
          <span className="ml-auto font-medium tabular-nums text-[var(--text-primary)]">
            {p.value}
          </span>
        </p>
      ))}
    </div>
  );
}
