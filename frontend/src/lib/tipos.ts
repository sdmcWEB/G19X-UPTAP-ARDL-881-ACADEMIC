export type Severidad = "critica" | "alta" | "media" | "baja" | "informativa";
export type Verificacion = "verificada" | "aproximada" | "no_verificada";
export type Revision = "pendiente" | "confirmado" | "descartado";
export type EstadoContrato =
  | "recibido"
  | "extrayendo"
  | "analizando"
  | "listo"
  | "error";

export interface BBox {
  page: number;
  bbox: [number, number, number, number]; // x0, y0, x1, y1 en puntos PDF
}

export interface Clausula {
  id: string;
  clause_id: string;
  orden: number;
  encabezado: string | null;
  texto: string;
  pagina_inicio: number;
  pagina_fin: number;
  bboxes: BBox[];
}

export interface Hallazgo {
  id: string;
  clausula_id: string | null;
  tipo_codigo: string;
  severidad: Severidad;
  titulo: string;
  explicacion: string;
  recomendacion: string;
  cita_textual: string;
  verificacion: Verificacion;
  score_similitud: number | null;
  confianza_modelo: number | null;

  revision: Revision;
  comentario_revision: string | null;
  revisado_at: string | null;
  revisado_por: string | null;
}

export interface Contrato {
  id: string;
  nombre_archivo: string;
  mime_type: string;
  paginas: number | null;
  status: EstadoContrato;
  error_msg: string | null;
  ocr_aplicado: boolean;
  puntuacion_riesgo: number | null;
  created_at: string;
  analizado_at: string | null;
}

export interface ContratoDetalle extends Contrato {
  hallazgos: Hallazgo[];
  clausulas: Clausula[];
}

export const SEVERIDADES: Severidad[] = [
  "critica",
  "alta",
  "media",
  "baja",
  "informativa",
];

export const ETIQUETA_SEVERIDAD: Record<Severidad, string> = {
  critica: "Crítica",
  alta: "Alta",
  media: "Media",
  baja: "Baja",
  informativa: "Informativa",
};

export const ETIQUETA_REVISION: Record<Revision, string> = {
  pendiente: "Sin revisar",
  confirmado: "Confirmado",
  descartado: "Descartado",
};

export const ETIQUETA_VERIFICACION: Record<Verificacion, string> = {
  verificada: "Cita verificada",
  aproximada: "Cita aproximada",
  no_verificada: "Cita no verificada",
};

// --- Tablero ---

export interface Conteo {
  clave: string;
  etiqueta: string;
  total: number;
}

export interface PuntoTendencia {
  fecha: string; // ISO (YYYY-MM-DD)
  contratos: number;
  hallazgos: number;
}

export interface ContratoRiesgoso {
  id: string;
  nombre_archivo: string;
  puntuacion_riesgo: number;
  hallazgos: number;
  ocr_aplicado: boolean;
}

export interface Resumen {
  dias: number | null;
  contratos_totales: number;
  contratos_analizados: number;
  hallazgos_totales: number;
  riesgo_promedio: number | null;
  pct_citas_verificadas: number | null;
  pct_con_ocr: number | null;
  por_severidad: Conteo[];
  por_verificacion: Conteo[];
  por_tipo: Conteo[];
  tendencia: PuntoTendencia[];
  contratos_riesgosos: ContratoRiesgoso[];
}

/** Opciones del filtro de periodo. `null` = todo el histórico. */
export const PERIODOS: { etiqueta: string; dias: number | null }[] = [
  { etiqueta: "30 días", dias: 30 },
  { etiqueta: "90 días", dias: 90 },
  { etiqueta: "1 año", dias: 365 },
  { etiqueta: "Todo", dias: null },
];

// --- Búsqueda semántica ---

export interface Coincidencia {
  clausula_id: string;
  clause_id: string;
  encabezado: string | null;
  fragmento: string;
  pagina_inicio: number;
  similitud: number; // 0-1
  contrato_id: string;
  nombre_archivo: string;
}

export interface Resultados {
  consulta: string;
  total: number;
  coincidencias: Coincidencia[];
}
