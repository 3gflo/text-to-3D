import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['umpire-frequency-morbidity.ngrok-free.dev'],
    proxy: {
      // Matches any request starting with /api
      '/api': {
        target: 'http://127.0.0.1:5055',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
