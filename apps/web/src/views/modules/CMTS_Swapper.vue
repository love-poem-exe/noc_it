<template>
    <div class="cmts-swapper">
        <div class="header">
            <h1>CMTS Swapper</h1>
            <div class="import-section">
                <input
                    type="file"
                    ref="fileInput"
                    accept=".xlsx"
                    style="display: none"
                    @change="handleFileImport"
                />
                <button class="import-button" @click="triggerFileInput">
                    Importuj plik BEFORE-AFTER
                </button>
            </div>
        </div>

        <div v-if="tableData.length" class="table-container">
            <table>
                <thead>
                    <tr>
                        <th colspan="3" class="section-header">Przed pracami</th>
                        <th colspan="3" class="section-header">Po pracach</th>
                    </tr>
                    <tr>
                        <th>CMTS</th>
                        <th>Interfejs</th>
                        <th>Node Code</th>
                        <th>CMTS</th>
                        <th>Interfejs</th>
                        <th>Node Code</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, index) in tableData" :key="index">
                        <td :class="{'highlight-cmts': isCmtsInDevices(row['Przed_CMTS'])}">
                            {{ row['Przed_CMTS'] }}
                        </td>
                        <td>{{ row['Przed_Interfejs'] }}</td>
                        <td>{{ row['Przed_Node Code'] }}</td>
                        <td :class="{'highlight-cmts': isCmtsInDevices(row['Po_CMTS'])}">
                            {{ row['Po_CMTS'] }}
                        </td>
                        <td>{{ row['Po_Interfejs'] }}</td>
                        <td>{{ row['Po_Node Code'] }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div v-else-if="fileSelected" class="loading">
            Wczytywanie danych...
        </div>
        <div v-else class="no-data">
            Wybierz plik BEFORE-AFTER aby rozpocząć
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const CACHE_KEY_TABLE = 'cmts_swapper_tableData'

const fileInput = ref(null)
const tableData = ref([])
const fileSelected = ref(false)
const devices = ref([])

const triggerFileInput = () => {
    fileInput.value.click()
}

// Zapisuj tableData do pamięci podręcznej przy każdej zmianie
watch(tableData, val => localStorage.setItem(CACHE_KEY_TABLE, JSON.stringify(val)), { deep: true })

// Wczytaj devices.json przy starcie komponentu + przywróć dane z cache
onMounted(async () => {
    try {
        const saved = localStorage.getItem(CACHE_KEY_TABLE)
        if (saved) tableData.value = JSON.parse(saved)
    } catch (e) {
        console.warn('CMTS Swapper: błąd wczytywania cache:', e)
    }
    try {
        const res = await fetch('../../data/devices.json')
        if (res.ok) {
            devices.value = await res.json()
        }
    } catch {
        devices.value = []
    }
})

// Sprawdź czy CMTS jest w devices.json z typem CMTS
function isCmtsInDevices(cmtsName) {
    if (!cmtsName || !devices.value?.length) return false
    // Loguj wszystkie hostname z devices.json tylko raz
    if (!isCmtsInDevices._loggedAll) {
        const allHostnames = devices.value.map(d => d.hostname).filter(Boolean)
        console.log('wszystkie hostname z pliku devices', allHostnames)
        isCmtsInDevices._loggedAll = true
    }
    // Loguj sprawdzany hostname
    console.log('hostname z tablicy', cmtsName)
    // Sprawdź zarówno po polu hostname jak i name
    const cmtsNameNorm = cmtsName.toString().trim().toLowerCase()
    const found = devices.value.some(
        d =>
            (
                (d.hostname?.toString().trim().toLowerCase() === cmtsNameNorm) ||
                (d.name?.toString().trim().toLowerCase() === cmtsNameNorm)
            ) &&
            d.type?.toString().trim().toLowerCase() === 'cmts'
    )
    // Log do konsoli porównanie
    if (cmtsName) {
        const matches = devices.value
            .filter(d =>
                (d.hostname?.toString().trim().toLowerCase() === cmtsNameNorm ||
                 d.name?.toString().trim().toLowerCase() === cmtsNameNorm)
            )
            .map(d => ({
                hostname: d.hostname,
                name: d.name,
                type: d.type
            }))
        console.log(`[CMTS CHECK] "${cmtsName}"`, { found, matches })
    }
    return found
}

// --- Dodaj logowanie struktur JSON: before: NODE CODE: Interface oraz after: NODE CODE: Interface ---
function logBeforeAfterNodeCodeJson(tableData) {
    const beforeMap = {}
    const afterMap = {}
    for (const row of tableData) {
        const nodeCodeBefore = row['Przed_Node Code']
        const interfejsBefore = row['Przed_Interfejs']
        const cmtsBefore = row['Przed_CMTS']
        if (nodeCodeBefore) {
            beforeMap[nodeCodeBefore] = cmtsBefore
                ? `${cmtsBefore}, ${interfejsBefore}`
                : interfejsBefore
        }
        const nodeCodeAfter = row['Po_Node Code']
        const interfejsAfter = row['Po_Interfejs']
        const cmtsAfter = row['Po_CMTS']
        if (nodeCodeAfter) {
            afterMap[nodeCodeAfter] = cmtsAfter
                ? `${cmtsAfter}, ${interfejsAfter}`
                : interfejsAfter
        }
    }
    // Dodaj dodatkowe urządzenie do beforeMap i afterMap
    beforeMap["DGC313R1"] = "pl-gdy01a-br03, Logical Upstream Channel 13/6.0/0 - Logical Upstream Channel 13/6.5/0"
    afterMap["DGC313R1"] = "pl-gdy01a-br03, Logical Upstream Channel 13/6.0/0 - Logical Upstream Channel 13/6.5/0"
    console.log('before:', JSON.stringify(beforeMap, null, 2))
    console.log('after:', JSON.stringify(afterMap, null, 2))
}

// Grupowanie i zwijanie powtórzeń po Node Code
function groupByNodeCode(rows, prefix) {
    const map = new Map()
    for (const row of rows) {
        const nodeCode = row[`${prefix}_Node Code`]
        if (!nodeCode) continue
        if (!map.has(nodeCode)) {
            map.set(nodeCode, [])
        }
        map.get(nodeCode).push(row)
    }
    const result = []
    for (const [nodeCode, group] of map.entries()) {
        if (!group.length) continue
        const cmts = group[0][`${prefix}_CMTS`] || ''
        const interfejsFirst = group[0][`${prefix}_Interfejs`] || ''
        const interfejsLast = group[group.length - 1][`${prefix}_Interfejs`] || ''
        let interfejs = interfejsFirst
        if (group.length > 1 && interfejsFirst !== interfejsLast) {
            interfejs = `${interfejsFirst} - ${interfejsLast}`
        }
        result.push({
            [`${prefix}_CMTS`]: cmts,
            [`${prefix}_Interfejs`]: interfejs,
            [`${prefix}_Node Code`]: nodeCode
        })
    }
    return result
}

const handleFileImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    fileSelected.value = true
    
    try {
        const data = await readExcelFile(file)
        if (data && data.length > 0) {
            // Grupowanie po Node Code osobno dla "Przed" i "Po"
            const beforeRows = groupByNodeCode(data, 'Przed')
            const afterRows = groupByNodeCode(data, 'Po')

            // Łączenie po indeksie (zakładamy, że kolejność odpowiada)
            const merged = []
            const maxLen = Math.max(beforeRows.length, afterRows.length)
            for (let i = 0; i < maxLen; i++) {
                merged.push({
                    'Przed_CMTS': beforeRows[i]?.['Przed_CMTS'] || '',
                    'Przed_Interfejs': beforeRows[i]?.['Przed_Interfejs'] || '',
                    'Przed_Node Code': beforeRows[i]?.['Przed_Node Code'] || '',
                    'Po_CMTS': afterRows[i]?.['Po_CMTS'] || '',
                    'Po_Interfejs': afterRows[i]?.['Po_Interfejs'] || '',
                    'Po_Node Code': afterRows[i]?.['Po_Node Code'] || ''
                })
            }
            tableData.value = merged

            // Dodaj logowanie JSON do konsoli (before i after)
            logBeforeAfterNodeCodeJson(merged)

            event.target.value = '' // Reset input file
        }
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
                const range = XLSX.utils.decode_range(firstSheet['!ref'])

                // Initialize column mappings
                const columns = {
                    before: {
                        cmts: null,
                        interfejs: null,
                        region: null,
                        nodeCode: null,
                        nodeLocation: null
                    },
                    after: {
                        cmts: null,
                        interfejs: null,
                        nodeCode: null,
                        nodeLocation: null
                    }
                }

                // Find section headers
                let afterSection = -1
                for (let C = range.s.c; C <= range.e.c; C++) {
                    const cell = firstSheet[XLSX.utils.encode_cell({r: 0, c: C})]
                    if (cell) {
                        const value = cell.v.toString().toLowerCase()
                        if (value.includes('po')) afterSection = C
                    }
                }

                // Map columns based on headers
                for (let C = range.s.c; C <= range.e.c; C++) {
                    const cell = firstSheet[XLSX.utils.encode_cell({r: 1, c: C})]
                    if (cell) {
                        const value = cell.v.toString().toLowerCase()
                        if (C < afterSection) {
                            // Before section
                            if (value.includes('cmts')) columns.before.cmts = C
                            if (value.includes('interfejs')) columns.before.interfejs = C
                            if (value.includes('region') || value.includes('hub')) columns.before.region = C
                            if (value.includes('node code')) columns.before.nodeCode = C
                            if (value.includes('node location')) columns.before.nodeLocation = C
                        } else {
                            // After section
                            if (value.includes('cmts')) columns.after.cmts = C
                            if (value.includes('interfejs')) columns.after.interfejs = C
                            if (value.includes('node code')) columns.after.nodeCode = C
                            if (value.includes('node location')) columns.after.nodeLocation = C
                        }
                    }
                }

                const result = []

                // Process data rows
                for (let R = 2; R <= range.e.r; R++) {
                    const row = {
                        'Przed_CMTS': '',
                        'Przed_Interfejs': '',
                        'Przed_Region/HUB': '',
                        'Przed_Node Code': '',
                        'Przed_Node Location': '',
                        'Po_CMTS': '',
                        'Po_Interfejs': '',
                        'Po_Node Code': '',
                        'Po_Node Location': ''
                    }

                    // Helper function to get cell value
                    const getCellValue = (r, c) => {
                        const cell = firstSheet[XLSX.utils.encode_cell({r, c})]
                        return cell ? cell.v : ''
                    }

                    // Fill "Before" data
                    if (columns.before.cmts !== null) row['Przed_CMTS'] = getCellValue(R, columns.before.cmts)
                    if (columns.before.interfejs !== null) row['Przed_Interfejs'] = getCellValue(R, columns.before.interfejs)
                    if (columns.before.region !== null) row['Przed_Region/HUB'] = getCellValue(R, columns.before.region)
                    if (columns.before.nodeCode !== null) row['Przed_Node Code'] = getCellValue(R, columns.before.nodeCode)
                    if (columns.before.nodeLocation !== null) row['Przed_Node Location'] = getCellValue(R, columns.before.nodeLocation)

                    // Fill "After" data
                    if (columns.after.cmts !== null) row['Po_CMTS'] = getCellValue(R, columns.after.cmts)
                    if (columns.after.interfejs !== null) row['Po_Interfejs'] = getCellValue(R, columns.after.interfejs)
                    if (columns.after.nodeCode !== null) row['Po_Node Code'] = getCellValue(R, columns.after.nodeCode)
                    if (columns.after.nodeLocation !== null) row['Po_Node Location'] = getCellValue(R, columns.after.nodeLocation)

                    // Add row only if it contains any data
                    if (Object.values(row).some(v => v !== '')) {
                        result.push(row)
                    }
                }

                resolve(result)
            } catch (error) {
                reject(error)
            }
        }

        reader.onerror = (error) => reject(error)
        reader.readAsArrayBuffer(file)
    })
}

// Przykład jak odczytać samo CMTS z wartości "pl-gdy01a-br03, Logical Upstream Channel 13/6.0/0 - Logical Upstream Channel 13/6.5/0"
function extractCmts(value) {
    if (!value) return ''
    // Jeśli jest przecinek, zwróć pierwszą część (CMTS)
    return value.split(',')[0].trim()
}

// Porównaj hostname z devices.json (tylko SYNCED) i loguj do konsoli
function checkHostnameSync(cmtsValue) {
    const cmts = extractCmts(cmtsValue)
    if (!cmts || !devices.value?.length) return
    const found = devices.value.some(
        d =>
            d.hostname?.toString().trim().toLowerCase() === cmts.toLowerCase() &&
            d.status?.toString().trim().toUpperCase() === 'SYNCED'
    )
    if (found) {
        console.log(`[SYNCED HOSTNAME] "${cmts}" istnieje w devices.json jako SYNCED`)
    }
}

// Przykład użycia:
const example = "pl-gdy01a-br03, Logical Upstream Channel 13/6.0/0 - Logical Upstream Channel 13/6.5/0"
console.log('CMTS:', extractCmts(example)) // wynik: pl-gdy01a-br03
checkHostnameSync(example)
</script>

<style scoped>
.cmts-swapper {
    padding: 20px;
    height: 100%;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
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

.table-container {
    max-height: calc(100vh - 150px);
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 4px;
}

table {
    width: 100%;
    border-collapse: collapse;
    background-color: white;
}

th, td {
    padding: 12px;
    text-align: left;
    border: 1px solid #ddd;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
    position: sticky;
    top: 0;
    z-index: 1;
}

.section-header {
    background-color: #e0e0e0;
    text-align: center;
    font-weight: bold;
    border: 1px solid #ddd;
}

tr:hover {
    background-color: #f9f9f9;
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

.highlight-cmts {
    background-color: #4caf50 !important;
    color: #fff !important;
}
</style>

