<template>
  <div class="general-settings">
    <h2>General Settings</h2>
    
    <div v-if="saveMessage" class="save-message" :class="saveMessageType">{{ saveMessage }}</div>

    <!-- ── Interface ──────────────────────────────────────────── -->
    <div class="settings-section" style="margin-bottom:16px">
      <h3>Interface</h3>

      <div class="setting-group">
        <label class="setting-label">UI Font Size</label>
        <div class="font-size-row">
          <input
            type="range"
            min="11" max="50" step="1"
            v-model.number="uiFontSize"
            @input="applyFontSize"
            class="font-slider"
          />
          <span class="font-size-badge">{{ uiFontSize }} px</span>
          <div class="font-presets">
            <button
              v-for="p in fontPresets" :key="p.px"
              class="preset-btn"
              :class="{ active: uiFontSize === p.px }"
              @click="setPreset(p.px)"
            >{{ p.label }}</button>
          </div>
        </div>
        <span class="setting-description">Applies immediately across the whole interface. Default: 13 px</span>
      </div>
    </div>

    <div class="settings-section">
      <h3>Terminal Settings</h3>
      
      <div class="setting-group">
        <label class="setting-label">Connection Timeout (seconds)</label>
        <input 
          type="number" 
          min="5" 
          max="120" 
          v-model.number="settings.connectionTimeout"
          class="setting-input"
        />
        <span class="setting-description">Maximum time to wait for SSH connection (default: 30s)</span>
      </div>

      <div class="setting-group">
        <label class="setting-label">Read Timeout (seconds)</label>
        <input 
          type="number" 
          min="10" 
          max="300" 
          v-model.number="settings.readTimeout"
          class="setting-input"
        />
        <span class="setting-description">Maximum time to wait for server response (default: 60s)</span>
      </div>

      <div class="setting-group">
        <label class="setting-label">Keepalive Interval (seconds)</label>
        <input 
          type="number" 
          min="5" 
          max="60" 
          v-model.number="settings.keepaliveInterval"
          class="setting-input"
        />
        <span class="setting-description">Interval for sending keepalive packets (default: 15s)</span>
      </div>

      <div class="setting-group">
        <label class="setting-label">Keepalive Max Retries</label>
        <input 
          type="number" 
          min="1" 
          max="10" 
          v-model.number="settings.keepaliveRetries"
          class="setting-input"
        />
        <span class="setting-description">Number of failed keepalive attempts before disconnect (default: 3)</span>
      </div>

      <div class="setting-group">
        <label class="setting-label">Window Size (KB)</label>
        <input 
          type="number" 
          min="32" 
          max="2048" 
          step="32" 
          v-model.number="settings.windowSize"
          class="setting-input"
        />
        <span class="setting-description">SSH flow control window size in KB (default: 256KB)</span>
      </div>

      <div class="setting-group checkbox-group">
        <label class="checkbox-label">
          <input 
            type="checkbox" 
            v-model="settings.enableCompression"
            class="setting-checkbox"
          />
          <span>Enable Compression</span>
        </label>
        <span class="setting-description">Compress SSH data (useful for slow connections)</span>
      </div>

      <div class="setting-group checkbox-group">
        <label class="checkbox-label">
          <input 
            type="checkbox" 
            v-model="settings.enableTcpKeepalive"
            class="setting-checkbox"
          />
          <span>Enable TCP Keepalive</span>
        </label>
        <span class="setting-description">Enable TCP-level keepalive packets</span>
      </div>
    </div>

    <div class="settings-section" style="margin-top:12px">
      <h3>Devices</h3>

      <div class="setting-group">
        <label class="setting-label">Batch Concurrency</label>
        <input
          type="number"
          min="1"
          max="50"
          v-model.number="settings.devicesConcurrency"
          class="setting-input"
        />
        <span class="setting-description">Number of devices to sync in parallel (default: 1)</span>
      </div>

      <div class="setting-group">
        <label class="setting-label">Device Request Timeout (seconds)</label>
        <input
          type="number"
          min="10"
          max="600"
          v-model.number="settings.deviceRequestTimeout"
          class="setting-input"
        />
        <span class="setting-description">Timeout for per-device sync HTTP request (default: 120s)</span>
      </div>
    </div>

    <div class="settings-actions">
      <button class="btn-save" @click="save" :disabled="isSaving">
        {{ isSaving ? 'Saving...' : 'Save Settings' }}
      </button>
      <button class="btn-reset" @click="resetDefaults">Reset Defaults</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface GeneralSettings {
  connectionTimeout: number
  readTimeout: number
  keepaliveInterval: number
  keepaliveRetries: number
  windowSize: number
  enableCompression: boolean
  enableTcpKeepalive: boolean
  devicesConcurrency: number
  deviceRequestTimeout: number
}

const SETTINGS_KEY = 'noc-it:general-settings'

const DEFAULTS: GeneralSettings = {
  connectionTimeout: 30,
  readTimeout: 60,
  keepaliveInterval: 15,
  keepaliveRetries: 3,
  windowSize: 256,
  enableCompression: false,
  enableTcpKeepalive: true,
  devicesConcurrency: 1,
  deviceRequestTimeout: 120,
}

const settings = ref<GeneralSettings>({ ...DEFAULTS })
const isSaving = ref(false)
const saveMessage = ref('')
const saveMessageType = ref<'success' | 'error'>('success')

// ── Font size ──────────────────────────────────────────────────────
const FONT_KEY = 'noc-it:font-size'
const fontPresets = [
  { label: 'S',  px: 11 },
  { label: 'M',  px: 13 },
  { label: 'L',  px: 16 },
  { label: 'XL', px: 20 },
  { label: '2X', px: 28 },
  { label: '3X', px: 40 },
]
const uiFontSize = ref(
  parseInt(localStorage.getItem(FONT_KEY) ?? '13', 10)
)

function applyFontSize() {
  const scale = uiFontSize.value / 13
  const app = document.getElementById('app')
  if (!app) return
  app.style.transformOrigin = '0 0'
  app.style.transform = `scale(${scale})`
  app.style.width  = (100 / scale) + 'vw'
  app.style.height = (100 / scale) + 'vh'
  localStorage.setItem(FONT_KEY, String(uiFontSize.value))
}

function setPreset(px: number) {
  uiFontSize.value = px
  applyFontSize()
}

// ── Load / Save via localStorage ───────────────────────────────────
onMounted(() => {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (raw) settings.value = { ...DEFAULTS, ...JSON.parse(raw) }
  } catch {
    // corrupt data — use defaults
  }
})

function save() {
  isSaving.value = true
  saveMessage.value = ''
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings.value))
    saveMessage.value = 'Settings saved'
    saveMessageType.value = 'success'
  } catch {
    saveMessage.value = 'Error saving settings'
    saveMessageType.value = 'error'
  } finally {
    isSaving.value = false
    setTimeout(() => { saveMessage.value = '' }, 3000)
  }
}

function resetDefaults() {
  settings.value = { ...DEFAULTS }
  localStorage.removeItem(SETTINGS_KEY)
  saveMessage.value = 'Defaults restored'
  saveMessageType.value = 'success'
  setTimeout(() => { saveMessage.value = '' }, 2000)
}
</script>

<style scoped>
.general-settings {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  box-sizing: border-box;
}

h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: #fff;
}

.settings-section {
  background: #0a0a0a;
  border: 1px solid #222;
  border-radius: 4px;
  padding: 15px;
}

h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #fff;
  border-bottom: 1px solid #222;
  padding-bottom: 8px;
}

.setting-group {
  margin-bottom: 15px;
}

.setting-label {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
  color: #ccc;
}

.setting-input {
  width: 120px;
  padding: 4px 8px;
  background: #000;
  border: 1px solid #333;
  border-radius: 3px;
  color: #fff;
  font-size: 13px;
}

.setting-input:focus {
  outline: none;
  border-color: #555;
}

.setting-description {
  display: block;
  margin-top: 3px;
  font-size: 11px;
  color: #666;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #ccc;
  font-size: 13px;
}

.setting-checkbox {
  width: 14px;
  height: 14px;
  cursor: pointer;
}

.settings-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.btn-save {
  padding: 6px 16px;
  background: #1a6b1a;
  border: 1px solid #2a8a2a;
  border-radius: 3px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.btn-save:hover:not(:disabled) {
  background: #228b22;
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-reset {
  padding: 6px 16px;
  background: #333;
  border: 1px solid #555;
  border-radius: 3px;
  color: #ccc;
  font-size: 13px;
  cursor: pointer;
}

.btn-reset:hover {
  background: #444;
}

.save-message {
  padding: 8px 12px;
  border-radius: 3px;
  margin-bottom: 15px;
  font-size: 13px;
}

.save-message.success {
  background: #0a2a0a;
  border: 1px solid #1a6b1a;
  color: #4caf50;
}

.save-message.error {
  background: #2a0a0a;
  border: 1px solid #6b1a1a;
  color: #f44336;
}

/* ── Font size control ──────────────────────────────────────────── */
.font-size-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.font-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 160px;
  height: 4px;
  border-radius: 2px;
  background: #323841;
  outline: none;
  cursor: pointer;
}
.font-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #22c55e;
  cursor: pointer;
  border: 2px solid #1c1f24;
}
.font-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #22c55e;
  cursor: pointer;
  border: 2px solid #1c1f24;
}

.font-size-badge {
  min-width: 42px;
  padding: 2px 8px;
  background: #1c1f24;
  border: 1px solid #323841;
  border-radius: 4px;
  font-size: 12px;
  color: #e5e7eb;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.font-presets {
  display: flex;
  gap: 4px;
}

.preset-btn {
  padding: 3px 10px;
  background: #252a30;
  border: 1px solid #323841;
  border-radius: 4px;
  color: #9ca3af;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: color .12s, border-color .12s, background .12s;
}
.preset-btn:hover {
  color: #e5e7eb;
  border-color: #4b5563;
  background: #2d333b;
}
.preset-btn.active {
  color: #22c55e;
  border-color: #22c55e;
  background: rgba(34,197,94,.08);
}
</style>
