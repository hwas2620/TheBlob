import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // 상대 경로: GitHub Pages 하위 경로(/저장소명/)에서도 자산이 로드됨
  base: './',
  plugins: [react(), tailwindcss()],
})
