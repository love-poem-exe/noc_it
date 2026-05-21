<template>
  <div class="terminal-container">
    <!-- Header z przyciskiem + i zakładkami -->
    <div class="terminal-header">
      <!-- Zakładki sesji -->
      <div class="tabs-container">
        <div 
          v-for="session in sessions" 
          :key="session.sessionId"
          @click="activeSessionId = session.sessionId"
          :class="['tab', { active: activeSessionId === session.sessionId }]"
        >
          <span class="tab-name">{{ session.hostname }}</span>
          <button 
            @click.stop="closeSession(session.sessionId)" 
            class="tab-close"
            title="Zamknij sesję"
          >×</button>
        </div>
      </div>
      
      <button @click="openNewSessionModal" class="btn-add" title="Nowa sesja" :disabled="connecting">+</button>
    </div>

    <!-- Pole terminala -->
    <div class="terminal-wrapper">
      <div ref="terminalOutput" class="terminal-output" @click="focusInput" @scroll="onTerminalScroll">
        <pre>{{ activeSessionOutput }}</pre>
        <div v-if="activeSessionId" class="terminal-input-inline">
          <span v-if="!deviceHasBuffer" class="terminal-prompt">{{ activePrompt }}</span>
          <input 
            ref="terminalInput"
            v-model="currentInput"
            @keydown.enter="sendCommand"
            @keydown="handleKeydown"
            class="terminal-input"
            spellcheck="false"
            :disabled="!activeSessionId"
          />
        </div>
        <div v-else class="terminal-placeholder">{{ placeholderText }}</div>
      </div>
    </div>

    <!-- Modal z wyborem urządzenia -->
    <div v-if="showModal" class="modal-overlay" @click="showModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Wybierz urządzenie</h3>
          <button @click="showModal = false" class="modal-close">×</button>
        </div>
        <div class="modal-body">
          <input 
            v-model="searchQuery" 
            type="text" 
            class="search-input" 
            placeholder="Szukaj urządzenia..."
            @input="filterDevices"
          />
          <div class="device-list">
            <div 
              v-for="device in filteredDevices" 
              :key="device.id" 
              @click="selectDevice(device)"
              class="device-item"
            >
              <div class="device-name">{{ device.hostname }}</div>
              <div class="device-address">{{ device.address }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useData } from '../composables/useData'
import { useTerminalStore } from '../stores/terminalStore'

export default {
  name: 'Terminal',
  setup() {
    const { devices, loadDevices } = useData()
    const store = useTerminalStore()

    const showModal = ref(false)
    const searchQuery = ref('')
    const filteredDevices = ref([])
    const terminalOutput = ref(null)
    const terminalInput = ref(null)
    const currentInput = ref('')
    /** When true, new output auto-scrolls to bottom. Disabled when user scrolls up. */
    let autoScroll = true

    const openNewSessionModal = () => {
      searchQuery.value = ''
      filteredDevices.value = devices.value
      showModal.value = true
    }

    const filterDevices = () => {
      if (!searchQuery.value) {
        filteredDevices.value = devices.value
      } else {
        const query = searchQuery.value.toLowerCase()
        filteredDevices.value = devices.value.filter(device =>
          device.hostname.toLowerCase().includes(query) ||
          device.address.toLowerCase().includes(query)
        )
      }
    }

    const scrollToBottom = () => {
      if (terminalOutput.value) {
        terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight
      }
    }

    const onTerminalScroll = () => {
      if (!terminalOutput.value) return
      const el = terminalOutput.value
      // User is "at bottom" if within 50px of the end
      autoScroll = (el.scrollHeight - el.scrollTop - el.clientHeight) < 50
    }

    // Auto-scroll on new output, but only if user hasn't scrolled up
    watch(() => store.activeSessionOutput.value, () => {
      if (autoScroll) {
        setTimeout(() => scrollToBottom(), 10)
      }
    })

    // ── Commands ────────────────────────────────────────────────────────

    const sendCommand = () => {
      if (!store.activeSessionId.value) return

      if (store.deviceHasBuffer.value) {
        store.sendRaw('\n')
        store.deviceHasBuffer.value = false
        currentInput.value = ''
        autoScroll = true
        setTimeout(() => {
          terminalInput.value?.focus()
          scrollToBottom()
        }, 10)
        return
      }

      if (!currentInput.value.trim()) return

      store.sendCommand(currentInput.value)
      currentInput.value = ''
      autoScroll = true
      setTimeout(() => {
        terminalInput.value?.focus()
        scrollToBottom()
      }, 10)
    }

    const focusInput = () => {
      terminalInput.value?.focus()
    }

    // ── ? help ─────────────────────────────────────────────────────

    const handleKeydown = (e) => {
      if (e.key === '?') {
        e.preventDefault()
        if (!store.activeSessionId.value) return

        const partial = currentInput.value
        store.sendRaw(partial + '?')
        store.deviceHasBuffer.value = true
        currentInput.value = ''
        autoScroll = true
        setTimeout(() => scrollToBottom(), 50)
      }
    }

    // ── Device selection ────────────────────────────────────────────────

    const selectDevice = (device) => {
      console.log('Nawiązywanie sesji z urządzeniem:', device)
      showModal.value = false
      store.connectDevice(device)
    }

    const closeSession = (sessionId) => {
      store.closeSession(sessionId)
    }

    // ── Lifecycle ───────────────────────────────────────────────────────

    onMounted(async () => {
      await loadDevices()
      filteredDevices.value = devices.value

      // Ensure WebSocket is connected (idempotent)
      store.ensureConnected()

      // Focus input if session already active
      if (store.activeSessionId.value) {
        setTimeout(() => {
          terminalInput.value?.focus()
          scrollToBottom()
        }, 100)
      }
    })

    onUnmounted(() => {
      // Do NOT close sessions or disconnect — they persist in the store
    })

    return {
      devices,
      showModal,
      searchQuery,
      filteredDevices,
      sessions: store.sessions,
      activeSessionId: store.activeSessionId,
      activeSessionOutput: store.activeSessionOutput,
      activePrompt: store.activePrompt,
      currentInput,
      terminalOutput,
      terminalInput,
      filterDevices,
      openNewSessionModal,
      selectDevice,
      closeSession,
      sendCommand,
      focusInput,
      onTerminalScroll,
      handleKeydown,
      deviceHasBuffer: store.deviceHasBuffer,
      connecting: store.connecting,
      placeholderText: store.placeholderText,
    }
  }
}
</script>

<style scoped>
.terminal-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: #1e1e1e;
  overflow: hidden;
}

.terminal-header {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: #252526;
  border-bottom: 1px solid #3e3e42;
  align-items: center;
}

.btn-add {
  width: 32px;
  height: 32px;
  background: #0e639c;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 20px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  flex-shrink: 0;
}

.btn-add:hover {
  background: #1177bb;
}

.btn-add:disabled {
  background: #3e3e42;
  cursor: not-allowed;
  opacity: 0.5;
}

/* Zakładki */
.tabs-container {
  display: flex;
  gap: 4px;
  flex: 0 1 auto;
  overflow-x: auto;
  overflow-y: hidden;
}

.tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #2d2d30;
  border: 1px solid #3e3e42;
  border-radius: 4px 4px 0 0;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  min-width: 120px;
  max-width: 200px;
}

.tab:hover {
  background: #37373d;
}

.tab.active {
  background: #1e1e1e;
  border-bottom-color: #1e1e1e;
}

.tab-name {
  color: #d4d4d4;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-close {
  background: transparent;
  border: none;
  color: #858585;
  font-size: 18px;
  cursor: pointer;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  transition: all 0.2s;
  flex-shrink: 0;
}

.tab-close:hover {
  background: #f48771;
  color: #fff;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #252526;
  border: 1px solid #3e3e42;
  border-radius: 6px;
  width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #3e3e42;
}

.modal-header h3 {
  margin: 0;
  color: #d4d4d4;
  font-size: 16px;
  font-weight: 600;
}

.modal-close {
  background: transparent;
  border: none;
  color: #d4d4d4;
  font-size: 28px;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.modal-close:hover {
  background: #3e3e42;
}

.modal-body {
  padding: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.search-input {
  width: 100%;
  padding: 10px 12px;
  background: #3c3c3c;
  color: #d4d4d4;
  border: 1px solid #3e3e42;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
}

.search-input:focus {
  border-color: #0e639c;
}

.device-list {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.device-item {
  padding: 12px 15px;
  background: #2d2d30;
  border: 1px solid #3e3e42;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.device-item:hover {
  background: #37373d;
  border-color: #0e639c;
}

.device-name {
  color: #d4d4d4;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.device-address {
  color: #858585;
  font-size: 12px;
}

.terminal-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #000;
  overflow: hidden;
}

.terminal-output {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  color: #fff;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  white-space: pre-wrap;
  word-wrap: break-word;
  cursor: text;
}

.terminal-output pre {
  margin: 0;
  font-family: inherit;
  color: inherit;
}

.terminal-input-inline {
  display: flex;
  align-items: center;
  margin-top: 0;
  line-height: 1.4;
}

.terminal-prompt {
  color: #fff;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  white-space: pre;
  flex-shrink: 0;
}

.terminal-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #fff;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  padding: 0;
  margin: 0;
  line-height: 1.4;
  caret-color: #fff;
}

.terminal-input:disabled {
  color: #666;
}

.terminal-placeholder {
  color: #666;
  font-style: italic;
  padding-top: 10px;
  user-select: none;
  pointer-events: none;
}
</style>

