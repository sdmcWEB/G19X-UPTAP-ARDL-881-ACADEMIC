import { useEffect, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

import { token } from "../lib/api";
import type { BBox } from "../lib/tipos";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface Props {
  url: string;
  /** Cajas de la cláusula seleccionada. Se resaltan sobre la página. */
  resaltados: BBox[];
  /** Página a la que salta el visor cuando cambia el hallazgo seleccionado. */
  paginaObjetivo?: number;
}

/** Dimensiones originales de la página, en puntos PDF. */
interface DimPagina {
  width: number;
  height: number;
}

export function VisorContrato({ url, resaltados, paginaObjetivo }: Props) {
  const [totalPaginas, setTotalPaginas] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [dim, setDim] = useState<DimPagina | null>(null);
  const [anchoRender, setAnchoRender] = useState(800);
  const [error, setError] = useState<string | null>(null);

  // El salto lo manda el panel de hallazgos al seleccionar un hallazgo.
  // Va en un efecto, no en el cuerpo del render: un setState durante el render
  // provoca un re-render inmediato y pelea con la navegación manual de páginas.
  useEffect(() => {
    if (paginaObjetivo) setPagina(paginaObjetivo);
  }, [paginaObjetivo]);

  const cajasDeEstaPagina = resaltados.filter((r) => r.page === pagina);

  // pdf.js no manda el header de auth por su cuenta: se le pasa explícito.
  const fuente = {
    url,
    httpHeaders: { Authorization: `Bearer ${token.get() ?? ""}` },
  };

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
        No se pudo cargar el documento: {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3 text-sm">
        <button
          onClick={() => setPagina((p) => Math.max(1, p - 1))}
          disabled={pagina <= 1}
          className="rounded border px-3 py-1 disabled:opacity-40"
        >
          Anterior
        </button>
        <span className="tabular-nums text-neutral-600">
          Página {pagina} de {totalPaginas || "…"}
        </span>
        <button
          onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
          disabled={pagina >= totalPaginas}
          className="rounded border px-3 py-1 disabled:opacity-40"
        >
          Siguiente
        </button>

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setAnchoRender((a) => Math.max(400, a - 100))}
            className="rounded border px-2 py-1"
          >
            −
          </button>
          <button
            onClick={() => setAnchoRender((a) => Math.min(1400, a + 100))}
            className="rounded border px-2 py-1"
          >
            +
          </button>
        </div>
      </div>

      <div className="relative overflow-auto rounded-lg border bg-neutral-100 p-4">
        <Document
          file={fuente}
          onLoadSuccess={({ numPages }) => setTotalPaginas(numPages)}
          onLoadError={(e) => setError(e.message)}
          loading={<p className="p-8 text-sm text-neutral-500">Cargando documento…</p>}
        >
          <div className="relative inline-block">
            <Page
              pageNumber={pagina}
              width={anchoRender}
              onLoadSuccess={(p) =>
                setDim({ width: p.originalWidth, height: p.originalHeight })
              }
            />

            {/* Capa de resaltado. Las coordenadas vienen en puntos PDF con
                origen arriba-izquierda (PyMuPDF), así que se convierten a
                porcentajes y quedan independientes del zoom. */}
            {dim &&
              cajasDeEstaPagina.map((r, i) => {
                const [x0, y0, x1, y1] = r.bbox;
                return (
                  <div
                    key={i}
                    className="pointer-events-none absolute bg-amber-300/40 ring-2 ring-amber-500"
                    style={{
                      left: `${(x0 / dim.width) * 100}%`,
                      top: `${(y0 / dim.height) * 100}%`,
                      width: `${((x1 - x0) / dim.width) * 100}%`,
                      height: `${((y1 - y0) / dim.height) * 100}%`,
                    }}
                  />
                );
              })}
          </div>
        </Document>
      </div>
    </div>
  );
}
