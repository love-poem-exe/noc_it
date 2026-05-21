import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: true
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/xlsx')) {
            return 'xlsx';
          }
          if (
            id.includes('node_modules/leaflet') ||
            id.includes('node_modules/maplibre-gl')
          ) {
            return 'maps';
          }
          if (
            id.includes('node_modules/vue') ||
            id.includes('node_modules/pinia') ||
            id.includes('node_modules/vue-router')
          ) {
            return 'vendor';
          }
        }
      }
    }
  }
});
