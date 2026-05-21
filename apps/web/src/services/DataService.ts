import { cacheService } from './CacheService'
import { requestJson, requestForm } from './ApiClient'
import { waitForJob } from './JobService'

// Async script helper - HTTP fallback for web backend
function invokeAsyncScript({
  script,
  method,
  payload,
  timeoutMs = 60000
}: {
  script: string,
  method: string,
  payload?: any,
  timeoutMs?: number
}) {
  return requestJson('/api/scripts/async', {
    method: 'POST',
    body: { script, method, payload },
    timeoutMs
  }).then(async (response) => {
    const jobId = response?.jobId
    if (!jobId) return response
    const status = await waitForJob(jobId, timeoutMs)
    const result = status?.result
    if (result?.result !== undefined) return result.result
    return result
  })
}

interface Device {
  id: string
  hostname: string
  address: string
  status: string
  vendor: string
  model: string
  software: string
  type: string
  account: string
  connection?: string
}

interface Account {
  id: string
  name: string
  login: string
  password: string
}

interface Site {
  id: string
  site_tag: string
  site_name: string
  location: string
}

interface TunnelStatus {
  status: string
  port?: number
  address?: string
  login?: string
}

const normalizeTunnelStatus = (raw: any): TunnelStatus => ({
  status: raw?.status || 'NOT CONNECTED',
  port: raw?.port,
  address: raw?.address,
  login: raw?.login
})

const normalizeDevices = (raw: any): Device[] => {
  const devicesArray = Array.isArray(raw) ? raw : raw?.data || raw?.devices || []
  if (!Array.isArray(devicesArray)) {
    console.error('[DataService] normalizeDevices: parsed response is not an array', raw)
    return []
  }
  return devicesArray.map((dev: any) => ({
    ...dev,
    hostname: dev.hostname ?? dev.name
  }))
}

const normalizeAccounts = (raw: any): Account[] => {
  const accountsArray = Array.isArray(raw) ? raw : raw?.data || raw?.accounts || []
  if (!Array.isArray(accountsArray)) {
    console.error('[DataService] normalizeAccounts: parsed response is not an array', raw)
    return []
  }
  return accountsArray
}

const normalizeSites = (raw: any): Site[] => {
  const arr = Array.isArray(raw) ? raw : raw?.data || raw?.sites || []
  if (!Array.isArray(arr)) {
    console.error('[DataService] normalizeSites: parsed response is not an array', raw)
    return []
  }
  return arr
}

class DataService {
  /**
   * Pobiera listę urządzeń z cache lub serwera
   */
  async getDevices(): Promise<Device[]> {
    return cacheService.get('devices', async () => {
      try {
        const resultRaw = await requestJson('/api/devices', { timeoutMs: 60000 })

        if (!resultRaw) {
          return []
        }

        return normalizeDevices(resultRaw)
      } catch (error: any) {
        if (String(error?.message || error).toLowerCase().includes('not implemented')) {
          throw error
        }
        throw error
      }
    })
  }

  /**
   * Pobiera listę urządzeń ze stronicowaniem (dla dużych list)
   */
  async getDevicesPaginated(page: number = 1, limit: number = 100): Promise<{
    data: Device[]
    total: number
    page: number
    pages: number
  }> {
    try {
      const parsed = await requestJson(`/api/devices?page=${page}&limit=${limit}`, { timeoutMs: 60000 })
      return {
        data: normalizeDevices(parsed.data || []),
        total: parsed.total || 0,
        page: parsed.page || page,
        pages: parsed.pages || 1
      }
    } catch (error: any) {
      if (String(error?.message || error).toLowerCase().includes('not implemented')) {
        throw error
      }
      throw error
    }
  }

  /**
   * Pobiera listę kont z cache lub serwera
   */
  async getAccounts(): Promise<Account[]> {
    return cacheService.get('accounts', async () => {
      try {
        const resultRaw = await requestJson('/api/accounts', { timeoutMs: 30000 })

        if (!resultRaw) {
          return []
        }

        return normalizeAccounts(resultRaw)
      } catch (error: any) {
        if (String(error?.message || error).toLowerCase().includes('not implemented')) {
          throw error
        }
        throw error
      }
    })
  }

  /**
   * Pobiera listę sites z cache lub serwera
   */
  async getSites(): Promise<Site[]> {
    return cacheService.get('sites', async () => {
      try {
        const resultRaw = await requestJson('/api/sites', { timeoutMs: 30000 })

        if (!resultRaw) {
          return []
        }

        return normalizeSites(resultRaw)
      } catch (error: any) {
        if (String(error?.message || error).toLowerCase().includes('not implemented')) {
          throw error
        }
        throw error
      }
    })
  }

  /**
   * Pobiera status tunelu z cache lub serwera
   */
  async getTunnelStatus(): Promise<TunnelStatus> {
    return cacheService.get('tunnelStatus', async () => {
      try {
        const result = await requestJson('/api/tunnel/status', { timeoutMs: 10000 })
        return normalizeTunnelStatus(result)
      } catch (error: any) {
        if (String(error?.message || error).toLowerCase().includes('not implemented')) {
          throw error
        }
        throw error
      }
    })
  }

  /**
   * Pobiera informacje o urządzeniach z cache lub serwera
   */
  async getDevicesInfo(): Promise<any> {
    return cacheService.get('devicesInfo', async () => {
      try {
        return await requestJson('/api/devices/info', { timeoutMs: 60000 })
      } catch (error: any) {
        if (String(error?.message || error).toLowerCase().includes('not implemented')) {
          throw error
        }
        throw error
      }
    })
  }

  /**
   * Dodaje nowe urządzenie i invaliduje cache
   */
  async addDevice(address: string): Promise<void> {
    await requestJson('/api/devices', {
      method: 'POST',
      body: { address },
      timeoutMs: 45000
    })
    
    // Invaliduj cache po dodaniu
    cacheService.invalidate('devices')
  }

  /**
   * Add a device by hostname/address and trigger sync on the server side.
   * Uses the /api/devices/add-and-sync endpoint which performs add+sync atomically.
   */
  async addAndSyncDevice(address: string, timeoutMs: number = 120000): Promise<any> {
    const result = await requestJson('/api/devices/add-and-sync', {
      method: 'POST',
      body: { hostname: address, address },
      timeoutMs
    })
    // Do NOT invalidate cache here for per-device calls — caller should refresh once after batch
    return result
  }

  /**
   * Add multiple devices and trigger synchronization for each on the server side.
   * Calls /api/devices/add-batch-and-sync with an array of hostnames.
   */
  async addAndSyncDevices(addresses: string[], timeoutMs: number = 300000): Promise<any> {
    if (!Array.isArray(addresses) || addresses.length === 0) return { ok: false, error: 'empty' }
    const result = await requestJson('/api/devices/add-batch-and-sync', {
      method: 'POST',
      body: { hostnames: addresses },
      timeoutMs
    })
    // Caller should refresh cache once after batch completes
    return result
  }

  /**
   * Usuwa urządzenie i invaliduje cache
   */
  async removeDevice(id: string): Promise<void> {
    await requestJson(`/api/devices/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      timeoutMs: 30000
    })
    
    cacheService.invalidate('devices')
  }

  /**
   * Usuwa wszystkie urządzenia ze statusem ERROR i invaliduje cache
   */
  async removeAllErrorDevices(): Promise<void> {
    await requestJson('/api/devices/cleanup', {
      method: 'POST',
      body: { status: 'ERROR' },
      timeoutMs: 60000
    })
    
    cacheService.invalidate('devices')
  }

  /**
   * Usuwa wszystkie urządzenia ze statusem UNSYNC i invaliduje cache
   */
  async removeAllUnsyncDevices(): Promise<void> {
    await requestJson('/api/devices/cleanup', {
      method: 'POST',
      body: { status: 'UNSYNC' },
      timeoutMs: 60000
    })
    
    cacheService.invalidate('devices')
  }

  /**
   * Dodaje nowe konto i invaliduje cache
   */
  async addAccount(name: string, login: string, password: string): Promise<void> {
    await requestJson('/api/accounts', {
      method: 'POST',
      body: { name, login, password },
      timeoutMs: 30000
    })
    
    cacheService.invalidate('accounts')
  }

  /**
   * Usuwa konto i invaliduje cache
   */
  async removeAccount(id: string): Promise<void> {
    await requestJson(`/api/accounts/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      timeoutMs: 30000
    })
    
    cacheService.invalidate('accounts')
  }

  /**
   * Dodaje site i invaliduje cache
   */
  async addSite(site_tag: string, site_name: string, location: string): Promise<void> {
    await requestJson('/api/sites', {
      method: 'POST',
      body: { site_tag, site_name, location },
      timeoutMs: 30000
    })
    cacheService.invalidate('sites')
  }

  /**
   * Aktualizuje site i invaliduje cache
   */
  async updateSite(id: string, site_tag: string, site_name: string, location: string): Promise<void> {
    await requestJson(`/api/sites/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: { site_tag, site_name, location },
      timeoutMs: 30000
    })
    cacheService.invalidate('sites')
  }

  /**
   * Usuwa site i invaliduje cache
   */
  async removeSite(id: string): Promise<void> {
    await requestJson(`/api/sites/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      timeoutMs: 30000
    })
    cacheService.invalidate('sites')
  }

  /**
   * Zapisuje całą listę sites (reorder/save) i invaliduje cache
   */
  async saveAllSites(sites: Site[]): Promise<void> {
    await requestJson('/api/sites/reorder', {
      method: 'POST',
      body: { sites },
      timeoutMs: 30000
    })
    cacheService.invalidate('sites')
  }

  /**
   * Synchronizuje urządzenie (nie cache'uje bo zawsze chcemy najnowsze dane)
   */
  async syncDevice(deviceId: string, timeoutMs: number = 120000): Promise<any> {
    const result = await requestJson(`/api/devices/${encodeURIComponent(deviceId)}/sync`, {
      method: 'POST',
      timeoutMs
    })
    
    cacheService.invalidate('devices')
    
    return result
  }

  /**
   * Przełącza tunel i invaliduje cache statusu
   */
  async toggleTunnel(): Promise<TunnelStatus> {
    try {
      const resultRaw = await requestJson('/api/tunnel/toggle', {
        method: 'POST',
        timeoutMs: 30000
      })

      cacheService.invalidate('tunnelStatus')

      return normalizeTunnelStatus(resultRaw)
    } catch (error: any) {
      if (String(error?.message || error).toLowerCase().includes('not implemented')) {
        throw error
      }
      throw error
    }
  }

  /**
   * Zapisuje dane tunelu i invaliduje cache
   */
  async saveTunnel(tunnelData: any): Promise<void> {
    try {
      await requestJson('/api/tunnel', {
        method: 'PUT',
        body: tunnelData,
        timeoutMs: 30000
      })

      cacheService.invalidate('tunnelStatus')
    } catch (error: any) {
      if (String(error?.message || error).toLowerCase().includes('not implemented')) {
        throw error
      }
      throw error
    }
  }

  /**
   * Tworzy nową sesję SSH na urządzeniu (otwiera połączenie SSH)
   */
  async createConsoleSession(deviceId: string): Promise<any> {
    const ts = () => {
      const now = new Date()
      return `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}]`
    }
    
    console.log(`${ts()} [DataService] CREATE_SESSION START: deviceId="${deviceId}"`)
    const startTime = performance.now()
    
    try {
      const resultRaw = await requestJson('/api/consoles/sessions', {
        method: 'POST',
        body: { deviceId },
        timeoutMs: 120000
      })
      
      const elapsed = performance.now() - startTime
      console.log(`${ts()} [DataService] CREATE_SESSION DONE in ${elapsed.toFixed(2)}ms`)
      
      const parsed = resultRaw
      return {
        success: true,
        sessionId: parsed.session_id || '',
        initialOutput: parsed.initial_output || '',
        debugLogs: parsed.debug_logs || []
      }
    } catch (error) {
      const elapsed = performance.now() - startTime
      console.error(`${ts()} [DataService] CREATE_SESSION ERROR after ${elapsed.toFixed(2)}ms: ${error}`)
      throw error
    }
  }

  /**
   * Wykonuje komendę w istniejącej sesji SSH (cache po device_id)
   */
  async executeCommandInSession(deviceId: string, command: string): Promise<any> {
    const ts = () => {
      const now = new Date()
      return `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}]`
    }
    
    console.log(`${ts()} [DataService] Command IN_SESSION START: "${command}" (deviceId="${deviceId}")`)
    const startTime = performance.now()
    
    try {
      const resultRaw = await requestJson('/api/consoles/sessions/command', {
        method: 'POST',
        body: { deviceId, command },
        timeoutMs: 120000
      })
      
      const elapsed = performance.now() - startTime
      console.log(`${ts()} [DataService] Command IN_SESSION DONE in ${elapsed.toFixed(2)}ms`)
      
      const parsed = resultRaw
      return {
        success: parsed.success || false,
        output: parsed.output || '',
        error: parsed.error || ''
      }
    } catch (error) {
      const elapsed = performance.now() - startTime
      console.error(`${ts()} [DataService] Command IN_SESSION ERROR after ${elapsed.toFixed(2)}ms: ${error}`)
      throw error
    }
  }

  /**
   * Zamyka sesję SSH
   */
  async closeConsoleSession(deviceId: string): Promise<void> {
    await requestJson('/api/consoles/sessions/close', {
      method: 'POST',
      body: { deviceId },
      timeoutMs: 30000
    })
  }

  /**
   * Wykonuje komendę SSH na urządzeniu (dla konsoli)
   */
  async executeCommand(deviceId: string, command: string): Promise<any> {
    const ts = () => {
      const now = new Date()
      return `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}]`
    }
    
    console.log(`${ts()} [DataService] Command START: "${command}"`)
    const startTime = performance.now()
    let invokeStartTime = 0
    let invokeEndTime = 0
    
    try {
      invokeStartTime = performance.now()
      console.log(`${ts()} [DataService] [INVOKE_START] Calling invokeAsyncScript...`)

      const resultRaw = await requestJson('/api/consoles/execute', {
        method: 'POST',
        body: { deviceId, command },
        timeoutMs: 120000
      })
      
      invokeEndTime = performance.now()
      const invokeElapsed = invokeEndTime - invokeStartTime
      console.log(`${ts()} [DataService] [INVOKE_END] Received response after ${invokeElapsed.toFixed(2)}ms from Python`)
      
      console.log(`${ts()} [DataService] [PARSE_START] Parsing response...`)
      const parseStartTime = performance.now()
      
      const parsed = resultRaw
      const result = {
        success: parsed.success || false,
        output: parsed.output || '',
        error: parsed.error || ''
      }
      
      const parseEndTime = performance.now()
      const parseElapsed = parseEndTime - parseStartTime
      console.log(`${ts()} [DataService] [PARSE_END] Parsed in ${parseElapsed.toFixed(2)}ms`)
      
      const totalElapsed = performance.now() - startTime
      console.log(`${ts()} [DataService] [COMPLETE] success=${result.success}, output_size=${result.output.length} bytes, total=${totalElapsed.toFixed(2)}ms`)
      
      return result
    } catch (error) {
      const totalElapsed = performance.now() - startTime
      console.error(`${ts()} [DataService] [ERROR] Command failed after ${totalElapsed.toFixed(2)}ms: ${error}`)
      throw error
    }
  }

  /**
   * Wymusza odświeżenie danych (omija cache)
   */
  async forceRefresh(dataType: 'devices' | 'accounts' | 'tunnelStatus' | 'devicesInfo'): Promise<any> {
    cacheService.invalidate(dataType)
    
    switch (dataType) {
      case 'devices':
        return this.getDevices()
      case 'accounts':
        return this.getAccounts()
      case 'tunnelStatus':
        return this.getTunnelStatus()
      case 'devicesInfo':
        return this.getDevicesInfo()
    }
  }

  /**
   * Pobiera statystyki cache
   */
  getCacheStats(): Record<string, any> {
    return cacheService.getStats()
  }

  /**
   * Czyści cały cache
   */
  clearCache(): void {
    cacheService.clear()
  }

  /**
   * Uploads SSH key material for tunnel configuration
   */
  async uploadTunnelKey(file: File): Promise<void> {
    const form = new FormData()
    form.append('key', file)
    await requestForm('/api/tunnel/key', form, { method: 'POST', timeoutMs: 30000 })
  }
}

// Eksportuj singleton instance
export const dataService = new DataService()
export default dataService

// Eksportuj helper dla niestandardowych skryptów
export { invokeAsyncScript }