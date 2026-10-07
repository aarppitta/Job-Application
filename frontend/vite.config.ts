import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The frontend runs on port 5001 and forwards /api calls to the backend (port 8001 unless BACKEND_URL is set).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5001, strictPort: true, proxy: { "/api": process.env.BACKEND_URL ?? "http://localhost:8001" } },
});
