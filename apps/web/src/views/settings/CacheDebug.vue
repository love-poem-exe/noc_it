<template>
  <div class="cache-debug">
    <h2>Cache Diagnostics</h2>
    
    <div class="controls">
      <button @click="refreshStats">Odśwież statystyki</button>
      <button @click="clearCache" class="danger">Wyczyść cache</button>
    </div>
    
    <div class="stats">
      <h3>Statystyki cache:</h3>
      <pre>{{ JSON.stringify(stats, null, 2) }}</pre>
    </div>
    
    <div class="data-status">
      <h3>Stan danych:</h3>
      <div class="status-item">
        <strong>Urządzenia:</strong> 
        {{ devices.length }} elementów 
        <span v-if="devicesLoading">(ładowanie...)</span>
        <button @click="forceRefresh('devices')">Odśwież</button>
      </div>
      <div class="status-item">
        <strong>Konta:</strong> 
        {{ accounts.length }} elementów 
        <span v-if="accountsLoading">(ładowanie...)</span>
        <button @click="forceRefresh('accounts')">Odśwież</button>
      </div>
      <div class="status-item">
        <strong>Status tunelu:</strong> 
        {{ tunnelStatus.status }} 
        <span v-if="tunnelLoading">(ładowanie...)</span>
        <button @click="forceRefresh('tunnel')">Odśwież</button>
      </div>
    </div>
    
    <div class="actions">
      <h3>Akcje testowe:</h3>
      <button @click="testLoadDevices">Test: Załaduj urządzenia</button>
      <button @click="testLoadAccounts">Test: Załaduj konta</button>
      <button @click="testLoadTunnel">Test: Załaduj status tunelu</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import useData from '../../composables/useData'

const {
  devices,
  accounts,
  tunnelStatus,
  devicesLoading,
  accountsLoading,
  tunnelLoading,
  loadDevices,
  loadAccounts,
  loadTunnelStatus,
  forceRefresh,
  getCacheStats,
  clearCache: clearDataCache
} = useData()

const stats = ref<Record<string, unknown>>({})

const refreshStats = () => {
  stats.value = getCacheStats()
}

const clearCache = () => {
  clearDataCache()
  refreshStats()
  alert('Cache został wyczyszczony')
}

const testLoadDevices = async () => {
  console.log('[Debug] Testing loadDevices...')
  const start = Date.now()
  await loadDevices()
  const time = Date.now() - start
  console.log(`[Debug] loadDevices took ${time}ms`)
  refreshStats()
}

const testLoadAccounts = async () => {
  console.log('[Debug] Testing loadAccounts...')
  const start = Date.now()
  await loadAccounts()
  const time = Date.now() - start
  console.log(`[Debug] loadAccounts took ${time}ms`)
  refreshStats()
}

const testLoadTunnel = async () => {
  console.log('[Debug] Testing loadTunnelStatus...')
  const start = Date.now()
  await loadTunnelStatus()
  const time = Date.now() - start
  console.log(`[Debug] loadTunnelStatus took ${time}ms`)
  refreshStats()
}

onMounted(() => {
  refreshStats()
})
</script>

<style scoped>
.cache-debug {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.controls {
  margin-bottom: 20px;
}

.controls button {
  margin-right: 10px;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  background-color: #1976d2;
  color: white;
  cursor: pointer;
}

.controls button.danger {
  background-color: #d32f2f;
}

.controls button:hover {
  opacity: 0.8;
}

.stats {
  background-color: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.stats pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
}

.data-status {
  margin-bottom: 20px;
}

.status-item {
  margin-bottom: 10px;
  padding: 10px;
  background-color: #fafafa;
  border-radius: 4px;
}

.status-item button {
  margin-left: 10px;
  padding: 4px 8px;
  font-size: 12px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.actions button {
  margin-right: 10px;
  margin-bottom: 10px;
  padding: 8px 16px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.actions button:hover {
  opacity: 0.8;
}
</style>