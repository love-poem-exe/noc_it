import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    globals: true,
    include: ['tests/**/*.{test,spec}.{js,ts}'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{js,ts,vue}'],
      exclude: ['src/data/**', 'src/scripts/**'],
    },
  },
  resolve: {
    alias: {
      '@services': '/src/services',
      '@utils': '/src/utils',
      '@types': '/src/types',
    },
  },
})
