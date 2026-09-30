export type Severidad = "critica" | "alta" | "media" | "baja" | "informativa";
export type Verificacion = "verificada" | "aproximada" | "no_verificada";
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

export const ETIQUETA_VERIFICACION: Record<Verificacion, string> = {
  verificada: "Cita verificada",
  aproximada: "Cita aproximada",
  no_verificada: "Cita no verificada",
};
