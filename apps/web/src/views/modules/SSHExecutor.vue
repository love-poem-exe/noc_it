<template>
  <div class="ssh-executor">
    <div class="executor-header">
      <h2>SSH Command Executor (Tokio Async)</h2>
      <div class="status-badge" :class="connectionStatus.toLowerCase()">
        {{ connectionStatus }}
      </div>
    </div>

    <!-- Wybór urządzenia -->
    <div class="device-selector">
      <label>Urządzenie:</label>
      <select v-model="selectedDevice" @change="updateDeviceInfo">
        <option value="">-- Wybierz urządzenie --</option>
        <option v-for="dev in devices" :key="dev.id" :value="dev">
          {{ dev.hostname }} ({{ dev.address }})
        </option>
      </select>
    </div>

    <!-- Info o urządzeniu -->
    <div v-if="selectedDevice" class="device-info">
      <p><strong>Adres:</strong> {{ selectedDevice.address }}</p>
      <p><strong>Konto:</strong> {{ selectedDevice.account }}</p>
      <p><strong>Status:</strong> {{ selectedDevice.status }}</p>
      <p><strong>Vendor:</strong> {{ selectedDevice.vendor || 'Nieznany' }}</p>
    </div>

    <!-- Input komend -->
    <div class="command-input">
      <label>Komenda SSH:</label>
      <textarea 
        v-model="commandText" 
        placeholder="Wpisz komendę do wykonania (np: show running-config)"
        :disabled="isExecuting"
        rows="4"
      ></textarea>
      
      <div class="timeout-selector">
        <label>Timeout (s):</label>
        <input v-model.number="timeoutSeconds" type="number" min="10" max="600" :disabled="isExecuting">
      </div>

      <button 
        @click="executeCommand" 
        :disabled="!selectedDevice || !commandText || isExecuting"
        class="btn-execute"
      >
        {{ isExecuting ? '⏳ Wykonywanie...' : '▶ Wykonaj' }}
      </button>
    </div>

    <!-- Progress Bar -->
    <div v-if="isExecuting" class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
      <p class="progress-text">{{ Math.floor(progressPercent) }}% | Elapsed: {{ elapsedTime }}s</p>
    </div>

    <!-- Output Terminal -->
    <div class="output-container">
      <div class="output-header">
        <h3>Output</h3>
        <button @click="clearOutput" class="btn-clear">Clear</button>
      </div>
      <div class="terminal" ref="terminalDiv">
        <div v-if="outputLines.length === 0" class="empty-state">
          Wynik pojawi się tutaj...
        </div>
        <div v-for="(line, idx) in outputLines" :key="idx" class="output-line">
          {{ line }}
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats">
      <div class="stat-item">
        <span class="stat-label">Commands Executed:</span>
        <span class="stat-value">{{ executedCount }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Avg Response Time:</span>
        <span class="stat-value">{{ avgResponseTime }}ms</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Last Execution:</span>
        <span class="stat-value">{{ lastExecutionTime }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { dataService, invokeAsyncScript } from '../../services/DataService'

const CACHE_KEY = 'ssh_executor_state'

// State
const devices = ref([])
const selectedDevice = ref(null)
const commandText = ref('')
const isExecuting = ref(false)
const outputLines = ref([])
const timeoutSeconds = ref(120)
const terminalDiv = ref(null)

// Stats
const executedCount = ref(0)
const responseTimes = ref([])
const lastExecutionTime = ref('-')
const elapsedTime = ref(0)

// Progress
const progressPercent = ref(0)
let progressInterval = null

// Zapis stanu do pamięci podręcznej
function saveState() {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({
      commandText: commandText.value,
      timeoutSeconds: timeoutSeconds.value,
      outputLines: outputLines.value,
      selectedDeviceId: selectedDevice.value?.id ?? null,
    }))
  } catch (e) { /* ignore */ }
}
watch([commandText, timeoutSeconds, outputLines, selectedDevice], saveState, { deep: true })

// Computed
const avgResponseTime = computed(() => {
  if (responseTimes.value.length === 0) return 0
  const sum = responseTimes.value.reduce((a, b) => a + b, 0)
  return Math.round(sum / responseTimes.value.length)
})

const connectionStatus = computed(() => {
  if (!selectedDevice.value) return 'DISCONNECTED'
  if (selectedDevice.value.status === 'ONLINE') return 'CONNECTED'
  return selectedDevice.value.status
})

// Load devices na start + przywróć dane z cache
onMounted(async () => {
  // Wczytaj cache
  let cached = null
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (raw) cached = JSON.parse(raw)
  } catch (e) {
    console.warn('SSH Executor: błąd wczytywania cache:', e)
  }
  if (cached) {
    if (cached.commandText)    commandText.value    = cached.commandText
    if (cached.timeoutSeconds) timeoutSeconds.value = cached.timeoutSeconds
    if (cached.outputLines)    outputLines.value    = cached.outputLines
  }

  try {
    const data = await dataService.getDevices()
    devices.value = data
    // Przywróć wybrane urządzenie po załadowaniu listy
    if (cached?.selectedDeviceId) {
      selectedDevice.value = data.find(d => d.id === cached.selectedDeviceId) ?? null
    }
  } catch (error) {
    console.error('Error loading devices:', error)
    outputLines.value.push(`❌ Error loading devices: ${error.message}`)
  }
})

// Execute SSH command
async function executeCommand() {
  if (!selectedDevice.value || !commandText.value) return

  isExecuting.value = true
  outputLines.value = []
  elapsedTime.value = 0
  progressPercent.value = 0

  // Simulate progress
  progressInterval = setInterval(() => {
    elapsedTime.value++
    if (elapsedTime.value <= timeoutSeconds.value) {
      progressPercent.value = (elapsedTime.value / timeoutSeconds.value) * 100
    }
  }, 1000)

  const startTime = Date.now()

  try {
    outputLines.value.push(`$ ${commandText.value}`)
    outputLines.value.push('---')

    // Execute via async
    const result = await invokeAsyncScript({
      script: 'settings-devices_controller',
      method: 'execute_command_on_device',
      payload: {
        device_id: selectedDevice.value.id,
        command: commandText.value,
        account_id: selectedDevice.value.account
      },
      timeoutMs: timeoutSeconds.value * 1000  // Convert to ms
    })

    // Parse result
    const parsed = typeof result === 'string' ? JSON.parse(result) : result
    
    if (parsed.error) {
      outputLines.value.push(`❌ Error: ${parsed.error}`)
    } else if (parsed.output) {
      const lines = parsed.output.split('\n')
      outputLines.value.push(...lines)
    }

    outputLines.value.push('---')
    outputLines.value.push('✅ Command executed successfully')

    // Update stats
    const responseTime = Date.now() - startTime
    responseTimes.value.push(responseTime)
    executedCount.value++
    lastExecutionTime.value = new Date().toLocaleTimeString()

  } catch (error) {
    outputLines.value.push('---')
    outputLines.value.push(`❌ Error: ${error.message}`)
    
    if (error.message.includes('TIMEOUT')) {
      outputLines.value.push('⚠️ Command timeout - increase timeout value if needed')
    }
  } finally {
    isExecuting.value = false
    clearInterval(progressInterval)
    progressPercent.value = 100
    await nextTick()
    if (terminalDiv.value) {
      terminalDiv.value.scrollTop = terminalDiv.value.scrollHeight
    }
  }
}

// Clear output
function clearOutput() {
  outputLines.value = []
  commandText.value = ''
}

// Update device info
function updateDeviceInfo() {
  outputLines.value = [
    `Connected to: ${selectedDevice.value.hostname}`,
    `Address: ${selectedDevice.value.address}`,
    `Status: ${selectedDevice.value.status}`,
    '---'
  ]
}
</script>

<style scoped>
.ssh-executor {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 2rem;
  background: #f5f5f5;
  height: 100%;
  overflow-y: auto;
}

.executor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #ddd;
  padding-bottom: 1rem;
}

.executor-header h2 {
  margin: 0;
  color: #333;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: bold;
  font-size: 0.9rem;
}

.status-badge.connected {
  background: #4caf50;
  color: white;
}

.status-badge.disconnected {
  background: #f44336;
  color: white;
}

.status-badge.online {
  background: #4caf50;
  color: white;
}

.status-badge.warning {
  background: #ff9800;
  color: white;
}

.device-selector {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.device-selector label {
  font-weight: bold;
  color: #333;
}

.device-selector select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.device-info {
  background: white;
  padding: 1rem;
  border-radius: 4px;
  border-left: 4px solid #2196f3;
}

.device-info p {
  margin: 0.5rem 0;
  color: #555;
}

.command-input {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: white;
  padding: 1rem;
  border-radius: 4px;
}

.command-input label {
  font-weight: bold;
  color: #333;
}

.command-input textarea {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.9rem;
  resize: vertical;
}

.command-input textarea:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.timeout-selector {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.timeout-selector input {
  width: 80px;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.btn-execute {
  padding: 0.75rem 1.5rem;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.3s;
}

.btn-execute:hover:not(:disabled) {
  background: #0b7dda;
}

.btn-execute:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.progress-container {
  background: white;
  padding: 1rem;
  border-radius: 4px;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background: #eee;
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2196f3, #4caf50);
  transition: width 0.3s;
}

.progress-text {
  margin: 0.75rem 0 0 0;
  font-size: 0.9rem;
  color: #666;
}

.output-container {
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 4px;
  overflow: hidden;
  flex: 1;
  min-height: 300px;
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #ddd;
}

.output-header h3 {
  margin: 0;
  color: #333;
}

.btn-clear {
  padding: 0.5rem 1rem;
  background: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-clear:hover {
  background: #da190b;
}

.terminal {
  flex: 1;
  padding: 1rem;
  background: #1e1e1e;
  overflow-y: auto;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
}

.output-line {
  color: #00ff00;
  white-space: pre-wrap;
  word-break: break-all;
}

.empty-state {
  color: #666;
  text-align: center;
  padding: 2rem;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  background: white;
  padding: 1rem;
  border-radius: 4px;
  text-align: center;
}

.stat-label {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #2196f3;
}
</style>
