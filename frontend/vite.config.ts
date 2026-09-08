import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Development-only proxy: lets the browser call the FastAPI backend on
      // http://localhost:8000 via same-origin "/api" paths, so the locked
      // backend requires NO CORS middleware changes.
      //
      //   Browser -> http://localhost:5173/api/... -> http://localhost:8000/api/...
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
