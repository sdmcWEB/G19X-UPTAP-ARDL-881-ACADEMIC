import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { token } from "../lib/api";

const ENLACES = [
  { a: "/tablero", texto: "Tablero" },
  { a: "/contratos", texto: "Contratos" },
  { a: "/busqueda", texto: "Búsqueda" },
];

export function Layout() {
  const navegar = useNavigate();

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-[1400px] items-center gap-6 px-6 py-3">
          <span className="font-semibold">Riesgos Contractuales</span>

          <nav className="flex gap-1">
            {ENLACES.map((e) => (
              <NavLink
                key={e.a}
                to={e.a}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm transition ${
                    isActive
                      ? "bg-neutral-900 text-white"
                      : "text-neutral-600 hover:bg-neutral-100"
                  }`
                }
              >
                {e.texto}
              </NavLink>
            ))}
          </nav>

          <button
            onClick={() => {
              token.clear();
              navegar("/login");
            }}
            className="ml-auto text-sm text-neutral-500 hover:underline"
          >
            Salir
          </button>
        </div>
      </header>

      <main>
        <Outlet />
      </main>
    </div>
  );
}
