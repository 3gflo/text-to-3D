import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Matches any request starting with /api
      '/api': {
        target: 'http://127.0.0.1:5055', // Your Flask URL
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
