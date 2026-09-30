import { Navigate, Route, Routes } from "react-router-dom";

import { token } from "./lib/api";
import { Contratos } from "./pages/Contratos";
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
        path="/contratos"
        element={
          <Privada>
            <Contratos />
          </Privada>
        }
      />
      <Route
        path="/contratos/:id"
        element={
          <Privada>
            <Detalle />
          </Privada>
        }
      />
      <Route path="*" element={<Navigate to="/contratos" replace />} />
    </Routes>
  );
}
