import { type ReactNode, useId, useState } from "react";

interface ColumnaTabla<T> {
  encabezado: string;
  valor: (fila: T) => ReactNode;
  numerica?: boolean;
}

interface Props<T> {
  titulo: string;
  subtitulo?: string;
  /** Aviso corto bajo el subtítulo, para advertencias sobre los datos. */
  nota?: ReactNode;
  grafica: ReactNode;
  /** Gemela en tabla. Ninguna gráfica se envía sin ella: un valor nunca
   *  queda accesible solo por color o solo por tooltip. */
  filas: T[];
  columnas: ColumnaTabla<T>[];
  /** Mientras se recarga, la vista previa se mantiene atenuada en lugar de
   *  parpadear un esqueleto y brincar el layout. */
  recargando?: boolean;
}

export function TarjetaGrafica<T>({
  titulo,
  subtitulo,
  nota,
  grafica,
  filas,
  columnas,
  recargando = false,
}: Props<T>) {
  const [verTabla, setVerTabla] = useState(false);
  const idPanel = useId();

  return (
    <section className="viz-root rounded-xl border border-[var(--hairline)] bg-[var(--surface-1)] p-5">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="font-semibold text-[var(--text-primary)]">{titulo}</h2>
          {subtitulo && (
            <p className="mt-0.5 text-sm text-[var(--text-secondary)]">{subtitulo}</p>
          )}
          {nota && <p className="mt-1.5 text-xs text-[var(--text-muted)]">{nota}</p>}
        </div>

        <button
          onClick={() => setVerTabla((v) => !v)}
          aria-expanded={verTabla}
          aria-controls={idPanel}
          className="shrink-0 rounded-lg border border-[var(--hairline)] px-2.5 py-1 text-xs text-[var(--text-secondary)] hover:bg-[var(--plane)]"
        >
          {verTabla ? "Ver gráfica" : "Ver tabla"}
        </button>
      </header>

      <div
        id={idPanel}
        className={`mt-4 transition-opacity ${recargando ? "opacity-50" : "opacity-100"}`}
      >
        {verTabla ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--grid)] text-left text-[var(--text-muted)]">
                {columnas.map((c) => (
                  <th
                    key={c.encabezado}
                    className={`py-1.5 font-normal ${c.numerica ? "text-right" : ""}`}
                  >
                    {c.encabezado}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filas.map((fila, i) => (
                <tr key={i} className="border-b border-[var(--grid)] last:border-0">
                  {columnas.map((c) => (
                    <td
                      key={c.encabezado}
                      className={`py-1.5 text-[var(--text-primary)] ${
                        c.numerica ? "text-right tabular-nums" : ""
                      }`}
                    >
                      {c.valor(fila)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          grafica
        )}
      </div>
    </section>
  );
}
