import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// Dev: the FastAPI backend runs on :8000 (same-origin in prod). Proxy the JSON API
// paths so the SPA can call them relatively (e.g. fetch('view')) with no CORS.
// Prefixes with a trailing slash for path-param routes so '/node/…' doesn't swallow
// Vite's own '/node_modules'.
const API_TARGET = process.env.VITE_API_TARGET || 'http://localhost:8000'
const proxied = ['/health', '/view', '/ask', '/ingest', '/openapi.json', '/docs', '/node/', '/evidence/', '/hitl/', '/config/']
const proxy = Object.fromEntries(
  proxied.map((p) => [p, { target: API_TARGET, changeOrigin: true }]),
)

export default defineConfig({
  plugins: [react()],
  // Relative asset URLs so the bundle resolves under any mount path (StaticFiles, tunnel, subpath).
  base: './',
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: { port: 5173, proxy },
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false },
})
