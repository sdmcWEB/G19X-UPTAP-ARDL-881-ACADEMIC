import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";

export function Login() {
  const navegar = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await api.login(email, password);
      navegar("/tablero");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 p-4">
      <form
        onSubmit={enviar}
        className="w-full max-w-sm rounded-xl border bg-white p-6 shadow-sm"
      >
        <h1 className="text-lg font-semibold">Riesgos Contractuales</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Develop Talent &amp; Technology
        </p>

        <label className="mt-6 block text-sm font-medium">Correo</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full rounded-lg border px-3 py-2"
          autoComplete="username"
        />

        <label className="mt-4 block text-sm font-medium">Contraseña</label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded-lg border px-3 py-2"
          autoComplete="current-password"
        />

        {error && <p className="mt-3 text-sm text-red-700">{error}</p>}

        <button
          type="submit"
          disabled={enviando}
          className="mt-6 w-full rounded-lg bg-neutral-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {enviando ? "Entrando…" : "Iniciar sesión"}
        </button>
      </form>
    </div>
  );
}
