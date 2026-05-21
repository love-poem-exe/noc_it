<template>
    <div class="cmts-modem-reset">
        <div class="header">
            <h1>CMTS Modem Reset</h1>
            <div class="import-section">
                <input
                    type="file"
                    ref="fileInput"
                    accept=".xlsx"
                    style="display: none"
                    @change="handleFileImport"
                />
                <button v-if="!tableData.length" class="import-button" @click="triggerFileInput">
                    Importuj plik XLSX
                </button>
                <button
                    v-if="tableData.length"
                    class="export-button action-button"
                    @click="exportToXlsx"
                    :disabled="isExporting"
                    title="Eksportuj widoczne dane do XLSX"
                >
                    {{ isExporting ? 'Eksport...' : 'Exportuj XLSX' }}
                </button>
                <button
                    v-if="tableData.length"
                    class="action-button reset-button"
                    @click="resetModems"
                    :disabled="isResetting"
                >
                    {{ isResetting ? 'Resetowanie...' : 'Resetuj Modemy z Listy' }}
                </button>
                <button
                    v-if="tableData.length"
                    class="action-button status-button"
                    @click="readStatuses"
                    :disabled="isReadingStatuses"
                >
                    {{ isReadingStatuses ? 'Odczytywanie...' : 'Odczytaj Statusy' }}
                </button>
                <template v-if="tableData.length">
                    <button
                        v-if="hasMissingDevices"
                        class="add-missing-button action-button"
                        @click="addMissingDevices"
                        :disabled="isAddingDevices"
                        title="Dodaj brakujące CMTS"
                    >
                        {{ isAddingDevices ? 'Dodawanie...' : 'Dodaj brakujące urządzenia' }}
                    </button>

                    <button
                        v-else-if="unsyncedCount > 0"
                        class="add-missing-button action-button"
                        @click="syncUnsyncedDevices"
                        :disabled="isSyncingMissing"
                        title="Synchronizuj urządzenia ze statusem UNSYNC"
                    >
                        {{ isSyncingMissing ? 'Synchronizacja...' : `Synchronizuj brakujące urządzenia (${unsyncedCount})` }}
                    </button>
                </template>
            </div>
        </div>

        <div v-if="tableData.length" class="summary">
            Wczytano <strong>{{ tableData.length }}</strong> rekordów
            | Unikalne CMTS: <strong>{{ uniqueCmtsCount }}</strong>
            | Unikalne MAC: <strong>{{ uniqueMacCount }}</strong>
        </div>

        <div v-if="tableData.length" class="table-container">
            <table>
                <thead>
                    <tr>
                        <th class="col-index">#</th>
                        <th class="col-cmts">CMTS_ID</th>
                        <th class="col-mac">CM_MAC</th>
                        <th class="col-status">Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, index) in tableData" :key="index">
                        <td class="col-index">{{ index + 1 }}</td>
                        <td class="col-cmts" :class="{
                            'cmts-synced': cmtsState(row.CMTS_ID) === 'synced',
                            'cmts-unsynced': cmtsState(row.CMTS_ID) === 'unsync',
                            'cmts-not-synced': cmtsState(row.CMTS_ID) === 'missing'
                        }">{{ row.CMTS_ID }}</td>
                        <td class="col-mac">{{ row.CM_MAC }}</td>
                        <td class="col-status" :class="statusClass(row.status)">{{ row.status || '—' }}</td>
                    </tr>
                </tbody>
            </table>
                        
        </div>

                <!-- Progress overlay for batch sync (hidden when adding devices from Modules view) -->
                <div v-if="showProgress" class="progress-container progress-overlay">
                    <div class="progress-header">
                        <span class="progress-status">{{ formattedElapsed || 'Trwa synchronizacja...' }}</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
                    </div>
                </div>

        <div v-else-if="fileSelected" class="loading">
            Wczytywanie danych...
        </div>
        <div v-else class="no-data">
            Wybierz plik XLSX z danymi modemów do resetu
        </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { requestJson } from '../../services/ApiClient'
import useData from '../../composables/useData'
import { dataService } from '../../services/DataService'
import { useSyncBatch } from '../../composables/useSyncBatch'

const CACHE_KEY_TABLE = 'cmts_modem_reset_tableData'

const fileInput = ref(null)
const tableData = ref([])
const fileSelected = ref(false)
const fileName = ref('')
const isResetting = ref(false)
const isReadingStatuses = ref(false)
const isAddingDevices = ref(false)
const isRefreshing = ref(false)
const isExporting = ref(false)

// use shared data composable and sync batch helper
const { addDevice, syncDevice, loadDevices, devices: cachedDevices, devicesLoading } = useData()
const { syncProgress, syncTotal, elapsed, progressPercent, formattedElapsed, runBatch, resetProgress } = useSyncBatch()

// Show progress overlay only when a batch is running and NOT while we're in the "adding devices" flow
const showProgress = computed(() => {
    return !isAddingDevices.value && progressPercent.value > 0
})

// Zapisuj i wczytuj tableData z pamięci podręcznej
watch(tableData, val => localStorage.setItem(CACHE_KEY_TABLE, JSON.stringify(val)), { deep: true })

// Try to ensure cached devices are loaded; if API fails, try local paths
onMounted(async () => {
    try {
        const saved = localStorage.getItem(CACHE_KEY_TABLE)
        if (saved) tableData.value = JSON.parse(saved)
    } catch (e) {
        console.warn('CMTS Modem Reset: błąd wczytywania cache:', e)
    }
    try {
        await loadDevices(true)
    } catch (err) {
        const paths = [
            '../../data/devices.json',
            '../data/devices.json',
            './data/devices.json',
            '/src/data/devices.json'
        ]
        for (const path of paths) {
            try {
                const res = await fetch(path)
                if (res.ok) {
                    cachedDevices.value = await res.json()
                    break
                }
            } catch (e) {
                // try next
            }
        }
    }
})

// Helpers
function extractCmts(value) {
    if (!value && value !== 0) return ''
    return value.toString().split(',')[0].trim()
}

function isCmtsSynced(cmtsId) {
    if (!cmtsId || !cachedDevices.value?.length) return false
    const norm = cmtsId.toString().trim().toLowerCase()
    return cachedDevices.value.some(
        d => d.hostname?.toString().trim().toLowerCase() === norm && d.status?.toString().trim().toUpperCase() === 'SYNCED'
    )
}

function cmtsState(cmtsId) {
    if (!cmtsId || !cachedDevices.value?.length) return 'missing'
    const norm = cmtsId.toString().trim().toLowerCase()
    const found = cachedDevices.value.find(d => d.hostname?.toString().trim().toLowerCase() === norm)
    if (!found) return 'missing'
    const st = (found.status || '').toString().trim().toUpperCase()
    return st === 'SYNCED' ? 'synced' : 'unsync'
}

const missingCmts = computed(() => {
    const uniqueCmts = Array.from(new Set(tableData.value.map(r => (r.CMTS_ID || '').toString().trim().toLowerCase()).filter(Boolean)))
    return uniqueCmts.filter(c => !cachedDevices.value.some(d => d.hostname?.toString().trim().toLowerCase() === c))
})

const hasMissingDevices = computed(() => missingCmts.value.length > 0)

// Core sync that mimics Devices.vue behavior: set SYNCING, call syncDevice, mark ERROR on failure
const syncDeviceCore = async (id) => {
    const idx = cachedDevices.value.findIndex(d => d.id === id)
    if (idx !== -1) {
        cachedDevices.value[idx] = { ...cachedDevices.value[idx], status: 'SYNCING' }
        cachedDevices.value = [...cachedDevices.value]
    }
    try {
        await syncDevice(id)
    } catch (err) {
        console.error('[syncDeviceCore] error', err)
        const i2 = cachedDevices.value.findIndex(d => d.id === id)
        if (i2 !== -1) {
            cachedDevices.value[i2] = { ...cachedDevices.value[i2], status: 'ERROR' }
            cachedDevices.value = [...cachedDevices.value]
        }
    }
}

const isSyncingMissing = ref(false)

const unsyncedCmts = computed(() => {
    const uniqueCmts = Array.from(new Set(tableData.value.map(r => (r.CMTS_ID || '').toString().trim().toLowerCase()).filter(Boolean)))
    return uniqueCmts.filter(c => {
        const found = cachedDevices.value?.find(d => d.hostname?.toString().trim().toLowerCase() === c)
        return found && (found.status?.toString().trim().toUpperCase() !== 'SYNCED')
    })
})

const unsyncedCount = computed(() => unsyncedCmts.value.length)

const syncUnsyncedDevices = async () => {
    if (unsyncedCount.value === 0) return
    isSyncingMissing.value = true
    const toSync = []
    const debugFound = []
    for (const hostname of unsyncedCmts.value) {
        const found = cachedDevices.value.find(d => d.hostname?.toString().trim().toLowerCase() === hostname)
        debugFound.push({ hostname, id: found?.id, status: found?.status })
        if (found && found.id) toSync.push({ id: found.id })
    }
    console.log('[CMTS Modem Reset] unsynced hostnames:', unsyncedCmts.value)
    console.log('[CMTS Modem Reset] mapped devices:', debugFound)
    try {
        if (toSync.length === 0) {
            alert('Brak urządzeń do synchronizacji.')
            return
        }

        // Use server-side batch add+sync to avoid client-side per-device reloads
        try {
            const res = await dataService.addAndSyncDevices(unsyncedCmts.value)
            console.log('[CMTS Modem Reset] backend batch addAndSyncDevices result:', res)
            await refreshTable()
            if (res && res.completed !== undefined) {
                if (res.completed === 0) {
                    alert('Brak zsynchronizowanych urządzeń. Sprawdź logi serwera.')
                } else {
                    alert(`Zsynchronizowano ${res.completed}/${res.requested} urządzeń.`)
                }
            } else if (res && res.ok) {
                alert('Zlecono synchronizację urządzeń na serwerze.')
            } else {
                alert('Operacja synchronizacji nie powiodła się. Sprawdź logi serwera.')
            }
        } catch (err) {
            console.error('[CMTS Modem Reset] addAndSyncDevices failed', err)
            alert('Błąd podczas synchronizacji. Sprawdź konsolę.')
        }
    } finally {
        isSyncingMissing.value = false
        resetProgress()
    }
}

const addMissingDevices = async () => {
    if (!hasMissingDevices.value) return
    isAddingDevices.value = true
    const toAdd = missingCmts.value.slice()
    const added = []

    try {
        // Send all hostnames in a single request to backend batch endpoint
        try {
            const res = await dataService.addAndSyncDevices(toAdd)
            // refresh table exactly as clicking "Odśwież tabelę"
            await refreshTable()
            if (res && res.completed !== undefined) {
                alert(`Zakończono proces: ${res.completed}/${res.requested} zsynchronizowanych.`)
            } else if (res && res.ok) {
                alert('Dodano urządzenia i wysłano do synchronizacji.')
            } else {
                alert('Nie dodano żadnych urządzeń.')
            }
        } catch (err) {
            console.error('[addMissingDevices] batch addAndSyncDevices failed', err)
            alert('Operacja nie powiodła się. Sprawdź logi serwera.')
        }
    } finally {
        // pause so UI shows completion
        await new Promise(r => setTimeout(r, 300))
        isAddingDevices.value = false
        resetProgress()
    }
}

const triggerFileInput = () => fileInput.value.click()

const refreshTable = async () => {
    isRefreshing.value = true
    try {
        await loadDevices(true)
        // update statuses shown in table according to refreshed devices cache
        tableData.value = tableData.value.map(r => ({ ...r, status: isCmtsSynced(r.CMTS_ID) ? 'ok' : r.status }))
    } catch (err) {
        console.error('[CMTS Modem Reset] refreshTable failed', err)
        alert('Błąd podczas odświeżania. Sprawdź logi.')
    } finally {
        isRefreshing.value = false
    }
}

const uniqueCmtsCount = computed(() => new Set(tableData.value.map(r => r.CMTS_ID)).size)
const uniqueMacCount = computed(() => new Set(tableData.value.map(r => r.CM_MAC)).size)

function statusClass(status) {
    if (!status) return ''
    const s = status.toLowerCase()
    if (s.startsWith('w-online') || s.startsWith('p-online') || s.startsWith('online')) return 'status-ok'
    if (s === 'ok' || s === 'reset' || s === 'success') return 'status-ok'
    if (s.startsWith('offline') || s === 'error' || s === 'fail' || s === 'brak urządzenia') return 'status-error'
    if (s.startsWith('init') || s.startsWith('reject') || s.startsWith('resetting')) return 'status-pending'
    if (s === 'pending' || s === 'waiting' || s === 'in-progress' || s === 'syncing') return 'status-pending'
    return ''
}

const resetModems = async () => {
    isResetting.value = true
    try {
        // Mark all as pending immediately
        tableData.value = tableData.value.map(row => ({ ...row, status: 'pending' }))

        // Group row indices by CMTS hostname
        const hostnameToEntries = new Map()
        for (let i = 0; i < tableData.value.length; i++) {
            const row = tableData.value[i]
            const hostname = row.CMTS_ID?.toString().trim().toLowerCase()
            if (!hostname) continue
            if (!hostnameToEntries.has(hostname)) hostnameToEntries.set(hostname, [])
            hostnameToEntries.get(hostname).push({ row, idx: i })
        }

        // Build hostname → deviceId map from cachedDevices
        const deviceMap = new Map()
        for (const hostname of hostnameToEntries.keys()) {
            const device = cachedDevices.value?.find(d => d.hostname?.toString().trim().toLowerCase() === hostname)
            if (device?.id) deviceMap.set(hostname, device.id)
        }

        // Read concurrency from localStorage
        let concurrency = 5
        try {
            const raw = localStorage.getItem('noc-it:general-settings')
            if (raw) {
                const parsed = JSON.parse(raw)
                if (parsed?.devicesConcurrency) concurrency = Math.max(1, Number(parsed.devicesConcurrency) || 5)
            }
        } catch (e) { /* ignore */ }

        const rows = [...tableData.value]
        const hostnames = [...hostnameToEntries.keys()]

        // For each CMTS, send a combined set of clear commands
        for (let i = 0; i < hostnames.length; i += concurrency) {
            const chunk = hostnames.slice(i, i + concurrency)
            await Promise.all(chunk.map(async (hostname) => {
                const deviceId = deviceMap.get(hostname)
                const entries = hostnameToEntries.get(hostname)

                if (!deviceId) {
                    for (const { idx } of entries) rows[idx] = { ...rows[idx], status: 'brak urządzenia' }
                    return
                }

                // Build combined clear commands for all MACs on this CMTS
                const command = entries
                    .map(({ row }) => `clear cable modem ${macToCisco(row.CM_MAC)} reset`)
                    .join('\n')

                try {
                    const params = new URLSearchParams({ device_id: deviceId, command })
                    const raw = await requestJson(`/api/devices/command?${params}`, { timeoutMs: 120000 })
                    const res = (typeof raw === 'string') ? JSON.parse(raw) : raw
                    const output = res?.output || ''

                    // Try to extract modem status lines from returned output (some devices echo status)
                    const macStatusMap = parseMacStatusMap(output)

                    for (const { row, idx } of entries) {
                        const ciscoMacLower = macToCisco(row.CM_MAC).toLowerCase()
                        const status = macStatusMap.get(ciscoMacLower)
                        if (status) {
                            rows[idx] = { ...rows[idx], status }
                        } else if (res?.error) {
                            rows[idx] = { ...rows[idx], status: 'error' }
                            console.warn(`[resetModems] ${hostname}:`, res.error)
                        } else {
                            // If no explicit status, mark as reset-requested
                            rows[idx] = { ...rows[idx], status: 'reset' }
                        }
                    }
                } catch (err) {
                    for (const { idx } of entries) rows[idx] = { ...rows[idx], status: 'error' }
                    console.error(`[resetModems] ${hostname}:`, err)
                }
            }))

            // Progressive update
            tableData.value = [...rows]
        }

    } finally {
        isResetting.value = false
    }
}

const exportToXlsx = async () => {
    if (!tableData.value || tableData.value.length === 0) return
    isExporting.value = true
    try {
        const XLSX = await import('xlsx')
        // Prepare rows: include index, CMTS_ID, CM_MAC, status and any other fields present
        const rows = tableData.value.map((r, i) => ({
            '#': i + 1,
            CMTS_ID: r.CMTS_ID ?? '',
            CM_MAC: r.CM_MAC ?? '',
            Status: r.status ?? ''
        }))

        const ws = XLSX.utils.json_to_sheet(rows)
        const wb = XLSX.utils.book_new()
        XLSX.utils.book_append_sheet(wb, ws, 'Modemy')

        const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
        const filename = `cmts_modem_reset_${ts}.xlsx`
        XLSX.writeFile(wb, filename)
    } catch (err) {
        console.error('[Export XLSX] error', err)
        alert('Błąd podczas eksportu. Sprawdź konsolę.')
    } finally {
        isExporting.value = false
    }
}

// Convert flat hex MAC (5C7B5C47BBE4) to Cisco dot notation (5C7B.5C47.BBE4)
function macToCisco(mac) {
    const clean = (mac || '').replace(/[^0-9a-fA-F]/g, '')
    if (clean.length !== 12) return mac
    return `${clean.slice(0, 4)}.${clean.slice(4, 8)}.${clean.slice(8, 12)}`
}

// Strip ANSI/VT100 escape sequences and normalize line endings
function cleanOutput(output) {
    if (!output) return ''
    // Remove ANSI escape sequences (ESC + [ + ... + letter)
     
    return output.replace(/\x1b\[[0-9;]*[A-Za-z]/g, '').replace(/\r/g, '')
}

// Build mac(lowercase) → status map from combined "show cable modem" output
function parseMacStatusMap(output) {
    const map = new Map()
    const cleaned = cleanOutput(output)
    // Matches known Cisco cable modem MAC states anywhere in the line
    const STATE_RE = /\b((?:w-online|p-online|online|offline|resetting|init|reject)(?:\([a-z0-9]*\))?)/i
    for (const line of cleaned.split('\n')) {
        const trimmed = line.trim()
        if (/^[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}\s/i.test(trimmed)) {
            const mac = trimmed.split(/\s+/)[0].toLowerCase()
            const m = STATE_RE.exec(trimmed)
            if (m) map.set(mac, m[1])
        }
    }
    return map
}

const readStatuses = async () => {
    isReadingStatuses.value = true
    try {
        // Group row indices by CMTS hostname
        const hostnameToEntries = new Map()
        for (let i = 0; i < tableData.value.length; i++) {
            const row = tableData.value[i]
            const hostname = row.CMTS_ID?.toString().trim().toLowerCase()
            if (!hostname) continue
            if (!hostnameToEntries.has(hostname)) hostnameToEntries.set(hostname, [])
            hostnameToEntries.get(hostname).push({ row, idx: i })
        }

        // Build hostname → deviceId map
        const deviceMap = new Map()
        for (const hostname of hostnameToEntries.keys()) {
            const device = cachedDevices.value?.find(d => d.hostname?.toString().trim().toLowerCase() === hostname)
            if (device?.id) deviceMap.set(hostname, device.id)
        }

        // Read concurrency from localStorage (number of parallel CMTS connections)
        let concurrency = 5
        try {
            const raw = localStorage.getItem('noc-it:general-settings')
            if (raw) {
                const parsed = JSON.parse(raw)
                if (parsed?.devicesConcurrency) concurrency = Math.max(1, Number(parsed.devicesConcurrency) || 5)
            }
        } catch (e) { /* ignore */ }

        const rows = [...tableData.value]
        const hostnames = [...hostnameToEntries.keys()]

        // Process CMTS devices in parallel chunks
        for (let i = 0; i < hostnames.length; i += concurrency) {
            const chunk = hostnames.slice(i, i + concurrency)
            await Promise.all(chunk.map(async (hostname) => {
                const deviceId = deviceMap.get(hostname)
                const entries = hostnameToEntries.get(hostname)

                if (!deviceId) {
                    for (const { idx } of entries) rows[idx] = { ...rows[idx], status: 'brak urządzenia' }
                    return
                }

                // One combined command with all MACs for this CMTS
                const command = entries
                    .map(({ row }) => `show cable modem ${macToCisco(row.CM_MAC)}`)
                    .join('\n')

                try {
                    const params = new URLSearchParams({ device_id: deviceId, command })
                    const raw = await requestJson(`/api/devices/command?${params}`, { timeoutMs: 120000 })
                    const res = (typeof raw === 'string') ? JSON.parse(raw) : raw
                    const output = res?.output || ''

                    // Build mac → status map from combined output (strips ANSI, normalizes \r\n)
                    const macStatusMap = parseMacStatusMap(output)

                    for (const { row, idx } of entries) {
                        const ciscoMacLower = macToCisco(row.CM_MAC).toLowerCase()
                        const status = macStatusMap.get(ciscoMacLower)
                        if (status) {
                            rows[idx] = { ...rows[idx], status }
                        } else if (res?.error) {
                            rows[idx] = { ...rows[idx], status: 'error' }
                            console.warn(`[readStatuses] ${hostname}:`, res.error)
                        } else {
                            rows[idx] = { ...rows[idx], status: 'brak danych' }
                        }
                    }
                } catch (err) {
                    for (const { idx } of entries) rows[idx] = { ...rows[idx], status: 'error' }
                    console.error(`[readStatuses] ${hostname}:`, err)
                }
            }))
            // Progressive table update after each CMTS chunk
            tableData.value = [...rows]
        }
    } finally {
        isReadingStatuses.value = false
    }
}

const handleFileImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return
    fileSelected.value = true
    try {
        const data = await readExcelFile(file)
        if (data && data.length > 0) tableData.value = data
        else {
            tableData.value = []
            alert('Plik nie zawiera danych lub format jest nieprawidłowy.')
        }
        event.target.value = ''
    } catch (error) {
        console.error('Error reading file:', error)
        alert('Błąd podczas wczytywania pliku. Sprawdź czy format pliku jest prawidłowy.')
    } finally {
        fileSelected.value = false
    }
}

const readExcelFile = async (file) => {
    const XLSX = await import('xlsx')
    return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
        try {
            const data = e.target.result
            const workbook = XLSX.read(data, { type: 'array' })
            const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
            const rows = XLSX.utils.sheet_to_json(firstSheet, { defval: '' })
            const result = rows.map(row => ({ CMTS_ID: extractCmts(row['CMTS_ID'] ?? ''), CM_MAC: (row['CM_MAC'] ?? '').toString().trim(), status: '' })).filter(r => r.CMTS_ID || r.CM_MAC)
            resolve(result)
        } catch (err) { reject(err) }
    }
    reader.onerror = (err) => reject(err)
    reader.readAsArrayBuffer(file)
})
}
</script>

<style scoped>
.cmts-modem-reset {
    padding: 20px;
    height: 100%;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.import-section {
    display: flex;
    align-items: center;
    gap: 12px;
}

.import-button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
}

.import-button:hover {
    background-color: #45a049;
}

.export-button {
    background-color: #2e7d32;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.2s;
}

.export-button:hover:not(:disabled) {
    background-color: #1b5e20;
}

.file-name {
    color: #888;
    font-size: 13px;
}

.summary {
    margin-bottom: 12px;
    padding: 8px 14px;
    background: #1e1e2e;
    border-radius: 4px;
    color: #ccc;
    font-size: 13px;
}

.table-container {
    height: 80%;
    overflow-y: auto;
    border: 1px solid #333;
    border-radius: 4px;
}

table {
    width: 100%;
    border-collapse: collapse;
    background-color: #1a1a2e;
}

th, td {
    padding: 10px 14px;
    text-align: left;
    border: 1px solid #333;
}

th {
    background-color: #2a2a3e;
    font-weight: bold;
    position: sticky;
    top: 0;
    z-index: 1;
    color: #ddd;
}

tr:hover {
    background-color: #2a2a40;
}

.col-index {
    width: 50px;
    text-align: center;
    color: #666;
}

.col-cmts {
    min-width: 180px;
}

.col-mac {
    min-width: 150px;
    font-family: monospace;
}

.cmts-synced {
    color: #4caf50 !important;
    font-weight: bold;
}

.cmts-not-synced {
    color: #f44336 !important;
    font-weight: bold;
}

.cmts-unsynced {
    color: #f59e0b !important;
    font-weight: bold;
}

.col-status {
    min-width: 130px;
    text-align: center;
    font-weight: bold;
    white-space: nowrap;
}

.status-ok {
    color: #4caf50;
}

.status-error {
    color: #f44336;
}

.status-pending {
    color: #ff9800;
}

.action-button {
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
    color: white;
}

.action-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.reset-button {
    background-color: #e53935;
}

.reset-button:hover:not(:disabled) {
    background-color: #c62828;
}

.status-button {
    background-color: #1976d2;
}

.status-button:hover:not(:disabled) {
    background-color: #1565c0;
}

.add-missing-button {
    background-color: #ff9800;
}

.add-missing-button:hover:not(:disabled) {
    background-color: #fb8c00;
}

.progress-overlay {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0,0,0,0.35);
    z-index: 50;
}

.progress-container {
    width: 60%;
    max-width: 700px;
    background: #1f2937;
    padding: 16px;
    border-radius: 6px;
}

.progress-header {
    display: flex;
    justify-content: space-between;
    color: #ddd;
    margin-bottom: 8px;
}

.progress-bar-container {
    background: #111827;
    height: 12px;
    border-radius: 6px;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #4caf50, #2196f3);
    transition: width 0.25s linear;
}

.no-data {
    text-align: center;
    color: #666;
    margin-top: 40px;
    font-size: 16px;
}

.loading {
    text-align: center;
    color: #666;
    margin-top: 40px;
    font-size: 16px;
}
</style>
