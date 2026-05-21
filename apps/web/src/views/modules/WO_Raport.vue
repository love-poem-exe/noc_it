<template>
    <div class="wo-raport">
        <div class="header">
            <h1>WO Raport</h1>
            <div class="import-section">
                <input
                    type="file"
                    ref="fileInput"
                    accept=".xlsx,.xls"
                    style="display: none"
                    @change="handleFileImport"
                />
                <button class="import-button" @click="triggerFileInput">
                    Importuj plik WO Raport
                </button>
                <button
                    v-if="tableData.length || closedData.length"
                    class="edit-toggle-button"
                    :class="{ 'edit-active': isEditing }"
                    @click="isEditing = !isEditing"
                >
                    {{ isEditing ? 'Anuluj edycję' : 'Edytuj' }}
                </button>
            </div>
        </div>

        <!-- Modal wykonawcy -->
        <div v-if="wykonawcaModal.visible" class="modal-overlay">
            <div class="modal">
                <h3>Podaj wykonawcę</h3>
                <p class="modal-hint">Pole "Wykonawca" jest puste. Wpisz wykonawcę przed rozpoczęciem prac.</p>
                <input
                    v-model="wykonawcaInput"
                    class="modal-input"
                    type="text"
                    placeholder="Nazwa wykonawcy..."
                    @keydown.enter="confirmWykonawca"
                    autofocus
                />
                <div class="modal-actions">
                    <button class="modal-option-btn" :disabled="!wykonawcaInput.trim()" @click="confirmWykonawca">Zapisz</button>
                    <button class="modal-cancel" @click="skipWykonawca">Anuluj</button>
                </div>
            </div>
        </div>

        <!-- Modal wyboru statusu zakończenia -->
        <div v-if="zakModal.visible" class="modal-overlay" @click.self="cancelZakModal">
            <div class="modal">
                <h3>Wybierz status zakończenia</h3>
                <div class="modal-options">
                    <button
                        v-for="opt in ZAK_OPCJE"
                        :key="opt"
                        class="modal-option-btn"
                        @click="confirmZakModal(opt)"
                    >{{ opt }}</button>
                </div>
                <button class="modal-cancel" @click="cancelZakModal">Anuluj</button>
            </div>
        </div>

        <!-- Modal edycji wiersza -->
        <div v-if="rowEditModal.visible" class="modal-overlay" @click.self="closeRowEditModal">
            <div class="modal row-edit-modal">
                <div class="row-edit-header">
                    <h3>Edycja pracy</h3>
                    <button class="modal-close-x" @click="closeRowEditModal">&times;</button>
                </div>

                <!-- Górna 1/3 – dane pracy -->
                <div class="row-edit-top">
                    <div class="row-edit-top-inner">
                        <!-- lewa: pola danych -->
                        <div class="row-edit-grid">
                            <div v-for="col in displayColumns" :key="col" class="row-edit-field" :class="{ 'field-title': col === 'Tytuł' }">
                                <label>{{ col }}</label>
                                <div v-if="col === 'Status'" class="row-edit-status">
                                    <button class="status-arrow" :class="{ 'status-arrow-disabled': rowEditModal.data['Status'] === 'Wczytano' }" :disabled="rowEditModal.data['Status'] === 'Wczytano'" @click="changeStatus(rowEditModal.rowIndex, -1); rowEditModal.data = { ...tableData[rowEditModal.rowIndex] }">&lt;</button>
                                    <span class="status-label" :class="statusClass(rowEditModal.data['Status'])">{{ rowEditModal.data['Status'] }}</span>
                                    <button class="status-arrow" @click="changeStatus(rowEditModal.rowIndex, 1); rowEditModal.data = { ...tableData[rowEditModal.rowIndex] }">&gt;</button>
                                </div>
                                <input v-else type="text" v-model="rowEditModal.data[col]" class="row-edit-input" />
                            </div>
                        </div>

                        <!-- prawa: załączniki -->
                        <div class="attachments-section">
                            <div class="attachments-header">
                                <span class="przebieg-label">Załączniki</span>
                                <label class="attach-add-btn">
                                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="6" y1="1" x2="6" y2="11"/><line x1="1" y1="6" x2="11" y2="6"/></svg>
                                    Dodaj plik
                                    <input type="file" multiple accept=".txt,.xlsx,.xls,.jpg,.jpeg,.png,.gif,.bmp,.webp" style="display:none" @change="addAttachments" />
                                </label>
                            </div>
                            <div v-if="rowEditModal.data._zalaczniki && rowEditModal.data._zalaczniki.length" class="attachments-list">
                                <div v-for="(f, i) in rowEditModal.data._zalaczniki" :key="i" class="attachment-item">
                                    <svg v-if="f.type === 'image'" width="13" height="13" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="3" width="16" height="14" rx="2"/><circle cx="7" cy="8" r="1.5"/><path d="M2 14l4-4 3 3 3-4 6 5"/></svg>
                                    <svg v-else-if="f.type === 'excel'" width="13" height="13" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="2" width="14" height="16" rx="1.5"/><path d="M7 7l6 6M13 7l-6 6"/></svg>
                                    <svg v-else width="13" height="13" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="2" width="12" height="16" rx="1.5"/><line x1="7" y1="7" x2="13" y2="7"/><line x1="7" y1="10" x2="13" y2="10"/><line x1="7" y1="13" x2="11" y2="13"/></svg>
                                    <span class="attachment-name">{{ f.name }}</span>
                                    <button class="attachment-preview-btn" @click="previewFile(f)" title="Podgląd">Podgląd</button>
                                    <button class="attachment-remove-btn" @click="removeAttachment(i)" title="Usuń">&times;</button>
                                </div>
                            </div>
                            <div v-else class="attachments-empty">Brak załączników</div>
                        </div>
                    </div>
                </div>

                <!-- Dolne 2/3 – notatki -->
                <div class="row-edit-bottom">
                    <div class="row-edit-bottom-header">
                        <label class="przebieg-label">{{ showOpis ? 'Opis prac' : 'Notatki' }}</label>
                        <button
                            class="toggle-opis-btn"
                            :class="{ active: showOpis }"
                            @click="showOpis = !showOpis"
                        >{{ showOpis ? 'Ukryj opis' : 'Wyświetl opis prac' }}</button>
                    </div>
                    <pre v-if="showOpis" class="opis-readonly">{{ rowEditModal.data._opis || '(Brak opisu prac w danych źródłowych)' }}</pre>
                    <textarea v-else v-model="rowEditModal.data['_notatki']" class="row-edit-textarea" placeholder="Dodaj notatki..."></textarea>
                </div>

                <div class="modal-actions row-edit-actions">
                    <button class="reb-save" @click="saveRowEdit">Zapisz</button>
                    <button class="reb-cancel" @click="closeRowEditModal">Anuluj</button>
                </div>
            </div>
        </div>

        <!-- Modal podglądu załącznika -->
        <div v-if="previewModal.visible" class="modal-overlay preview-overlay" @click.self="previewModal.visible = false">
            <div class="preview-modal">
                <div class="preview-modal-header">
                    <span class="preview-modal-title">{{ previewModal.name }}</span>
                    <button class="modal-close-x" @click="previewModal.visible = false">&times;</button>
                </div>
                <div class="preview-modal-body">
                    <img v-if="previewModal.type === 'image'" :src="previewModal.dataUrl" class="preview-image" />
                    <pre v-else-if="previewModal.type === 'text'" class="preview-text">{{ previewModal.text }}</pre>
                    <div v-else class="preview-no-preview">
                        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="#9ca3af" stroke-width="1.5"><rect x="8" y="4" width="24" height="32" rx="3"/><line x1="14" y1="14" x2="26" y2="14"/><line x1="14" y1="20" x2="26" y2="20"/><line x1="14" y1="26" x2="22" y2="26"/></svg>
                        <p>Podgląd niedostępny dla plików Excel.</p>
                        <a :download="previewModal.name" :href="previewModal.dataUrl" class="preview-download-btn">Pobierz plik</a>
                    </div>
                </div>
            </div>
        </div>

        <div v-if="tableData.length" class="table-container">
            <table>
                <thead>
                    <tr>
                        <th v-for="col in displayColumns" :key="col">{{ col }}</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, index) in tableData" :key="index" :class="rowClass(row['Status'])">
                        <template v-for="col in displayColumns" :key="col">
                            <td v-if="col === 'Status'" class="status-cell">
                                <button class="status-arrow" :class="{ 'status-arrow-disabled': row['Status'] === 'Wczytano' }" :disabled="row['Status'] === 'Wczytano'" @click="changeStatus(index, -1)">&lt;</button>
                                <span class="status-label" :class="statusClass(row['Status'])">{{ row['Status'] }}</span>
                                <button class="status-arrow" @click="changeStatus(index, 1)">&gt;</button>
                            </td>
                            <td v-else
                                :contenteditable="isEditing"
                                class="editable-cell"
                                :class="{ 'cell-readonly': !isEditing }"
                                @blur="isEditing && onCellEdit($event, index, col)"
                                @keydown.enter.prevent="isEditing && $event.target.blur()"
                                @keydown="isEditing && onCellKeydown($event, col)"
                                @input="isEditing && onCellInput($event, col)"
                            >{{ row[col] }}</td>
                        </template>
                        <td class="action-cell">
                            <button class="row-edit-btn" @click="openRowEditModal(index)">Edytuj</button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Tabela zakończonych prac -->
        <div v-if="closedData.length" class="closed-section">
            <button class="closed-toggle" @click="closedVisible = !closedVisible">
                {{ closedVisible ? '▾' : '▸' }} Zakończone prace ({{ closedData.length }})
            </button>
            <div v-if="closedVisible" class="table-container closed-table">
                <table>
                    <thead>
                        <tr>
                            <th v-for="col in closedDisplayColumns" :key="col">{{ col }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, ci) in closedData" :key="ci" class="row-zamknieto">
                            <template v-for="col in closedDisplayColumns" :key="col">
                                <td v-if="col === 'Status'" class="status-cell">
                                    <button class="status-arrow" @click="restoreRow(ci)" title="Przywróć">↩</button>
                                    <span class="status-label status-zamknieto">Zamknięto</span>
                                </td>
                                <td v-else-if="col === 'Data zamknięcia'" class="editable-cell">{{ row._closedAt }}</td>
                                <td v-else-if="col === 'Uwagi'" class="editable-cell uwagi-cell">{{ row._uwagi }}</td>
                                <td v-else class="editable-cell">{{ row[col] }}</td>
                            </template>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div v-if="fileSelected && !tableData.length" class="loading">
            Wczytywanie danych...
        </div>
        <div v-if="!fileSelected && !tableData.length && !closedData.length" class="no-data">
            Wybierz plik WO Raport aby rozpocząć
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const CACHE_KEY_TABLE  = 'wo_raport_tableData'
const CACHE_KEY_CLOSED = 'wo_raport_closedData'

const STATUSES = ['Wczytano', 'W gotowości', 'W trakcie', 'Zakończono', 'Zamknięto']
const ZAK_OPCJE = ['Zakończono zgodnie z planem', 'Nie odbyły się', 'Nie zakończono planowo']
const closedData = ref([])
const closedVisible = ref(false)
const zakModal = ref({ visible: false, rowIndex: null, dir: null })
const wykonawcaModal = ref({ visible: false, rowIndex: null })
const wykonawcaInput = ref('')

function confirmWykonawca() {
    const val = wykonawcaInput.value.trim()
    if (!val) return
    tableData.value[wykonawcaModal.value.rowIndex]['Wykonawca'] = val
    tableData.value[wykonawcaModal.value.rowIndex]['Status'] = 'W trakcie'
    wykonawcaModal.value.visible = false
    wykonawcaInput.value = ''
}

function skipWykonawca() {
    // Anuluj — status zostaje bez zmian (W gotowości)
    wykonawcaModal.value.visible = false
    wykonawcaInput.value = ''
}

function cancelZakModal() {
    zakModal.value.visible = false
    zakModal.value.rowIndex = null
}

function confirmZakModal(opcja) {
    const row = tableData.value[zakModal.value.rowIndex]
    row['Status'] = opcja
    row['_uwagi'] = opcja
    zakModal.value.visible = false
    zakModal.value.rowIndex = null
}

function rowClass(status) {
    const map = {
        'Wczytano':                    'row-wczytano',
        'W gotowości':                 'row-gotowosci',
        'W trakcie':                   'row-trakcie',
        'Zakończono zgodnie z planem': 'row-zakonczone',
        'Nie odbyły się':             'row-zakonczone',
        'Nie zakończono planowo':      'row-zakonczone',
    }
    return map[status] || ''
}

function changeStatus(rowIndex, dir) {
    const row = tableData.value[rowIndex]
    const current = STATUSES.indexOf(row['Status'])
    // Jeśli aktualny status nie jest w STATUSES (np. podstatus zakończenia), traktuj jak "Zakończono"
    const currentIdx = current === -1 ? STATUSES.indexOf('Zakończono') : current
    const next = (currentIdx + dir + STATUSES.length) % STATUSES.length
    const nextStatus = STATUSES[next]
    if (nextStatus === 'Zamknięto') {
        const now = new Date()
        const pad = n => String(n).padStart(2, '0')
        const closedAt = `${pad(now.getDate())}.${pad(now.getMonth()+1)}.${now.getFullYear()} ${pad(now.getHours())}:${pad(now.getMinutes())}`
        row['Status'] = 'Zamknięto'
        closedData.value.push({ ...row, _closedAt: closedAt, _uwagi: row['_uwagi'] || '' })
        tableData.value.splice(rowIndex, 1)
    } else if (nextStatus === 'Zakończono') {
        zakModal.value = { visible: true, rowIndex }
    } else {
        if (nextStatus === 'W trakcie' && !row['Wykonawca']?.toString().trim()) {
            wykonawcaModal.value = { visible: true, rowIndex }
            // NIE zmieniaj statusu — zostaje W gotowości do czasu potwierdzenia
        } else {
            row['Status'] = nextStatus
        }
    }
}

function restoreRow(closedIndex) {
    const row = { ...closedData.value[closedIndex], Status: 'Zakończono' }
    closedData.value.splice(closedIndex, 1)
    tableData.value.push(row)
}

const CELL_MAX_DIGITS = { 'WO': 7, 'NEF': 7, 'NMS': 6 }

function onCellKeydown(event, col) {
    const limit = CELL_MAX_DIGITS[col]
    if (!limit) return
    const allowed = ['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab']
    if (allowed.includes(event.key)) return
    // Blokuj znaki niebędące cyframi
    if (!/^\d$/.test(event.key)) {
        event.preventDefault()
        return
    }
    // Blokuj gdy osiągnięto limit
    const text = event.target.innerText.replace(/\s/g, '')
    if (text.length >= limit) {
        event.preventDefault()
    }
}

function onCellInput(event, col) {
    const limit = CELL_MAX_DIGITS[col]
    if (!limit) return
    const el = event.target
    const text = el.innerText.replace(/\D/g, '').slice(0, limit)
    if (el.innerText !== text) {
        el.innerText = text
        // Przesuń kursor na koniec
        const range = document.createRange()
        const sel = window.getSelection()
        range.selectNodeContents(el)
        range.collapse(false)
        sel.removeAllRanges()
        sel.addRange(range)
    }
}

function onCellEdit(event, rowIndex, col) {
    const raw = event.target.innerText.trim()

    // Walidacja
    if (col === 'WO' || col === 'NEF') {
        if (raw !== '' && !/^\d{7}$/.test(raw)) {
            alert(`Pole "${col}" musi zawierać dokładnie 7 cyfr.`)
            event.target.innerText = tableData.value[rowIndex][col]
            return
        }
    }
    if (col === 'NMS') {
        if (raw !== '' && !/^\d{6}$/.test(raw)) {
            alert('Pole "NMS" musi zawierać dokładnie 6 cyfr.')
            event.target.innerText = tableData.value[rowIndex][col]
            return
        }
    }

    tableData.value[rowIndex][col] = raw
}

function statusClass(status) {
    const map = {
        'Wczytano':                    'status-wczytano',
        'W gotowości':                 'status-gotowosci',
        'W trakcie':                   'status-trakcie',
        'Zakończono zgodnie z planem': 'status-zakonczone',
        'Nie odbyły się':             'status-zakonczone',
        'Nie zakończono planowo':      'status-zakonczone',
        'Zamknięto':                   'status-zamknieto',
    }
    return map[status] || ''
}

const fileInput = ref(null)
const tableData = ref([])
const fileSelected = ref(false)
const isEditing = ref(false)
const rowEditModal = ref({ visible: false, rowIndex: null, data: {} })

function openRowEditModal(index) {
    showOpis.value = false
    rowEditModal.value = {
        visible: true,
        rowIndex: index,
        data: { ...tableData.value[index], _zalaczniki: [...(tableData.value[index]._zalaczniki || [])] }
    }
}

function closeRowEditModal() {
    rowEditModal.value.visible = false
    rowEditModal.value.rowIndex = null
    rowEditModal.value.data = {}
}

function saveRowEdit() {
    const idx = rowEditModal.value.rowIndex
    if (idx === null) return
    tableData.value[idx] = { ...rowEditModal.value.data }
    closeRowEditModal()
}

// Załączniki
const previewModal = ref({ visible: false, name: '', type: '', dataUrl: '', text: '' })
const showOpis = ref(false)

function addAttachments(e) {
    const files = Array.from(e.target.files)
    if (!rowEditModal.value.data._zalaczniki) rowEditModal.value.data._zalaczniki = []
    files.forEach(file => {
        const ext = file.name.split('.').pop().toLowerCase()
        const type = ['jpg','jpeg','png','gif','bmp','webp'].includes(ext) ? 'image'
                   : ['xlsx','xls'].includes(ext) ? 'excel' : 'text'
        const reader = new FileReader()
        reader.onload = ev => {
            rowEditModal.value.data._zalaczniki.push({ name: file.name, type, dataUrl: ev.target.result })
        }
        reader.readAsDataURL(file)
    })
    e.target.value = ''
}

function removeAttachment(i) {
    rowEditModal.value.data._zalaczniki.splice(i, 1)
}

function previewFile(f) {
    if (f.type === 'image') {
        previewModal.value = { visible: true, name: f.name, type: 'image', dataUrl: f.dataUrl, text: '' }
    } else if (f.type === 'text') {
        try {
            const base64 = f.dataUrl.split(',')[1]
            const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0))
            const text = new TextDecoder('utf-8').decode(bytes)
            previewModal.value = { visible: true, name: f.name, type: 'text', dataUrl: f.dataUrl, text }
        } catch {
            previewModal.value = { visible: true, name: f.name, type: 'text', dataUrl: f.dataUrl, text: '(Nie można odczytać pliku)' }
        }
    } else {
        previewModal.value = { visible: true, name: f.name, type: 'excel', dataUrl: f.dataUrl, text: '' }
    }
}

// Wczytaj dane z pamięci podręcznej przy powrocie do widoku
onMounted(() => {
    try {
        const savedTable  = localStorage.getItem(CACHE_KEY_TABLE)
        const savedClosed = localStorage.getItem(CACHE_KEY_CLOSED)
        if (savedTable)  tableData.value  = JSON.parse(savedTable)
        if (savedClosed) closedData.value = JSON.parse(savedClosed)
    } catch (e) {
        console.warn('WO Raport: nie udało się wczytać danych z cache:', e)
    }
})

// Zapisuj dane do pamięci podręcznej przy każdej zmianie
watch(tableData,  val => localStorage.setItem(CACHE_KEY_TABLE,  JSON.stringify(val)), { deep: true })
watch(closedData, val => localStorage.setItem(CACHE_KEY_CLOSED, JSON.stringify(val)), { deep: true })

// Mapowanie: klucz Excel → etykieta wyświetlana w tabeli
const DATE_COLUMNS = ['P. data rozpoczęcia', 'P. data zakończenia']

// Konwersja Excel serial number → czytelna data
function excelDateToString(value) {
    if (value === '' || value === null || value === undefined) return ''
    const num = Number(value)
    if (isNaN(num) || num === 0) return value
    // Excel epoch: 1 = 1900-01-01, ale Excel błędnie uznaje 1900 za rok przestępny (+1 dzień korekta)
    const date = new Date(Math.round((num - 25569) * 86400 * 1000))
    if (isNaN(date.getTime())) return value
    const pad = n => String(n).padStart(2, '0')
    return `${pad(date.getUTCDate())}.${pad(date.getUTCMonth() + 1)}.${date.getUTCFullYear()} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`
}

// Wyciąga 6-cyfrowy numer NMS z opisu (po "Numer NMS:")
function extractNMS(opis) {
    if (!opis) return ''
    const match = opis.match(/Numer NMS:\s*(\d{6})/)
    return match ? match[1] : ''
}

const COLUMN_MAP = [
    { from: 'Numer',                      to: 'WO'                          },
    { from: 'NEF nadrzędny',              to: 'NEF'                         },
    { from: 'Tytuł',                      to: 'Tytuł'                       },
    { from: 'Planowana data rozpoczęcia', to: 'P. data rozpoczęcia'  },
    { from: 'Planowana data zakończenia', to: 'P. data zakończenia'  },
    { from: 'Wykonawca',                  to: 'Wykonawca'                   },
    { from: 'NMS',                        to: 'NMS'                         },
    { from: 'Status',                     to: 'Status'                      },
    { from: 'Opis',                       to: '_opis'                       },
]

const displayColumns = COLUMN_MAP.map(c => c.to).filter(c => !c.startsWith('_'))

// Kolumny tabeli zakończonych: daty zastąpione przez Data zamknięcia, dodana kolumna Uwagi
const closedDisplayColumns = computed(() => {
    const DATE_COLS = ['P. data rozpoczęcia', 'P. data zakończenia']
    const base = displayColumns.filter(c => !DATE_COLS.includes(c))
    const statusIdx = base.indexOf('Status')
    const result = [...base]
    result.splice(statusIdx, 0, 'Data zamknięcia')
    result.push('Uwagi')
    return result
})

const triggerFileInput = () => {
    fileInput.value.click()
}

const handleFileImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    fileSelected.value = true

    try {
        const data = await readExcelFile(file)
        if (data && data.length > 0) {
            tableData.value = data
            event.target.value = ''
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
                const rawRows = XLSX.utils.sheet_to_json(firstSheet, { defval: '' })

                // Przemapuj kolumny – zachowaj tylko zdefiniowane, z nowymi etykietami
                const mapped = rawRows.map(row => {
                    const out = {}

                    for (const { from, to } of COLUMN_MAP) {
                        const matchedKey = Object.keys(row).find(
                            k => k.trim().toLowerCase() === from.trim().toLowerCase()
                        )
                        let val = matchedKey !== undefined ? String(row[matchedKey]) : ''
                        if (DATE_COLUMNS.includes(to)) val = excelDateToString(val)
                        if (to === 'Status') val = 'Wczytano'
                        out[to] = val
                    }
                    // NMS wyciągamy z pola _opis po zmapowaniu
                    if (out['_opis']) out['NMS'] = extractNMS(out['_opis'])
                    return out
                })

                resolve(mapped)
            } catch (error) {
                reject(error)
            }
        }

        reader.onerror = (error) => reject(error)
        reader.readAsArrayBuffer(file)
    })
}
</script>

<style scoped>
.wo-raport {
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

.edit-toggle-button {
    background-color: #2d6cdf;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
}

.edit-toggle-button:hover {
    background-color: #1a55c7;
}

.edit-toggle-button.edit-active {
    background-color: #b03030;
}

.edit-toggle-button.edit-active:hover {
    background-color: #8f2020;
}

.cell-readonly {
    cursor: default;
    user-select: text;
}

.cell-readonly:hover {
    cursor: default;
}

/* ── Row edit button ──────────────────────────────────────────────── */
.action-cell {
    text-align: center;
    padding: 4px 6px;
    white-space: nowrap;
}

.row-edit-btn {
    background: #2d6cdf;
    color: #fff;
    border: none;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.2s;
}

.row-edit-btn:hover {
    background: #1a55c7;
}

/* ── Row edit modal ───────────────────────────────────────────────── */
.row-edit-modal {
    width: 100vw;
    max-width: 100vw;
    max-height: 88vh;
    height: 88vh;
    display: flex;
    flex-direction: column;
    padding: 0;
    overflow: hidden;
    background: #f5f6f8;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.35);
    color: #111827;
}

.row-edit-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 18px 10px;
    border-bottom: 1px solid #d1d5db;
    flex-shrink: 0;
    background: #e9ebee;
}

.row-edit-header h3 {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    color: #111827;
}

.modal-close-x {
    background: none;
    border: none;
    color: #6b7280;
    font-size: 20px;
    cursor: pointer;
    line-height: 1;
    padding: 0 2px;
    transition: color 0.15s;
}

.modal-close-x:hover {
    color: #111827;
}

/* Górna 1/3 – dane pracy */
.row-edit-top {
    flex: 1;
    overflow-y: auto;
    padding: 14px 20px;
    border-bottom: 1px solid #d1d5db;
    background: #f5f6f8;
}

.row-edit-field {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.row-edit-field label {
    font-size: 10px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.row-edit-input {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    color: #111827;
    padding: 5px 9px;
    font-size: 12px;
    outline: none;
    transition: border-color 0.15s;
    width: 100%;
}

.row-edit-input:focus {
    border-color: #6b7280;
}

/* Dolne 2/3 – notatki / opis */
.row-edit-bottom {
    flex: 2;
    display: flex;
    flex-direction: column;
    padding: 14px 20px;
    gap: 0;
    background: #f5f6f8;
}

.row-edit-bottom-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
    margin-bottom: 6px;
}

.toggle-opis-btn {
    padding: 3px 12px;
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 600;
    color: #374151;
    cursor: pointer;
    transition: background 0.12s, color 0.12s, border-color 0.12s;
}
.toggle-opis-btn:hover { background: #e5e7eb; }
.toggle-opis-btn.active {
    background: #2d6cdf;
    border-color: #2d6cdf;
    color: #fff;
}

.opis-readonly {
    flex: 1;
    margin: 0;
    padding: 10px 12px;
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    font-family: inherit;
    font-size: 12px;
    line-height: 1.6;
    color: #374151;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-y: auto;
    user-select: text;
}

.przebieg-label {
    font-size: 10px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    flex-shrink: 0;
}

.row-edit-textarea {
    flex: 1;
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    color: #111827;
    padding: 8px 10px;
    font-size: 12px;
    outline: none;
    resize: none;
    font-family: inherit;
    line-height: 1.6;
    transition: border-color 0.15s;
}

.row-edit-textarea:focus {
    border-color: #6b7280;
}

.row-edit-status {
    display: flex;
    align-items: center;
    gap: 6px;
}

/* Akcje modala edycji */
.row-edit-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    padding: 10px 18px;
    border-top: 1px solid #d1d5db;
    background: #e9ebee;
    flex-shrink: 0;
}

.reb-save {
    padding: 7px 20px;
    background: #22c55e;
    border: none;
    border-radius: 5px;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
}
.reb-save:hover { background: #16a34a; }

.reb-cancel {
    padding: 7px 16px;
    background: transparent;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    color: #374151;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
}
.reb-cancel:hover { background: #d1d5db; color: #111827; }

/* ── Załączniki ─────────────────────────────────────────────────── */
.row-edit-top-inner {
    display: flex;
    gap: 16px;
    height: 100%;
}

.row-edit-grid {
    flex: 1;
    min-width: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px 14px;
    align-content: start;
}

.field-title {
    grid-column: 1 / -1;
    order: 99;
}

.attachments-section {
    width: 280px;
    flex-shrink: 0;
    border-left: 1px solid #d1d5db;
    padding-left: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
}

.attachments-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}

.attach-add-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    background: #2d6cdf;
    color: #fff;
    border-radius: 5px;
    font-size: 11.5px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
    user-select: none;
}
.attach-add-btn:hover { background: #1a55c7; }

.attachments-list {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.attachments-empty {
    font-size: 11px;
    color: #9ca3af;
    font-style: italic;
}

.attachment-item {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 5px 10px;
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    font-size: 12px;
    color: #374151;
}

.attachment-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.attachment-preview-btn {
    flex-shrink: 0;
    padding: 3px 10px;
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    font-size: 11px;
    color: #374151;
    cursor: pointer;
    transition: background 0.12s;
}
.attachment-preview-btn:hover { background: #e5e7eb; }

.attachment-remove-btn {
    flex-shrink: 0;
    background: none;
    border: none;
    color: #9ca3af;
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    padding: 0 2px;
    transition: color 0.12s;
}
.attachment-remove-btn:hover { color: #ef4444; }

/* ── Preview modal ──────────────────────────────────────────────── */
.preview-overlay { z-index: 1100; }

.preview-modal {
    background: #1c1f24;
    border: 1px solid #323841;
    border-radius: 10px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.7);
    width: 90vw;
    max-width: 1100px;
    height: 85vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.preview-modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    background: #252a30;
    border-bottom: 1px solid #323841;
    flex-shrink: 0;
}

.preview-modal-title {
    font-size: 12px;
    font-weight: 600;
    color: #e5e7eb;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.preview-modal-body {
    flex: 1;
    overflow: auto;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 16px;
    background: #1c1f24;
}

.preview-image {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    border-radius: 4px;
}

.preview-text {
    width: 100%;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.6;
    color: #e5e7eb;
    margin: 0;
}

.preview-no-preview {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    color: #9ca3af;
    font-size: 13px;
    padding-top: 40px;
}

.preview-download-btn {
    display: inline-block;
    padding: 7px 20px;
    background: #2d6cdf;
    color: #fff;
    border-radius: 5px;
    font-size: 12px;
    font-weight: 600;
    text-decoration: none;
    transition: background 0.15s;
}
.preview-download-btn:hover { background: #1a55c7; }

.table-container {
    max-height: calc(100vh - 150px);
    overflow-y: auto;
    overflow-x: auto;
    border: 1px solid #ddd;
    border-radius: 4px;
}

table {
    width: 100%;
    border-collapse: collapse;
    background-color: white;
}

th, td {
    padding: 8px 10px;
    text-align: center;
    border: 1px solid #ddd;
    white-space: nowrap;
    font-size: 12px;
}

.editable-cell:focus {
    outline: 2px solid #4CAF50;
    background: #f9fff9;
    cursor: text;
    color: #000;
}

.editable-cell:hover:not(.cell-readonly) {
    background: #f5f5f5;
    cursor: text;
}

th {
    background-color: #1e1e1e;
    color: #fff;
    font-weight: bold;
    position: sticky;
    top: 0;
    z-index: 1;
}

tr:hover td {
    filter: brightness(0.93);
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

.status-cell {
    white-space: nowrap;
    text-align: center;
    padding: 4px 6px;
}

.status-arrow {
    background: none;
    border: 1px solid #bbb;
    border-radius: 3px;
    cursor: pointer;
    font-size: 11px;
    padding: 1px 5px;
    color: #444;
    line-height: 1;
}

.status-arrow:hover {
    background: #e8e8e8;
}

.status-arrow-disabled,
.status-arrow:disabled {
    opacity: 0.3;
    cursor: not-allowed;
    pointer-events: none;
}

.status-label {
    display: inline-block;
    min-width: 160px;
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 3px;
    margin: 0 4px;
}

.status-wczytano   { background: #e0e0e0; color: #444; }
.status-gotowosci  { background: #bbdefb; color: #1565c0; }
.status-trakcie    { background: #fff9c4; color: #f57f17; }
.status-zakonczone { background: #c8e6c9; color: #2e7d32; }
.status-zamknieto  { background: #cfd8dc; color: #37474f; }

/* Kolory wierszy */
.row-wczytano   { background-color: #ffffff; color: #000; }
.row-gotowosci  { background-color: #9e9e9e; color: #fff; }
.row-trakcie    { background-color: #f9a825; color: #000; }
.row-zakonczone { background-color: #388e3c; color: #fff; }
.row-zamknieto  { background-color: #eceff1; color: #000; }

.row-wczytano td,
.row-gotowosci td,
.row-trakcie td,
.row-zakonczone td,
.row-zamknieto td {
    background-color: inherit;
    color: inherit;
}

/* Sekcja zamkniętych */
.closed-section {
    margin-top: 24px;
}

.closed-toggle {
    background: none;
    border: 1px solid #bbb;
    border-radius: 4px;
    padding: 6px 14px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    color: #444;
    margin-bottom: 8px;
}

.closed-toggle:hover {
    background: #f0f0f0;
}

.closed-table {
    border: 1px solid #b0bec5;
}

.uwagi-cell {
    font-style: italic;
    color: #444;
}

/* Modal */
.modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal {
    background: #fff;
    border-radius: 8px;
    padding: 28px 32px;
    min-width: 320px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.modal h3 {
    margin: 0;
    font-size: 15px;
    color: #1e1e1e;
}

.modal-options {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.modal-option-btn {
    padding: 10px 16px;
    border: 1px solid #bbb;
    border-radius: 5px;
    background: #f5f5f5;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
    transition: background 0.15s;
}

.modal-option-btn:hover {
    background: #388e3c;
    color: #fff;
    border-color: #388e3c;
}

.modal-cancel {
    margin-top: 4px;
    padding: 7px 16px;
    border: 1px solid #ccc;
    border-radius: 5px;
    background: none;
    cursor: pointer;
    font-size: 12px;
    color: #666;
    align-self: flex-end;
}

.modal-cancel:hover {
    background: #eee;
}

.modal-hint {
    margin: 0;
    font-size: 12px;
    color: #666;
}

.modal-input {
    padding: 8px 10px;
    border: 1px solid #bbb;
    border-radius: 5px;
    font-size: 13px;
    width: 100%;
    box-sizing: border-box;
}

.modal-input:focus {
    outline: 2px solid #4CAF50;
}

.modal-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
}
</style>
