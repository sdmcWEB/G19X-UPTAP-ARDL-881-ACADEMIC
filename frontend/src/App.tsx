import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { token } from "./lib/api";
import { Contratos } from "./pages/Contratos";
import { Dashboard } from "./pages/Dashboard";
import { Detalle } from "./pages/Detalle";
import { Login } from "./pages/Login";

function Privada({ children }: { children: React.ReactNode }) {
  return token.get() ? children : <Navigate to="/login" replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <Privada>
            <Layout />
          </Privada>
        }
      >
        <Route path="/tablero" element={<Dashboard />} />
        <Route path="/contratos" element={<Contratos />} />
        <Route path="/contratos/:id" element={<Detalle />} />
      </Route>

      <Route path="*" element={<Navigate to="/tablero" replace />} />
    </Routes>
  );
}
