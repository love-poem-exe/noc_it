<template>
    <div class="cmts-tmpfs">
        <div class="header">
            <h1>CMTS TMPFS</h1>
            <div class="text-input-section">
                <button 
                    v-if="hasMissingDevices && tableData.length > 0"
                    class="add-missing-button" 
                    @click="addMissingDevices"
                    :disabled="isAddingDevices"
                >
                    {{ isAddingDevices ? 'Dodawanie...' : 'Dodaj nieznalezione urządzenia' }}
                </button>
                <button 
                    v-if="hasUnsyncedDevices && tableData.length > 0"
                    class="sync-devices-button" 
                    @click="syncUnsyncedDevices"
                    :disabled="isSyncingDevices"
                >
                    {{ isSyncingDevices ? 'Synchronizowanie...' : 'Synchronizuj urządzenia' }}
                </button>
                <button 
                    v-if="allDevicesSynced && tableData.length > 0 && !hasAlarmsData()"
                    class="verify-alarms-button" 
                    @click="verifyAlarms"
                    :disabled="isVerifyingAlarms"
                >
                    {{ isVerifyingAlarms ? 'Weryfikowanie...' : 'Check alarms' }}
                </button>
                
                <button 
                    v-if="allDevicesSynced && tableData.length > 0 && hasAlarmsData()"
                    class="check-all-statuses-button" 
                    :class="{ 'active': isAutoCheckEnabled }"
                    @click="toggleAutoCheck"
                >
                    {{ isAutoCheckEnabled ? `Auto Check ON (${autoCheckCountdown}s)` : 'Auto Check OFF' }}
                </button>
                
                <!-- Pasek postępu weryfikacji -->
                <div v-if="isVerifyingAlarms" class="progress-container progress-overlay">
                    <div class="progress-header">
                        <span class="progress-status">{{ verificationStatus || 'Weryfikowanie urządzeń...' }}</span>
                        <span class="progress-percentage">{{ verificationProgress }}%</span>
                    </div>
                    <div class="progress-bar-container">
                        <div 
                            class="progress-bar"
                            :class="{ complete: verificationProgress >= 100 }"
                            :style="{ width: verificationProgress + '%' }"
                        ></div>
                    </div>
                    <!-- Przycisk przerwania procesu -->
                    <div class="progress-actions">
                        <button 
                            class="cancel-process-button"
                            @click="cancelVerification"
                            :disabled="verificationProgress >= 100"
                        >
                            Przerwij proces
                        </button>
                    </div>
                </div>
                
                <!-- Pasek postępu synchronizacji -->
                <div v-if="isSyncingDevices" class="progress-container progress-overlay">
                    <div class="progress-header">
                        <span class="progress-status">{{ syncStatus || 'Synchronizowanie urządzeń...' }}</span>
                        <span class="progress-percentage">{{ syncProgress }}%</span>
                    </div>
                    <div class="progress-bar-container">
                        <div 
                            class="progress-bar"
                            :class="{ complete: syncProgress >= 100 }"
                            :style="{ width: syncProgress + '%' }"
                        ></div>
                    </div>
                    <div class="progress-controls">
                        <button 
                            class="cancel-process-button"
                            @click="cancelSync"
                            :disabled="syncProgress >= 100"
                        >
                            Przerwij proces
                        </button>
                    </div>
                </div>
                
                <button 
                    v-if="!tableData.length" 
                    class="input-button" 
                    @click="showTextModal = true"
                >
                    Wprowadź dane Splunk Report
                </button>
                
                <button 
                    v-if="!tableData.length" 
                    class="add-all-cmts-button" 
                    @click="addAllCmtsDevices"
                    :disabled="isAddingAllCmts"
                >
                    {{ isAddingAllCmts ? 'Dodawanie...' : 'Dodaj wszystkie CMTS' }}
                </button>
                
                <button 
                    v-else 
                    class="clear-button" 
                    @click="clearTableData"
                >
                    Wyczyść
                </button>
                
            </div>
        </div>

        <!-- Modal z textarea -->
        <div v-if="showTextModal" class="modal-overlay" @click="closeModal">
            <div class="modal-content" @click.stop>
                <div class="modal-header">
                    <h3>Wprowadź dane Splunk Report</h3>
                    <button class="close-button" @click="closeModal">×</button>
                </div>
                <div class="modal-body">
                    <textarea
                        v-model="textInput"
                        placeholder="Wklej tutaj dane z raportu Splunk..."
                        rows="20"
                        cols="80"
                    ></textarea>
                </div>
                <div class="modal-footer">
                    <button class="cancel-button" @click="closeModal">Anuluj</button>
                    <button class="confirm-button" @click="processTextData">Zatwierdź</button>
                </div>
            </div>
        </div>

        <div v-if="tableData.length" class="table-container">
            <table :key="tableKey">
                <thead>
                    <tr>
                        <th>CMTS</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, index) in tableData" :key="index">
                        <td class="device-cell">
                            <span>
                                {{ row.device }}
                            </span>
                            <span 
                                class="status-icon"
                                :title="getDeviceStatus(row.device).message"
                            >
                                {{ getDeviceStatus(row.device).icon }}
                            </span>
                        </td>
                        <td class="alarms-cell" :class="{ 
                            'connection-error': row.status === 'CONNECTION_ERROR',
                            'verification-error': row.status === 'ERROR' 
                        }">
                            <!-- Status badge: show OK (green) when no alarms in time window -->
                            <div class="status-badge" :class="{
                                'status-ok': (row.alarm_count === 0 || row.alarm_count === '0') && (row.status === 'SUCCESS' || row.status === 'OK'),
                                'status-error': row.error || ['ERROR','CONNECTION_ERROR','FAILED'].includes((row.status||'').toString().toUpperCase())
                            }">
                                <span v-if="(row.alarm_count === 0 || row.alarm_count === '0') && (row.status === 'SUCCESS' || row.status === 'OK')">OK</span>
                                <span v-else-if="row.error || (['ERROR','FAILED','CONNECTION_ERROR'].includes((row.status||'').toString().toUpperCase()))">ERROR</span>
                            </div>
                            <div v-if="row.alarms && row.alarms !== '-' && !row.alarms.includes('Błąd')" class="alarms-with-buttons">
                                <div v-for="(line, lineIndex) in row.alarms.split('\n').filter(l => l.trim())" :key="lineIndex" class="alarm-line" :class="{ 'alarm-line-dismissed': dismissedCards[`${row.device}-${getSipCardFromLine(line)}`] }">
                                    <div v-if="getSipCardFromLine(line)" class="card-buttons">
                                        <button
                                            class="dismiss-button"
                                            @click="toggleDismissCard(row.device, getSipCardFromLine(line))"
                                            :title="dismissedCards[`${row.device}-${getSipCardFromLine(line)}`] ? `Przywróć ${getSipCardFromLine(line)}` : `Wyszarz ${getSipCardFromLine(line)}`"
                                        >
                                            {{ dismissedCards[`${row.device}-${getSipCardFromLine(line)}`] ? '↩' : '✕' }}
                                        </button>
                                        <template v-if="isCardRecentlyRestarted(row.device, getSipCardFromLine(line)) && cardRestartStatus[`${row.device}-${getSipCardFromLine(line)}`] === 'RESTARTED'">
                                            <button 
                                                class="refresh-button"
                                                @click="showPlatformForSip(row.device, getSipCardFromLine(line))"
                                                :disabled="isPlatformLoading[`${row.device}-${getSipCardFromLine(line)}`]"
                                                :title="`Odśwież ${getSipCardFromLine(line)}`"
                                            >
                                                {{ isPlatformLoading[`${row.device}-${getSipCardFromLine(line)}`] ? '⏳' : '🔄' }}
                                            </button>
                                            <span class="restart-status restart-status-success">KARTA ZRESTARTOWANA</span>
                                        </template>
                                        <template v-else>
                                            <button 
                                                class="refresh-button"
                                                @click="showPlatformForSip(row.device, getSipCardFromLine(line))"
                                                :disabled="isPlatformLoading[`${row.device}-${getSipCardFromLine(line)}`]"
                                                :title="`Odśwież ${getSipCardFromLine(line)}`"
                                            >
                                                {{ isPlatformLoading[`${row.device}-${getSipCardFromLine(line)}`] ? '⏳' : '🔄' }}
                                            </button>
                                            <button 
                                                class="restart-button"
                                                @click="restartSipCard(row.device, getSipCardFromLine(line))"
                                                :disabled="isRestartLoading[`${row.device}-${getSipCardFromLine(line)}`]"
                                                :title="`Restartuj ${getSipCardFromLine(line)}`"
                                            >
                                                {{ isRestartLoading[`${row.device}-${getSipCardFromLine(line)}`] ? '⏳' : '🔃' }}
                                            </button>
                                            <button 
                                                class="check-restart-button"
                                                @click="checkRestartLogsForCard(row.device, getSipCardFromLine(line))"
                                                :disabled="isCheckingRestartLogsForCard[`${row.device}-${getSipCardFromLine(line)}`]"
                                                :title="`Sprawdź logi restartów dla ${getSipCardFromLine(line)}`"
                                            >
                                                {{ isCheckingRestartLogsForCard[`${row.device}-${getSipCardFromLine(line)}`] ? '⏳' : '📋' }}
                                                <span 
                                                    v-if="cardRestartStatus[`${row.device}-${getSipCardFromLine(line)}`]"
                                                    class="restart-status"
                                                    :class="cardRestartStatus[`${row.device}-${getSipCardFromLine(line)}`] === 'RESTARTED' ? 'restart-status-success' : 'restart-status-fail'"
                                                >
                                                    {{ cardRestartStatus[`${row.device}-${getSipCardFromLine(line)}`] === 'RESTARTED' ? 'KARTA ZRESTARTOWANA' : 'KARTA NIEZRESTARTOWANA' }}
                                                </span>
                                            </button>
                                            <div 
                                                v-if="restartLogsMessages[`${row.device}-${getSipCardFromLine(line)}`]"
                                                class="restart-log-message"
                                            >
                                                {{ restartLogsMessages[`${row.device}-${getSipCardFromLine(line)}`] }}
                                            </div>
                                        </template>
                                    </div>
                                    <span class="alarm-text">{{ line.trim() }}</span>
                                </div>
                            </div>
                            <span v-else>{{ (row.alarms && row.alarms !== '-') ? row.alarms : '' }}</span>
                        </td>
                        <td class="actions-cell">
                            <div v-if="getDeviceStatus(row.device).icon === '✅'">
                                <!-- Restart-related actions only when alarms exist -->
                                <div v-if="row.alarms && row.alarms !== '-'" class="restart-actions">
                                    <button 
                                        class="restart-status-button"
                                        @click="checkRestartLogs(row.device)"
                                        :disabled="isCheckingRestartLogs[row.device]"
                                        :title="'Sprawdź logi restartów (OIR events)'"
                                    >
                                        {{ isCheckingRestartLogs[row.device] ? '⏳' : '🔄' }} Check Restart
                                    </button>
                                    <div 
                                        v-if="restartLogsMessages[row.device]"
                                        class="restart-log-message"
                                    >
                                        {{ restartLogsMessages[row.device] }}
                                    </div>
                                </div>

                                <!-- Główny przycisk Check Status (pokazuj zawsze dla zsynchronizowanych urządzeń) -->
                                <button 
                                    class="platform-button"
                                    @click="showPlatform(row.device)"
                                    :disabled="isPlatformLoading[row.device]"
                                >
                                    {{ isPlatformLoading[row.device] ? 'Ładowanie...' : 'Check Status' }}
                                </button>
                            </div>
                            <span v-else class="no-action">-</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div v-else-if="processing" class="loading">
            Przetwarzanie danych...
        </div>
        <div v-else class="no-data">
            Kliknij "Wprowadź dane Splunk Report" aby rozpocząć
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { requestJson } from '../../services/ApiClient'
import { waitForJob } from '../../services/JobService'
import { dataService } from '../../services/DataService'
import { useCmtsTmpfsStore } from '../../stores/cmtsTmpfsStore'

const runScript = async ({ script, method, payload, timeoutMs = 120000 }) => {
    const result = await requestJson('/api/scripts/run', {
        method: 'POST',
        body: { script, method, payload },
        timeoutMs
    })
    return typeof result === 'string' ? result : JSON.stringify(result)
}

const runScriptAsync = async ({ script, method, payload, timeoutMs }) => {
    const options = {
        method: 'POST',
        body: { script, method, payload }
    }

    if (timeoutMs && timeoutMs > 0) {
        options.timeoutMs = timeoutMs
    }

    const response = await requestJson('/api/scripts/async', options)

    const waitTimeout = timeoutMs && timeoutMs > 0 ? timeoutMs : 10 * 60 * 1000

    if (response?.jobId) {
        ;(async () => {
            try {
                const jobStatus = await waitForJob(response.jobId, waitTimeout)
                const payloadToEmit = jobStatus?.result?.result ?? jobStatus?.result ?? jobStatus
                emitScriptEvent('script-finished', payloadToEmit)
            } catch (error) {
                emitScriptEvent('script-error', {
                    jobId: response.jobId,
                    script,
                    method,
                    message: error?.message || 'Unknown async script error'
                })
            }
        })()
    } else if (response) {
        emitScriptEvent('script-finished', response)
    }

    return response
}



const scriptEventTarget = typeof window !== 'undefined' ? window : null

const emitScriptEvent = (eventName, payload) => {
    if (!scriptEventTarget) return
    const detail = typeof payload === 'string' ? payload : JSON.stringify(payload)
    scriptEventTarget.dispatchEvent(new CustomEvent(`cmts_tmpfs:${eventName}`, { detail }))
}

const listen = async (eventName, handler) => {
    if (!scriptEventTarget) {
        console.warn('[CMTS_TMPFS] Event listener not available in this environment')
        return () => {}
    }

    const wrappedHandler = (event) => {
        handler({ payload: event.detail })
    }

    scriptEventTarget.addEventListener(`cmts_tmpfs:${eventName}`, wrappedHandler)

    return () => {
        scriptEventTarget.removeEventListener(`cmts_tmpfs:${eventName}`, wrappedHandler)
    }
}

const cmtsTmpfsStore = useCmtsTmpfsStore()
const devices = computed(() => cmtsTmpfsStore.devices)
const cmtsTmpfsSettings = ref({ hoursBack: 12, restartLookback: 12 })
// settings saved via Modules Settings UI

const showTextModal = ref(false)
const textInput = ref('')
const tableData = ref([])
const processing = ref(false)
const hasMissingDevices = ref(false)
const isAddingDevices = ref(false)
const hasUnsyncedDevices = ref(false)
const isSyncingDevices = ref(false)
const isSyncingScript = ref(false) // ⭐ NOWE: Mutex dla verify_alarms - czekaj gdy sync się odbywa
const allDevicesSynced = ref(false)
const isVerifyingAlarms = ref(false)
const isAutoCheckEnabled = ref(false) // Automatyczne sprawdzanie statusów włączone/wyłączone
const autoCheckInterval = ref(30) // Interwał w sekundach (domyślnie 30s)
const autoCheckTimer = ref(null) // Timer dla automatycznego sprawdzania
const autoCheckCountdown = ref(30) // Odliczanie do kolejnego auto-check
const autoCheckCountdownTimer = ref(null)
const tableRefreshTimer = ref(null) // Timer dla odświeżania tabeli z pliku (wyłączony dla auto-check)
const isAutoCheckRunning = ref(false) // Mutex, by nie nakladać cykli auto-check
const tableKey = ref(0) // Klucz do wymuszenia ponownego renderowania tabeli
const isPlatformLoading = ref({}) // Śledzenie statusu ładowania dla każdego urządzenia
const isRestartLoading = ref({}) // Śledzenie statusu restartowania dla każdej karty SIP
const verificationProgress = ref(0) // Postęp weryfikacji (0-100)
const verificationStatus = ref('') // Status weryfikacji
const isVerificationCancelled = ref(false) // Flaga przerwania weryfikacji
const isAddingAllCmts = ref(false) // Status dodawania wszystkich CMTS
const syncProgress = ref(0) // Postęp synchronizacji (0-100)
const syncStatus = ref('') // Status synchronizacji
const isSyncCancelled = ref(false) // Flaga przerwania synchronizacji
const isCheckingRestartLogs = ref({}) // Status sprawdzania logów restartów dla każdego urządzenia
const isCheckingRestartLogsForCard = ref({}) // Status sprawdzania logów restartów dla konkretnej karty
const cardRestartStatus = ref({}) // Status restart dla każdej karty (RESTARTED/NOT_RESTARTED/null)
const restartLogsMessages = ref({}) // Informacje o błędach podczas sprawdzania logów
const cardRestartTimestamps = ref({}) // ISO timestamps of last restart per `${device}-${SIP/x}`
const dismissedCards = ref({}) // Wyszarzone (odrzucone) karty SIP - klucz: `${device}-${sipCard}`
let autoCheckFinishedListener = null
let autoCheckErrorListener = null

// Toggle wyszarzenia karty SIP
function toggleDismissCard(deviceName, sipCard) {
    const key = `${deviceName}-${sipCard}`
    dismissedCards.value[key] = !dismissedCards.value[key]
    console.log(`[DISMISS] ${sipCard} on ${deviceName}: ${dismissedCards.value[key] ? 'dismissed' : 'restored'}`)
}

// Funkcja zapisywania danych tabeli do pliku temp
const saveTableDataToFile = async () => {
    try {
        console.log('[SAVE DATA] Saving table data to temp file...')
        
        const result = await runScript({
            script: 'modules-cmts_tmpfs_controller',
            method: 'save_table_data',
            payload: {
                timestamp: new Date().toISOString(),
                tableData: tableData.value
            }
        })
        
        console.log('[SAVE DATA] Table data saved successfully:', result)
        
    } catch (error) {
        console.error('[SAVE DATA] Error saving table data:', error)
    }
}

// Funkcja czyszczenia danych tabeli i pliku temp
const clearTableData = async () => {
    try {
        console.log('[CLEAR DATA] Clearing table data and temp file...')
        
        // Zatrzymaj auto-sprawdzanie przy czyszczeniu tabeli
        if (isAutoCheckEnabled.value) {
            stopAutoCheck()
        }
        
        const result = await runScript({
            script: 'modules-cmts_tmpfs_controller',
            method: 'clear_table_data',
            payload: {}
        })
        
        const parsed = JSON.parse(result)
        
        if (parsed.status === 'OK') {
            // Wyczyść tabelę w interfejsie
            tableData.value = []
            
            // Resetuj wszystkie statusy
            hasMissingDevices.value = false
            hasUnsyncedDevices.value = false
            allDevicesSynced.value = false
            
            // Wymuś ponowne renderowanie tabeli
            tableKey.value++
            
            console.log('[CLEAR DATA] Table data cleared successfully')
        } else {
            console.error('[CLEAR DATA] Error clearing data:', parsed.message)
        }
        
    } catch (error) {
        console.error('[CLEAR DATA] Error clearing table data:', error)
    }
}

// Funkcja dodawania wszystkich urządzeń CMTS Cisco
const addAllCmtsDevices = async () => {
    if (isAddingAllCmts.value) return
    
    isAddingAllCmts.value = true
    
    try {
        console.log('[ADD ALL CMTS] Starting to add all CMTS devices...')
        
        // Filtruj urządzenia: tylko CMTS i Cisco
        const cmtsDevices = devices.value.filter(device => 
            device.type === 'CMTS' && device.vendor === 'Cisco'
        )
        
        console.log(`[ADD ALL CMTS] Found ${cmtsDevices.length} CMTS Cisco devices`)
        
        if (cmtsDevices.length === 0) {
            console.log('[ADD ALL CMTS] No CMTS Cisco devices found in devices.json')
            return
        }
        
        // Stwórz dane tabeli z wszystkich CMTS
        const tableDataArray = cmtsDevices.map(device => ({
            device: device.hostname,
            alarms: '-' // Początkowo bez alarmów
        }))
        
        // Załaduj dane do tabeli
        tableData.value = tableDataArray
        
        console.log(`[ADD ALL CMTS] Added ${tableDataArray.length} CMTS devices to table`)
        
        // Zapisz dane do pliku temp
        await saveTableDataToFile()
        
        // Sprawdź statusy urządzeń
        checkForMissingDevices()
        checkForUnsyncedDevices()
        checkAllDevicesSynced()
        
        // Wymuś ponowne renderowanie tabeli
        tableKey.value++
        
    } catch (error) {
        console.error('[ADD ALL CMTS] Error adding all CMTS devices:', error)
    } finally {
        isAddingAllCmts.value = false
    }
}

// Funkcja wczytywania danych tabeli z pliku temp
const loadTableDataFromFile = async () => {
    try {
        console.log('[LOAD DATA] Loading table data from temp file...')
        
        const result = await runScript({
            script: 'modules-cmts_tmpfs_controller',
            method: 'load_table_data',
            payload: {}
        })
        
        const parsed = JSON.parse(result)
        
        if (parsed.status === 'OK' && parsed.data && Array.isArray(parsed.data) && parsed.data.length > 0) {
            tableData.value = parsed.data
            console.log('[LOAD DATA] Table data loaded successfully:', parsed.count, 'rows from', parsed.timestamp)
            
            // Sprawdź statusy po wczytaniu
            checkForMissingDevices()
            checkForUnsyncedDevices()
            checkAllDevicesSynced()
            
            return true
        } else if (parsed.status === 'EMPTY') {
            console.log('[LOAD DATA] Temp file exists but is empty')
            return false
        } else if (parsed.status === 'NOT_FOUND') {
            console.log('[LOAD DATA] No temp file found')
            return false
        }
        
    } catch (error) {
        console.log('[LOAD DATA] Error loading temp data:', error.message)
        return false
    }
}

// Funkcja czyszczenia przy zamknięciu
const cleanupOnExit = async () => {
    console.log('[APP EXIT] Cleaning up CMTS TMPFS data...')
    
    // Zatrzymaj auto-check
    if (isAutoCheckEnabled.value) {
        stopAutoCheck()
        console.log('[APP EXIT] Auto-check stopped')
    }
    
    // Wyczyść cały folder temp
    try {
        const result = await runScript({
            script: 'application_controller',
            method: 'cleanup_temp_folder',
            payload: {}
        })
        console.log('[APP EXIT] Temp folder cleaned:', result)
    } catch (error) {
        console.error('[APP EXIT] Error cleaning temp folder:', error)
    }
}

const loadCmtsTmpfsSettings = async () => {
    try {
        const settingsData = await requestJson('/api/modules/settings', { timeoutMs: 10000 })
        if (!settingsData) return
        const hoursBack = Number(settingsData?.cmtsTmpfs?.hoursBack)
        if (!Number.isNaN(hoursBack) && hoursBack > 0) {
            cmtsTmpfsSettings.value.hoursBack = hoursBack
        }
        const restartLookback = Number(settingsData?.cmtsTmpfs?.restartLookback)
        if (!Number.isNaN(restartLookback) && restartLookback > 0) {
            cmtsTmpfsSettings.value.restartLookback = restartLookback
        }
    } catch (error) {
        console.warn('[CMTS_TMPFS] Error loading settings:', error)
    }
}

// settings persisted via Modules Settings UI; no inline save here

const handleAutoCheckPayload = (payload) => {
    if (typeof payload !== 'string') return null
    const jsonMatch = payload.match(/\{[\s\S]*\}/)
    if (!jsonMatch) return null

    try {
        const parsed = JSON.parse(jsonMatch[0])
        if (parsed?.action !== 'auto_check_statuses') return null
        return parsed
    } catch {
        return null
    }
}

// Wczytaj devices.json przy starcie komponentu
onMounted(async () => {
    console.log('[CMTS_TMPFS] Component mounted, initializing store...')
    
    // Inicjalizuj store tylko raz - dane będą dostępne w pamięci do zamknięcia aplikacji
    await cmtsTmpfsStore.initialize()
    console.log('[CMTS_TMPFS] Store initialized, devices count:', cmtsTmpfsStore.devices.length)
    
    // 🔥 Natychmiast przeładuj devices żeby mieć świeże dane (np. jeśli usunięto urządzenie z devices.json)
    await cmtsTmpfsStore.loadDevices()
    console.log('[CMTS_TMPFS] Devices refreshed from file, count:', cmtsTmpfsStore.devices.length)
    
    // Spróbuj wczytać poprzednie dane z pliku temp
    await loadTableDataFromFile()

    // Wczytaj ustawienia modułu (hoursBack) do pamięci
    await loadCmtsTmpfsSettings()
    
    // Cleanup on browser/tab close
    const _beforeUnloadHandler = () => { cleanupOnExit() }
    window.addEventListener('beforeunload', _beforeUnloadHandler)

    try {
        if (!autoCheckFinishedListener) {
            autoCheckFinishedListener = await listen('script-finished', (event) => {
                const parsed = handleAutoCheckPayload(event.payload)
                if (!parsed) return

                if (parsed.status === 'OK' && Array.isArray(parsed.data)) {
                    tableData.value = parsed.data
                    tableKey.value++
                }

                isAutoCheckRunning.value = false
                autoCheckCountdown.value = autoCheckInterval.value
            })
        }

        if (!autoCheckErrorListener) {
            autoCheckErrorListener = await listen('script-error', (event) => {
                if (!isAutoCheckRunning.value) return
                const parsed = handleAutoCheckPayload(event.payload)
                if (parsed) {
                    console.error('[AUTO CHECK] Backend error:', parsed.message || 'Unknown error')
                } else {
                    console.error('[AUTO CHECK] Backend error:', event.payload)
                }
                isAutoCheckRunning.value = false
                autoCheckCountdown.value = autoCheckInterval.value
            })
        }
    } catch (error) {
        console.error('[CMTS_TMPFS] Error registering auto-check listeners:', error)
    }
})

const refreshDevicesList = async () => {
    try {
        console.log('[REFRESH] Refreshing devices list from store...')
        
        // Odśwież dane z store'u (dane są już wczytane przy initialize)
        await cmtsTmpfsStore.loadDevices()
        console.log(`[REFRESH] Refreshed devices, count: ${cmtsTmpfsStore.devices.length}`)
        
        // Wymuś ponowne renderowanie tabeli
        tableKey.value++
        
    } catch (error) {
        console.error('[REFRESH] Error refreshing devices:', error)
    }
}

// Funkcje pomocnicze do komunikacji z backend
const addDevice = async (deviceName) => {
    try {
        console.log(`[ADD DEVICE] Adding device: ${deviceName}`)
        
        // Używamy tego samego API co Settings Devices
        await runScript({
            script: 'settings-devices_controller',
            method: 'add_device',
            payload: { address: deviceName }
        })
        
        console.log(`[ADD DEVICE] Device ${deviceName} added successfully`)
        return { success: true }
    } catch (error) {
        console.error(`[ADD DEVICE] Error adding device ${deviceName}:`, error)
        return { success: false, error: error.message }
    }
}

const syncDevice = async (deviceName) => {
    try {
        console.log(`[SYNC DEVICE] Finding device: ${deviceName}`)
        
        // Najpierw pobierz listę urządzeń aby znaleźć ID
        const devicesDataRaw = await runScript({
            script: 'settings-devices_controller',
            method: 'get_all_devices',
            payload: {}
        })
        
        // Sprawdź czy mamy dane i sparsuj je
        if (!devicesDataRaw || (typeof devicesDataRaw === 'string' && devicesDataRaw.trim() === '')) {
            console.error(`[SYNC DEVICE] No devices data received`)
            return { success: false, error: 'No devices data available' }
        }
        
        let devicesData
        try {
            devicesData = typeof devicesDataRaw === 'string' ? JSON.parse(devicesDataRaw) : devicesDataRaw
        } catch (parseError) {
            console.error(`[SYNC DEVICE] Error parsing devices data:`, parseError)
            return { success: false, error: 'Error parsing devices data' }
        }
        
        if (!Array.isArray(devicesData)) {
            console.error(`[SYNC DEVICE] Devices data is not an array:`, typeof devicesData)
            return { success: false, error: 'Invalid devices data format' }
        }
        
        // Znajdź urządzenie po hostname
        const device = devicesData.find(d => d && d.hostname === deviceName)
        if (!device) {
            console.error(`[SYNC DEVICE] Device not found: ${deviceName}`)
            return { success: false, error: `Device not found: ${deviceName}` }
        }
        
        console.log(`[SYNC DEVICE] Found device ID: ${device.id} for ${deviceName}`)
        
        // Teraz zsynchronizuj urządzenie używając ID
        const result = await runScript({
            script: 'settings-devices_controller',
            method: 'sync_device',
            payload: { id: device.id }
        })
        
        console.log(`[SYNC DEVICE] Device ${deviceName} synchronized successfully`, result)
        return { success: true, result }
    } catch (error) {
        console.error(`[SYNC DEVICE] Error syncing device ${deviceName}:`, error)
        return { success: false, error: error.message }
    }
}

const closeModal = () => {
    showTextModal.value = false
    textInput.value = ''
}

// Sprawdź status urządzenia i zwróć informacje o stanie
function getDeviceStatus(cmtsName) {
    if (!cmtsName || !devices.value?.length) {
        return { found: false, synced: false, message: 'Nie znaleziono urządzenia', icon: '❌' }
    }
    
    const cmtsNameNorm = cmtsName.toString().trim().toLowerCase()
    
    // Znajdź urządzenie po hostname lub name
    const device = devices.value.find(d => {
        const hostname = d.hostname?.toString().trim().toLowerCase()
        const name = d.name?.toString().trim().toLowerCase()
        return hostname === cmtsNameNorm || name === cmtsNameNorm
    })
    
    if (!device) {
        return { found: false, synced: false, message: 'Nie znaleziono urządzenia', icon: '❌' }
    }
    
    const status = device.status?.toString().trim().toUpperCase()
    
    if (status === 'SYNCED') {
        return { found: true, synced: true, message: 'Urządzenie zsynchronizowane', icon: '✅' }
    } else if (device.failed_sync) {
        return { found: true, synced: false, message: 'Synchronizacja nie powiodła się', icon: '‼️' }
    } else {
        return { found: true, synced: false, message: 'Oczekuje na synchronizację', icon: '⚠️' }
    }
}

// Sprawdź czy są brakujące urządzenia w tabeli
function checkForMissingDevices() {
    if (!tableData.value?.length) {
        hasMissingDevices.value = false
        return
    }
    
    // Urządzenie jest "brakujące" jeśli nie jest w devices.json (niezależnie od statusu synchronizacji)
    const missing = tableData.value.some(row => {
        const status = getDeviceStatus(row.device)
        return !status.found
    })
    hasMissingDevices.value = missing
    console.log(`[MISSING CHECK] Has missing devices: ${missing}`)
    
    // Wymuś ponowne renderowanie tabeli przy zmianie statusu
    tableKey.value++
}

// Sprawdź czy są niezsynchronizowane urządzenia w tabeli
function checkForUnsyncedDevices() {
    if (!tableData.value?.length) {
        hasUnsyncedDevices.value = false
        return
    }
    
    // Urządzenie jest "niezsynchronizowane" jeśli jest w devices.json ale nie jest SYNCED
    const unsynced = tableData.value.some(row => {
        const status = getDeviceStatus(row.device)
        return status.found && !status.synced
    })
    hasUnsyncedDevices.value = unsynced
    console.log(`[UNSYNCED CHECK] Has unsynced devices: ${unsynced}`)
    
    // Wymuś ponowne renderowanie tabeli przy zmianie statusu
    tableKey.value++
}

// Parsuj karty SIP z tekstu alarmów
function getSipCardsFromAlarms(alarms) {
    if (!alarms || alarms === '-' || alarms.includes('Błąd')) {
        return []
    }
    
    // Podziel na linie i wyciągnij numery SIP
    const lines = alarms.split('\n').filter(line => line.trim() !== '')
    const sipCards = []
    
    lines.forEach(line => {
        // Szukaj wzorców: SIP/6, SIP/9, etc.
        const sipMatch = line.match(/SIP\/(\d+)/i)
        if (sipMatch) {
            sipCards.push(`SIP/${sipMatch[1]}`)
        }
    })
    
    // Usuń duplikaty
    return [...new Set(sipCards)]
}

// Wyciągnij kartę SIP z pojedynczej linii tekstu
function getSipCardFromLine(line) {
    if (!line || typeof line !== 'string') return null
    
    const sipMatch = line.match(/SIP\/(\d+)/i)
    return sipMatch ? `SIP/${sipMatch[1]}` : null
}

// Sprawdź platformę dla konkretnej karty SIP
const showPlatformForSip = async (deviceName, sipCard, options = {}) => {
    const loadingKey = `${deviceName}-${sipCard}`
    const { deferRefresh = false } = options
    
    if (isPlatformLoading.value[loadingKey]) return
    
    isPlatformLoading.value[loadingKey] = true
    console.log(`[SIP CHECK] Executing show platform for ${sipCard} on ${deviceName}...`)
    
    try {
        // Znajdź urządzenie w devices
        const device = devices.value.find(d => d.hostname === deviceName)
        if (!device) {
            console.error(`[SIP CHECK] Device ${deviceName} not found in devices.json`)
            return
        }
        
        // Znajdź wiersz urządzenia w tabeli
        const deviceRow = tableData.value.find(row => row.device === deviceName)
        if (!deviceRow) {
            console.error(`[SIP CHECK] Device ${deviceName} not found in table`)
            return
        }
        
        // Wykonaj komendę show platform przez API /api/devices/command (GET)
        let apiResult = null
        try {
            const params = new URLSearchParams({ device_id: device.id, command: 'show platform' })
            apiResult = await requestJson(`/api/devices/command?${params}`, { timeoutMs: 120000 })
        } catch (err) {
            console.error(`[SIP CHECK] Error calling /api/devices/command for ${deviceName}:`, err)
        }

        console.log(`[SIP CHECK] API response for ${sipCard} on ${deviceName}:`, apiResult)

        if (apiResult) {
            try {
                let parsed = apiResult
                if (typeof parsed === 'string') {
                    try { parsed = JSON.parse(parsed) } catch (e) { /* keep string */ }
                }

                let output = null
                if (parsed && typeof parsed === 'object') {
                    output = parsed.output || (parsed.result && parsed.result.output) || (parsed.result && parsed.result)
                } else if (typeof parsed === 'string') {
                    output = parsed
                }

                if (output) {
                    const slotNumber = sipCard.replace('SIP/', '')
                    const slotStates = extractSlotStates(output, sipCard)
                    await updateSingleSipStatus(deviceName, sipCard, slotStates[slotNumber], { deferRefresh })
                    console.log(`[SIP CHECK] Updated status for ${sipCard} on ${deviceName}:`, slotStates[slotNumber])
                } else {
                    console.error(`[SIP CHECK] No output from API for ${deviceName}`)
                }
            } catch (parseError) {
                console.error(`[SIP CHECK] Error parsing API response:`, parseError)
            }
        } else {
            console.error('[SIP CHECK] No response from device API')
        }
        
        if (!deferRefresh) {
            await saveTableDataToFile()
            tableKey.value++
        }
        
    } catch (error) {
        console.error(`[SIP CHECK] Error checking ${sipCard} on ${deviceName}:`, error)
    } finally {
        isPlatformLoading.value[loadingKey] = false
    }
}

// Restartuj konkretną kartę SIP (hw slot X reload)
const restartSipCard = async (deviceName, sipCard) => {
    const loadingKey = `${deviceName}-${sipCard}`
    
    if (isRestartLoading.value[loadingKey]) return
    
    isRestartLoading.value[loadingKey] = true
    console.log(`[SIP RESTART] Restarting ${sipCard} on ${deviceName}...`)
    
    try {
        // Find device
        const device = devices.value.find(d => d.hostname === deviceName)
        if (!device) {
            console.error(`[SIP RESTART] Device ${deviceName} not found`)
            return
        }

        // Extract slot number from sipCard (e.g. SIP/7 -> 7)
        const slot = (sipCard || '').toString().replace('SIP/', '')
        if (!slot) {
            console.error(`[SIP RESTART] Could not extract slot from ${sipCard}`)
            return
        }

        const command = `hw slot ${slot} reload\ny`
        console.log(`[SIP RESTART] Sending command to ${deviceName}: hw slot ${slot} reload (with auto-confirm)`)

        try {
            const params = new URLSearchParams({ device_id: device.id, command })
            const resp = await requestJson(`/api/devices/command?${params}`, { timeoutMs: 120000 })
            console.log(`[SIP RESTART] API response for ${deviceName}:`, resp)

            // Extract and log the output from the response
            let output = null
            if (resp && typeof resp === 'object') {
                output = resp.output || (resp.result && resp.result.output) || (resp.result && resp.result) || resp
            } else if (typeof resp === 'string') {
                output = resp
            }
            console.log(`[SIP RESTART] Output from "${command}" on ${deviceName}:`, output)

            cardRestartStatus.value[loadingKey] = 'RESTARTED'
            restartLogsMessages.value[loadingKey] = ''
        } catch (err) {
            console.error(`[SIP RESTART] Error calling /api/devices/command for "${command}" on ${deviceName}:`, err)
            restartLogsMessages.value[loadingKey] = `Błąd: ${err?.message || err}`
        }

        // Refresh table view
        tableKey.value++

        // Automatycznie odśwież status karty SIP po restarcie
        console.log(`[SIP RESTART] Auto-refreshing status for ${sipCard} on ${deviceName}...`)
        await showPlatformForSip(deviceName, sipCard)
    } catch (error) {
        console.error(`[SIP RESTART] Error restarting ${sipCard} on ${deviceName}:`, error)
        restartLogsMessages.value[loadingKey] = `Błąd: ${error.message}`
    } finally {
        isRestartLoading.value[loadingKey] = false
    }
}

// Sprawdź czy wszystkie urządzenia są zsynchronizowane
function checkAllDevicesSynced() {
    if (!tableData.value?.length) {
        allDevicesSynced.value = false
        return
    }
    
    // Wszystkie urządzenia są zsynchronizowane jeśli:
    // 1. Wszystkie są znalezione w devices.json
    // 2. Wszystkie mają status SYNCED
    const allSynced = tableData.value.every(row => {
        const status = getDeviceStatus(row.device)
        return status.found && status.synced
    })
    allDevicesSynced.value = allSynced
    console.log(`[ALL SYNCED CHECK] All devices synced: ${allSynced}`)
    
    // Wymuś ponowne renderowanie tabeli przy zmianie statusu
    tableKey.value++
}

// Sprawdź czy istnieją dane o alarmach w tabeli (wartości inne niż puste lub "-")
function hasAlarmsData() {
    if (!tableData.value?.length) return false
    
    return tableData.value.some(row => {
        const alarms = row.alarms
        const isValid = alarms && 
                       alarms !== '' && 
                       alarms !== '-' && 
                       alarms.trim() !== '' &&
                       alarms !== 'Brak danych' &&
                       !alarms.includes('Błąd') // Traktuj błędy jako brak danych
        
        return isValid
    })
}

// Pobierz listę brakujących urządzeń (nie znalezione lub nie zsynchronizowane)
function getMissingDevices() {
    return tableData.value.filter(row => {
        const status = getDeviceStatus(row.device)
        // Uwzględnij tylko urządzenia które w ogóle nie istnieją (nie ma sensu dodawać istniejących)
        return !status.found
    })
}


// Parsowanie raportu Splunk CMTS TMPFS
const parseSplunkReport = (text) => {
    const lines = text.split('\n')
    const devices = []
    
    // Regex do wyciągnięcia informacji z linii logu CMTS
    // Przykład: 2025-10-28T20:53:00+01:00 1238117 1238117: [syslog.err]  CMTS_CISCO_pl-bzg01a-br05: Oct 28 20:52:59.217: %PLATFORM-3-ELEMENT_TMPFS_WARNING: R0/0: smand: SIP/3: TMPFS value 43% above warning level 40%
    const logRegex = /(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2}).*CMTS_CISCO_([^:]+):.*SIP\/(\d+):\s*TMPFS\s+value\s+(\d+)%/i
    
    for (const line of lines) {
        const match = line.match(logRegex)
        if (match) {
            const [, timestamp, deviceName, sipNumber, tmpfsValue] = match
            
            // Konwertuj timestamp na czytelny format
            const date = new Date(timestamp)
            const formattedTime = date.toLocaleString('pl-PL', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            })
            
            devices.push({
                timestamp: formattedTime,
                device: deviceName,
                sip: `SIP/${sipNumber}`,
                value: parseInt(tmpfsValue),
                rawLine: line
            })
        }
    }
    
    // Sortuj urządzenia według wartości TMPFS (malejąco) i potem według nazwy
    devices.sort((a, b) => {
        if (b.value !== a.value) {
            return b.value - a.value
        }
        return a.device.localeCompare(b.device)
    })
    
    return devices
}

// Przetwarzanie tekstu wklejonego przez użytkownika
const processTextData = async () => {
    if (!textInput.value.trim()) {
        console.log('[PROCESS TEXT] No data provided to process')
        return
    }

    processing.value = true
    showTextModal.value = false

    try {
        const data = parseSplunkReport(textInput.value)
        if (data && data.length > 0) {
            tableData.value = data
            console.log('Parsed CMTS TMPFS devices:', data)
            
            // Zapisz dane do pliku temp
            await saveTableDataToFile()
            
            // Zatrzymaj automatyczne sprawdzanie przy nowych danych
            if (isAutoCheckEnabled.value) {
                console.log('[AUTO CHECK] Stopping due to new data')
                stopAutoCheck()
                isAutoCheckEnabled.value = false
            }
            
            // Sprawdź czy są brakujące urządzenia
            checkForMissingDevices()
            checkForUnsyncedDevices()
            checkAllDevicesSynced()
        } else {
            console.log('[PROCESS TEXT] No CMTS devices found in report')
        }

        textInput.value = '' // Reset textarea
    } catch (error) {
        console.error('Error processing Splunk report:', error)
    } finally {
        processing.value = false
    }
}

// Dodaj brakujące urządzenia i zsynchronizuj je
const addMissingDevices = async () => {
    if (isAddingDevices.value) return
    
    isAddingDevices.value = true
    const missingDevices = getMissingDevices()
    
    console.log(`[ADD MISSING] Starting to add ${missingDevices.length} missing devices`)
    
    try {
        for (const deviceData of missingDevices) {
            const deviceName = deviceData.device
            console.log(`[ADD MISSING] Processing device: ${deviceName}`)
            
            try {
                // Dodaj urządzenie
                console.log(`[ADD MISSING] Adding device: ${deviceName}`)
                const addResult = await addDevice(deviceName)
                if (addResult.success) {
                    console.log(`[ADD MISSING] Device ${deviceName} added successfully`)
                    
                    // Odśwież listę urządzeń aby mieć najnowsze dane
                    await refreshDevicesList()
                    
                    // Dodatkowe opóźnienie żeby upewnić się że dane są załadowane
                    await new Promise(resolve => setTimeout(resolve, 200))
                    
                    // Sprawdź czy nadal są brakujące urządzenia (pozwoli ukryć przycisk w trakcie procesu)
                    checkForMissingDevices()
                    checkForUnsyncedDevices()
                    checkAllDevicesSynced()
                    
                    // Zapisz zaktualizowane dane do pliku temp
                    await saveTableDataToFile()
                    
                    console.log(`[ADD MISSING] After refresh - device status for ${deviceName}:`, getDeviceStatus(deviceName))
                    
                    // Spróbuj zsynchronizować
                    console.log(`[ADD MISSING] Synchronizing device: ${deviceName}`)
                    const syncResult = await syncDevice(deviceName)
                    if (syncResult.success) {
                        console.log(`[ADD MISSING] Device ${deviceName} synchronized successfully`)
                    } else {
                        console.log(`[ADD MISSING] Failed to sync device ${deviceName}:`, syncResult.error)
                    }
                } else {
                    console.log(`[ADD MISSING] Failed to add device ${deviceName}:`, addResult.error)
                }
                
            } catch (deviceError) {
                console.error(`[ADD MISSING] Error processing device ${deviceName}:`, deviceError)
            }
            
            // Krótka pauza między urządzeniami
            await new Promise(resolve => setTimeout(resolve, 1000))
        }
        
        // Końcowe odświeżenie listy urządzeń aby upewnić się że wszystko jest aktualne
        console.log('[ADD MISSING] Final refresh of devices list...')
        await refreshDevicesList()
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // Końcowe sprawdzenie brakujących urządzeń
        checkForMissingDevices()
        checkForUnsyncedDevices()
        checkAllDevicesSynced()
        
        // Loguj końcowy status wszystkich urządzeń z tabeli
        console.log('[ADD MISSING] Final device statuses:')
        tableData.value.forEach(row => {
            const status = getDeviceStatus(row.device)
            console.log(`  ${row.device}: found=${status.found}, synced=${status.synced}, icon=${status.icon}`)
        })
        
        console.log('[ADD MISSING] Process completed')
        console.log(`[ADD MISSING] Added ${missingDevices.length} missing devices`)
        
        // Odśwież widok po dodaniu urządzeń
        tableKey.value++
        
    } catch (error) {
        console.error('[ADD MISSING] Error during process:', error)
    } finally {
        isAddingDevices.value = false
    }
}

// Synchronizuj niezsynchronizowane urządzenia
const syncUnsyncedDevices = async () => {
    if (isSyncingDevices.value) return
    
    isSyncingDevices.value = true
    isSyncingScript.value = true // ⭐ Ustaw mutex dla verify_alarms
    isSyncCancelled.value = false
    syncProgress.value = 0
    syncStatus.value = 'Przygotowywanie...'
    
    // Pobierz urządzenia które są w devices.json ale nie są SYNCED
    const unsyncedDevices = tableData.value.filter(row => {
        const status = getDeviceStatus(row.device)
        return status.found && !status.synced
    })
    
    if (unsyncedDevices.length === 0) {
        console.log('[SYNC UNSYNCED] All devices are already synced')
        isSyncingDevices.value = false
        syncProgress.value = 0
        syncStatus.value = ''
        return
    }
    
    console.log(`[SYNC UNSYNCED] Starting to sync ${unsyncedDevices.length} unsynced devices`)
    
    try {
        const queue = unsyncedDevices
            .map((deviceData) => {
                const deviceName = deviceData.device
                const device = devices.value.find(d => d.hostname === deviceName)
                if (!device) {
                    return null
                }
                return { deviceName, deviceId: device.id }
            })
            .filter(Boolean)

        const total = unsyncedDevices.length
        let completed = 0
        let refreshChain = Promise.resolve()
        const concurrency = 3

        const markProgress = (deviceName, isError = false) => {
            completed += 1
            syncProgress.value = Math.round((completed / total) * 100)
            syncStatus.value = isError
                ? `❌ Błąd: ${deviceName} (${completed}/${total})`
                : `Synchronizowanie: ${deviceName} (${completed}/${total})`
        }

        const refreshSerialized = async () => {
            refreshChain = refreshChain.then(() => refreshDevicesList())
            await refreshChain
        }

        const runSync = async (task, index) => {
            if (isSyncCancelled.value) return

            const { deviceName, deviceId } = task
            console.log(`[SYNC UNSYNCED] Syncing device ${index + 1}/${total}: ${deviceName}`)

            try {
                const resultRaw = await runScript({
                    script: 'settings-devices_controller',
                    method: 'sync_device',
                    payload: { id: deviceId }
                })

                const parsed = typeof resultRaw === 'string' ? JSON.parse(resultRaw) : resultRaw
                console.log(`[SYNC UNSYNCED] Device ${deviceName} synced successfully:`, parsed)

                const device = devices.value.find(d => d.hostname === deviceName)
                if (device) {
                    device.failed_sync = false
                }

                await refreshSerialized()
                checkForUnsyncedDevices()
                checkForMissingDevices()
                checkAllDevicesSynced()
                await saveTableDataToFile()

                markProgress(deviceName, false)
            } catch (error) {
                console.error(`[SYNC UNSYNCED] Error syncing device ${deviceName}:`, error)
                const device = devices.value.find(d => d.hostname === deviceName)
                if (device) {
                    device.failed_sync = true
                }
                markProgress(deviceName, true)
            }

            await new Promise(resolve => setTimeout(resolve, 200))
        }

        const workers = Array.from({ length: Math.min(concurrency, queue.length) }, (_, workerIndex) => (async () => {
            while (queue.length && !isSyncCancelled.value) {
                const task = queue.shift()
                if (!task) break
                const index = completed
                await runSync(task, index)
            }
        })())

        await Promise.all(workers)
        
        // Końcowe sprawdzenie niezsynchronizowanych urządzeń
        checkForUnsyncedDevices()
        checkForMissingDevices()
        checkAllDevicesSynced()
        
        console.log('[SYNC UNSYNCED] Process completed')
        console.log(`[SYNC UNSYNCED] Synced ${unsyncedDevices.length} devices`)
        
        if (!isSyncCancelled.value) {
            syncStatus.value = '✅ Synchronizacja zakończona!'
            syncProgress.value = 100
        }
        
        // Odśwież widok po synchronizacji
        tableKey.value++
        
        // Schowaj pasek postępu po 2 sekundach
        await new Promise(resolve => setTimeout(resolve, 2000))
        
    } catch (error) {
        console.error('[SYNC UNSYNCED] Error during sync process:', error)
        syncStatus.value = '❌ Błąd synchronizacji'
    } finally {
        isSyncingDevices.value = false
        isSyncingScript.value = false // ⭐ Odblokuj dla verify_alarms
        isSyncCancelled.value = false
        syncProgress.value = 0
        syncStatus.value = ''
    }
}

// Przełącz automatyczne sprawdzanie statusów ON/OFF
const toggleAutoCheck = () => {
    isAutoCheckEnabled.value = !isAutoCheckEnabled.value
    
    if (isAutoCheckEnabled.value) {
        console.log(`[AUTO CHECK] Enabled with ${autoCheckInterval.value}s interval`)
        startAutoCheck()
    } else {
        console.log('[AUTO CHECK] Disabled')
        stopAutoCheck()
    }
    
    // Tabela odświeża się tylko po otrzymaniu statusu z metody.
}

// Uruchom automatyczne sprawdzanie statusów
const startAutoCheck = () => {
    console.log(`[AUTO CHECK] Starting background process with ${autoCheckInterval.value}s checks`)

    autoCheckCountdown.value = autoCheckInterval.value
    if (autoCheckCountdownTimer.value) {
        clearInterval(autoCheckCountdownTimer.value)
    }
    autoCheckCountdownTimer.value = setInterval(() => {
        if (!isAutoCheckEnabled.value) return
        if (autoCheckCountdown.value <= 1) {
            autoCheckCountdown.value = autoCheckInterval.value
            return
        }
        autoCheckCountdown.value -= 1
    }, 1000)
    
    // Wykonaj sprawdzenie od razu w tle (fire-and-forget, nigdy nie czekaj!)
    try {
        performStatusCheck()
    } catch (error) {
        console.error('[AUTO CHECK] Error during immediate check:', error)
    }
    
    // Ustaw timer na cykliczne sprawdzanie (będzie działać w tle dopóki nie wyłączysz)
    autoCheckTimer.value = setInterval(() => {
        try {
            performStatusCheck()
        } catch (error) {
            console.error('[AUTO CHECK] Error during background check:', error)
        }
    }, autoCheckInterval.value * 1000)
    
    console.log('[AUTO CHECK] Background process running - checks every 30s')
}

// Zatrzymaj automatyczne sprawdzanie statusów
const stopAutoCheck = () => {
    if (autoCheckTimer.value) {
        clearInterval(autoCheckTimer.value)
        autoCheckTimer.value = null
        console.log('[AUTO CHECK] Checks stopped')
    }

    if (autoCheckCountdownTimer.value) {
        clearInterval(autoCheckCountdownTimer.value)
        autoCheckCountdownTimer.value = null
    }

    autoCheckCountdown.value = autoCheckInterval.value
    
    console.log('[AUTO CHECK] Background process fully stopped')
}

// Wykonaj sprawdzenie statusów (w tle, nigdy nie czeka na wyniki!)
const performStatusCheck = async () => {
    if (isAutoCheckRunning.value) {
        console.log('[AUTO CHECK] Previous cycle still running, skipping this tick')
        return
    }

    isAutoCheckRunning.value = true
    console.log('[AUTO CHECK] Starting background status check (fire-and-forget mode)')
    
    try {
        await runScriptAsync({
            script: 'modules-cmts_tmpfs_controller',
            method: 'auto_check_statuses',
            payload: {
                tableData: tableData.value
            }
        })
        console.log('[AUTO CHECK] Auto-check started on backend')
        
    } catch (error) {
        console.error('[AUTO CHECK] Error preparing status check:', error)
        isAutoCheckRunning.value = false
    }
}

// Weryfikuj alarmy
const verifyAlarms = async () => {
    if (isVerifyingAlarms.value) return
    
    // ⭐ NOWE: Czekaj jeśli inne procesy się odbywa (sync, etc)
    if (isSyncingScript.value || isSyncingDevices.value) {
        console.log('[VERIFY ALARMS] ⏳ Czekaj - inne procesy się odbywa')
        verificationStatus.value = '⏳ Czekaj na inne procesy...'
        return
    }
    
    isVerifyingAlarms.value = true
    isVerificationCancelled.value = false
    verificationProgress.value = 0
    verificationStatus.value = 'Rozpoczynanie weryfikacji...'
    console.log('[VERIFY ALARMS] Starting alarm verification (non-blocking)...')
    
    try {
        // 🔥 Przeładuj listę devices aby upewnić się że mamy świeże dane (np. jeśli usunięto urządzenie z devices.json)
        await cmtsTmpfsStore.loadDevices()
        console.log('[VERIFY ALARMS] Devices list refreshed from file:', cmtsTmpfsStore.devices.length, 'devices')
        
        // Pobierz listę urządzeń z tabeli do sprawdzenia
        const deviceHostnames = tableData.value.map(row => row.device)
        console.log('[VERIFY ALARMS] Devices to check:', deviceHostnames)
        
        if (deviceHostnames.length === 0) {
            console.log('[VERIFY ALARMS] No devices in table to check')
            isVerifyingAlarms.value = false
            return
        }
        
        const totalDevices = deviceHostnames.length
        verificationStatus.value = `Uruchamianie weryfikacji dla ${totalDevices} urządzeń...`
        
        // Czytaj hoursBack z settings.json
        let hoursBack = 12
        try {
            const response = await fetch('/src/data/settings.json')
            const settingsData = await response.json()
            const configuredHours = Number(settingsData.cmtsTmpfs?.hoursBack)
            if (!Number.isNaN(configuredHours) && configuredHours > 0) {
                hoursBack = configuredHours
                cmtsTmpfsSettings.value.hoursBack = configuredHours
            }
            console.log(`[VERIFY ALARMS] Using hoursBack: ${hoursBack}`)
        } catch (err) {
            console.warn('[VERIFY ALARMS] Could not read settings, using default hoursBack=12:', err)
        }
        
        // Przygotuj tracking dla każdego urządzenia
        const completedDevices = new Set()
        const allAlarmsCollected = [] // 🔥 NOWE: Zbierz wszystkie alarmy do pliku
        let scriptFinishedListener = null
        let scriptErrorListener = null
        
        try {
            // Słuchaj na event script-finished - ale TYLKO dla verify_tmpfs_alarms
            scriptFinishedListener = await listen('script-finished', (event) => {
                try {
                    const eventTime = new Date().toLocaleTimeString('pl-PL')
                    const payload = event.payload
                    if (typeof payload === 'string' && payload.includes('"action":"auto_check_statuses"')) {
                        return
                    }
                    console.log(`[VERIFY ALARMS] 📨 ${eventTime} - Received script-finished event, payload type: ${typeof payload}`)
                    console.log('[VERIFY ALARMS] Completed so far:', completedDevices.size, '/', totalDevices)
                    
                    // Backend wysyła raw string z output'u - szukaj JSON'a w nim
                    if (typeof payload === 'string') {
                        try {
                            // Szukaj JSON'a w string'u (backend wysyła: print(json.dumps(...)))
                            const jsonMatch = payload.match(/\{[\s\S]*"results"[\s\S]*\}/)
                            if (jsonMatch) {
                                const parsed = JSON.parse(jsonMatch[0])
                                console.log('[VERIFY ALARMS] Parsed JSON, found hostnames:', Object.keys(parsed.results || {}))
                                
                                // Szukaj pola z wynikami alarmów
                                if (parsed.results && typeof parsed.results === 'object') {
                                    // Iteruj po każdym urządzeniu w results
                                    for (const hostname of Object.keys(parsed.results)) {
                                        const resultTime = new Date().toLocaleTimeString('pl-PL')
                                        console.log(`[VERIFY ALARMS] ⏱️ ${resultTime} - Processing hostname: ${hostname}, already completed? ${completedDevices.has(hostname)}`)
                                        if (deviceHostnames.includes(hostname) && !completedDevices.has(hostname)) {
                                            const deviceResult = parsed.results[hostname]
                                            completedDevices.add(hostname)
                                            
                                            // 🔥 NOWE: Zaktualizuj tableData z wynikami
                                            const tableRow = tableData.value.find(row => row.device === hostname)
                                            if (tableRow && deviceResult) {
                                                tableRow.alarm_count = deviceResult.alarm_count || 0
                                                tableRow.status = deviceResult.status || 'UNKNOWN'
                                                console.log(`[VERIFY ALARMS] ✅ Updated ${hostname}: ${deviceResult.alarm_count} alarmów, status: ${deviceResult.status}`)
                                                
                                                // 🔥 NOWE: Wyświetl szczegóły alarmy
                                                if (deviceResult.filtered_alarms && Array.isArray(deviceResult.filtered_alarms) && deviceResult.filtered_alarms.length > 0) {
                                                    console.log(`[VERIFY ALARMS] 📋 Alarmy dla ${hostname} (${deviceResult.filtered_alarms.length}):`)
                                                    
                                                    // Wyciągnij czasy alarmy do znalezienia zakresu
                                                    let minTime = null
                                                    let maxTime = null
                                                    const alarmLines = []
                                                    const sipCards = new Set() // Unikalne karty SIP
                                                    
                                                    deviceResult.filtered_alarms.forEach((alarm) => {
                                                        // Sparsuj czas i kartę SIP z pełnego loga
                                                        // Format: "Nov  6 00:50:24.699: %PLATFORM-3-ELEMENT_TMPFS_WARNING: ... SIP/1: ..."
                                                        const timeMatch = alarm.match(/^(\w+\s+\d+\s+\d+:\d+:\d+\.\d+)/)
                                                        const sipMatch = alarm.match(/SIP\/(\d+)/)
                                                        
                                                        if (timeMatch && sipMatch) {
                                                            const timeStr = timeMatch[1]
                                                            const sipCard = `SIP/${sipMatch[1]}`
                                                            alarmLines.push(`${timeStr}: ${sipCard}`)
                                                            sipCards.add(sipCard) // Dodaj do zbioru unikalnych kart
                                                            
                                                            // Track min/max czasu
                                                            if (!minTime) minTime = timeStr
                                                            maxTime = timeStr
                                                            
                                                            // 🔥 NOWE: Zbierz alarm do pliku temp
                                                            allAlarmsCollected.push({
                                                                timestamp: timeStr,
                                                                device: hostname,
                                                                sip: sipCard,
                                                                value: null,
                                                                rawLine: alarm
                                                            })
                                                        }
                                                    })
                                                    
                                                    // 🔥 NOWE: Przypisz karty SIP do row.alarms dla wyświetlenia w tabeli
                                                    if (tableRow && sipCards.size > 0) {
                                                        tableRow.alarms = Array.from(sipCards).sort().join('\n')
                                                    }
                                                    
                                                    // Wyświetl zakres czasowy
                                                    if (minTime && maxTime) {
                                                        console.log(`[VERIFY ALARMS] ⏰ Zakres: ${minTime} → ${maxTime}`)
                                                    }
                                                    
                                                    // 🔥 Wyświetl teoretyczny zakres (teraz - hoursBack do teraz)
                                                    const now = new Date()
                                                    const hoursBackMs = hoursBack * 60 * 60 * 1000
                                                    const startTime = new Date(now.getTime() - hoursBackMs)
                                                    const endTimeStr = now.toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(',', '')
                                                    const startTimeStr = startTime.toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(',', '')
                                                    console.log(`[VERIFY ALARMS] 📅 Pełny zakres weryfikacji: ${startTimeStr} → ${endTimeStr} (${hoursBack}h wstecz)`)
                                                    
                                                    // 🔥 Wyświetl tylko pierwsze 3 alarmy (zamiast całej listy)
                                                    const firstThreeAlarms = alarmLines.slice(0, 3)
                                                    if (firstThreeAlarms.length > 0) {
                                                        console.log(`[VERIFY ALARMS] 🔔 Pierwsze ${firstThreeAlarms.length} alarmy:`)
                                                        firstThreeAlarms.forEach((line, index) => {
                                                            console.log(`  ${index + 1}. ${line}`)
                                                        })
                                                        if (alarmLines.length > 3) {
                                                            console.log(`  ... i ${alarmLines.length - 3} więcej`)
                                                        }
                                                    }
                                                    
                                                    // 🔥 Wyświetl ostatnie 3 alarmy
                                                    const lastThreeAlarms = alarmLines.slice(-3)
                                                    if (alarmLines.length > 3) {
                                                        console.log(`[VERIFY ALARMS] 🔚 Ostatnie ${lastThreeAlarms.length} alarmy:`)
                                                        lastThreeAlarms.forEach((line, index) => {
                                                            console.log(`  ${index + 1}. ${line}`)
                                                        })
                                                    }
                                                    
                                                    // Wyświetl karty SIP
                                                    console.log(`[VERIFY ALARMS] 📌 Karty SIP: ${Array.from(sipCards).sort().join(', ')}`)
                                                } else if (deviceResult.alarm_count === 0) {
                                                    console.log(`[VERIFY ALARMS] ✅ Brak alarmów dla ${hostname}`)
                                                    if (tableRow) {
                                                        tableRow.alarms = '-'
                                                    }
                                                    
                                                    // 🔥 Wyświetl error jeśli istnieje
                                                    if (deviceResult.error) {
                                                        console.log(`[VERIFY ALARMS] ❌ Błąd: ${deviceResult.error}`)
                                                    }
                                                    
                                                    // 🔥 Wyświetl ostatnie 3 linii z raw logu
                                                    if (deviceResult.tmpfs_logs) {
                                                        // Split lines, normalize and remove pure prompt lines (ending with '#')
                                                        const rawLines = deviceResult.tmpfs_logs.split('\n').map(l => l.replace(/\r/g, '').trim())
                                                        const nonPromptLines = rawLines.filter(l => l && !l.endsWith('#'))
                                                        // Prefer last 3 non-prompt lines; if none, fall back to last non-empty lines (including prompts)
                                                        let lastLines = nonPromptLines.slice(-3)
                                                        if (lastLines.length === 0) {
                                                            lastLines = rawLines.filter(l => l).slice(-3)
                                                        }
                                                        if (lastLines.length > 0) {
                                                            console.log(`[VERIFY ALARMS] 📝 Ostatnie ${lastLines.length} linii z logu:`)
                                                            lastLines.forEach((line, idx) => {
                                                                console.log(`    ${idx + 1}. ${line}`)
                                                            })
                                                        }
                                                    }
                                                } else if (deviceResult.error) {
                                                    console.log(`[VERIFY ALARMS] ❌ Błąd dla ${hostname}: ${deviceResult.error}`)
                                                    if (tableRow) {
                                                        tableRow.alarms = `Błąd: ${deviceResult.error}`
                                                    }
                                                }
                                            }
                                            
                                            const progress = Math.round((completedDevices.size / totalDevices) * 100)
                                            verificationProgress.value = progress
                                            verificationStatus.value = `✅ ${completedDevices.size}/${totalDevices} urządzeń sprawdzonych`
                                            console.log(`[VERIFY ALARMS] Completed ${hostname}: ${progress}%`)
                                        }
                                    }
                                }
                            } else {
                                // Jeśli nie ma JSON'a, to zwykły output - licz jako próbę dla pierwszego urządzenia
                                console.log('[VERIFY ALARMS] No JSON found in output, counting as one device completed')
                                if (deviceHostnames.length > completedDevices.size) {
                                    const hostname = deviceHostnames[completedDevices.size]
                                    completedDevices.add(hostname)
                                    const progress = Math.round((completedDevices.size / totalDevices) * 100)
                                    verificationProgress.value = progress
                                    verificationStatus.value = `✅ ${completedDevices.size}/${totalDevices} urządzeń sprawdzonych`
                                    console.log(`[VERIFY ALARMS] Marked ${hostname} as completed (by order): ${progress}%`)
                                }
                            }
                        } catch (_err) {
                            // Jeśli nie da się sparsować, licz jako próbę
                            console.log('[VERIFY ALARMS] Could not parse output, counting as completed')
                            if (deviceHostnames.length > completedDevices.size) {
                                const hostname = deviceHostnames[completedDevices.size]
                                completedDevices.add(hostname)
                                const progress = Math.round((completedDevices.size / totalDevices) * 100)
                                verificationProgress.value = progress
                                verificationStatus.value = `✅ ${completedDevices.size}/${totalDevices} urządzeń sprawdzonych`
                            }
                        }
                    }
                } catch (err) {
                    console.error('[VERIFY ALARMS] Error handling script-finished event:', err)
                }
            })
            
            // Słuchaj na event script-error
            scriptErrorListener = await listen('script-error', (event) => {
                try {
                    const payload = event.payload
                    if (typeof payload === 'string' && payload.includes('"action":"auto_check_statuses"')) {
                        return
                    }
                    console.error('[VERIFY ALARMS] Received script-error event:', payload)
                    
                    // Liczymy to jako próbę (nawet jeśli error)
                    if (typeof payload === 'string') {
                        try {
                            // Szukaj JSON'a w string'u
                            const jsonMatch = payload.match(/\{[\s\S]*"results"[\s\S]*\}/)
                            if (jsonMatch) {
                                const parsed = JSON.parse(jsonMatch[0])
                                if (parsed.results && typeof parsed.results === 'object') {
                                    for (const hostname of Object.keys(parsed.results)) {
                                        if (deviceHostnames.includes(hostname) && !completedDevices.has(hostname)) {
                                            const deviceResult = parsed.results[hostname]
                                            completedDevices.add(hostname)
                                            
                                            // 🔥 NOWE: Zaktualizuj tableData z wynikami (nawet z błędem)
                                            const tableRow = tableData.value.find(row => row.device === hostname)
                                            if (tableRow && deviceResult) {
                                                tableRow.alarm_count = deviceResult.alarm_count || 0
                                                tableRow.status = deviceResult.status || 'FAILED'
                                                console.log(`[VERIFY ALARMS] Updated ${hostname} (error): ${deviceResult.alarm_count} alarmów, status: ${deviceResult.status}`)
                                                
                                                // 🔥 NOWE: Wyświetl szczegóły alarmy nawet z błędem
                                                if (deviceResult.filtered_alarms && Array.isArray(deviceResult.filtered_alarms) && deviceResult.filtered_alarms.length > 0) {
                                                    console.log(`[VERIFY ALARMS] 📋 Alarmy dla ${hostname} (${deviceResult.filtered_alarms.length}):`)
                                                    
                                                    // Wyciągnij czasy alarmy do znalezienia zakresu
                                                    let minTime = null
                                                    let maxTime = null
                                                    const alarmLines = []
                                                    const sipCards = new Set() // Unikalne karty SIP
                                                    
                                                    deviceResult.filtered_alarms.forEach((alarm) => {
                                                        // Sparsuj czas i kartę SIP z pełnego loga
                                                        // Format: "Nov  6 00:50:24.699: %PLATFORM-3-ELEMENT_TMPFS_WARNING: ... SIP/1: ..."
                                                        const timeMatch = alarm.match(/^(\w+\s+\d+\s+\d+:\d+:\d+\.\d+)/)
                                                        const sipMatch = alarm.match(/SIP\/(\d+)/)
                                                        
                                                        if (timeMatch && sipMatch) {
                                                            const timeStr = timeMatch[1]
                                                            const sipCard = `SIP/${sipMatch[1]}`
                                                            alarmLines.push(`${timeStr}: ${sipCard}`)
                                                            sipCards.add(sipCard) // Dodaj do zbioru unikalnych kart
                                                            
                                                            // Track min/max czasu
                                                            if (!minTime) minTime = timeStr
                                                            maxTime = timeStr
                                                        }
                                                    })
                                                    
                                                    // 🔥 NOWE: Przypisz karty SIP do row.alarms dla wyświetlenia w tabeli
                                                    if (tableRow && sipCards.size > 0) {
                                                        tableRow.alarms = Array.from(sipCards).sort().join('\n')
                                                    }
                                                    
                                                    // Wyświetl zakres czasowy
                                                    if (minTime && maxTime) {
                                                        console.log(`[VERIFY ALARMS] ⏰ Zakres: ${minTime} → ${maxTime}`)
                                                    }
                                                    
                                                    // 🔥 Wyświetl teoretyczny zakres (teraz - hoursBack do teraz)
                                                    const now = new Date()
                                                    const hoursBackMs = hoursBack * 60 * 60 * 1000
                                                    const startTime = new Date(now.getTime() - hoursBackMs)
                                                    const endTimeStr = now.toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(',', '')
                                                    const startTimeStr = startTime.toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(',', '')
                                                    console.log(`[VERIFY ALARMS] 📅 Pełny zakres weryfikacji: ${startTimeStr} → ${endTimeStr} (${hoursBack}h wstecz)`)
                                                    
                                                    // 🔥 Wyświetl tylko pierwsze 3 alarmy (zamiast całej listy) - script-error listener
                                                    const firstThreeAlarms = alarmLines.slice(0, 3)
                                                    if (firstThreeAlarms.length > 0) {
                                                        console.log(`[VERIFY ALARMS] 🔔 Pierwsze ${firstThreeAlarms.length} alarmy:`)
                                                        firstThreeAlarms.forEach((line, index) => {
                                                            console.log(`  ${index + 1}. ${line}`)
                                                        })
                                                        if (alarmLines.length > 3) {
                                                            console.log(`  ... i ${alarmLines.length - 3} więcej`)
                                                        }
                                                    }
                                                    
                                                    // 🔥 Wyświetl ostatnie 3 alarmy
                                                    const lastThreeAlarms = alarmLines.slice(-3)
                                                    if (alarmLines.length > 3) {
                                                        console.log(`[VERIFY ALARMS] 🔚 Ostatnie ${lastThreeAlarms.length} alarmy:`)
                                                        lastThreeAlarms.forEach((line, index) => {
                                                            console.log(`  ${index + 1}. ${line}`)
                                                        })
                                                    }
                                                    
                                                    // Wyświetl karty SIP
                                                    console.log(`[VERIFY ALARMS] 📌 Karty SIP: ${Array.from(sipCards).sort().join(', ')}`)
                                                } else if (deviceResult.alarm_count === 0) {
                                                    console.log(`[VERIFY ALARMS] ✅ Brak alarmów dla ${hostname}`)
                                                    if (tableRow) {
                                                        tableRow.alarms = '-'
                                                    }
                                                    
                                                    // 🔥 Wyświetl error jeśli istnieje
                                                    if (deviceResult.error) {
                                                        console.log(`[VERIFY ALARMS] ❌ Błąd: ${deviceResult.error}`)
                                                    }
                                                    
                                                    // 🔥 Wyświetl ostatnie 3 linii z raw logu
                                                    if (deviceResult.tmpfs_logs) {
                                                        const allLines = deviceResult.tmpfs_logs.split('\n').filter(l => l.trim())
                                                        const lastLines = allLines.slice(-3)
                                                        if (lastLines.length > 0) {
                                                            console.log(`[VERIFY ALARMS] 📝 Ostatnie ${lastLines.length} linii z logu:`)
                                                            lastLines.forEach((line, idx) => {
                                                                console.log(`    ${idx + 1}. ${line}`)
                                                            })
                                                        }
                                                    }
                                                } else if (deviceResult.error) {
                                                    console.log(`[VERIFY ALARMS] ❌ Błąd dla ${hostname}: ${deviceResult.error}`)
                                                    if (tableRow) {
                                                        tableRow.alarms = `Błąd: ${deviceResult.error}`
                                                    }
                                                }
                                            }
                                            
                                            const progress = Math.round((completedDevices.size / totalDevices) * 100)
                                            verificationProgress.value = progress
                                            verificationStatus.value = `⚠️ ${completedDevices.size}/${totalDevices} urządzeń (z błędami)`
                                        }
                                    }
                                }
                            } else {
                                // Licz błąd jako próbę
                                if (deviceHostnames.length > completedDevices.size) {
                                    const hostname = deviceHostnames[completedDevices.size]
                                    completedDevices.add(hostname)
                                    const progress = Math.round((completedDevices.size / totalDevices) * 100)
                                    verificationProgress.value = progress
                                    verificationStatus.value = `⚠️ ${completedDevices.size}/${totalDevices} urządzeń (z błędami)`
                                }
                            }
                        } catch (_parseErr) {
                            // Błąd parsowania - też licz jako próbę
                            if (deviceHostnames.length > completedDevices.size) {
                                const hostname = deviceHostnames[completedDevices.size]
                                completedDevices.add(hostname)
                                const progress = Math.round((completedDevices.size / totalDevices) * 100)
                                verificationProgress.value = progress
                                verificationStatus.value = `⚠️ ${completedDevices.size}/${totalDevices} urządzeń (z błędami)`
                            }
                        }
                    }
                } catch (err) {
                    console.error('[VERIFY ALARMS] Error handling script-error event:', err)
                }
            })
        } catch (err) {
            console.error('[VERIFY ALARMS] Error setting up event listeners:', err)
        }
        
        // Uruchom skrypty SEKWENCYJNIE - jedno urządzenie po drugim
        for (let index = 0; index < deviceHostnames.length; index++) {
            const hostname = deviceHostnames[index]
            try {
                const startTime = new Date().toLocaleTimeString('pl-PL')
                console.log(`[VERIFY ALARMS] ⏱️ START ${startTime} - Starting verification for device ${index + 1}/${totalDevices}: ${hostname}`)

                await runScriptAsync({
                    script: 'modules-cmts_tmpfs_controller',
                    method: 'verify_tmpfs_alarms',
                    payload: { devices: [hostname], hoursBack }
                })

                console.log(`[VERIFY ALARMS] Async script started for ${hostname}`)
            } catch (error) {
                console.error(`[VERIFY ALARMS] Error starting script for ${hostname}:`, error)
            }
            // after each start, wait a short moment to let backend register progress
            await new Promise(resolve => setTimeout(resolve, 200))
        }

        const completionTimeoutMs = Math.max(180000, totalDevices * 30000)
        const waitStart = Date.now()
        while (completedDevices.size < totalDevices && Date.now() - waitStart < completionTimeoutMs) {
            await new Promise(resolve => setTimeout(resolve, 500))
        }

        if (completedDevices.size < totalDevices) {
            const endTime = new Date().toLocaleTimeString('pl-PL')
            console.warn(`[VERIFY ALARMS] ⏱️ END ${endTime} - Timeout waiting for devices (${completedDevices.size}/${totalDevices}) after ${Math.round(completionTimeoutMs / 1000)}s`)
        }
        
        verificationProgress.value = 100
        verificationStatus.value = '✅ Wszystkie urządzenia sprawdzono. Wyniki w konsoli.'
        console.log('[VERIFY ALARMS] All scripts completed successfully')
        
        // Schowaj pasek po 3 sekundach
        await new Promise(resolve => setTimeout(resolve, 3000))
        
        // Oczyść event listenery
        if (scriptFinishedListener) scriptFinishedListener()
        if (scriptErrorListener) scriptErrorListener()
        
    } catch (error) {
        console.error('[VERIFY ALARMS] Error during verification startup:', error)
        verificationStatus.value = '❌ Błąd podczas uruchamiania weryfikacji'
    } finally {
        isVerifyingAlarms.value = false
        verificationProgress.value = 0
        verificationStatus.value = ''
    }
}

// Funkcja przerwania weryfikacji
const cancelVerification = () => {
    console.log('[CANCEL] User requested verification cancellation')
    isVerificationCancelled.value = true
    verificationStatus.value = 'Przerwanie procesu...'
}

// Funkcja przerwania synchronizacji
const cancelSync = () => {
    console.log('[CANCEL] User requested sync cancellation')
    isSyncCancelled.value = true
    syncStatus.value = 'Przerwanie procesu...'
    isSyncingDevices.value = false
    syncProgress.value = 0
}

// Funkcja sprawdzenia logów restartów (OIR events)
const checkRestartLogs = async (deviceHostname) => {
    if (isCheckingRestartLogs.value[deviceHostname]) return
    
    isCheckingRestartLogs.value[deviceHostname] = true
    console.log(`[CHECK RESTART LOGS] Executing show log for device: ${deviceHostname}`)
    
    try {
        // Znajdź urządzenie w devices
        const device = devices.value.find(d => d.hostname === deviceHostname)
        if (!device) {
            console.error(`[CHECK RESTART LOGS] Device ${deviceHostname} not found in devices.json`)
            return
        }
        
        // Use API /api/devices/command (GET) to fetch restart logs
        try {
            const params = new URLSearchParams({ device_id: device.id, command: 'terminal length 0\nshow log | include %IOSXE_OIR-6' })
            const apiResp = await requestJson(`/api/devices/command?${params}`, { timeoutMs: 120000 })
            console.log(`[CHECK RESTART LOGS] API response for ${deviceHostname}:`, apiResp)

            let parsed = apiResp
            if (typeof parsed === 'string') {
                try { parsed = JSON.parse(parsed) } catch (e) { /* keep string */ }
            }

            let output = null
            if (parsed && typeof parsed === 'object') {
                output = parsed.output || (parsed.result && parsed.result.output) || (parsed.result && parsed.result)
            } else if (typeof parsed === 'string') {
                output = parsed
            }

            if (output) {
                const cleaned = output.split('\n').filter(l => {
                    const t = l.trim()
                    return !(t.startsWith(`${deviceHostname}#show log`) || t === `${deviceHostname}#show log | include %IOSXE_OIR-6`)
                }).join('\n')

                const oirData = extractOIREventsFiltered(cleaned, cmtsTmpfsSettings.value?.restartLookback)
                updateCardRestartStatusesForDevice(deviceHostname, oirData.slotStates)
                // Record last restart timestamps per slot from events
                try {
                    const now = new Date()
                    const prefix = `${deviceHostname}-`
                    oirData.events.forEach(ev => {
                        const slotMatch = ev.match(/slot\s+(\d+)|SIP\/(\d+)/i)
                        if (!slotMatch) return
                        const slot = slotMatch[1] || slotMatch[2]
                        const stateMatch = ev.toLowerCase()
                        if (stateMatch.includes('online') || stateMatch.includes('inserted') || stateMatch.includes('powered')) {
                            const ts = parseLogTimestamp(ev)
                            if (ts) {
                                const key = `${prefix}SIP/${slot}`
                                const prev = cardRestartTimestamps.value[key] ? new Date(cardRestartTimestamps.value[key]) : null
                                if (!prev || ts > prev) {
                                    cardRestartTimestamps.value = { ...cardRestartTimestamps.value, [key]: ts.toISOString() }
                                }
                            }
                        }
                    })
                } catch (e) {
                    console.warn('[CHECK RESTART LOGS] Failed to record restart timestamps', e)
                }
                logFilteredOirEvents(deviceHostname, oirData)
                console.log(`[CHECK RESTART LOGS] ${deviceHostname} • Slot states snapshot:`, oirData.slotStates)
                restartLogsMessages.value[deviceHostname] = ''
            } else {
                console.error(`[CHECK RESTART LOGS] No output from API for ${deviceHostname}`)
                restartLogsMessages.value[deviceHostname] = 'Błąd: brak outputu z urządzenia'
            }
        } catch (err) {
            console.error(`[CHECK RESTART LOGS] Error calling /api/devices/command for ${deviceHostname}:`, err)
            restartLogsMessages.value[deviceHostname] = `Błąd: ${err?.message || err}`
        }
        
    } catch (error) {
        console.error(`[CHECK RESTART LOGS] Error executing show log for ${deviceHostname}:`, error)
        restartLogsMessages.value[deviceHostname] = `Błąd: ${error.message}`
    } finally {
        isCheckingRestartLogs.value[deviceHostname] = false
    }
}

// Funkcja sprawdzenia logów restartów dla konkretnej karty
const checkRestartLogsForCard = async (deviceHostname, cardName) => {
    const key = `${deviceHostname}-${cardName}`
    if (isCheckingRestartLogsForCard.value[key]) return
    
    isCheckingRestartLogsForCard.value[key] = true
    console.log(`[CHECK RESTART LOGS FOR CARD] Executing show log for device: ${deviceHostname}, card: ${cardName}`)
    
    try {
        // Znajdź urządzenie w devices
        const device = devices.value.find(d => d.hostname === deviceHostname)
        if (!device) {
            console.error(`[CHECK RESTART LOGS FOR CARD] Device ${deviceHostname} not found in devices.json`)
            return
        }
        
        // Use API /api/devices/command (GET) to fetch restart logs for card
        try {
            const params = new URLSearchParams({ device_id: device.id, command: 'terminal length 0\nshow log | include %IOSXE_OIR-6' })
            const apiResp = await requestJson(`/api/devices/command?${params}`, { timeoutMs: 120000 })
            console.log(`[CHECK RESTART LOGS FOR CARD] API response for ${deviceHostname}:`, apiResp)

            let parsed = apiResp
            if (typeof parsed === 'string') {
                try { parsed = JSON.parse(parsed) } catch (e) { /* keep string */ }
            }

            let output = null
            if (parsed && typeof parsed === 'object') {
                output = parsed.output || (parsed.result && parsed.result.output) || (parsed.result && parsed.result)
            } else if (typeof parsed === 'string') {
                output = parsed
            }

            if (output) {
                const cleaned = output.split('\n').filter(l => {
                    const t = l.trim()
                    return !(t.startsWith(`${deviceHostname}#show log`) || t === `${deviceHostname}#show log | include %IOSXE_OIR-6`)
                }).join('\n')

                const oirData = extractOIREventsFiltered(cleaned, cmtsTmpfsSettings.value?.restartLookback)
                updateCardRestartStatusesForDevice(deviceHostname, oirData.slotStates)

                const cardSlot = extractSlotNumberFromCardName(cardName)
                const cardEvents = oirData.events.filter(event => event.includes(`slot ${cardSlot}`))
                console.log(`[CHECK RESTART LOGS FOR CARD] Found ${cardEvents.length} OIR events for ${cardName} in last ${oirData.hoursBack}h:`)
                cardEvents.forEach((event, idx) => console.log(`  ${idx + 1}. ${event}`))

                // Record last restart timestamp for this specific card from events
                try {
                    if (cardEvents.length) {
                        const sipCard = cardName.includes('/') ? cardName : `SIP/${cardSlot}`
                        const tsPrefixKey = `${deviceHostname}-${sipCard}`
                        cardEvents.forEach(ev => {
                            const ts = parseLogTimestamp(ev)
                            if (!ts) return
                            const prev = cardRestartTimestamps.value[tsPrefixKey] ? new Date(cardRestartTimestamps.value[tsPrefixKey]) : null
                            if (!prev || ts > prev) {
                                cardRestartTimestamps.value = { ...cardRestartTimestamps.value, [tsPrefixKey]: ts.toISOString() }
                            }
                        })
                    }
                } catch (e) {
                    console.warn(`[CHECK RESTART LOGS FOR CARD] Failed to record timestamp for ${key}:`, e)
                }

                if (cardSlot && oirData.slotStates[cardSlot]) {
                    cardRestartStatus.value[key] = oirData.slotStates[cardSlot]
                }

                restartLogsMessages.value[key] = ''
            } else {
                console.error(`[CHECK RESTART LOGS FOR CARD] No output from API for ${deviceHostname}`)
                restartLogsMessages.value[key] = 'Błąd: brak outputu z urządzenia'
            }
        } catch (err) {
            console.error(`[CHECK RESTART LOGS FOR CARD] Error calling /api/devices/command for ${deviceHostname}:`, err)
            restartLogsMessages.value[key] = `Błąd: ${err?.message || err}`
        }
        
    } catch (error) {
        console.error(`[CHECK RESTART LOGS FOR CARD] Error executing show log for ${deviceHostname}:`, error)
        restartLogsMessages.value[key] = `Błąd: ${error.message}`
    } finally {
        isCheckingRestartLogsForCard.value[key] = false
    }
}

const updateCardRestartStatusesForDevice = (deviceHostname, slotStates) => {
    if (!deviceHostname || !slotStates || !Object.keys(slotStates).length) {
        return
    }

    const deviceRow = tableData.value.find(row => row.device === deviceHostname)
    if (!deviceRow || !deviceRow.alarms) {
        return
    }

    const alarmLines = deviceRow.alarms.split('\n').filter(line => line.trim())

    alarmLines.forEach(line => {
        const sipCard = getSipCardFromLine(line)
        if (!sipCard) return
        const slotNumber = sipCard.replace('SIP/', '')
        if (slotStates[slotNumber]) {
            cardRestartStatus.value[`${deviceHostname}-${sipCard}`] = slotStates[slotNumber]
        }
    })
}

// Funkcja wyciągania numeru slotu z nazwy karty (np. "SIP (cc) - slot 3" → "3" lub "SIP/2" → "2")
const extractSlotNumberFromCardName = (cardName) => {
    // Spróbuj format "slot N"
    let match = cardName.match(/slot\s+(\d+)/)
    if (match) return match[1]
    
    // Spróbuj format "SIP/N" lub "CC/N"
    match = cardName.match(/([A-Z]+)\/(\d+)/)
    if (match) return match[2]
    
    // Spróbuj format ze znakiem spacji "SIP (cc) - N"
    match = cardName.match(/slot\s+(\d+)|\/(\d+)/)
    if (match) return match[1] || match[2]
    
    return null
}

// Funkcja parsowania timestampu z logi
const parseLogTimestamp = (logLine) => {
    try {
        // Format: "Nov  6 04:13:37.413: %IOSXE_OIR-6-..."
        // Wyciągnij pierwszych 15 znaków: "Nov  6 04:13:37"
        const dateStr = logLine.substring(0, 15).trim()
        
        // Sparsuj "Nov  6 04:13:37" do Date
        const now = new Date()
        const parsed = new Date(`${now.getFullYear()} ${dateStr}`)
        
        // Jeśli parsed jest w przyszłości, to z ubiegłego roku
        if (parsed > now) {
            parsed.setFullYear(now.getFullYear() - 1)
        }
        
        return parsed
    } catch (error) {
        return null
    }
}

    // Czy karta została zrestartowana w ostatnim `restartLookback` godzin?
    const isCardRecentlyRestarted = (deviceHostname, sipCard) => {
        if (!deviceHostname || !sipCard) return false
        const key = `${deviceHostname}-${sipCard}`
        const ts = cardRestartTimestamps.value[key]
        if (!ts) return false
        const d = new Date(ts)
        if (isNaN(d.getTime())) return false
        const hours = Number(cmtsTmpfsSettings.value?.restartLookback) > 0 ? Number(cmtsTmpfsSettings.value.restartLookback) : 12
        const cutoff = new Date(Date.now() - hours * 60 * 60 * 1000)
        return d >= cutoff
    }

const formatConsoleTimestamp = (date) => {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
        return 'nieznany'
    }
    return date.toLocaleString('pl-PL', {
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    }).replace(',', '')
}

const logFilteredOirEvents = (contextLabel, oirData) => {
    if (!oirData) {
        return
    }

    const {
        events = [],
        hoursBack,
        windowStart,
        windowEnd,
        eventsOutsideWindow = []
    } = oirData

    const startLabel = formatConsoleTimestamp(windowStart)
    const endLabel = formatConsoleTimestamp(windowEnd)
    const prefix = `[CHECK RESTART LOGS] ${contextLabel}`

    console.log(`${prefix} • Zakres analizy (${hoursBack}h): ${startLabel} → ${endLabel}`)

    if (events.length > 0) {
        console.log(`${prefix} • Logi w zakresie (${events.length} wpisów):`)
        events.forEach((event, idx) => {
            console.log(`  ${idx + 1}. ${event}`)
        })
    } else {
        console.log(`${prefix} • Brak logów w zadanym zakresie`)
        if (eventsOutsideWindow.length > 0) {
            const preview = eventsOutsideWindow.slice(-3)
            console.log(`${prefix} • Najnowsze wpisy spoza zakresu (${preview.length}):`)
            preview.forEach((event, idx) => {
                console.log(`  ${idx + 1}. ${event}`)
            })
        }
    }
}

const extractOIREventsFiltered = (rawOutput, overrideHoursBack) => {
    const hoursBack = Number(overrideHoursBack) > 0
        ? Number(overrideHoursBack)
        : (Number(cmtsTmpfsSettings.value?.hoursBack) > 0 ? Number(cmtsTmpfsSettings.value.hoursBack) : 12)
    const events = []
    const eventsOutsideWindow = []
    const slotStates = {}

    const windowEnd = new Date()
    const windowStart = new Date(windowEnd.getTime() - hoursBack * 60 * 60 * 1000)

    if (!rawOutput || typeof rawOutput !== 'string') {
        return { events, hoursBack, slotStates, windowStart, windowEnd, eventsOutsideWindow }
    }

    const now = new Date()
    const cutoff = windowStart

    const classifySlotState = (line) => {
        const normalized = line.toLowerCase()
        if (normalized.includes('online') || normalized.includes('inserted') || normalized.includes('powered')) {
            return 'RESTARTED'
        }
        if (normalized.includes('offline') || normalized.includes('removed') || normalized.includes('shutdown')) {
            return 'NOT_RESTARTED'
        }
        return null
    }

    rawOutput.split('\n').forEach((line) => {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.includes('%IOSXE_OIR-6')) {
            return
        }

        const timestamp = parseLogTimestamp(trimmed)
        if (timestamp && timestamp < cutoff) {
            eventsOutsideWindow.push(trimmed)
            return
        }

        events.push(trimmed)

        const slotMatch = trimmed.match(/slot\s+(\d+)|SIP\/(\d+)/i)
        if (slotMatch) {
            const slot = slotMatch[1] || slotMatch[2]
            const state = classifySlotState(trimmed)
            if (state) {
                slotStates[slot] = state
            } else if (!slotStates[slot]) {
                slotStates[slot] = 'NOT_RESTARTED'
            }
        }
    })

    return { events, hoursBack, slotStates, windowStart, windowEnd, eventsOutsideWindow }
}

// Funkcja obsługi show platform dla urządzenia
const showPlatform = async (deviceHostname, options = {}) => {
    const { deferRefresh = false } = options
    if (isPlatformLoading.value[deviceHostname]) return
    
    isPlatformLoading.value[deviceHostname] = true
    console.log(`[SHOW PLATFORM] Executing show platform for device: ${deviceHostname}`)
    
    try {
        // Znajdź urządzenie w devices
        const device = devices.value.find(d => d.hostname === deviceHostname)
        if (!device) {
            console.error(`[SHOW PLATFORM] Device ${deviceHostname} not found in devices.json`)
            return
        }
        
        // Znajdź informacje o alarmach dla tego urządzenia w tabeli
        const deviceRow = tableData.value.find(row => row.device === deviceHostname)
        let alarmsInfo = null
        
        if (deviceRow && deviceRow.alarms && deviceRow.alarms !== '-' && deviceRow.alarms !== 'Brak alarmów') {
            // Parsuj informacje o alarmach, szukaj slotów/kart
            console.log(`[SHOW PLATFORM] Device ${deviceHostname} alarms info:`, deviceRow.alarms)
            alarmsInfo = deviceRow.alarms
        }
        
        // Wykonaj komendę show platform przez API /api/devices/command (GET)
        let apiResult = null
        try {
            const params = new URLSearchParams({ device_id: device.id, command: 'show platform' })
            apiResult = await requestJson(`/api/devices/command?${params}`, { timeoutMs: 120000 })
        } catch (err) {
            console.error(`[SHOW PLATFORM] Error calling /api/devices/command for ${deviceHostname}:`, err)
        }

        console.log(`[SHOW PLATFORM] API response for ${deviceHostname}:`, apiResult)

        if (apiResult) {
            try {
                let parsed = apiResult
                if (typeof parsed === 'string') {
                    try { parsed = JSON.parse(parsed) } catch (e) { /* keep string */ }
                }

                let output = null
                if (parsed && typeof parsed === 'object') {
                    output = parsed.output || (parsed.result && parsed.result.output) || (parsed.result && parsed.result)
                } else if (typeof parsed === 'string') {
                    output = parsed
                }

                if (output) {
                    const slotStates = extractSlotStates(output, alarmsInfo)
                    await updateAlarmsWithStatus(deviceHostname, alarmsInfo, slotStates, { deferRefresh })
                    console.log(`[SHOW PLATFORM] Updated alarms for ${deviceHostname} with slot states:`, slotStates)
                } else {
                    console.error(`[SHOW PLATFORM] No output from API for ${deviceHostname}`)
                }
            } catch (parseError) {
                console.error(`[SHOW PLATFORM] Error parsing API response:`, parseError)
            }
        } else {
            console.error('[SHOW PLATFORM] No response from device API')
        }
        
    } catch (error) {
        console.error(`[SHOW PLATFORM] Error executing show platform for ${deviceHostname}:`, error)
    } finally {
        isPlatformLoading.value[deviceHostname] = false
    }
}

// Funkcja wyciągania statusów slotów z output show platform
const extractSlotStates = (rawOutput, alarmsInfo) => {
    try {
        const lines = rawOutput.split('\n')
        const slotStates = {}
        let inSlotSection = false
        
        // Wyciągnij sloty z alarmsInfo jeśli są dostępne
        let targetSlots = []
        if (alarmsInfo) {
            const slotMatches = alarmsInfo.match(/\b\d+(?:\/\d+)?\b/g)
            if (slotMatches) {
                targetSlots = slotMatches.map(slot => {
                    if (slot.startsWith('SIP/')) {
                        return slot.replace('SIP/', '')
                    }
                    return slot
                })
            }
        }
        
        for (const line of lines) {
            if (line.includes('Slot') && line.includes('Type') && line.includes('State')) {
                inSlotSection = true
                continue
            }
            
            if (line.includes('CPLD Version') || line.includes('-----')) {
                if (line.includes('CPLD Version')) {
                    inSlotSection = false
                }
                continue
            }
            
            if (inSlotSection && line.trim()) {
                const parts = line.trim().split(/\s+/)
                if (parts.length >= 3) {
                    const slot = parts[0]
                    const state = parts[2]
                    
                    // Sprawdź czy slot jest w targetSlots
                    if (targetSlots.length > 0) {
                        const shouldInclude = targetSlots.some(targetSlot => {
                            return slot === targetSlot || 
                                   slot.startsWith(targetSlot + '/') ||
                                   targetSlot.startsWith(slot + '/')
                        })
                        
                        if (shouldInclude) {
                            slotStates[slot] = state
                        }
                    }
                }
            }
        }
        
        return slotStates
    } catch (error) {
        console.error('[EXTRACT SLOT STATES] Error parsing platform output:', error)
        return {}
    }
}

// Funkcja aktualizacji kolumny Alarms o statusy slotów
const updateAlarmsWithStatus = async (deviceHostname, alarmsInfo, slotStates, options = {}) => {
    try {
        const { deferRefresh = false } = options
        if (!alarmsInfo || !slotStates || Object.keys(slotStates).length === 0) {
            return
        }
        
        // Znajdź wiersz w tabeli dla tego urządzenia
        const deviceRow = tableData.value.find(row => row.device === deviceHostname)
        if (!deviceRow) {
            return
        }
        
        // Parsuj istniejące karty SIP
        const sipCards = alarmsInfo.split('\n').filter(line => line.trim())
        const updatedCards = []
        
        for (const card of sipCards) {
            if (card.startsWith('SIP/')) {
                // Wyciągnij tylko numer SIP (usuń poprzednie statusy)
                const sipMatch = card.match(/^SIP\/(\d+)/)
                if (sipMatch) {
                    const slotNumber = sipMatch[1]
                    const state = slotStates[slotNumber] || slotStates[slotNumber + '/1'] || 'unknown'
                    updatedCards.push(`SIP/${slotNumber} ${state}`)
                } else {
                    updatedCards.push(card)
                }
            } else {
                updatedCards.push(card)
            }
        }
        
        // Zaktualizuj kolumnę alarms
        deviceRow.alarms = updatedCards.join('\n')
        
        if (!deferRefresh) {
            tableKey.value++
            await saveTableDataToFile()
        }
        
        console.log(`[UPDATE ALARMS] Updated ${deviceHostname} alarms:`, deviceRow.alarms)
        
    } catch (error) {
        console.error('[UPDATE ALARMS] Error updating alarms:', error)
    }
}

// Funkcja aktualizacji statusu pojedynczej karty SIP
const updateSingleSipStatus = async (deviceHostname, sipCard, slotState, options = {}) => {
    try {
    const { deferRefresh = false } = options
        // Znajdź wiersz w tabeli dla tego urządzenia
        const deviceRow = tableData.value.find(row => row.device === deviceHostname)
        if (!deviceRow || !deviceRow.alarms) {
            return
        }
        
        // Parsuj istniejące linie alarmów
        const alarmLines = deviceRow.alarms.split('\n').filter(line => line.trim())
        const updatedLines = []
        
        for (const line of alarmLines) {
            // Sprawdź czy linia dotyczy naszej karty SIP
            if (line.includes(sipCard)) {
                // Zaktualizuj status tej karty
                const state = slotState || 'unknown'
                updatedLines.push(`${sipCard} ${state}`)
            } else {
                // Zostaw pozostałe linie bez zmian
                updatedLines.push(line)
            }
        }
        
        // Zaktualizuj kolumnę alarms
        deviceRow.alarms = updatedLines.join('\n')
        
        if (!deferRefresh) {
            tableKey.value++
        }
        
        console.log(`[UPDATE SIP] Updated ${sipCard} on ${deviceHostname} with status: ${slotState}`)
        
    } catch (error) {
        console.error(`[UPDATE SIP] Error updating ${sipCard} status:`, error)
    }
}
</script>

<style scoped>
.cmts-tmpfs {
    padding: 20px;
    height: 100%;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.text-input-section {
    display: flex;
    gap: 10px;
}

.input-button {
    background-color: #2196F3;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
}

.input-button:hover {
    background-color: #1976D2;
}

.clear-button {
    background-color: #f44336;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
}

.clear-button:hover {
    background-color: #d32f2f;
}

.add-all-cmts-button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
    margin-left: 10px;
}

.add-all-cmts-button:hover:not(:disabled) {
    background-color: #45a049;
}

.add-all-cmts-button:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
}

.add-missing-button {
    background-color: #FF9800;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
}

.add-missing-button:hover:not(:disabled) {
    background-color: #F57C00;
}

.add-missing-button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
}

.sync-devices-button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
}

.sync-devices-button:hover:not(:disabled) {
    background-color: #45a049;
}

.sync-devices-button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
}

.verify-alarms-button {
    background-color: #2196F3;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
}

.verify-alarms-button:hover:not(:disabled) {
    background-color: #1976D2;
}

.verify-alarms-button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
}

.check-all-statuses-button {
    background-color: #9C27B0;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
    margin-left: 10px;
}

.check-all-statuses-button:hover:not(:disabled) {
    background-color: #7B1FA2;
}

.check-all-statuses-button.active {
    background-color: #4CAF50;
    box-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
}

.check-all-statuses-button.active:hover {
    background-color: #45a049;
}

.check-all-statuses-button:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
}

/* Modal styles */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal-content {
    background-color: white;
    border-radius: 8px;
    padding: 0;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    max-width: 80%;
    max-height: 80%;
    display: flex;
    flex-direction: column;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid #ddd;
}

.modal-header h3 {
    margin: 0;
    color: #333;
}

.close-button {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #666;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.close-button:hover {
    color: #333;
}

.modal-body {
    padding: 20px;
    flex: 1;
    overflow: auto;
}

.modal-body textarea {
    width: 100%;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px;
    font-family: monospace;
    font-size: 12px;
    resize: vertical;
    min-height: 300px;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 20px;
    border-top: 1px solid #ddd;
}

.cancel-button {
    background-color: #f5f5f5;
    color: #666;
    padding: 10px 20px;
    border: 1px solid #ddd;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.cancel-button:hover {
    background-color: #e0e0e0;
}

.confirm-button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.confirm-button:hover {
    background-color: #45a049;
}

/* Table styles */
.table-container {
    height: 80%;
    overflow-y: auto;
    border: 1px solid #374151;
    border-radius: 4px;
}

table {
    width: 100%;
    border-collapse: collapse;
    background-color: transparent;
    color: #e6eef8;
    table-layout: fixed; /* Wymusza stałe szerokości kolumn */
}

/* Szerokości kolumn */
th:nth-child(1), td:nth-child(1) { /* CMTS */
    width: 30%;
}

th:nth-child(2), td:nth-child(2) { /* Status */
    width: 50%;
}

th:nth-child(3), td:nth-child(3) { /* Actions */
    width: 20%;
}

th, td {
    padding: 12px;
    text-align: center;
    border: 1px solid #374151;
    vertical-align: middle;
    height: auto;
    color: #e6eef8;
}

tr {
    height: auto;
}

tbody tr {
    vertical-align: middle;
}

th {
    background-color: #0f1724;
    font-weight: bold;
    position: sticky;
    top: 0;
    z-index: 1;
    color: #e6eef8;
}

.section-header {
    background-color: #0f1724;
    text-align: center;
    font-weight: bold;
    border: 1px solid #374151;
    color: #e6eef8;
}

tr:hover {
    background-color: rgba(230,238,248,0.03);
}

.device-cell { 
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 100%;
    min-height: 100%;
}

.warning-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    background-color: #f44336;
    color: white;
    border-radius: 50%;
    font-size: 12px;
    font-weight: bold;
    cursor: help;
    flex-shrink: 0;
}

.warning-icon::before {
    content: "!";
}

.status-icon {
    font-size: 16px;
    margin-left: 5px;
    cursor: help;
    flex-shrink: 0;
}

.no-data {
    text-align: center;
    color: #cbd5e1;
    margin-top: 40px;
    font-size: 16px;
}

.loading {
    text-align: center;
    color: #cbd5e1;
    margin-top: 40px;
    font-size: 16px;
}

/* Status badge for alarms/status column */
.status-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 6px;
}
.status-badge.status-ok {
    background-color: #10b981; /* green-500 */
    color: white;
}
.status-badge.status-error {
    background-color: #ef4444; /* red-500 */
    color: white;
}

/* Style dla statusu alarmów TMPFS */
.alarm-status-alarm {
    color: #dc3545;
    font-weight: bold;
}

.alarm-status-ok {
    color: #28a745;
    font-weight: bold;
}

.alarm-status-error {
    color: #ffc107;
    font-weight: bold;
}

.alarms-cell {
    white-space: pre-line;
    vertical-align: middle;
    width: 20%;
    padding: 8px;/* Fixed width dla kolumny Status */
    text-align: left; /* Wyrównanie do lewej zamiast center */
    
}

.alarms-cell.connection-error {
    color: #dc3545;
    font-weight: bold;
    background-color: #f8d7da;
}

.alarms-cell.verification-error {
    color: #dc3545;
    font-style: italic;
}

/* Alarms with refresh buttons */
.alarms-with-buttons {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 100%;
}

.alarm-line {
    display: flex;
    align-items: center;
    gap: 4px; /* Zmniejszony gap między przyciskami a tekstem */
    width: 100%;
    transition: opacity 0.2s;
}

.alarm-line-dismissed {
    opacity: 0.3;
    pointer-events: none;
}

.alarm-line-dismissed .dismiss-button {
    pointer-events: auto;
    opacity: 1;
}

.refresh-button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 14px;
    padding: 2px;
    border-radius: 3px;
    transition: background-color 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
}

.refresh-button:hover:not(:disabled) {
    background-color: #e9ecef;
}

.refresh-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.dismiss-button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 13px;
    padding: 2px;
    border-radius: 3px;
    transition: background-color 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    color: #999;
}

.dismiss-button:hover {
    background-color: #f8d7da;
    color: #c62828;
}

.card-buttons {
    display: flex;
    gap: 1px; /* Zmniejszony odstęp między przyciskami */
    align-items: center;
    flex-shrink: 0; /* Nie pozwól przyciskąm się kurczyć */
}

.restart-button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 14px;
    padding: 2px;
    border-radius: 3px;
    transition: background-color 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
}

.restart-button:hover:not(:disabled) {
    background-color: #fff3cd;
}

.restart-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.check-restart-button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 14px;
    padding: 2px;
    border-radius: 3px;
    transition: background-color 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
}

.check-restart-button:hover:not(:disabled) {
    background-color: #cfe2ff;
}

.check-restart-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.restart-status {
    margin-left: 4px;
    font-size: 12px;
    font-weight: bold;
    display: inline-block;
    white-space: nowrap;
}

.restart-status-success {
    color: #2e7d32;
}

.restart-status-fail {
    color: #c62828;
}

.restart-log-message {
    margin-top: 4px;
    font-size: 12px;
    line-height: 1.3;
    color: #1f3a93;
    white-space: pre-line;
}

.alarm-text {
    flex: 1;
    line-height: 1.2;
    margin-left: 4px; /* Mały margines od przycisków */
    text-align: left; /* Wyrównanie do lewej */
}

.actions-cell {
    text-align: center;
    padding: 8px;
}

.platform-button {
    background: #007bff;
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: background-color 0.2s;
}

.platform-button:hover:not(:disabled) {
    background: #0056b3;
}

.platform-button:disabled {
    background: #6c757d;
    cursor: not-allowed;
}

/* Restart Status Check Button */
.restart-status-button {
    background: #fd7e14;
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: background-color 0.2s;
    margin-bottom: 4px;
}

.restart-status-button:hover:not(:disabled) {
    background: #e06c00;
}

.restart-status-button:disabled {
    background: #6c757d;
    cursor: not-allowed;
}

/* Actions Container - holds all buttons vertically */
.actions-container {
    display: flex;
    flex-direction: column;
    gap: 4px;
    align-items: center;
}

.sip-button {
    background: #28a745;
    color: white;
    border: none;
    padding: 4px 8px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 11px;
    transition: background-color 0.2s;
    white-space: nowrap;
}

.sip-button:hover:not(:disabled) {
    background: #1e7e34;
}

.sip-button:disabled {
    background: #6c757d;
    cursor: not-allowed;
}

.no-action {
    color: #6c757d;
    font-style: italic;
}

/* Progress Bar Styles */
.progress-container {
    margin: 20px 0;
    padding: 15px;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
}

/* Progress Overlay - appears on top */
.progress-overlay {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 9999;
    background: white;
    border: 2px solid #007bff;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    min-width: 400px;
    max-width: 600px;
}

.progress-overlay::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: -1;
}

.progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.progress-status {
    font-size: 14px;
    font-weight: 500;
    color: #495057;
}

.progress-percentage {
    font-size: 14px;
    font-weight: bold;
    color: #007bff;
}

.progress-bar-container {
    width: 100%;
    height: 20px;
    background: #e9ecef;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #007bff 0%, #0056b3 100%);
    border-radius: 10px;
    transition: width 0.3s ease-in-out;
    box-shadow: 0 1px 3px rgba(0, 123, 255, 0.3);
}

.progress-bar.complete {
    background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
}

.progress-actions {
    margin-top: 15px;
    text-align: center;
}

.cancel-process-button {
    background: #dc3545;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: background-color 0.2s;
}

.cancel-process-button:hover:not(:disabled) {
    background: #c82333;
}

.cancel-process-button:disabled {
    background: #6c757d;
    cursor: not-allowed;
    opacity: 0.6;
}
</style>