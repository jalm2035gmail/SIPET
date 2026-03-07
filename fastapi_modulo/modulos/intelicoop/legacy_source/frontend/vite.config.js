import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const djangoApiUrl = env.VITE_DJANGO_API_URL || 'http://localhost:8010/api'
  const djangoOrigin = djangoApiUrl.replace(/\/api\/?$/, '')

  return {
    plugins: [react()],
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setupTests.js'
    },
    server: {
      host: '0.0.0.0',
      port: Number(env.VITE_PORT || 3010),
      proxy: {
        '/api': {
          target: djangoOrigin,
          changeOrigin: true
        }
      }
    }
  }
})
