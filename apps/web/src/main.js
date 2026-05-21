import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './views/App.vue'
import router from './router'
import { requestJson } from './services/ApiClient'
import 'maplibre-gl/dist/maplibre-gl.css'

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

const app = createApp(App)
app.use(pinia)
app.use(router)
app.mount('#app')

// Initialize at startup
async function initTunnelStatus() {
  try {
    const statusResult = await requestJson('/api/tunnel/status', { timeoutMs: 10000 })
    await maybeAutoConnect(statusResult)
  } catch (error) {
    console.error('[APP INIT] Error initializing tunnel status:', error)
  }
}

async function maybeAutoConnect(statusResult) {
  try {
    const raw = localStorage.getItem('noc-it:tunnel-settings')
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (!parsed.autoConnectOnStartup) return

    const currentStatus = (statusResult?.status || 'NOT CONNECTED').toUpperCase()
    if (currentStatus === 'CONNECTED') {
      console.log('[APP INIT] Auto-connect: tunel już połączony, pomijam.')
      return
    }

    console.log('[APP INIT] Auto-connect: łączenie tunelu...')
    await requestJson('/api/tunnel/toggle', { method: 'POST', timeoutMs: 30000 })
    console.log('[APP INIT] Auto-connect: zakończono.')
  } catch (err) {
    console.warn('[APP INIT] Auto-connect failed:', err)
  }
}

async function cleanupTempFiles() {
  try {
    await requestJson('/api/system/cleanup', { method: 'POST', timeoutMs: 10000 })
  } catch (error) {
    console.error('[APP INIT] Error cleaning temp folder:', error)
  }
}

// Run startup tasks
initTunnelStatus()
cleanupTempFiles()
