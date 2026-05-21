import { ref, type Ref } from 'vue'
import { dataService } from '../services/DataService'
import { cacheService } from '../services/CacheService'

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
  site_id?: string
  connection?: string
}

export interface Account {
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

/**
 * Composable do zarządzania danymi z cache
 */
export function useData() {
  // Stany ładowania
  const devicesLoading = ref(false)
  const accountsLoading = ref(false)
  const tunnelLoading = ref(false)
  const sitesLoading = ref(false)

  // Dane
  const devices: Ref<Device[]> = ref([])
  const accounts: Ref<Account[]> = ref([])
  const sites: Ref<Site[]> = ref([])
  const tunnelStatus: Ref<TunnelStatus> = ref({ status: 'NOT CONNECTED' })

  // Stany załadowania (czy dane zostały już pobrane)
  const devicesLoaded = ref(false)
  const accountsLoaded = ref(false)
  const tunnelLoaded = ref(false)
  const sitesLoaded = ref(false)

  /**
   * Ładuje urządzenia z cache lub serwera
   */
  const loadDevices = async (force = false) => {
    if (devicesLoaded.value && !force) {
      console.log('[useData] Devices already loaded, skipping...')
      return devices.value
    }

    if (force) {
      cacheService.invalidate('devices')
    }

    devicesLoading.value = true
    try {
      const result = await dataService.getDevices()
      devices.value = result

      // Attempt to assign site_id by matching hostname against site_tag values
      try {
        // Ensure sites are loaded (use cache if present)
        const siteList = await loadSites()
        if (Array.isArray(siteList) && siteList.length) {
          // build map of site_tag -> id
          const tagMap: { tag: string; id: string }[] = siteList
            .filter(s => s.site_tag)
            .map(s => ({ tag: (s.site_tag || '').toLowerCase(), id: s.id }))

          // for each device, find the best matching tag (longest match)
          devices.value = devices.value.map((dev) => {
            const hn = (dev.hostname || '').toLowerCase()
            let best: string | null = null
            let bestId: string | null = null
            for (const t of tagMap) {
              if (!t.tag) continue
              if (hn.includes(t.tag)) {
                if (best === null || t.tag.length > best.length) {
                  best = t.tag
                  bestId = t.id
                }
              }
            }
            if (bestId) dev.site_id = bestId
            return dev
          })
        }
      } catch (e) {
        // ignore site matching failures — devices still load
        console.warn('[useData] site matching failed', e)
      }
      devicesLoaded.value = true
      return result
    } catch (error) {
      console.error('[useData] Error loading devices:', error)
      devices.value = []
      throw error
    } finally {
      devicesLoading.value = false
    }
  }

  /**
   * Ładuje konta z cache lub serwera
   */
  const loadAccounts = async (force = false) => {
    if (accountsLoaded.value && !force) {
      console.log('[useData] Accounts already loaded, skipping...')
      return accounts.value
    }

    accountsLoading.value = true
    try {
      const result = await dataService.getAccounts()
      accounts.value = result
      accountsLoaded.value = true
      console.log(`[useData] Loaded ${result.length} accounts`)
      return result
    } catch (error) {
      console.error('[useData] Error loading accounts:', error)
      accounts.value = []
      throw error
    } finally {
      accountsLoading.value = false
    }
  }

  /**
   * Ładuje sites z cache lub serwera
   */
  const loadSites = async (force = false) => {
    if (sitesLoaded.value && !force) {
      return sites.value
    }

    if (force) {
      cacheService.invalidate('sites')
    }

    sitesLoading.value = true
    try {
      const result = await dataService.getSites()
      sites.value = result
      sitesLoaded.value = true
      return result
    } catch (error) {
      console.warn('[useData] getSites failed, attempting fallback to /data/sites.json', error)
      try {
        // try common public path first
        const paths = ['/data/sites.json', '/src/data/sites.json']
        for (const p of paths) {
          try {
            const res = await fetch(p)
            if (res.ok) {
              const parsed = await res.json()
              sites.value = parsed || []
              sitesLoaded.value = true
              return sites.value
            }
          } catch (e) {
            // try next
          }
        }
      } catch (e) {
        console.warn('[useData] local sites.json fallback failed', e)
      }

      sites.value = []
      throw error
    } finally {
      sitesLoading.value = false
    }
  }

  /**
   * Ładuje status tunelu z cache lub serwera
   */
  const loadTunnelStatus = async (force = false) => {
    if (tunnelLoaded.value && !force) {
      return tunnelStatus.value
    }

    tunnelLoading.value = true
    try {
      const result = await dataService.getTunnelStatus()
      tunnelStatus.value = result
      tunnelLoaded.value = true
      return result
    } catch (error) {
      console.error('[useData] Error loading tunnel status:', error)
      tunnelStatus.value = { status: 'NOT CONNECTED' }
      throw error
    } finally {
      tunnelLoading.value = false
    }
  }

  /**
   * Dodaje urządzenie i odświeża listę
   */
  const addDevice = async (address: string) => {
    await dataService.addDevice(address)
    // Wymuś przeładowanie urządzeń
    devicesLoaded.value = false
    return loadDevices(true)
  }

  /**
   * Usuwa urządzenie i odświeża listę
   */
  const removeDevice = async (id: string) => {
    await dataService.removeDevice(id)
    // Wymuś przeładowanie urządzeń
    devicesLoaded.value = false
    return loadDevices(true)
  }

  /**
   * Usuwa wszystkie urządzenia ze statusem ERROR i odświeża listę
   */
  const removeAllErrorDevices = async () => {
    await dataService.removeAllErrorDevices()
    // Wymuś przeładowanie urządzeń
    devicesLoaded.value = false
    return loadDevices(true)
  }

  /**
   * Usuwa wszystkie urządzenia ze statusem UNSYNC i odświeża listę
   */
  const removeAllUnsyncDevices = async () => {
    await dataService.removeAllUnsyncDevices()
    // Wymuś przeładowanie urządzeń
    devicesLoaded.value = false
    return loadDevices(true)
  }

  /**
   * Dodaje konto i odświeża listę
   */
  const addAccount = async (name: string, login: string, password: string) => {
    await dataService.addAccount(name, login, password)
    // Wymuś przeładowanie kont
    accountsLoaded.value = false
    return loadAccounts(true)
  }

  /**
   * Dodaje site i odświeża listę
   */
  const addSite = async (site_tag: string, site_name: string, location: string) => {
    await dataService.addSite(site_tag, site_name, location)
    sitesLoaded.value = false
    return loadSites(true)
  }

  /**
   * Aktualizuje site i odświeża listę
   */
  const updateSite = async (id: string, site_tag: string, site_name: string, location: string) => {
    await dataService.updateSite(id, site_tag, site_name, location)
    sitesLoaded.value = false
    return loadSites(true)
  }

  /**
   * Usuwa site i odświeża listę
   */
  const removeSite = async (id: string) => {
    await dataService.removeSite(id)
    sitesLoaded.value = false
    return loadSites(true)
  }

  /**
   * Zapisuje całą listę sites (reorder) i odświeża
   */
  const saveAllSites = async (list: Site[]) => {
    await dataService.saveAllSites(list)
    sitesLoaded.value = false
    return loadSites(true)
  }

  /**
   * Usuwa konto i odświeża listę
   */
  const removeAccount = async (id: string) => {
    await dataService.removeAccount(id)
    // Wymuś przeładowanie kont
    accountsLoaded.value = false
    return loadAccounts(true)
  }

  /**
   * Synchronizuje urządzenie
   */
  const syncDevice = async (deviceId: string) => {
    // Read optional per-device timeout from general settings (seconds)
    let timeoutMs = 120000
    try {
      const raw = localStorage.getItem('noc-it:general-settings')
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed && parsed.deviceRequestTimeout) {
          timeoutMs = Number(parsed.deviceRequestTimeout) * 1000
        }
      }
    } catch (e) {
      // ignore and use default
    }

    const result = await dataService.syncDevice(deviceId, timeoutMs)
    // Wymuś przeładowanie urządzeń po synchronizacji
    devicesLoaded.value = false
    await loadDevices(true)
    return result
  }

  /**
   * Przełącza tunel
   */
  const toggleTunnel = async () => {
    const result = await dataService.toggleTunnel()
    tunnelStatus.value = result
    tunnelLoaded.value = true
    return result
  }

  /**
   * Zapisuje konfigurację tunelu
   */
  const saveTunnel = async (tunnelData: any) => {
    await dataService.saveTunnel(tunnelData)
    // Wymuś przeładowanie statusu tunelu
    tunnelLoaded.value = false
    return loadTunnelStatus(true)
  }

  /**
   * Wymusza odświeżenie danych (omija cache)
   */
  const forceRefresh = async (dataType: 'devices' | 'accounts' | 'tunnel' | 'sites') => {
    switch (dataType) {
      case 'devices':
        devicesLoaded.value = false
        return loadDevices(true)
      case 'accounts':
        accountsLoaded.value = false
        return loadAccounts(true)
      case 'tunnel':
        tunnelLoaded.value = false
        return loadTunnelStatus(true)
      case 'sites':
        sitesLoaded.value = false
        return loadSites(true)
    }
  }

  /**
   * Pobiera statystyki cache
   */
  const getCacheStats = () => {
    return dataService.getCacheStats()
  }

  /**
   * Czyści cache
   */
  const clearCache = () => {
    dataService.clearCache()
    // Resetuj stany załadowania
    devicesLoaded.value = false
    accountsLoaded.value = false
    tunnelLoaded.value = false
  }

  /**
   * Znajduje konto po ID
   */
  const getAccountById = (id: string) => {
    return accounts.value.find(acc => acc.id === id)
  }

  /**
   * Znajduje nazwę konta po ID
   */
  const getAccountName = (id: string) => {
    const account = getAccountById(id)
    return account ? account.name : ''
  }

  return {
    // Stan
    devices,
    accounts,
    sites,
    tunnelStatus,
    
    // Stany ładowania
    devicesLoading,
    accountsLoading,
    sitesLoading,
    tunnelLoading,
    
    // Stany załadowania
    devicesLoaded,
    accountsLoaded,
    sitesLoaded,
    tunnelLoaded,
    
    // Funkcje ładowania
    loadDevices,
    loadAccounts,
    loadSites,
    loadTunnelStatus,
    
    // Funkcje modyfikacji
    addDevice,
    removeDevice,
    removeAllErrorDevices,
    removeAllUnsyncDevices,
    addAccount,
    removeAccount,
    addSite,
    updateSite,
    removeSite,
    syncDevice,
    toggleTunnel,
    saveTunnel,
    
    // Funkcje pomocnicze
    forceRefresh,
    getCacheStats,
    clearCache,
    getAccountById,
    getAccountName
  }
}

export default useData