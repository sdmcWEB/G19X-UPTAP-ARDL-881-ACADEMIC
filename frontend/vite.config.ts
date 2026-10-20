import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dónde vive la API vista desde el proceso de Vite, no desde el navegador.
// En el host es localhost; dentro de Docker Compose el contenedor `web` tiene
// su propio localhost, así que ahí hay que apuntar al servicio `api`.
const destinoApi = process.env.VITE_API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Escucha en todas las interfaces para que otro dispositivo de la red
    // pueda abrirlo por la IP de esta máquina.
    host: true,
    proxy: {
      // El navegador solo habla con Vite y Vite reenvía: así no hay CORS de
      // por medio, ni siquiera cuando se entra desde otro equipo.
      "/api": { target: destinoApi, changeOrigin: true },
    },
  },
});
