import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../quobuz_data/webui_build',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:3420',
    },
  },
})
