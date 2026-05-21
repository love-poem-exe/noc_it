<template>
    <div class="modules-settings">
        <h2>Modules Settings</h2>
        
        <div class="module-tabs">
            <button 
                v-for="module in modules" 
                :key="module.id"
                :class="['tab-btn', { active: activeModule === module.id }]"
                @click="activeModule = module.id"
            >
                {{ module.name }}
            </button>
        </div>
        
        <div class="module-content">
            <!-- CMTS TMPFS Settings -->
            <div v-if="activeModule === 'cmts-tmpfs'" class="module-panel">
                <h3>CMTS TMPFS Settings</h3>
                <div v-if="saveMessage" class="save-status" :class="saveSuccess ? 'save-ok' : 'save-err'">{{ saveMessage }}</div>
                <div class="setting-group">
                    <label for="tmpfs-hours">Godziny wstecz dla alarmów TMPFS:</label>
                    <input 
                        id="tmpfs-hours"
                        type="number" 
                        min="1" 
                        max="168"
                        v-model.number="settings.cmtsTmpfs.hoursBack"
                    />
                    <button 
                        class="save-btn" 
                        @click="saveSettings"
                        :disabled="isSaving"
                    >
                        {{ isSaving ? 'Zapisywanie...' : 'Zapisz' }}
                    </button>
                    <span class="setting-description">
                        Określa ile godzin wstecz sprawdzać alarmy TMPFS (domyślnie 2h, maksymalnie 168h = 7 dni)
                    </span>
                </div>
                <div class="setting-group">
                    <label for="tmpfs-restart-hours">Godziny wstecz dla restartów kart SIP:</label>
                    <input
                        id="tmpfs-restart-hours"
                        type="number"
                        min="1"
                        max="168"
                        v-model.number="settings.cmtsTmpfs.restartLookback"
                    />
                    <button 
                        class="save-btn" 
                        @click="saveSettings"
                        :disabled="isSaving"
                    >
                        {{ isSaving ? 'Zapisywanie...' : 'Zapisz' }}
                    </button>
                    <span class="setting-description">
                        Określa ile godzin wstecz brać pod uwagę przy wykrywaniu restartów kart SIP (domyślnie 12h)
                    </span>
                </div>
                <div class="setting-group">
                    <label for="sip-slot">Numer karty SIP do restartu:</label>
                    <input
                        id="sip-slot"
                        type="number"
                        min="0"
                        v-model.number="sipSlotNumber"
                    />
                    <button 
                        class="save-btn" 
                        @click="restartSipDevice"
                        :disabled="isRestarting"
                    >
                        {{ isRestarting ? 'Restartowanie...' : 'Restartuj SIP' }}
                    </button>
                    <span class="setting-description">
                        Wprowadź numer karty SIP, aby wysłać polecenie restartu.
                    </span>
                </div>
            </div>
            
            <!-- CMTS Compare Settings -->
            <div v-if="activeModule === 'cmts-compare'" class="module-panel">
                <h3>CMTS Compare Settings</h3>
                <div v-if="saveMessage" class="save-status" :class="saveSuccess ? 'save-ok' : 'save-err'">{{ saveMessage }}</div>
                <div class="setting-group">
                    <label for="cmts-compare-threshold">Próg offline dla alarmów (%):</label>
                    <input
                        id="cmts-compare-threshold"
                        type="number"
                        min="1"
                        max="100"
                        v-model.number="settings.cmtsCompare.offlineThreshold"
                    />
                    <button
                        class="save-btn"
                        @click="saveSettings"
                        :disabled="isSaving"
                    >
                        {{ isSaving ? 'Zapisywanie...' : 'Zapisz' }}
                    </button>
                    <span class="setting-description">
                        Minimalna procentowa liczba offline modemów w grupie upstream, aby wyświetlić alarm (domyślnie 80%).
                    </span>
                </div>
                <div class="setting-group">
                    <label for="cmts-compare-timeout">Limit czasu polecenia (sekundy):</label>
                    <input
                        id="cmts-compare-timeout"
                        type="number"
                        min="10"
                        max="300"
                        v-model.number="settings.cmtsCompare.commandTimeout"
                    />
                    <button
                        class="save-btn"
                        @click="saveSettings"
                        :disabled="isSaving"
                    >
                        {{ isSaving ? 'Zapisywanie...' : 'Zapisz' }}
                    </button>
                    <span class="setting-description">
                        Maksymalny czas oczekiwania na odpowiedź CMTS przy wykonaniu polecenia (domyślnie 120 s).
                    </span>
                </div>
            </div>

            <!-- Placeholder for other modules -->
            <div v-else-if="!['cmts-tmpfs','cmts-compare'].includes(activeModule)" class="module-panel">
                <h3>{{ modules.find(m => m.id === activeModule)?.name }} Settings</h3>
                <p>Ustawienia dla tego modułu będą dodane w przyszłości.</p>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { requestJson } from '../../services/ApiClient'

const activeModule = ref('cmts-tmpfs')

const modules = [
    { id: 'cmts-tmpfs', name: 'CMTS TMPFS' },
    { id: 'cmts-compare', name: 'CMTS Compare' },
    { id: 'cmts-swapper', name: 'CMTS Swapper' },
    { id: 'console', name: 'Console' }
]

const settings = ref({
    cmtsTmpfs: {
        hoursBack: 2
        , restartLookback: 12
    },
    cmtsCompare: {
        offlineThreshold: 80,
        commandTimeout: 120
    },
    general: {
        autoRefresh: true,
        debugMode: false
    }
})

const isSaving = ref(false)
const saveMessage = ref('')
const saveSuccess = ref(null)

const sipSlotNumber = ref(0)
const isRestarting = ref(false)

const loadSettings = async () => {
    try {
        console.log('[MODULES SETTINGS] Loading settings using backend controller...')
        
        // Użyj backend controller do wczytania ustawień
        const result = await requestJson('/api/modules/settings', {
            timeoutMs: 10000
        })
        
        console.log('[MODULES SETTINGS] Backend response:', result)
        
        if (result && typeof result === 'object') {
            settings.value = { ...settings.value, ...result }
            // Ensure restartLookback exists for cmtsTmpfs (backwards compatibility)
            try {
                const rl = Number(settings.value.cmtsTmpfs?.restartLookback)
                if (Number.isNaN(rl) || rl <= 0) {
                    settings.value.cmtsTmpfs = { ...(settings.value.cmtsTmpfs || {}), restartLookback: 12 }
                }
            } catch (e) {
                settings.value.cmtsTmpfs = { ...(settings.value.cmtsTmpfs || {}), restartLookback: 12 }
            }
            console.log('[MODULES SETTINGS] Settings loaded from backend:', result)
        } else if (result && typeof result === 'string') {
            // Backend może zwrócić JSON w konsoli lub error
            const lines = result.split('\n')
            let loadedSettings = null
            
            for (const line of lines) {
                try {
                    // Spróbuj sparsować każdą linię jako JSON
                    const parsed = JSON.parse(line)
                    if (parsed && typeof parsed === 'object' && !parsed.error) {
                        loadedSettings = parsed
                        break
                    }
                } catch {
                    // Ignoruj linie które nie są JSON
                    continue
                }
            }
            
            if (loadedSettings) {
                // Merge z domyślnymi ustawieniami
                settings.value = { ...settings.value, ...loadedSettings }
                console.log('[MODULES SETTINGS] Settings loaded from backend:', loadedSettings)
            } else {
                console.log('[MODULES SETTINGS] No valid settings in backend response, using defaults')
            }
        } else {
            console.log('[MODULES SETTINGS] Invalid backend response, using defaults')
        }
        
    } catch (error) {
        console.error('[MODULES SETTINGS] Error loading settings from backend:', error)
        console.log('[MODULES SETTINGS] Using default settings')
    }
}

const saveSettings = async () => {
    try {
        isSaving.value = true
        console.log('[MODULES SETTINGS] Saving settings:', settings.value)
        
        // Przygotuj dane do zapisania jako JSON string
        const settingsJSON = JSON.stringify(settings.value)
        console.log('[MODULES SETTINGS] Settings JSON:', settingsJSON)
        
        // Zapisz ustawienia przez API
        const result = await requestJson('/api/modules/settings', {
            method: 'PUT',
            body: settings.value,
            timeoutMs: 10000
        })
        
        console.log('[MODULES SETTINGS] Backend response:', result)
        
        if (result && (result.success === true || (typeof result === 'string' && (result.includes('"success": true') || result.includes('SUCCESS'))))) {
            console.log('[MODULES SETTINGS] Settings saved successfully')
            saveMessage.value = 'Ustawienia zapisane'
            saveSuccess.value = true
        } else {
            console.error('[MODULES SETTINGS] Backend returned error:', result)
            saveMessage.value = 'Błąd podczas zapisywania: ' + (typeof result === 'string' ? result : JSON.stringify(result))
            saveSuccess.value = false
        }
        
    } catch (error) {
        console.error('[MODULES SETTINGS] Error saving settings:', error)
        saveMessage.value = 'Błąd podczas zapisywania: ' + (error?.message || String(error))
        saveSuccess.value = false
    } finally {
        isSaving.value = false
        // Clear message after 4 seconds
        setTimeout(() => {
            saveMessage.value = ''
            saveSuccess.value = null
        }, 4000)
    }
}

const restartSipDevice = async (deviceHostname, slotNumber, options = {}) => {
    const { deferRefresh = false } = options;
    if (isPlatformLoading.value[deviceHostname]) return;

    isPlatformLoading.value[deviceHostname] = true;
    console.log(`[SIP RESTART] Checking status for device: ${deviceHostname}, slot: ${slotNumber}`);

    try {
        // Find the device in devices
        const device = devices.value.find(d => d.hostname === deviceHostname);
        if (!device) {
            console.error(`[SIP RESTART] Device ${deviceHostname} not found in devices.json`);
            return;
        }

        // Execute the status check command via API
        let apiResult = null;
        try {
            const params = new URLSearchParams({ device_id: device.id, command: `show platform slot ${slotNumber}` });
            apiResult = await requestJson(`/api/devices/command?${params}`, { timeoutMs: 120000 });
        } catch (err) {
            console.error(`[SIP RESTART] Error calling /api/devices/command for ${deviceHostname}:`, err);
        }

        console.log(`[SIP RESTART] API response for ${deviceHostname}, slot ${slotNumber}:`, apiResult);

        if (apiResult) {
            try {
                let parsed = apiResult;
                if (typeof parsed === 'string') {
                    try { parsed = JSON.parse(parsed); } catch (e) { /* keep string */ }
                }

                let output = null;
                if (parsed && typeof parsed === 'object') {
                    output = parsed.output || (parsed.result && parsed.result.output) || (parsed.result && parsed.result);
                } else if (typeof parsed === 'string') {
                    output = parsed;
                }

                if (output) {
                    console.log(`[SIP RESTART] Device ${deviceHostname}, slot ${slotNumber} status output:`, output);
                } else {
                    console.error(`[SIP RESTART] No output from API for ${deviceHostname}, slot ${slotNumber}`);
                }
            } catch (parseError) {
                console.error(`[SIP RESTART] Error parsing API response:`, parseError);
            }
        } else {
            console.error('[SIP RESTART] No response from device API');
        }
    } catch (error) {
        console.error(`[SIP RESTART] Error executing status check for ${deviceHostname}, slot ${slotNumber}:`, error);
    } finally {
        isPlatformLoading.value[deviceHostname] = false;
    }
}

onMounted(async () => {
    await loadSettings()
})
</script>

<style scoped>
.modules-settings {
    padding: 20px;
    max-width: 800px;
}

.module-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    border-bottom: 2px solid #e0e0e0;
}

.tab-btn {
    padding: 10px 20px;
    background: none;
    border: none;
    cursor: pointer;
    border-bottom: 3px solid transparent;
    font-size: 16px;
    transition: all 0.3s ease;
}

.tab-btn:hover {
    background-color: #f5f5f5;
}

.tab-btn.active {
    border-bottom-color: #007bff;
    color: #007bff;
    font-weight: bold;
}

.module-content {
    padding: 20px 0;
}

.module-panel h3 {
    margin-bottom: 20px;
    color: #333;
}

.setting-group {
    margin-bottom: 20px;
    padding: 15px;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    background-color: #f9f9f9;
}

.setting-group label {
    display: block;
    font-weight: bold;
    margin-bottom: 10px;
    color: #333;
}

.setting-group input {
    padding: 8px 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 16px;
    width: 100px;
    margin-right: 10px;
}

.save-btn {
    background-color: #28a745;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    transition: background-color 0.3s;
    margin-right: 10px;
}

.save-btn:hover:not(:disabled) {
    background-color: #218838;
}

.save-btn:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
}

.setting-description {
    display: block;
    margin-top: 8px;
    font-size: 14px;
    color: #666;
    font-style: italic;
}

.save-status {
    margin: 10px 0 16px 0;
    padding: 8px 12px;
    border-radius: 4px;
}
.save-ok {
    background: #e6f4ea;
    color: #155724;
    border: 1px solid #c3e6cb;
}
.save-err {
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}
</style>
