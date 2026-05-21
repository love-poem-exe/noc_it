/**
 * terminalStore — persistent terminal session state.
 *
 * Lives outside any component so sessions survive navigation.
 * WebSocket connection stays open as long as there are active sessions.
 */
import { ref, computed } from 'vue'
import terminalService from '../services/TerminalService'

// ── Singleton state (survives component mount/unmount) ─────────────────────

const sessions = ref([])
const activeSessionId = ref(null)
const pendingDevice = ref(null)
const connecting = ref(false)
const deviceHasBuffer = ref(false)

let wsConnected = false

// ── Helpers ────────────────────────────────────────────────────────────────

const stripAnsi = (str) => {
  return str
    .replace(/\u001b\[[\d;]*[A-Za-z]/g, '')
    .replace(/\u001b\([A-Za-z]/g, '')
    .replace(/\u001b[=>]/g, '')
    .replace(/\u001b\]\d+;[^\u0007]*\u0007/g, '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, '')
}

const appendToSession = (sessionId, text) => {
  const session = sessions.value.find(s => s.sessionId === sessionId)
  if (session) {
    session.output += stripAnsi(text)
  }
}

const removeSession = (sessionId) => {
  const index = sessions.value.findIndex(s => s.sessionId === sessionId)
  if (index !== -1) {
    sessions.value.splice(index, 1)
  }
  if (activeSessionId.value === sessionId) {
    activeSessionId.value = sessions.value.length > 0
      ? sessions.value[sessions.value.length - 1].sessionId
      : null
  }
}

// ── WebSocket message handler ──────────────────────────────────────────────

const handleGatewayMessage = (msg) => {
  const { type } = msg

  if (type === 'connected') {
    const newSession = {
      sessionId: msg.sessionId,
      deviceId: pendingDevice.value?.id || '',
      hostname: msg.hostname,
      address: msg.address,
      login: msg.login,
      useTunnel: msg.useTunnel,
      output: '',
    }
    sessions.value.push(newSession)
    activeSessionId.value = msg.sessionId

    const banner = msg.banner || ''
    appendToSession(msg.sessionId,
`=== Sesja utworzona ===
Hostname: ${msg.hostname}
Address: ${msg.address}
Login: ${msg.login}
Session ID: ${msg.sessionId}
Tunel: ${msg.useTunnel ? 'TAK' : 'NIE'}
Status: CONNECTED
======================

${banner}
`)
    pendingDevice.value = null
    connecting.value = false

    // Disable terminal pagination on the device
    setTimeout(() => {
      terminalService.sendCommand(msg.sessionId, 'terminal length 0')
    }, 500)
  }

  else if (type === 'output') {
    if (msg.sessionId && msg.data) {
      appendToSession(msg.sessionId, msg.data)
    }
  }

  else if (type === 'disconnected') {
    appendToSession(msg.sessionId, '\n=== Sesja zakończona ===\n')
    removeSession(msg.sessionId)
  }

  else if (type === 'error') {
    console.error('[SSH Gateway] Error:', msg.message)
    if (pendingDevice.value) {
      const errorSessionId = 'error-' + Date.now()
      sessions.value.push({
        sessionId: errorSessionId,
        hostname: (pendingDevice.value.hostname || '?') + ' (ERROR)',
        output: `=== BŁĄD POŁĄCZENIA ===\nUrządzenie: ${pendingDevice.value.hostname}\nBłąd: ${msg.message}\n===================\n`,
      })
      activeSessionId.value = errorSessionId
      pendingDevice.value = null
      connecting.value = false
    } else if (msg.sessionId) {
      appendToSession(msg.sessionId, `\nERROR: ${msg.message}\n`)
    }
  }
}

// ── Public API ─────────────────────────────────────────────────────────────

function ensureConnected() {
  if (!wsConnected) {
    terminalService.connect()
    terminalService.onMessage(handleGatewayMessage)
    wsConnected = true
  }
}

function connectDevice(device) {
  ensureConnected()
  pendingDevice.value = device
  connecting.value = true
  terminalService.connectDevice({
    deviceId: device.id,
    hostname: device.hostname,
    address: device.address,
    port: device.port || 22,
  })
}

function sendCommand(command) {
  if (!activeSessionId.value) return
  const session = sessions.value.find(s => s.sessionId === activeSessionId.value)
  if (!session) return

  appendToSession(activeSessionId.value, `${session.hostname}# ${command}\n`)
  terminalService.sendCommand(activeSessionId.value, command)
}

function sendRaw(data) {
  if (!activeSessionId.value) return
  terminalService.sendRaw(activeSessionId.value, data)
}

function closeSession(sessionId) {
  terminalService.disconnectSession(sessionId)
  removeSession(sessionId)
}

// ── Computed ───────────────────────────────────────────────────────────────

const activeSessionOutput = computed(() => {
  const session = sessions.value.find(s => s.sessionId === activeSessionId.value)
  return session ? session.output : ''
})

const activePrompt = computed(() => {
  const session = sessions.value.find(s => s.sessionId === activeSessionId.value)
  return session ? `${session.hostname}# ` : ''
})

const placeholderText = computed(() => {
  if (connecting.value && pendingDevice.value) {
    return `Próba nawiązania sesji z ${pendingDevice.value.hostname}...`
  }
  return 'Kliknij + aby utworzyć sesję'
})

// ── Export ──────────────────────────────────────────────────────────────────

export function useTerminalStore() {
  return {
    // State
    sessions,
    activeSessionId,
    pendingDevice,
    connecting,
    deviceHasBuffer,
    // Computed
    activeSessionOutput,
    activePrompt,
    placeholderText,
    // Actions
    ensureConnected,
    connectDevice,
    sendCommand,
    sendRaw,
    closeSession,
    appendToSession,
  }
}
