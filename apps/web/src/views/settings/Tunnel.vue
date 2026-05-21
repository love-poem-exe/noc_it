<template>
  <div class="tunnel-container">
    <div class="left-panel">
      <h2>Ustawienia tunelu</h2>
      <input v-model="tunnel.address" placeholder="Adres IP / host" />
      <input v-model="tunnel.login" placeholder="Login" />
      <div class="auth-toggle">
        <span :class="['auth-label', { active: tunnel.authMode === 'password' }]">Hasło</span>
        <button type="button" class="auth-switch" @click="toggleAuthMode">
          <span :class="['auth-thumb', { right: tunnel.authMode === 'key' }]" />
        </button>
        <span :class="['auth-label', { active: tunnel.authMode === 'key' }]">Klucz SSH</span>
      </div>
      <input
        v-if="tunnel.authMode === 'password'"
        v-model="tunnel.password"
        placeholder="Hasło"
        type="password"
      />
      <div v-else class="key-input">
        <input
          v-model="tunnel.keyPath"
          placeholder="Wybierz plik z kluczem SSH"
          readonly
        />
        <button type="button" class="key-button" @click="chooseKeyFile">
          Wybierz plik
        </button>
        <input
          ref="keyFileInput"
          type="file"
          class="hidden-file-input"
          @change="onKeyFileChange"
        />
        
      </div>
      <div class="status-text">{{ getStatusText() }}</div>
      <button :disabled="isProcessing || isLoading" @click="handleClick">
        {{ getButtonText() }}
      </button>

      <div class="autoconnect-row">
        <span class="autoconnect-label">Automatyczne łączenie przy starcie</span>
        <button
          type="button"
          class="toggle-switch"
          :class="{ 'toggle-on': autoConnectOnStartup }"
          @click="toggleAutoConnect"
          :title="autoConnectOnStartup ? 'Wyłącz automatyczne łączenie' : 'Włącz automatyczne łączenie'"
        >
          <span class="toggle-thumb" />
        </button>
        <span class="toggle-state-label" :class="{ 'state-on': autoConnectOnStartup }">
          {{ autoConnectOnStartup ? 'ON' : 'OFF' }}
        </span>
      </div>

    </div>
    <div class="right-panel">
      <div v-if="diagnosisResult" class="diagnosis-result">
        <h3>Wynik diagnozy:</h3>
        <pre>{{ diagnosisResult }}</pre>
      </div>
      <div class="tunnel-console" v-if="true">
        <h3>Konsola tunelu</h3>
        <div class="console-output" ref="consoleOutput">
          <pre>{{ tunnelConsole }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'

import useData from '../../composables/useData'
import { requestJson, requestText } from '../../services/ApiClient'
import { dataService } from '../../services/DataService'

const route = useRoute()

// Użyj cache dla statusu tunelu
const {
  tunnelStatus,
  toggleTunnel: toggleTunnelFromCache,
  saveTunnel: saveTunnelToCache,
  forceRefresh,
  loadTunnelStatus
} = useData()

const tunnel = ref({
  address: '',
  login: '',
    password: '',
    authMode: 'password',
    keyPath: ''
})

// Używamy prostego ref zsynchronizowanego z tunnelStatus
const status = ref(tunnelStatus.value?.status || 'NOT CONNECTED')
const interval = ref(null)
const isProcessing = ref(false)
const isLoading = ref(false) // zmienione na false - nie ładujemy domyślnie
const diagnosisResult = ref(null)
const keyFileInput = ref(null)
const selectedKeyFile = ref(null)
const tunnelConsole = ref('')
const logsInterval = ref(null)
const consoleOutput = ref(null)

const TUNNEL_SETTINGS_KEY = 'noc-it:tunnel-settings'
const autoConnectOnStartup = ref(false)

const loadTunnelSettings = () => {
  try {
    const raw = localStorage.getItem(TUNNEL_SETTINGS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      autoConnectOnStartup.value = !!parsed.autoConnectOnStartup
    }
  } catch (e) {
    console.warn('[Tunnel] Błąd odczytu ustawień tunelu:', e)
  }
}

const saveTunnelSettings = () => {
  try {
    const existing = JSON.parse(localStorage.getItem(TUNNEL_SETTINGS_KEY) || '{}')
    localStorage.setItem(TUNNEL_SETTINGS_KEY, JSON.stringify({
      ...existing,
      autoConnectOnStartup: autoConnectOnStartup.value
    }))
  } catch (e) {
    console.warn('[Tunnel] Błąd zapisu ustawień tunelu:', e)
  }
}

const toggleAutoConnect = () => {
  autoConnectOnStartup.value = !autoConnectOnStartup.value
  saveTunnelSettings()
}


const loadTunnel = async () => {
  try {
    const parsed = await requestJson('/api/tunnel', { timeoutMs: 10000 })
    tunnel.value.address = parsed.address || ''
    tunnel.value.login = parsed.login || ''
    tunnel.value.authMode = parsed.authMode || 'password'
    tunnel.value.keyPath = parsed.keyPath || ''
    tunnel.value.password = parsed.password || ''
    // key content is not loaded in the UI; keyPath is stored on backend
  } catch (err) {
    console.error("Błąd podczas ładowania tunelu:", err)
  }
}

watch(
  () => route.fullPath,
  async (newPath) => {
    if (newPath.includes('/tunneling') || newPath.includes('/settings/tunnel')) {
      await loadTunnel()
      // Użyj cache dla szybkiego ładowania przy przejściu
      await loadStatusFromCache()
      // Przejście do widoku tunelu
    }
  },
  { immediate: true }
)


const loadStatusFromCache = async () => {
  try {
    console.log("🚀 Próba ładowania z cache...")
    // Najpierw spróbuj z cache (szybko)
    const cachedResult = await loadTunnelStatus()
    if (cachedResult && cachedResult.status) {
      // Update tunnelStatus w composable i lokalny status
      tunnelStatus.value = cachedResult
      status.value = cachedResult.status
      console.log(`💾 Status z cache: ${cachedResult.status}`)
      return cachedResult
    }
  } catch {
    console.warn("Cache miss, ładowanie z serwera...")
  }
  
  // Jeśli nie ma w cache, ustaw ładowanie i pobierz z serwera
  isLoading.value = true
  return await loadStatus()
}

const loadStatus = async () => {
  try {
    // Wymuś pobranie najnowszego statusu tunelu (omija cache)
    const result = await forceRefresh('tunnel')
    tunnelStatus.value = {
      status: result.status || 'NOT CONNECTED',
      port: result.port,
      address: result.address,
      login: result.login
    }
    status.value = result.status || 'NOT CONNECTED'

    return result
  } catch (error) {
    console.warn("Nie można odczytać statusu tunelu:", error)
    tunnelStatus.value = { status: 'NOT CONNECTED' }
    status.value = 'NOT CONNECTED'
  } finally {
    isLoading.value = false // status został załadowany
  }
}


const handleClick = async () => {
  console.log("🟢 Kliknięto przycisk Połącz")
  if (isProcessing.value) return
  isProcessing.value = true
  isLoading.value = true

  try {
    if (selectedKeyFile.value) {
      await dataService.uploadTunnelKey(selectedKeyFile.value)
    }
    await saveTunnelToCache(tunnel.value)
    console.log("✅ save_tunnel wywołane")

    const result = await toggleTunnelFromCache()
    console.log("✅ toggle_tunnel wywołane, nowy status:", result.status)
    
    // Aktualizuj status natychmiast z wynikiem
    status.value = result.status || 'NOT CONNECTED'
    
  } catch (error) {
    console.error("❌ Błąd przy obsłudze tunelu:", error)
    diagnosisResult.value = `❌ Błąd tunelowania: ${String(error?.message || error)}`
  } finally {
    isProcessing.value = false
    isLoading.value = false
  }
}

// Helper functions for status display
const getStatusText = () => {
  if (isLoading.value) return 'ŁADOWANIE...'
  return status.value === 'CONNECTED' ? 'CONNECTED' : 'ROZŁĄCZONO'
}

const getButtonText = () => {
  if (isLoading.value) return 'Ładowanie...'
  return status.value === 'CONNECTED' ? 'Rozłącz' : 'Połącz'
}

const loadTunnelLogs = async () => {
  try {
    const res = await requestJson('/api/tunnel/logs', { timeoutMs: 5000 })
    tunnelConsole.value = res?.logs || ''
    await nextTick()
    try {
      const el = consoleOutput.value
      if (el && el.scrollHeight !== undefined) {
        el.scrollTop = el.scrollHeight
      }
    } catch (_e) {
      // ignore scroll errors
    }
  } catch (e) {
    tunnelConsole.value = `Error fetching logs: ${String(e)}`
    await nextTick()
    try {
      const el = consoleOutput.value
      if (el && el.scrollHeight !== undefined) el.scrollTop = el.scrollHeight
    } catch (_e) {}
  }
}

const closeTunnel = async () => {
  if (isProcessing.value) return
  isProcessing.value = true
  diagnosisResult.value = null

  try {
    const result = await requestText('/api/tunnel/close', {
      method: 'POST',
      timeoutMs: 30000
    })
    diagnosisResult.value = result
    console.log('✅ ' + result)
    
    // Odśwież status tunelu
    await loadStatusFromCache()
  } catch (error) {
    console.error('❌ Błąd przy zamykaniu tunelu:', error.message)
    diagnosisResult.value = `❌ Błąd zamykania tunelu: ${error.message}`
  } finally {
    isProcessing.value = false
  }
}

const toggleAuthMode = () => {
  if (tunnel.value.authMode === 'password') {
    tunnel.value.authMode = 'key'
    tunnel.value.password = ''
  } else {
    tunnel.value.authMode = 'password'
    tunnel.value.keyPath = ''
  }
}

const chooseKeyFile = async () => {
  if (keyFileInput.value) keyFileInput.value.click()
}

const onKeyFileChange = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  tunnel.value.keyPath = file.name
  selectedKeyFile.value = file
}

onMounted(async () => {
  loadTunnelSettings()
  await loadTunnel()
  await loadStatusFromCache() // Użyj cache na początku
  interval.value = setInterval(loadStatus, 5000) // Dla kolejnych odświeżeń używaj force refresh
  // Start polling tunnel logs every second
  await loadTunnelLogs()
  logsInterval.value = setInterval(loadTunnelLogs, 1000)
})

onUnmounted(() => {
  if (interval.value) clearInterval(interval.value)
  if (logsInterval.value) clearInterval(logsInterval.value)
  // Globalny monitoring NIE jest zatrzymywany - kontynuuje się w tle!
})
</script>

<style scoped>
.tunnel-container {
  display: flex; width: 100%; gap: 1.25rem;
  padding: 1rem; box-sizing: border-box;
  background: #0d1117; color: #e6edf3; height: 100%;
}

.left-panel {
  flex: 0 0 32%; min-width: 260px;
  display: flex; flex-direction: column; gap: 10px;
  background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; padding: 1rem;
}

.right-panel {
  flex: 1 1 auto; min-width: 360px;
  background: #161b22; border: 1px solid #30363d;
  padding: 1rem; border-radius: 8px;
  overflow: auto; display: flex; flex-direction: column; gap: 10px;
}

input {
  width: 100%; padding: 7px 10px;
  background: #0d1117; border: 1px solid #30363d;
  border-radius: 6px; color: #e6edf3; font-size: 13px;
  font-family: inherit; outline: none;
  transition: border-color 0.15s; box-sizing: border-box;
}
input::placeholder { color: #484f58; }
input:focus { border-color: #388bfd; }

button {
  padding: 8px 12px; background: #1f6feb;
  color: #fff; border: 1px solid #1f6feb;
  border-radius: 6px; font-size: 13px; font-weight: 500;
  font-family: inherit; cursor: pointer; width: 100%;
  transition: background 0.15s;
}
button:hover { background: #388bfd; border-color: #388bfd; }
button:disabled { background: #21262d; border-color: #30363d; color: #484f58; cursor: not-allowed; }

.auth-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
}

.auth-label {
  font-size: 12.5px; color: #8b949e;
}
.auth-label.active { color: #e6edf3; font-weight: 600; }

.auth-switch {
  width: 44px; height: 24px; padding: 0;
  background: #21262d; border: 1px solid #30363d;
  border-radius: 999px; display: inline-flex;
  align-items: center; justify-content: flex-start;
}

.auth-thumb {
  width: 20px;
  height: 20px;
  background-color: #fff;
  border-radius: 50%;
  margin-left: 3px;
  transition: transform 0.2s ease;
}

.auth-thumb.right {
  transform: translateX(22px);
}

.key-input {
  display: flex;
  gap: 8px;
}

.key-input input {
  flex: 1 1 auto;
}

.key-button {
  width: auto;
  padding: 10px 12px;
  white-space: nowrap;
}

.hidden-file-input {
  display: none;
}

.status-label {
  padding: 8px 12px; text-align: center;
  font-weight: 600; font-size: 13px; border-radius: 6px;
}
.connected    { background: rgba(63,185,80,0.15); color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
.disconnected { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
.loading      { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }

.diagnosis-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  margin-bottom: 1rem;
  align-self: stretch;
  width: 100%;
}

.diagnosis-buttons button {
  width: 100%;
}

.diagnosis-result {
  background: #0d1117; border: 1px solid #30363d;
  padding: 1rem; border-radius: 6px; margin-top: 0.5rem; align-self: stretch;
}
.diagnosis-result pre {
  white-space: pre-wrap; word-wrap: break-word;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px; color: #c9d1d9;
  background: #161b22; padding: 0.75rem;
  border-radius: 5px; border: 1px solid #30363d;
}

.tunnel-console {
  margin-top: 0.5rem;
}

.console-output {
  height: 420px;
  overflow: auto;
  background: #0b1220;
  border: 1px solid #30363d;
  padding: 10px;
  border-radius: 6px;
  color: #c9d1d9;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px;
}

.console-output pre { margin: 0; white-space: pre-wrap; }

.monitoring-active {
  background: rgba(63,185,80,0.2) !important;
  border-color: rgba(63,185,80,0.4) !important;
  color: #3fb950 !important;
  animation: pulse 1.5s infinite;
}
.tunnel-close-button { background: #da3633 !important; border-color: #da3633 !important; }
.tunnel-close-button:hover:not(:disabled) { background: #f85149 !important; border-color: #f85149 !important; }

.autoconnect-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
}

.autoconnect-label {
  flex: 1 1 auto;
  font-size: 12.5px;
  color: #8b949e;
}

.toggle-switch {
  width: 44px;
  height: 24px;
  padding: 0;
  border-radius: 999px;
  background: #21262d;
  border: 1px solid #30363d;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  flex-shrink: 0;
  width: 100%;
  max-width: 44px;
}

.toggle-switch.toggle-on {
  background: rgba(63,185,80,0.3);
  border-color: rgba(63,185,80,0.5);
}

.toggle-thumb {
  width: 20px;
  height: 20px;
  background: #8b949e;
  border-radius: 50%;
  margin-left: 3px;
  transition: transform 0.2s ease, background 0.2s;
}

.toggle-switch.toggle-on .toggle-thumb {
  transform: translateX(22px);
  background: #3fb950;
}

.toggle-state-label {
  font-size: 12px;
  font-weight: 600;
  color: #484f58;
  min-width: 24px;
}

.toggle-state-label.state-on {
  color: #3fb950;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}
</style>
