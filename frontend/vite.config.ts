import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Evita CORS en desarrollo: el front habla con /api y Vite lo reenvía.
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
