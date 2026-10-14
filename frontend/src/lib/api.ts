import type { Contrato, ContratoDetalle, Resultados, Resumen } from "./tipos";

const TOKEN_KEY = "riesgos.access_token";

export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(ruta: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const t = token.get();
  if (t) headers.set("Authorization", `Bearer ${t}`);

  const res = await fetch(`/api${ruta}`, { ...init, headers });

  if (res.status === 401) {
    token.clear();
    throw new ApiError(401, "Tu sesión expiró. Vuelve a iniciar sesión.");
  }
  if (!res.ok) {
    const cuerpo = await res.json().catch(() => ({}));
    throw new ApiError(res.status, cuerpo.detail ?? `Error ${res.status}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  async login(email: string, password: string) {
    // OAuth2PasswordRequestForm espera form-urlencoded, no JSON.
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch("/api/auth/login", { method: "POST", body });
    if (!res.ok) {
      const cuerpo = await res.json().catch(() => ({}));
      throw new ApiError(res.status, cuerpo.detail ?? "No se pudo iniciar sesión");
    }
    const datos = (await res.json()) as { access_token: string };
    token.set(datos.access_token);
    return datos;
  },

  yo: () => request<{ id: string; nombre: string; email: string; role: string }>("/auth/yo"),

  contratos: () => request<Contrato[]>("/contratos"),

  contrato: (id: string) => request<ContratoDetalle>(`/contratos/${id}`),

  buscar: (q: string, contratoId?: string) => {
    const params = new URLSearchParams({ q });
    if (contratoId) params.set("contrato_id", contratoId);
    return request<Resultados>(`/busqueda?${params}`);
  },

  // El backend lee `dias=0` como "todo el histórico".
  dashboard: (dias: number | null) => request<Resumen>(`/dashboard?dias=${dias ?? 0}`),

  async subir(archivo: File) {
    const body = new FormData();
    body.append("archivo", archivo);
    const headers = new Headers();
    const t = token.get();
    if (t) headers.set("Authorization", `Bearer ${t}`);

    const res = await fetch("/api/contratos", { method: "POST", body, headers });
    if (!res.ok) {
      const cuerpo = await res.json().catch(() => ({}));
      throw new ApiError(res.status, cuerpo.detail ?? "No se pudo subir el archivo");
    }
    return (await res.json()) as Contrato;
  },

  reanalizar: (id: string) =>
    request<Contrato>(`/contratos/${id}/reanalizar`, { method: "POST" }),

  urlArchivo: (id: string) => `/api/contratos/${id}/archivo`,
};
