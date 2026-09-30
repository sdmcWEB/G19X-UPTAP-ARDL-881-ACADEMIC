import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { Link } from "react-router-dom";

import { api } from "../lib/api";
import type { Contrato, EstadoContrato } from "../lib/tipos";

const ETIQUETA_ESTADO: Record<EstadoContrato, string> = {
  recibido: "En cola",
  extrayendo: "Extrayendo texto",
  analizando: "Analizando",
  listo: "Listo",
  error: "Error",
};

const EN_PROCESO: EstadoContrato[] = ["recibido", "extrayendo", "analizando"];

function Riesgo({ valor }: { valor: number | null }) {
  if (valor === null) return <span className="text-neutral-400">—</span>;
  const color =
    valor >= 70 ? "text-red-700" : valor >= 40 ? "text-amber-700" : "text-emerald-700";
  return <span className={`font-semibold tabular-nums ${color}`}>{valor.toFixed(0)}</span>;
}

export function Contratos() {
  const qc = useQueryClient();
  const inputArchivo = useRef<HTMLInputElement>(null);

  const { data: contratos = [], isLoading } = useQuery({
    queryKey: ["contratos"],
    queryFn: api.contratos,
    // Mientras haya algo en proceso, se refresca solo.
    refetchInterval: (q) =>
      (q.state.data as Contrato[] | undefined)?.some((c) => EN_PROCESO.includes(c.status))
        ? 3000
        : false,
  });

  const subir = useMutation({
    mutationFn: api.subir,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contratos"] }),
  });

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Contratos</h1>
        <div>
          <input
            ref={inputArchivo}
            type="file"
            accept=".pdf,.docx"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) subir.mutate(f);
              e.target.value = "";
            }}
          />
          <button
            onClick={() => inputArchivo.current?.click()}
            disabled={subir.isPending}
            className="rounded-lg bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {subir.isPending ? "Subiendo…" : "Subir contrato"}
          </button>
        </div>
      </div>

      {subir.error && (
        <p className="mt-3 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-800">
          {subir.error.message}
        </p>
      )}

      {isLoading ? (
        <p className="mt-6 text-sm text-neutral-500">Cargando…</p>
      ) : contratos.length === 0 ? (
        <p className="mt-6 rounded-lg border border-dashed p-10 text-center text-sm text-neutral-500">
          Todavía no hay contratos. Sube un PDF o un .docx para analizarlo.
        </p>
      ) : (
        <table className="mt-6 w-full text-sm">
          <thead className="border-b text-left text-neutral-500">
            <tr>
              <th className="py-2">Archivo</th>
              <th className="py-2">Estado</th>
              <th className="py-2">Págs.</th>
              <th className="py-2">Riesgo</th>
              <th className="py-2">Subido</th>
            </tr>
          </thead>
          <tbody>
            {contratos.map((c) => (
              <tr key={c.id} className="border-b last:border-0 hover:bg-neutral-50">
                <td className="py-2">
                  <Link to={`/contratos/${c.id}`} className="font-medium hover:underline">
                    {c.nombre_archivo}
                  </Link>
                  {c.ocr_aplicado && (
                    <span
                      className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900"
                      title="El texto se obtuvo por OCR: puede tener errores de reconocimiento"
                    >
                      OCR
                    </span>
                  )}
                </td>
                <td className="py-2">
                  {ETIQUETA_ESTADO[c.status]}
                  {c.status === "error" && c.error_msg && (
                    <span className="block text-xs text-red-700">{c.error_msg}</span>
                  )}
                </td>
                <td className="py-2 tabular-nums">{c.paginas ?? "—"}</td>
                <td className="py-2">
                  <Riesgo valor={c.puntuacion_riesgo} />
                </td>
                <td className="py-2 text-neutral-500">
                  {new Date(c.created_at).toLocaleDateString("es-MX")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
