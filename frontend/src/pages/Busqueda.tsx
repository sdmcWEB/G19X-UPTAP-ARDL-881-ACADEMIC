import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../lib/api";

/** Barra de similitud. El número va al lado: el color no carga el dato solo. */
function Similitud({ valor }: { valor: number }) {
  return (
    <div className="flex shrink-0 items-center gap-2" title={`Similitud ${(valor * 100).toFixed(0)}%`}>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-neutral-200">
        <div
          className="h-full rounded-full bg-neutral-700"
          style={{ width: `${Math.min(valor * 100, 100)}%` }}
        />
      </div>
      <span className="w-9 text-right text-xs tabular-nums text-neutral-500">
        {(valor * 100).toFixed(0)}%
      </span>
    </div>
  );
}

export function Busqueda() {
  const [texto, setTexto] = useState("");
  // La consulta enviada se separa de lo que se escribe: así no se dispara una
  // búsqueda (y una vectorización) por cada tecla.
  const [consulta, setConsulta] = useState("");

  const { data, isFetching, error } = useQuery({
    queryKey: ["busqueda", consulta],
    queryFn: () => api.buscar(consulta),
    enabled: consulta.length >= 3,
  });

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="text-xl font-semibold">Búsqueda en cláusulas</h1>
      <p className="mt-1 text-sm text-neutral-600">
        Busca por significado, no por palabras exactas. &ldquo;Penalización por retraso&rdquo;
        encuentra cláusulas que dicen &ldquo;pena convencional por demora en la entrega&rdquo;.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setConsulta(texto.trim());
        }}
        className="mt-5 flex gap-2"
      >
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="¿Qué buscas en los contratos?"
          className="flex-1 rounded-lg border px-3 py-2"
          autoFocus
        />
        <button
          type="submit"
          disabled={texto.trim().length < 3 || isFetching}
          className="rounded-lg bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-40"
        >
          {isFetching ? "Buscando…" : "Buscar"}
        </button>
      </form>

      {texto.trim().length > 0 && texto.trim().length < 3 && (
        <p className="mt-2 text-xs text-neutral-500">Escribe al menos 3 caracteres.</p>
      )}

      {error && (
        <p className="mt-4 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-800">
          {error instanceof Error ? error.message : "La búsqueda falló"}
        </p>
      )}

      {data && (
        <div className="mt-6">
          <p className="text-sm text-neutral-500">
            {data.total === 0
              ? "Ninguna cláusula se parece lo suficiente a esa consulta."
              : `${data.total} ${data.total === 1 ? "cláusula" : "cláusulas"}`}
          </p>

          <ul className="mt-3 flex flex-col gap-2">
            {data.coincidencias.map((c) => (
              <li key={c.clausula_id}>
                <Link
                  to={`/contratos/${c.contrato_id}`}
                  className="block rounded-lg border p-4 transition hover:bg-neutral-50"
                >
                  <div className="flex items-start justify-between gap-4">
                    <p className="min-w-0 font-medium">
                      {c.encabezado ? `Cláusula ${c.encabezado}` : c.clause_id}
                    </p>
                    <Similitud valor={c.similitud} />
                  </div>

                  <p className="mt-1.5 text-sm text-neutral-700">{c.fragmento}</p>

                  {/* El archivo va al pie: en una búsqueda dentro de un mismo
                      contrato se repite idéntico en cada resultado. */}
                  <p className="mt-2 truncate text-xs text-neutral-500">
                    {c.nombre_archivo} · página {c.pagina_inicio}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
