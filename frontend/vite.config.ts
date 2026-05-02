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
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/react") || id.includes("node_modules/react-dom") || id.includes("node_modules/react-router")) return "vendor-react"
          if (id.includes("node_modules/lucide-react") || id.includes("node_modules/clsx") || id.includes("node_modules/tailwind-merge")) return "vendor-ui"
          if (id.includes("node_modules/d3") || id.includes("node_modules/d3-")) return "vendor-charts"
          if (id.includes("node_modules/@xyflow")) return "vendor-flow"
          if (id.includes("node_modules/i18next") || id.includes("node_modules/react-i18next")) return "vendor-i18n"
        },
      },
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
