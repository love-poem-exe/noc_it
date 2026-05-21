<template>
  <div class="accounts-container">
    <div class="left-panel">
      <h2>Dodaj site</h2>
      <input v-model="form.site_tag" placeholder="Site Tag (e.g. PL-WAW)" />
      <input v-model="form.site_name" placeholder="Site Name (e.g. Warsaw Data Center)" />

      <div style="display:flex; gap:8px; align-items:center">
      <button v-if="!locationSet" @click="openMapPicker(form.location)">Pick on map</button>
        <div v-else style="display:flex;align-items:center;gap:6px;flex:1">
          <input v-model="form.location" placeholder="(picked address)" disabled title="Picked location" />
          <button class="clear-loc" @click="clearLocation" title="Clear location">✕</button>
        </div>
      </div>

      <button @click="addSiteAction">{{ editingId ? 'Zapisz' : 'Dodaj' }}</button>
    </div>

    <div class="right-panel">
      <h2>Lista sites</h2>
      <table v-if="sites && sites.length">
        <thead>
          <tr><th>Tag</th><th>Name</th><th>Location</th><th>Akcje</th></tr>
        </thead>
        <tbody>
          <template v-for="(s, idx) in sites" :key="s.id || s.site_tag || idx">
            <tr>
            <template v-if="editRowIdx === idx">
              <td><input v-model="editRow.site_tag" class="inline-edit" /></td>
              <td><input v-model="editRow.site_name" class="inline-edit" /></td>
              <td>
                <div style="display:flex;align-items:center;gap:4px">
                  <input :value="editRow.location" disabled class="inline-edit" style="flex:1" />
                  <button class="clear-loc" @click="openEditMapPicker" title="Pick new location">📍</button>
                </div>
              </td>
              <td>
                <button @click="confirmEdit">✅</button>
                <button @click="cancelEdit">✖️</button>
              </td>
            </template>
            <template v-else>
              <td>{{ s.site_tag }}</td>
              <td>{{ s.site_name }}</td>
              <td style="max-width:40ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" :title="s.location">{{ formatLocationShort(s.location) }}</td>
              <td>
                <button @click="startEdit(idx)">✏️</button>
                <button @click="removeSite(idx)">❌</button>
                <button @click="toggleExpand(idx, s)" title="Toggle devices">▾</button>
              </td>
            </template>
            </tr>
            <tr v-if="expandedRows.has(idx)" class="expanded-row">
            <td colspan="4">
              <div style="padding:8px">
                <strong>Devices assigned to this site:</strong>
                <div v-if="devices && devices.length">
                  <ul style="margin:6px 0 0 16px">
                    <li v-for="d in devices.filter(dev => (dev.site_id === s.id) || (Array.isArray(s.site_devices) && s.site_devices.includes(dev.id)))" :key="d.id">
                      {{ d.hostname || d.id }}
                    </li>
                    <li v-if="devices.filter(dev => (dev.site_id === s.id) || (Array.isArray(s.site_devices) && s.site_devices.includes(dev.id))).length === 0">No devices assigned.</li>
                  </ul>
                </div>
                <div v-else>Loading devices...</div>
              </div>
            </td>
            </tr>
          </template>
        </tbody>
      </table>
      <p v-else>Brak sites do wyświetlenia.</p>
    </div>

    <!-- Map picker modal -->
    <div v-if="showMapPicker" class="map-modal">
      <div class="map-modal-content">
        <div style="display:flex;gap:8px;align-items:flex-start;">
          <div style="flex:1">
            <input v-model="searchQuery" placeholder="Search place or address" @keyup.enter="searchLocation" style="width:100%;padding:6px;margin-bottom:8px" />
            <div v-if="searchResults.length" class="search-results">
              <div v-for="(r, i) in searchResults" :key="i" class="search-result" @click="selectResult(r)">
                <div style="display:flex;align-items:baseline;gap:6px">
                  <strong>{{ r.display_name.split(',')[0] }}</strong>
                  <span v-if="r.typeLabel" class="result-type">{{ r.typeLabel }}</span>
                </div>
                <div style="font-size:11px;color:#8b949e;margin-top:1px">{{ r.display_name }}</div>
              </div>
            </div>
          </div>
          <div style="flex:2">
            <div ref="pickerMapEl" class="picker-map"></div>
          </div>
        </div>
        <div class="picker-actions">
          <button @click="confirmPick">Confirm</button>
          <button @click="closeMapPicker" style="margin-left:8px">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick, onBeforeUnmount } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

import useData from '../../composables/useData'

const {
  sites,
  devices,
  loadSites,
  loadDevices,
  addSite,
  updateSite,
  removeSite: removeSiteApi
} = useData()

const expandedRows = ref(new Set())

function toggleExpand(idx, site) {
  const key = idx
  if (expandedRows.value.has(key)) {
    expandedRows.value.delete(key)
  } else {
    expandedRows.value.add(key)
    // Use already-loaded devices; only load if empty
    if (!devices || !devices.value || devices.value.length === 0) {
      loadDevices().catch(() => {})
    }
  }
}

async function showDeviceIds(site) {
  try {
    const gather = () => {
      const ids = new Set()
      if (site && Array.isArray(site.site_devices)) {
        for (const id of site.site_devices) ids.add(id)
      }
      if (devices && devices.value && devices.value.length) {
        for (const d of devices.value) {
          if (d.site_id === site.id) ids.add(d.id)
        }
      }
      const arr = Array.from(ids)
      const mapped = arr.map(id => {
        const found = devices && devices.value ? devices.value.find(dd => dd.id === id) : null
        return { id, hostname: found ? (found.hostname || null) : null }
      })
      const missing = mapped.filter(m => !m.hostname).map(m => m.id)
      const names = mapped.map(m => m.hostname || m.id)
      return { ids: arr, mapped, missing, names }
    }

    let res = gather()
    if (res.missing.length > 0) {
      // Try loading devices once if some ids are missing
      await loadDevices().catch(() => {})
      res = gather()
    }

    console.log(`Site ${site.site_tag || site.id} assigned devices (${res.names.length}):`, res.names)
    console.log(JSON.stringify(res.names))
    if (res.missing.length > 0) {
      console.warn('Some device IDs were not found locally:', res.missing)
    }
  } catch (e) {
    console.error('showDeviceIds error', e)
  }
}

const form = ref({ site_tag: '', site_name: '', location: '' })
const editingId = ref('')
const editRowIdx = ref(-1)
const editRow = ref({ id: '', site_tag: '', site_name: '', location: '' })
const processing = ref(false)
const showMapPicker = ref(false)
const pickerMapEl = ref(null)
let pickerMap = null
let pickerMarker = null
let pickedLngLat = null
const searchQuery = ref('')
const searchResults = ref([])
const locationSet = ref(false)
let searchTimer = null
let searchEpoch = 0
let pendingInitialLocation = null

async function addSiteAction() {
  if (processing.value) return
  processing.value = true
  const tag = (form.value.site_tag || '').trim()
  const name = (form.value.site_name || '').trim()
  const location = (form.value.location || '').trim()
  if (!tag || !name) return alert('site_tag and site_name are required')
  if (!locationSet.value) return alert('location is required — please pick a location on the map')
  // check duplicate tag locally
  if (sites.value.some(s => s.site_tag === tag && s.id !== editingId.value)) return alert('site_tag already exists')

  if (editingId.value) {
    try {
      await updateSite(editingId.value, tag, name, location)
      await loadSites(true)
    } catch {
      // fallback: update locally so UI refreshes
      const idx = sites.value.findIndex(s => s.id === editingId.value)
      if (idx !== -1) {
        sites.value[idx].site_tag = tag
        sites.value[idx].site_name = name
        sites.value[idx].location = location
      }
    }
  } else {
    try {
      await addSite(tag, name, location)
      await loadSites(true)
    } catch {
      // fallback: add locally so UI refreshes immediately
      const fakeId = 'local-' + Date.now() + '-' + Math.floor(Math.random() * 1000)
      sites.value.push({ id: fakeId, site_tag: tag, site_name: name, location })
    }
  }

  form.value.site_tag = ''
  form.value.site_name = ''
  form.value.location = ''
  editingId.value = ''
  locationSet.value = false
  processing.value = false
}

function openMapPicker(initial = '') {
  // remember initial location text so the picker can prefill the search box
  pendingInitialLocation = initial || ''
  showMapPicker.value = true
  nextTick(async () => {
    // prefill the search input inside the modal
    searchQuery.value = pendingInitialLocation || ''
    initPickerMap()
    // If we have a prefilled query, run the search immediately so results reflect it
    try {
      if (searchQuery.value && typeof searchLocation === 'function') {
        await searchLocation()
      }
    } catch (e) {
      // ignore search errors (network/timeouts)
      console.warn('prefill searchLocation failed', e)
    }
  })
}

function closeMapPicker() {
  showMapPicker.value = false
  destroyPickerMap()
}

function initPickerMap() {
  if (pickerMap) return
  pickerMap = new maplibregl.Map({
    container: pickerMapEl.value,
    style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    center: [19.1451, 52.2370],
    zoom: 15,
    pitch: 0,
    bearing: 0,
    maxZoom: 22,
    antialias: true,
  })

  pickerMap.on('load', () => {
    // prefer flat, high-contrast labels on the light style — keep buildings hidden for clarity
    try {
      const style = pickerMap.getStyle()
            if (style && style.layers) {
        	    style.layers.forEach((layer) => {
        	      if (layer.type === 'fill-extrusion' || /building/i.test(layer.id || '')) {
        	        try {
        	          pickerMap.setLayoutProperty(layer.id, 'visibility', 'none')
        	        } catch {}
        	      }
        	    })
        	  }
    } catch {
      // noop
    }
  })

  // If the picker was opened with an initial location string, try to parse coords and set marker
  if (pendingInitialLocation) {
    // Try to extract trailing coords like "(...lat,lon...)" or plain "lat,lon"
    const txt = (pendingInitialLocation || '').trim()
    let m = txt.match(/\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)\s*$/)
    if (!m) m = txt.match(/^\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*$/)
    if (m) {
      const lat = parseFloat(m[1])
      const lon = parseFloat(m[2])
      if (!isNaN(lat) && !isNaN(lon)) {
        pickedLngLat = { lat, lng: lon }
        if (!pickerMarker) pickerMarker = new maplibregl.Marker().setLngLat([lon, lat]).addTo(pickerMap)
        else pickerMarker.setLngLat([lon, lat])
        pickerMap.flyTo({ center: [lon, lat], zoom: 17 })
      }
    }
    // clear pending flag
    pendingInitialLocation = null
  }

  pickerMap.on('click', (e) => {
    pickedLngLat = e.lngLat
    if (!pickerMarker) pickerMarker = new maplibregl.Marker().setLngLat(pickedLngLat).addTo(pickerMap)
    else pickerMarker.setLngLat(pickedLngLat)
  })
}

function destroyPickerMap() {
  if (pickerMarker) { pickerMarker.remove(); pickerMarker = null }
  if (pickerMap) { pickerMap.remove(); pickerMap = null }
  pickedLngLat = null
}

async function confirmPick() {
  if (!pickedLngLat) return
  const lat = pickedLngLat.lat
  const lon = pickedLngLat.lng
  let locationStr = `${lat.toFixed(6)},${lon.toFixed(6)}`
  try {
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&zoom=18&addressdetails=1`
    const res = await fetch(url, { headers: { 'Accept-Language': 'pl' } })
    if (res.ok) {
      const data = await res.json()
      const a = data.address || {}
      const city = a.city || a.town || a.village || a.municipality || a.county || ''
      const road = a.road || a.pedestrian || a.footway || ''
      const houseNo = a.house_number || ''
      const streetPart = road ? (houseNo ? `${road} ${houseNo}` : road) : ''
      const shortName = [city, streetPart].filter(Boolean).join(', ')
      if (shortName) locationStr = `${shortName} (${lat.toFixed(6)},${lon.toFixed(6)})`
      else if (data.display_name) locationStr = `${data.display_name} (${lat.toFixed(6)},${lon.toFixed(6)})`
    }
  } catch {
    // keep coords-only fallback
  }

  // If we're editing a row inline, update editRow; otherwise update the left-panel form
  if (editRowIdx.value >= 0) {
    editRow.value.location = locationStr
  } else {
    form.value.location = locationStr
    locationSet.value = true
  }
  closeMapPicker()
}

function clearLocation() {
  form.value.location = ''
  locationSet.value = false
}

// Normalize a Photon feature to a unified result object
function normalizePhoton(f) {
  const props = f.properties || {}
  const coords = (f.geometry && f.geometry.coordinates) || []
  const lon = coords[0]
  const lat = coords[1]
  if (!lat || !lon) return null
  // Build a structured name: street+number, city, postcode, country
  const streetPart = props.housenumber && props.street
    ? `${props.street} ${props.housenumber}`
    : props.street || props.name || ''
  const cityPart = props.city || props.town || props.village || ''
  const postcodepart = props.postcode ? `(${props.postcode})` : ''
  const countryPart = props.country || ''
  const lines = [cityPart, streetPart, postcodepart, countryPart].filter(Boolean)
  const display_name = lines.join(', ')
  const typeLabel = props.type || props.osm_value || ''
  return { lat, lon, display_name: display_name || `${lat.toFixed(5)},${lon.toFixed(5)}`, typeLabel, _key: `${lat.toFixed(4)}:${lon.toFixed(4)}` }
}

// Normalize a Nominatim result to a unified result object
function normalizeNominatim(d) {
  const lat = parseFloat(d.lat)
  const lon = parseFloat(d.lon)
  if (!lat || !lon) return null
  // Nominatim already provides a human-readable display_name
  const a = d.address || {}
  // Build a tidy short label: road housenumber, city, postcode
  const streetPart = a.road
    ? (a.house_number ? `${a.road} ${a.house_number}` : a.road)
    : (d.name || '')
  const cityPart = a.city || a.town || a.village || a.county || ''
  const postcodePart = a.postcode ? `(${a.postcode})` : ''
  const countryPart = a.country || ''
  const short = [cityPart, streetPart, postcodePart, countryPart].filter(Boolean).join(', ')
  const typeLabel = d.type || d.class || ''
  return {
    lat, lon,
    display_name: short || d.display_name,
    display_full: d.display_name,
    typeLabel,
    _key: `${lat.toFixed(4)}:${lon.toFixed(4)}`
  }
}

async function searchLocation() {
  const q = (searchQuery.value || '').trim()
  if (!q) return
  // mark this search with an epoch so older responses are ignored
  const myEpoch = ++searchEpoch
  // clear visible results immediately while we fetch
  searchResults.value = []

  // Poland bounding box for Nominatim viewbox (prefer Polish results)
  const POLAND_VIEWBOX = '14.12,49.00,24.15,54.84'

  // Run Photon and Nominatim in parallel for best coverage
  const [photonRes, nominatimRes] = await Promise.allSettled([
    // Photon: geographic bias toward Poland center, higher limit
    fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(q)}&limit=10&lat=52.2&lon=19.1&lang=en`)
      .then(r => r.ok ? r.json() : null),
    // Nominatim: restricted to Poland, with address details for better labels
    fetch(
      `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=10&addressdetails=1&countrycodes=pl&viewbox=${POLAND_VIEWBOX}&bounded=0&q=${encodeURIComponent(q)}`,
      { headers: { 'Accept-Language': 'en' } }
    ).then(r => r.ok ? r.json() : null)
  ])

  const seenKeys = new Set()
  const merged = []

  // Add Photon results first (faster, better autocomplete)
  if (photonRes.status === 'fulfilled' && photonRes.value) {
    for (const f of (photonRes.value.features || [])) {
      const n = normalizePhoton(f)
      if (n && !seenKeys.has(n._key)) {
        seenKeys.add(n._key)
        merged.push(n)
      }
    }
  }

  // Append unique Nominatim results
  if (nominatimRes.status === 'fulfilled' && nominatimRes.value) {
    for (const d of (nominatimRes.value || [])) {
      const n = normalizeNominatim(d)
      if (n && !seenKeys.has(n._key)) {
        seenKeys.add(n._key)
        merged.push(n)
      }
    }
  }

  // only apply results if no newer search has been started
  if (myEpoch === searchEpoch) {
    searchResults.value = merged.slice(0, 12)
  }

  if (searchResults.value.length && pickerMap) {
    const first = searchResults.value[0]
    pickerMap.flyTo({ center: [first.lon, first.lat], zoom: 17 })
  }
}

// Debounced live search while modal is open
watch(searchQuery, (val) => {
  if (!showMapPicker.value) return
  if (searchTimer) clearTimeout(searchTimer)
  const q = (val || '').trim()
  if (q.length < 2) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(() => {
    searchLocation()
  }, 280)
})

function selectResult(r) {
  const lat = parseFloat(r.lat)
  const lon = parseFloat(r.lon)
  pickedLngLat = { lat, lng: lon }
  if (!pickerMarker) pickerMarker = new maplibregl.Marker().setLngLat([lon, lat]).addTo(pickerMap)
  else pickerMarker.setLngLat([lon, lat])
  pickerMap.flyTo({ center: [lon, lat], zoom: 19 })
  // set the searchQuery to the display name
  searchQuery.value = r.display_name
  searchResults.value = []
}

onBeforeUnmount(() => {
  destroyPickerMap()
  if (searchTimer) clearTimeout(searchTimer)
})

function formatLocationShort(loc) {
  if (!loc) return '-'
  // Strip trailing (lat,lon) coords for cleaner table display
  return loc.replace(/\s*\(\s*-?\d+\.\d+\s*,\s*-?\d+\.\d+\s*\)\s*$/, '').trim() || loc
}

async function removeSite(idx) {
  if (processing.value) return
  processing.value = true
  const s = sites.value[idx]
  if (!s) { processing.value = false; return }
  if (!confirm('Delete site "' + (s.site_tag || s.site_name) + '"?')) { processing.value = false; return }
  try {
    await removeSiteApi(s.id)
    await loadSites(true)
  } catch {
    // fallback: remove locally
    sites.value.splice(idx, 1)
  }
  processing.value = false
}

// clearAll intentionally removed; use UI actions to remove sites individually

// Inline editing is handled by startEdit / confirmEdit / cancelEdit below

function startEdit(idx) {
  const s = sites.value[idx]
  if (!s) return
  editRowIdx.value = idx
  editRow.value = { id: s.id, site_tag: s.site_tag || '', site_name: s.site_name || '', location: s.location || '' }
}

function cancelEdit() {
  editRowIdx.value = -1
  editRow.value = { id: '', site_tag: '', site_name: '', location: '' }
}

async function confirmEdit() {
  const { id, site_tag, site_name, location } = editRow.value
  if (!site_tag.trim() || !site_name.trim()) return alert('Tag and Name are required')
  try {
    await updateSite(id, site_tag.trim(), site_name.trim(), location.trim())
    await loadSites(true)
  } catch {
    // fallback: update locally
    const idx = sites.value.findIndex(s => s.id === id)
    if (idx !== -1) {
      sites.value[idx].site_tag = site_tag.trim()
      sites.value[idx].site_name = site_name.trim()
      sites.value[idx].location = location.trim()
    }
  }
  cancelEdit()
}

function openEditMapPicker() {
  // open the picker prefilling the current editRow location
  openMapPicker(editRow.value.location || '')
}

onMounted(async () => {
  console.log('[Sites.vue] Loading sites with cache...')
  await loadSites()
  console.log('[Sites.vue] Sites loaded:', sites.value.length)
})

</script>

<style scoped>
.accounts-container {
  display: flex; width: 100%; height: 100%;
  gap: 1.25rem; padding: 1rem; box-sizing: border-box;
  background: #0d1117; color: #e6edf3;
}

.left-panel {
  width: 28%; flex-shrink: 0;
  display: flex; flex-direction: column; gap: 10px;
  background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; padding: 1rem;
}

.left-panel h2 { font-size: 13px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }

.right-panel {
  flex: 1; overflow-x: auto;
  display: flex; flex-direction: column; gap: 0.5rem;
}

.right-panel h2 { font-size: 13px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }

input {
  width: 100%; padding: 7px 10px;
  background: #0d1117; border: 1px solid #30363d;
  border-radius: 6px; color: #e6edf3;
  font-size: 13px; font-family: inherit; outline: none;
  transition: border-color 0.15s; box-sizing: border-box;
}
input::placeholder { color: #484f58; }
input:focus { border-color: #388bfd; }

button {
  padding: 7px 14px; background: #1f6feb;
  color: #fff; border: 1px solid #1f6feb;
  border-radius: 6px; font-size: 13px; font-weight: 500;
  font-family: inherit; cursor: pointer; width: 100%;
  transition: background 0.15s;
}
button:hover { background: #388bfd; border-color: #388bfd; }

.clear-loc { width: auto; padding: 4px 8px; background: transparent; border: 1px solid #30363d; color: #8b949e; border-radius:5px }
.clear-loc:hover { background:#21262d; color:#e6edf3 }

table { width: 100%; border-collapse: collapse; }

th, td {
  border-bottom: 1px solid #21262d;
  padding: 9px 14px; text-align: left;
  color: #e6edf3; font-size: 13px;
}

th {
  background: #161b22; color: #8b949e;
  font-weight: 600; font-size: 11.5px;
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid #30363d;
}

tr { background: #0d1117; }
tr:nth-child(even) { background: #0f1318; }
tr:hover { background: #161b22; }

td button {
  width: auto; padding: 4px 8px;
  background: transparent; color: #8b949e;
  border: 1px solid #30363d; border-radius: 5px; font-size: 13px;
}
td button:hover { background: #21262d; color: #e6edf3; }
td button:disabled { opacity: 0.3; cursor: not-allowed; }

.inline-edit {
  width: 100%; padding: 5px 8px;
  background: #161b22; border: 1px solid #388bfd;
  border-radius: 4px; color: #e6edf3;
  font-size: 13px; font-family: inherit; outline: none;
  box-sizing: border-box;
}

.map-modal {
  position: fixed;
  left: 0; top: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.map-modal-content {
  background: #0f1720;
  padding: 12px;
  border-radius: 6px;
  width: 80%;
  max-width: 1000px;
}
.picker-map { width: 100%; height: 500px; border-radius:4px; }
.picker-actions { margin-top:8px; display:flex; justify-content:flex-end }
.search-results { max-height:220px; overflow-y:auto; background:#0d1117; border:1px solid #30363d; border-radius:5px; margin-bottom:6px; }
.result-type { font-size:10px; color:#388bfd; background:#0d1f3a; border:1px solid #1f6feb44; border-radius:3px; padding:1px 5px; font-weight:500; text-transform:lowercase; white-space:nowrap; }
.search-result { padding:7px 10px; cursor:pointer; border-bottom:1px solid #21262d; }
.search-result:last-child { border-bottom:none; }
.search-result:hover { background:#161b22; }
</style>
