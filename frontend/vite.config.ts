/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    allowedHosts: ['frontend.snaptrip.orb.local'],
    proxy: {
      '/api': {
        target: 'http://marketplace:8000',
        changeOrigin: true,
      },
    },
  },
  // @ts-expect-error vitest config augmentation
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})