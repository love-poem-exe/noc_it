/**
 * useCmtsCompare — business logic & reactive state for the CMTS Compare module.
 * Extracted from CMTS_Compare.vue for better testability and separation of concerns.
 */
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useData } from './useData'
import { requestJson } from '../services/ApiClient'

// ─── Parsing helpers ──────────────────────────────────────────────────────────

/**
 * Parsuje format zapisu "show cable modem" (format NMS):
 *   NMS: …  / CMTS: …  / Interfejsy: … / Data: …
 */
export function parseSavedFile(text) {
    const lines = text.split('\n')
    const header = {}
    let dataStart = 0
    for (let i = 0; i < lines.length; i++) {
        const l = lines[i]
        if (l.startsWith('NMS:'))        header.nms   = l.slice(4).trim()
        else if (l.startsWith('CMTS:'))  header.cmts  = l.slice(5).trim()
        else if (l.startsWith('Interfejsy:'))
            header.ifaces = l.slice(11).trim().split(',').map(s => s.trim())
        else if (l.startsWith('Data:'))  header.date  = l.slice(5).trim()
        else if (l.startsWith('-'))      { dataStart = i + 1; break }
    }
    const rows = []
    for (let i = dataStart; i < lines.length; i++) {
        const parts = lines[i].trim().split(/\s+/)
        if (parts.length < 4) continue
        const [mac, ip, iface, status] = parts
        const dBmV = parts[4] ?? ''
        if (!/^[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}$/i.test(mac)) continue
        rows.push({ mac: mac.toLowerCase(), ip, iface, status, dBmV })
    }
    return { header, rows }
}

export function buildDiff(oldRows, newRows) {
    const oldMap = new Map(oldRows.map(r => [r.mac, r]))
    const newMap = new Map(newRows.map(r => [r.mac, r]))
    const wentOffline = [], cameOnline = [], disappeared = [], appeared = []

    for (const [mac, old] of oldMap) {
        const cur = newMap.get(mac)
        if (!cur) { disappeared.push(old); continue }
        const wasOnline = old.status === '1'
        const isOnline  = cur.status.includes('online') || cur.status === '1'
        if (wasOnline && !isOnline)  wentOffline.push({ ...cur, mac })
        else if (!wasOnline && isOnline) cameOnline.push({ ...cur, mac })
    }
    for (const [mac, cur] of newMap) {
        if (!oldMap.has(mac)) appeared.push(cur)
    }
    return { wentOffline, cameOnline, disappeared, appeared,
             totalOld: oldRows.length, totalNew: newRows.length }
}

/**
 * Parsuje output "show cable modem summary total" (Cisco).
 * Hierarchia: karta (C1) → interfejs kablowy (C1/0/0, C1/0/1 …)
 */
export function parseCiscoCards(rawOutput) {
    const lines = rawOutput.split('\n')
    let colMap = null
    const cards = {}, cardOrder = []

    for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue

        if (!colMap && /\btotal\b/i.test(trimmed) && (/\breg\b/i.test(trimmed) || /\boffline\b/i.test(trimmed))) {
            const tokens = trimmed.split(/\s+/).map(t => t.toLowerCase())
            const off = /^(interface|i\/f)$/i.test(tokens[0]) ? 1 : 0
            const totalIdx    = tokens.indexOf('total')    - off
            const regIdx      = tokens.indexOf('reg')      - off
            const widebandIdx = tokens.indexOf('wideband') - off
            if (totalIdx >= 0) colMap = { total: totalIdx, reg: regIdx, wideband: widebandIdx }
            continue
        }

        if (colMap && /^C\d+\//i.test(trimmed)) {
            const tokens     = trimmed.split(/\s+/)
            const iface      = tokens[0]
            const isUB       = /\/UB$/i.test(iface)
            const cableIface = iface.replace(/\/U[B\d]+$/i, '')
            const cardKey    = (iface.match(/^(C\d+)/i)?.[1] ?? '').toUpperCase()
            if (!cardKey) continue

            if (!cards[cardKey]) { cards[cardKey] = { total: 0, reg: 0, ifaceOrder: [], ifaces: {} }; cardOrder.push(cardKey) }
            if (!cards[cardKey].ifaces[cableIface]) { cards[cardKey].ifaces[cableIface] = { total: 0, reg: 0 }; cards[cardKey].ifaceOrder.push(cableIface) }

            const nums     = tokens.slice(1).map(Number)
            const total    = isNaN(nums[colMap.total]) ? 0 : nums[colMap.total]
            const reg      = (colMap.reg >= 0 && !isNaN(nums[colMap.reg])) ? nums[colMap.reg] : 0
            const wideband = (colMap.wideband >= 0 && !isNaN(nums[colMap.wideband])) ? nums[colMap.wideband] : -1

            if (isUB || wideband === 0) {
                cards[cardKey].ifaces[cableIface].total += total
                cards[cardKey].ifaces[cableIface].reg   += reg
                cards[cardKey].total += total
                cards[cardKey].reg   += reg
            }
        }
    }

    const cardList = cardOrder.map(key => {
        const { total, reg, ifaceOrder, ifaces } = cards[key]
        return { key, total, reg, ifaceList: ifaceOrder.map(k => ({ key: k, ...ifaces[k] })) }
    })
    return { cardCount: cardOrder.length, cardList }
}

/**
 * Parsuje output "show cable fiber-node".
 * Zwraca mapę: cardKey → [{ num, desc, upstream }, …]
 */
export function parseFiberNodes(rawOutput) {
    const cardMap = {}
    let currentNum = null, currentDesc = null

    for (const line of rawOutput.split('\n')) {
        const trimmed = line.trim()
        const nodeMatch = trimmed.match(/^Fiber-Node\s+(\d+)/i)
        if (nodeMatch)  { currentNum = nodeMatch[1]; currentDesc = null; continue }

        const descMatch = trimmed.match(/^Description:\s*(.+)/i)
        if (descMatch)  { currentDesc = descMatch[1].trim(); continue }

        const upMatch = trimmed.match(/^Upstream-Cable\s+(\d+)\/(\d+)\/(\d+)/i)
        if (upMatch && currentNum !== null && currentDesc !== null) {
            const cardKey  = 'C' + upMatch[1]
            const upstream = `${upMatch[1]}/${upMatch[2]}/${upMatch[3]}`
            if (!cardMap[cardKey]) cardMap[cardKey] = []
            cardMap[cardKey].push({ num: currentNum, desc: currentDesc, upstream })
            currentNum = null; currentDesc = null
        }
    }
    return cardMap
}

/** Buduje timestamp HHMMSS-DDMMYYYY */
export function buildTimestamp() {
    const d = new Date(), pad = n => String(n).padStart(2, '0')
    return `${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}-${pad(d.getDate())}${pad(d.getMonth()+1)}${d.getFullYear()}`
}

/** Parsuje nazwę pliku "NMS-HHMMSS-DDMMYYYY.txt" → { nms, date, time } */
export function parseMeasureFilename(filename) {
    const base  = filename.replace(/\.txt$/, '')
    const parts = base.split('-')
    if (parts.length < 3) return { nms: base, date: '', time: '' }
    const [nms, t = '', d = ''] = parts
    const time = t.length === 6 ? `${t.slice(0,2)}:${t.slice(2,4)}:${t.slice(4,6)}` : t
    const date = d.length === 8 ? `${d.slice(0,2)}.${d.slice(2,4)}.${d.slice(4,8)}` : d
    return { nms, date, time }
}

// ─── Composable ───────────────────────────────────────────────────────────────

export function useCmtsCompare() {
    const { devices: allDevices, loadDevices } = useData()

    const cmtsDevices = computed(() =>
        allDevices.value.filter(d => d.type === 'CMTS' && d.status === 'SYNCED'))

    const CACHE_KEY_SELECTED = 'cmts_compare_selectedDeviceIds'

    // ── Reactive state ──────────────────────────────────────────────────────
    const selectedDeviceIds = ref([])
    const searchQuery       = ref('')
    const dropdownOpen      = ref(false)
    const isExecuting       = ref(false)
    const results           = reactive({})
    const expandedCards     = reactive({})
    const checkedIfaces     = reactive({})
    const popupData         = ref(null)
    const nmsDialog         = ref(null)
    const measureFiles      = ref([])
    const addingMeasure     = ref(false)
    const confirmDelete     = ref(null)
    const previewFile       = ref(null)
    const previewContent    = ref('')
    const previewLoading    = ref(false)
    const compareDialog     = ref(null)
    const receiverSearch    = ref('')
    const receiverResult    = ref(null)
    const cmtsCompareSettings = ref({ offlineThreshold: 80, commandTimeout: 120 })

    let popupTimer = null

    // ── Computed ────────────────────────────────────────────────────────────
    const filteredDevices = computed(() => {
        if (!searchQuery.value) return cmtsDevices.value
        const q = searchQuery.value.toLowerCase()
        return cmtsDevices.value.filter(d =>
            d.hostname.toLowerCase().includes(q) || d.address.includes(q))
    })

    const selectedDevices = computed(() =>
        cmtsDevices.value.filter(d => selectedDeviceIds.value.includes(d.id)))

    // ── Measure files ───────────────────────────────────────────────────────
    async function loadMeasureFiles() {
        try {
            const res = await requestJson('/api/modules/cmts-compare/files')
            measureFiles.value = res?.files ?? []
        } catch { measureFiles.value = [] }
    }

    async function loadPreview(file) {
        if (previewFile.value === file) { previewFile.value = null; return }
        previewFile.value   = file
        previewContent.value = ''
        previewLoading.value = true
        try {
            const res = await requestJson(`/api/modules/cmts-compare/content?filename=${encodeURIComponent(file)}`)
            previewContent.value = res?.content ?? res?.error ?? 'Błąd'
        } catch (e) {
            previewContent.value = 'Błąd wczytywania: ' + e.message
        } finally {
            previewLoading.value = false
        }
    }

    function requestDeleteFile(file) { confirmDelete.value = file }

    async function executeDelete() {
        const file = confirmDelete.value
        if (!file) return
        confirmDelete.value = null
        try {
            const res = await requestJson('/api/modules/cmts-compare/delete',
                { method: 'DELETE', body: { filename: file } })
            if (res?.ok === false) throw new Error(res.error || 'Błąd usuwania')
            await loadMeasureFiles()
        } catch (e) { alert('Błąd usuwania: ' + e.message) }
    }

    // ── Device selection / cards ─────────────────────────────────────────────
    function removeDevice(id) {
        selectedDeviceIds.value = selectedDeviceIds.value.filter(i => i !== id)
        delete results[id]
    }

    function isCardChecked(deviceId, card) {
        return card.ifaceList.length > 0 &&
            card.ifaceList.every(i => checkedIfaces[deviceId + '__' + i.key])
    }
    function isCardIndeterminate(deviceId, card) {
        const n = card.ifaceList.filter(i => checkedIfaces[deviceId + '__' + i.key]).length
        return n > 0 && n < card.ifaceList.length
    }
    function toggleCard(deviceId, card, checked) {
        card.ifaceList.forEach(i => { checkedIfaces[deviceId + '__' + i.key] = checked })
    }
    function isDeviceChecked(deviceId) {
        const all = (results[deviceId]?.cardList ?? []).flatMap(c => c.ifaceList)
        return all.length > 0 && all.every(i => checkedIfaces[deviceId + '__' + i.key])
    }
    function isDeviceIndeterminate(deviceId) {
        const all = (results[deviceId]?.cardList ?? []).flatMap(c => c.ifaceList)
        const n   = all.filter(i => checkedIfaces[deviceId + '__' + i.key]).length
        return n > 0 && n < all.length
    }
    function toggleDevice(deviceId, checked) {
        ;(results[deviceId]?.cardList ?? []).forEach(card => toggleCard(deviceId, card, checked))
    }

    function deviceCheckedIfaceKeys(deviceId) {
        return Object.keys(checkedIfaces)
            .filter(k => k.startsWith(deviceId + '__') && checkedIfaces[k])
            .map(k => k.slice(deviceId.length + 2))
    }
    function deviceCheckedModemCount(deviceId) {
        const keys = new Set(deviceCheckedIfaceKeys(deviceId))
        let sum = 0
        for (const card of (results[deviceId]?.cardList ?? [])) {
            for (const iface of card.ifaceList) {
                if (keys.has(iface.key)) sum += iface.total
            }
        }
        return sum
    }

    // ── Popup ───────────────────────────────────────────────────────────────
    function showCardPopup(deviceId, cardKey, event) {
        event.stopPropagation()
        if (popupData.value?.cardKey === cardKey) {
            popupData.value = null; clearTimeout(popupTimer); return
        }
        popupData.value = { cardKey, nodes: results[deviceId]?.fiberMap?.[cardKey] ?? [] }
        clearTimeout(popupTimer)
        popupTimer = setTimeout(() => { popupData.value = null }, 8000)
    }

    // ── Verify (run on devices) ─────────────────────────────────────────────
    async function onVerify() {
        if (!selectedDevices.value.length) return
        isExecuting.value = true
        Object.keys(results).forEach(k => delete results[k])
        Object.keys(expandedCards).forEach(k => delete expandedCards[k])
        Object.keys(checkedIfaces).forEach(k => delete checkedIfaces[k])
        receiverResult.value = null; receiverSearch.value = ''

        const timeout = (cmtsCompareSettings.value.commandTimeout ?? 120) * 1000
        const runCmd  = (device, command) => requestJson('/api/scripts/run', {
            method: 'POST',
            body: { script: 'settings-devices_controller', method: 'execute_command_on_device',
                    payload: { device, command } },
            timeoutMs: timeout
        })

        await Promise.allSettled(selectedDevices.value.map(async (device) => {
            try {
                const [raw, rawFiber] = await Promise.all([
                    runCmd(device, 'show cable modem summary total'),
                    runCmd(device, 'show cable fiber-node')
                ])
                const parsed      = typeof raw      === 'string' ? JSON.parse(raw)      : raw
                const parsedFiber = typeof rawFiber === 'string' ? JSON.parse(rawFiber) : rawFiber

                if (parsed?.error) { results[device.id] = { error: parsed.error }; return }

                const fullOutput  = parsed?.output  || (typeof parsed      === 'string' ? parsed      : JSON.stringify(parsed))
                const fiberOutput = parsedFiber?.output || (typeof parsedFiber === 'string' ? parsedFiber : '')
                const fiberMap    = fiberOutput ? parseFiberNodes(fiberOutput) : {}

                if (device.vendor === 'Cisco') {
                    const { cardCount, cardList } = parseCiscoCards(fullOutput)
                    results[device.id] = { cardList, filteredCount: cardCount, fiberMap }
                } else {
                    results[device.id] = { output: fullOutput, filteredCount: 0, fiberMap }
                }
            } catch (err) {
                results[device.id] = { error: err.message }
            }
        }))

        isExecuting.value = false
    }

    // ── Fetch modems (NMS dialog) ────────────────────────────────────────────
    async function fetchModems(device) {
        const ifaces = deviceCheckedIfaceKeys(device.id)
        if (!ifaces.length) return
        nmsDialog.value = {
            deviceHostname: device.hostname, device, ifaces,
            nmsInput: '', timestamp: buildTimestamp(),
            loading: true, fetchError: null, rows: null,
            saving: false, saveOk: false, savedPath: '', saveError: null
        }
        try {
            const filter = ifaces.join('|')
            const raw    = await requestJson('/api/scripts/run', {
                method: 'POST',
                body: { script: 'settings-devices_controller', method: 'execute_command_on_device',
                        payload: { device, command: `show cable modem | include ${filter}` } },
                timeoutMs: (cmtsCompareSettings.value.commandTimeout ?? 120) * 1000
            })
            const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
            const output = parsed?.output || (typeof parsed === 'string' ? parsed : '')
            const rows   = []
            for (const line of output.split('\n')) {
                const parts = line.trim().split(/\s+/)
                if (parts.length < 4) continue
                const [mac, ip, iface, status] = parts
                if (!/^[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}$/i.test(mac)) continue
                rows.push({ mac, ip, iface, status, dBmV: parts[5] ?? '' })
            }
            nmsDialog.value.loading = false
            nmsDialog.value.rows    = rows
        } catch (err) {
            nmsDialog.value.loading    = false
            nmsDialog.value.fetchError = err.message
        }
    }

    async function confirmSave() {
        const d = nmsDialog.value
        if (!d || !d.nmsInput.trim() || !d.rows) return
        d.saving = true; d.saveError = null
        try {
            const header = `NMS: ${d.nmsInput.trim()}\nCMTS: ${d.deviceHostname}\n` +
                `Interfejsy: ${d.ifaces.join(', ')}\nData: ${new Date().toLocaleString('pl-PL')}\n\n` +
                `MAC               IP               Interfejs        Status  dBmV\n` +
                '-'.repeat(80) + '\n'
            const body = d.rows.map(r =>
                `${r.mac.padEnd(18)}${r.ip.padEnd(17)}${r.iface.padEnd(17)}` +
                `${(r.status.includes('online') ? '1' : '0').padEnd(8)}${r.dBmV}`
            ).join('\n')
            const filename = `${d.nmsInput.trim()}-${d.timestamp}.txt`
            const res = await requestJson('/api/modules/cmts-compare/save', {
                method: 'POST',
                body: { nms: d.nmsInput.trim(), filename, content: header + body }
            })
            if (res?.ok) {
                d.saving = false; d.saveOk = true; d.savedPath = filename
                loadMeasureFiles()
                setTimeout(() => { nmsDialog.value = null; addingMeasure.value = false }, 1200)
            } else throw new Error(res?.error || 'Błąd zapisu')
        } catch (err) { d.saving = false; d.saveError = err.message }
    }

    // ── Compare ──────────────────────────────────────────────────────────────
    async function startCompare(file) {
        const contentRes = await requestJson(
            `/api/modules/cmts-compare/content?filename=${encodeURIComponent(file)}`)
        if (!contentRes?.ok && !contentRes?.content) return
        const { header, rows: oldRows } = parseSavedFile(contentRes.content)
        const device = allDevices.value.find(d => d.hostname === header.cmts)
        if (!device) {
            compareDialog.value = { file, error: `Nie znaleziono urządzenia: ${header.cmts}`, header, loading: false, diff: null }
            return
        }
        compareDialog.value = { file, header, oldRows, device, loading: true, error: null, diff: null }
        try {
            const filter = header.ifaces.join('|')
            const raw    = await requestJson('/api/scripts/run', {
                method: 'POST',
                body: { script: 'settings-devices_controller', method: 'execute_command_on_device',
                        payload: { device, command: `show cable modem | include ${filter}` } },
                timeoutMs: (cmtsCompareSettings.value.commandTimeout ?? 120) * 1000
            })
            const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
            const output = parsed?.output || (typeof parsed === 'string' ? parsed : '')
            const newRows = []
            for (const line of output.split('\n')) {
                const parts = line.trim().split(/\s+/)
                if (parts.length < 4) continue
                const [mac, ip, iface, status] = parts
                if (!/^[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}$/i.test(mac)) continue
                newRows.push({ mac: mac.toLowerCase(), ip, iface, status, dBmV: parts[5] ?? '' })
            }
            compareDialog.value.loading = false
            compareDialog.value.diff    = buildDiff(oldRows, newRows)
        } catch (err) {
            compareDialog.value.loading = false
            compareDialog.value.error   = err.message
        }
    }

    // ── Receiver search ──────────────────────────────────────────────────────
    function searchReceiver() {
        const queries = [...new Set(
            receiverSearch.value.split(/[\n,;]+/).map(s => s.trim().toUpperCase()).filter(Boolean))]
        if (!queries.length) { receiverResult.value = null; return }

        receiverResult.value = queries.map(query => {
            const foundCards = []
            for (const deviceId of Object.keys(results)) {
                for (const [cardKey, nodes] of Object.entries(results[deviceId]?.fiberMap ?? {})) {
                    if (nodes.some(n => n.desc.toUpperCase().includes(query))) {
                        const card = (results[deviceId]?.cardList ?? []).find(c => c.key === cardKey)
                        if (card) { toggleCard(deviceId, card, true); expandedCards[deviceId + '__' + cardKey] = true; foundCards.push(cardKey) }
                    }
                }
            }
            const unique = [...new Set(foundCards)]
            return unique.length ? { query, found: true, cards: unique } : { query, found: false }
        })
    }

    // ── Lifecycle ────────────────────────────────────────────────────────────
    function onClickOutside(e, dropdownRef) {
        if (dropdownRef?.value && !dropdownRef.value.contains(e.target))
            dropdownOpen.value = false
    }

    onBeforeUnmount(() => { clearTimeout(popupTimer) })

    // Zapisuj wybrane urządzenia do pamięci podręcznej
    watch(selectedDeviceIds, val => localStorage.setItem(CACHE_KEY_SELECTED, JSON.stringify(val)), { deep: true })

    onMounted(async () => {
        // Wczytaj zapamiętane urządzenia
        try {
            const saved = localStorage.getItem(CACHE_KEY_SELECTED)
            if (saved) selectedDeviceIds.value = JSON.parse(saved)
        } catch (e) {
            console.warn('[CMTS Compare] błąd wczytywania cache:', e)
        }
        await loadDevices()
        await loadMeasureFiles()
        try {
            const s = await requestJson('/api/modules/settings', { timeoutMs: 5000 })
            if (s?.cmtsCompare)
                cmtsCompareSettings.value = { ...cmtsCompareSettings.value, ...s.cmtsCompare }
        } catch (e) {
            console.warn('[CMTS Compare] settings unavailable:', e.message)
        }
    })

    return {
        // state
        selectedDeviceIds, searchQuery, dropdownOpen, isExecuting,
        results, expandedCards, checkedIfaces,
        popupData, nmsDialog, measureFiles,
        addingMeasure, confirmDelete,
        previewFile, previewContent, previewLoading,
        compareDialog, receiverSearch, receiverResult,
        cmtsCompareSettings,
        // computed
        cmtsDevices, filteredDevices, selectedDevices,
        // actions
        loadMeasureFiles, loadPreview, requestDeleteFile, executeDelete,
        removeDevice,
        isCardChecked, isCardIndeterminate, toggleCard,
        isDeviceChecked, isDeviceIndeterminate, toggleDevice,
        deviceCheckedIfaceKeys, deviceCheckedModemCount,
        showCardPopup, onVerify,
        fetchModems, confirmSave,
        startCompare, searchReceiver,
        onClickOutside,
        parseMeasureFilename,
    }
}
