import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // 상대 경로: GitHub Pages 하위 경로(/저장소명/)에서도 자산이 로드됨
  base: './',
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      // 게임(index.html)과 0단계 디버그 페이지(stage0.html)
      input: { main: 'index.html', stage0: 'stage0.html' },
    },
  },
})
