import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // The browser only ever talks to one origin, so session cookies and CSRF
    // work without CORS. In production Django serves the built app itself.
    // changeOrigin must stay false (the string shorthand turns it on): Django's
    // CSRF check compares the Origin header with the Host header it receives.
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: false },
      "/admin": { target: "http://localhost:8000", changeOrigin: false },
      "/static": { target: "http://localhost:8000", changeOrigin: false },
    },
  },
});
