import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api } from "../lib/api";
import {
  ETIQUETA_REVISION,
  ETIQUETA_SEVERIDAD,
  ETIQUETA_VERIFICACION,
  type Hallazgo,
  type Revision,
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

const COLOR_REVISION: Record<Revision, string> = {
  pendiente: "text-amber-700",
  confirmado: "text-emerald-700",
  descartado: "text-neutral-500",
};

/** Botonera del dictamen. Descartar pide motivo porque sin él, quien revise
 *  después no sabe si el riesgo no aplicaba o si alguien lo cerró por error. */
function Dictamen({ hallazgo, contratoId }: { hallazgo: Hallazgo; contratoId: string }) {
  const qc = useQueryClient();
  const [pidiendoMotivo, setPidiendoMotivo] = useState(false);
  const [motivo, setMotivo] = useState("");

  const dictaminar = useMutation({
    mutationFn: ({ revision, comentario }: { revision: Revision; comentario?: string }) =>
      api.dictaminar(hallazgo.id, revision, comentario),
    onSuccess: () => {
      setPidiendoMotivo(false);
      setMotivo("");
      qc.invalidateQueries({ queryKey: ["contrato", contratoId] });
    },
  });

  const ocupado = dictaminar.isPending;

  return (
    <div onClick={(e) => e.stopPropagation()}>
      {hallazgo.revision === "pendiente" ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            onClick={() => dictaminar.mutate({ revision: "confirmado" })}
            disabled={ocupado}
            className="rounded-lg bg-emerald-700 px-3 py-1 text-xs text-white disabled:opacity-40"
          >
            Confirmar
          </button>
          <button
            onClick={() => setPidiendoMotivo((v) => !v)}
            disabled={ocupado}
            className="rounded-lg border px-3 py-1 text-xs disabled:opacity-40"
          >
            Descartar
          </button>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className={`font-medium ${COLOR_REVISION[hallazgo.revision]}`}>
            {ETIQUETA_REVISION[hallazgo.revision]}
            {hallazgo.revisado_por && ` por ${hallazgo.revisado_por}`}
          </span>
          <button
            onClick={() => dictaminar.mutate({ revision: "pendiente" })}
            disabled={ocupado}
            className="text-neutral-500 underline disabled:opacity-40"
          >
            deshacer
          </button>
        </div>
      )}

      {hallazgo.comentario_revision && (
        <p className="mt-1.5 text-xs text-neutral-600">{hallazgo.comentario_revision}</p>
      )}

      {pidiendoMotivo && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            dictaminar.mutate({ revision: "descartado", comentario: motivo });
          }}
          className="mt-2 flex gap-2"
        >
          <input
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="¿Por qué se descarta?"
            autoFocus
            className="flex-1 rounded-lg border px-2 py-1 text-xs"
          />
          <button
            type="submit"
            disabled={!motivo.trim() || ocupado}
            className="rounded-lg bg-neutral-900 px-3 py-1 text-xs text-white disabled:opacity-40"
          >
            Descartar
          </button>
        </form>
      )}

      {dictaminar.error && (
        <p className="mt-1.5 text-xs text-red-700">{dictaminar.error.message}</p>
      )}
    </div>
  );
}

interface Props {
  hallazgos: Hallazgo[];
  contratoId: string;
  seleccionado: string | null;
  onSeleccionar: (id: string) => void;
}

export function PanelHallazgos({ hallazgos, contratoId, seleccionado, onSeleccionar }: Props) {
  const [soloVerificados, setSoloVerificados] = useState(false);
  const [soloPendientes, setSoloPendientes] = useState(false);

  const visibles = useMemo(() => {
    let lista = hallazgos;
    if (soloVerificados) lista = lista.filter((h) => h.verificacion !== "no_verificada");
    if (soloPendientes) lista = lista.filter((h) => h.revision === "pendiente");
    return [...lista].sort((a, b) => ORDEN[a.severidad] - ORDEN[b.severidad]);
  }, [hallazgos, soloVerificados, soloPendientes]);

  const pendientes = hallazgos.filter((h) => h.revision === "pendiente").length;

  const noVerificados = hallazgos.filter((h) => h.verificacion === "no_verificada").length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">
          Hallazgos <span className="text-neutral-500">({visibles.length})</span>
        </h2>
        <div className="flex flex-col items-end gap-1 text-sm text-neutral-600">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={soloVerificados}
              onChange={(e) => setSoloVerificados(e.target.checked)}
            />
            Solo con cita verificada
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={soloPendientes}
              onChange={(e) => setSoloPendientes(e.target.checked)}
            />
            Solo sin revisar ({pendientes})
          </label>
        </div>
      </div>

      {noVerificados > 0 && !soloVerificados && (
        <p className="rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">
          {noVerificados} {noVerificados === 1 ? "hallazgo" : "hallazgos"} con cita que no se
          pudo confirmar contra el documento. Revísalos antes de tomarlos como evidencia.
        </p>
      )}

      <div className="flex flex-col gap-2">
        {visibles.map((h) => (
          // No es <button>: lleva controles dentro, y un botón anidado en otro
          // es HTML inválido y rompe la navegación por teclado.
          <div
            key={h.id}
            role="button"
            tabIndex={0}
            onClick={() => onSeleccionar(h.id)}
            onKeyDown={(e) => {
              // Solo cuando la tecla es de la tarjeta. Sin esta guarda, el
              // Enter que sube desde el campo de motivo lo captura la tarjeta
              // y el formulario nunca se envía.
              if (e.target !== e.currentTarget) return;
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSeleccionar(h.id);
              }
            }}
            className={`cursor-pointer rounded-lg border p-3 text-left transition ${
              seleccionado === h.id ? "ring-2 ring-neutral-900" : "hover:bg-neutral-50"
            } ${h.revision === "descartado" ? "opacity-60" : ""}`}
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

            <Dictamen hallazgo={h} contratoId={contratoId} />
          </div>
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
