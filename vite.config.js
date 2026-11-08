import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: '0.0.0.0', // 允许局域网与本机同时访问
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    allowedHosts: ['3qawb6uhbkhrhvatx2a3uvb5em.srv.us'],
    proxy: {
      '/api': 'http://127.0.0.1:43100',
    },
  },
})
