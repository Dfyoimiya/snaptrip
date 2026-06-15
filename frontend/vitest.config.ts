import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  test: {
    // Use happy-dom for lightweight DOM environment
    environment: 'happy-dom',
    // Glob imports for test files
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    // Setup file for global mocks
    setupFiles: ['src/test/setup.ts'],
    // Coverage config (optional, activate with --coverage flag)
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,vue}'],
      exclude: [
        'src/test/**',
        'src/**/*.{test,spec}.{ts,tsx}',
        'src/types/**',
      ],
    },
  },
})
