import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        ws: true,
      },
      "/vnc-ws": {
        target: "ws://127.0.0.1:6080",
        ws: true,
        rewrite: (p) => p.replace(/^\/vnc-ws/, ""),
      },
    },
  },
})
