import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const DEFAULT_BACKEND_URL = 'http://localhost:8003'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5273,
    strictPort: true,
    proxy: {
      '/api': {
        target: DEFAULT_BACKEND_URL,
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 5273,
    strictPort: true
  }
})
