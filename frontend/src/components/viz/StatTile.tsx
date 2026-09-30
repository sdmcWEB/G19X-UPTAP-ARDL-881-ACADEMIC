import type { ReactNode } from "react";

interface Props {
  etiqueta: string;
  valor: ReactNode;
  /** Contexto bajo el valor: contra qué se compara o de qué universo sale. */
  pie?: string;
  /** Figura principal del tablero. Solo una por vista. */
  destacado?: boolean;
}

export function StatTile({ etiqueta, valor, pie, destacado = false }: Props) {
  return (
    <div className="viz-root rounded-xl border border-[var(--hairline)] bg-[var(--surface-1)] p-5">
      <p className="text-sm text-[var(--text-secondary)]">{etiqueta}</p>
      {/* Cifras proporcionales, no tabulares: a este tamaño `tabular-nums`
          deja los números sueltos. */}
      <p
        className={`mt-1 font-semibold text-[var(--text-primary)] ${
          destacado ? "text-5xl" : "text-3xl"
        }`}
      >
        {valor}
      </p>
      {pie && <p className="mt-1 text-xs text-[var(--text-muted)]">{pie}</p>}
    </div>
  );
}
