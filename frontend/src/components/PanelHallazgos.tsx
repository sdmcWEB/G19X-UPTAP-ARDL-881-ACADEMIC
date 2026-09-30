import { useMemo, useState } from "react";

import {
  ETIQUETA_SEVERIDAD,
  ETIQUETA_VERIFICACION,
  type Hallazgo,
  type Severidad,
} from "../lib/tipos";

const COLOR_SEVERIDAD: Record<Severidad, string> = {
  critica: "bg-red-100 text-red-900 border-red-300",
  alta: "bg-orange-100 text-orange-900 border-orange-300",
  media: "bg-amber-100 text-amber-900 border-amber-300",
  baja: "bg-sky-100 text-sky-900 border-sky-300",
  informativa: "bg-neutral-100 text-neutral-700 border-neutral-300",
};

const ORDEN: Record<Severidad, number> = {
  critica: 0,
  alta: 1,
  media: 2,
  baja: 3,
  informativa: 4,
};

interface Props {
  hallazgos: Hallazgo[];
  seleccionado: string | null;
  onSeleccionar: (id: string) => void;
}

export function PanelHallazgos({ hallazgos, seleccionado, onSeleccionar }: Props) {
  const [soloVerificados, setSoloVerificados] = useState(false);

  const visibles = useMemo(() => {
    const lista = soloVerificados
      ? hallazgos.filter((h) => h.verificacion !== "no_verificada")
      : hallazgos;
    return [...lista].sort((a, b) => ORDEN[a.severidad] - ORDEN[b.severidad]);
  }, [hallazgos, soloVerificados]);

  const noVerificados = hallazgos.filter((h) => h.verificacion === "no_verificada").length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">
          Hallazgos <span className="text-neutral-500">({visibles.length})</span>
        </h2>
        <label className="flex items-center gap-2 text-sm text-neutral-600">
          <input
            type="checkbox"
            checked={soloVerificados}
            onChange={(e) => setSoloVerificados(e.target.checked)}
          />
          Solo con cita verificada
        </label>
      </div>

      {noVerificados > 0 && !soloVerificados && (
        <p className="rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">
          {noVerificados} {noVerificados === 1 ? "hallazgo" : "hallazgos"} con cita que no se
          pudo confirmar contra el documento. Revísalos antes de tomarlos como evidencia.
        </p>
      )}

      <div className="flex flex-col gap-2">
        {visibles.map((h) => (
          <button
            key={h.id}
            onClick={() => onSeleccionar(h.id)}
            className={`rounded-lg border p-3 text-left transition ${
              seleccionado === h.id ? "ring-2 ring-neutral-900" : "hover:bg-neutral-50"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-medium">{h.titulo}</span>
              <span
                className={`shrink-0 rounded border px-2 py-0.5 text-xs ${
                  COLOR_SEVERIDAD[h.severidad]
                }`}
              >
                {ETIQUETA_SEVERIDAD[h.severidad]}
              </span>
            </div>

            <p className="mt-2 text-sm text-neutral-700">{h.explicacion}</p>

            <blockquote className="mt-2 border-l-2 border-neutral-300 pl-2 text-sm italic text-neutral-600">
              “{h.cita_textual}”
            </blockquote>

            <p className="mt-2 text-sm">
              <span className="font-medium">Recomendación: </span>
              {h.recomendacion}
            </p>

            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-neutral-500">
              <span
                className={
                  h.verificacion === "verificada"
                    ? "text-emerald-700"
                    : h.verificacion === "aproximada"
                      ? "text-amber-700"
                      : "text-red-700"
                }
              >
                {ETIQUETA_VERIFICACION[h.verificacion]}
                {h.score_similitud !== null && ` · ${h.score_similitud.toFixed(0)}%`}
              </span>
              <span>·</span>
              <span>{h.tipo_codigo}</span>
              {h.confianza_modelo !== null && (
                <>
                  <span>·</span>
                  <span>confianza {(h.confianza_modelo * 100).toFixed(0)}%</span>
                </>
              )}
            </div>
          </button>
        ))}

        {visibles.length === 0 && (
          <p className="rounded border border-dashed p-6 text-center text-sm text-neutral-500">
            Sin hallazgos que mostrar.
          </p>
        )}
      </div>
    </div>
  );
}
