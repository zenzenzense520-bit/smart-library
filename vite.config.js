import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
  },
  // 公网演示时由 Vite 预览服务把同源 API 请求转发给本机 Django。
  preview: {
    allowedHosts: ['3qawb6uhbkhrhvatx2a3uvb5em.srv.us'],
    proxy: {
      '/api': 'http://127.0.0.1:43100',
    },
  },
})
