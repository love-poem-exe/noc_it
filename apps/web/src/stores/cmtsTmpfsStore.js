import { defineStore } from 'pinia'
import { ref } from 'vue'
import { requestJson } from '../services/ApiClient'

export const useCmtsTmpfsStore = defineStore('cmtsTmpfs', () => {
  // Stan
  const isInitialized = ref(false)
  const devices = ref([])
  const accounts = ref([])
  
  // Funkcja inicjalizacji - wykonywana tylko raz
  const initialize = async () => {
    if (isInitialized.value) {
      console.log('[CMTS TMPFS STORE] Already initialized, skipping...')
      return
    }
    
    console.log('[CMTS TMPFS STORE] Initializing store...')
    
    try {
      // Wczytaj devices.json
      await loadDevices()
      
      // Wczytaj accounts.json
      await loadAccounts()
      
      isInitialized.value = true
      console.log('[CMTS TMPFS STORE] Store initialized successfully')
    } catch (error) {
      console.error('[CMTS TMPFS STORE] Error initializing store:', error)
    }
  }
  
  const loadDevices = async () => {
    try {
      console.log('[CMTS TMPFS STORE] Loading devices...')

      const apiResult = await requestJson('/api/devices', { timeoutMs: 10000 })
      if (Array.isArray(apiResult)) {
        devices.value = apiResult
        console.log(`[CMTS TMPFS STORE] Loaded ${devices.value.length} devices from API`)
        return
      }
      
      console.error('[CMTS TMPFS STORE] API did not return an array')
      devices.value = []
    } catch (error) {
      console.error('[CMTS TMPFS STORE] Error loading devices:', error)
      devices.value = []
    }
  }
  
  const loadAccounts = async () => {
    try {
      console.log('[CMTS TMPFS STORE] Loading accounts...')

      const apiResult = await requestJson('/api/accounts', { timeoutMs: 10000 })
      if (Array.isArray(apiResult)) {
        accounts.value = apiResult
        console.log(`[CMTS TMPFS STORE] Loaded ${accounts.value.length} accounts from API`)
        return
      }
      
      console.error('[CMTS TMPFS STORE] API did not return an array')
      accounts.value = []
    } catch (error) {
      console.error('[CMTS TMPFS STORE] Error loading accounts:', error)
      accounts.value = []
    }
  }
  
  const reset = () => {
    console.log('[CMTS TMPFS STORE] Resetting store...')
    isInitialized.value = false
    devices.value = []
    accounts.value = []
  }
  
  return {
    isInitialized,
    devices,
    accounts,
    initialize,
    loadDevices,
    loadAccounts,
    reset
  }
})
