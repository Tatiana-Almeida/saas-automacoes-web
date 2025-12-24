import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Single, clean config. In dev, proxy /api to Django on 8080 (docker-compose mapping).
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        // Prefer Vite env `VITE_API_URL` if provided, otherwise default to localhost:8000
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
