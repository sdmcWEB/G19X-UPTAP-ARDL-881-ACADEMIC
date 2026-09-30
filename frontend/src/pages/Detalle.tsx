import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { PanelHallazgos } from "../components/PanelHallazgos";
import { VisorContrato } from "../components/VisorContrato";
import { api } from "../lib/api";

const EN_PROCESO = ["recibido", "extrayendo", "analizando"];

export function Detalle() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const [seleccionado, setSeleccionado] = useState<string | null>(null);

  const { data: contrato, isLoading } = useQuery({
    queryKey: ["contrato", id],
    queryFn: () => api.contrato(id),
    refetchInterval: (q) =>
      q.state.data && EN_PROCESO.includes(q.state.data.status) ? 3000 : false,
  });

  const reanalizar = useMutation({
    mutationFn: () => api.reanalizar(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contrato", id] }),
  });

  // La cláusula del hallazgo seleccionado es la que se resalta en el visor.
  const { resaltados, paginaObjetivo } = useMemo(() => {
    if (!contrato || !seleccionado) return { resaltados: [], paginaObjetivo: undefined };
    const hallazgo = contrato.hallazgos.find((h) => h.id === seleccionado);
    const clausula = contrato.clausulas.find((c) => c.id === hallazgo?.clausula_id);
    return {
      resaltados: clausula?.bboxes ?? [],
      paginaObjetivo: clausula?.pagina_inicio,
    };
  }, [contrato, seleccionado]);

  if (isLoading) return <p className="p-6 text-sm text-neutral-500">Cargando…</p>;
  if (!contrato) return <p className="p-6 text-sm text-red-700">Contrato no encontrado.</p>;

  const esPdf = contrato.mime_type === "application/pdf";

  return (
    <div className="mx-auto max-w-[1600px] p-6">
      <Link to="/contratos" className="text-sm text-neutral-500 hover:underline">
        ← Contratos
      </Link>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{contrato.nombre_archivo}</h1>
          <p className="text-sm text-neutral-500">
            {contrato.paginas ?? "—"} páginas · {contrato.hallazgos.length} hallazgos
            {contrato.puntuacion_riesgo !== null &&
              ` · riesgo ${contrato.puntuacion_riesgo.toFixed(0)}/100`}
          </p>
        </div>
        <button
          onClick={() => reanalizar.mutate()}
          disabled={reanalizar.isPending || EN_PROCESO.includes(contrato.status)}
          className="rounded-lg border px-4 py-2 text-sm disabled:opacity-40"
        >
          Volver a analizar
        </button>
      </div>

      {contrato.ocr_aplicado && (
        <p className="mt-3 rounded border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900">
          Este documento se procesó con OCR. El texto puede tener errores de
          reconocimiento y eso afecta la precisión de las citas.
        </p>
      )}

      {EN_PROCESO.includes(contrato.status) && (
        <p className="mt-3 rounded border bg-neutral-50 p-2 text-sm text-neutral-600">
          Análisis en curso… esta página se actualiza sola.
        </p>
      )}

      {contrato.status === "error" && (
        <p className="mt-3 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-800">
          El análisis falló: {contrato.error_msg}
        </p>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_480px]">
        <div>
          {esPdf ? (
            <VisorContrato
              url={api.urlArchivo(contrato.id)}
              resaltados={resaltados}
              paginaObjetivo={paginaObjetivo}
            />
          ) : (
            <p className="rounded-lg border border-dashed p-6 text-sm text-neutral-500">
              Los archivos de Word no tienen geometría de página, así que no hay
              visor con resaltado. El hallazgo se ubica por cláusula.
            </p>
          )}
        </div>

        <PanelHallazgos
          hallazgos={contrato.hallazgos}
          seleccionado={seleccionado}
          onSeleccionar={setSeleccionado}
        />
      </div>
    </div>
  );
}
