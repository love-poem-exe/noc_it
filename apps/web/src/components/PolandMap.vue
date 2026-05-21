<template>
  <div ref="mapContainer" class="map-container">
    <div ref="zoomDisplay" class="zoom-display">zoom: --</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import useData from '../composables/useData'

const mapContainer = ref(null)
let map = null
let markers = []
let siteMarkers = []
const zoomDisplay = ref(null)

// keep handlers in module scope so they can be removed on unmount
const handleWindowResize = () => {
  try { if (map) map.resize() } catch (e) {}
}

function onZoom() {
  try {
    if (zoomDisplay && zoomDisplay.value && map) zoomDisplay.value.innerText = `zoom: ${map.getZoom().toFixed(2)}`
  } catch (e) {}
}

onMounted(() => {
  // Use the ArcGIS hybrid style provided by the user
    map = new maplibregl.Map({
      container: mapContainer.value,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [19.1451, 52.2370],
      zoom: 6.0,
    })

  // add default nav control
  map.addControl(new maplibregl.NavigationControl(), 'top-right')

  // After style loads, try to hide country label symbol layers
    // Use the base style as-is; do not modify layer visibility here.
    map.on('load', () => {
      // style loaded
      try {
        const canvas = map.getCanvas()
        if (canvas) {
          canvas.style.width = '100%'
          canvas.style.height = '100%'
          // prefer default image rendering (no pixelated scaling)
          canvas.style.imageRendering = 'auto'
        }
      } catch (e) {}
      // continent/coastline loaders removed — map relies on base style layers

      // Freeze map appearance: warstwy widoczne przy zoom ≤ 7 zostają widoczne
      // przy każdym wyższym zoomie. Warstwy pojawiające się dopiero po zoom 7
      // są trwale ukryte — mapa wygląda tak samo niezależnie od przybliżenia.
      //
      // Dodatkowo: warstwy kończące się na maxzoom 4 rozszerzamy do 5.5,
      // a warstwy startujące między (4, 5.5] przesuwamy na 5.5.
      try {
        const st = map.getStyle()
        const layers = (st && st.layers) || []
        for (const l of layers) {
          try {
            const origMin = (typeof l.minzoom === 'number') ? l.minzoom : 0
            const origMax = (typeof l.maxzoom === 'number') ? l.maxzoom : 24

            // Warstwy startujące po zoom 7 — trwale ukryj
            if (origMin > 7) {
              map.setLayoutProperty(l.id, 'visibility', 'none')
              continue
            }

            // Ustal nowy minzoom (reguła 4→5.5)
            let newMin = (origMin > 4 && origMin <= 5.5) ? 5.5 : origMin

            // Ustal nowy maxzoom:
            //  - warstwy kończące się na 4 → rozszerz do 5.5, potem do 24
            //  - wszystkie pozostałe widoczne do ≤7 → rozszerz do 24 (trwale widoczne)
            const newMax = 24

            map.setLayerZoomRange(l.id, newMin, newMax)
          } catch (e) {}
        }
      } catch (e) {}
    })

    // show current zoom value once; keep synced via onZoom
    try { onZoom() } catch (e) {}

    // Ensure map is resized to match container and device pixel ratio
    window.addEventListener('resize', handleWindowResize)

    // update zoom display whenever map zooms
    try { map.on('zoom', onZoom) } catch (e) {}

  // No static city labels — map shows only Sites markers.

  // Site markers: load and render
  const { sites, devices, loadSites, loadDevices } = useData()
  let deviceMarkers = []
  const _activePopups = []
  let _mouseMoveHandler = null

  function parseCoordsFromLocation(loc) {
    if (!loc) return null
    const m = loc.match(/\(\s*([-+]?[0-9]*\.?[0-9]+)\s*,\s*([-+]?[0-9]*\.?[0-9]+)\s*\)\s*$/)
    if (!m) return null
    const lat = parseFloat(m[1])
    const lon = parseFloat(m[2])
    if (Number.isFinite(lat) && Number.isFinite(lon)) return { lat, lon }
    return null
  }

  function clearSiteMarkers() {
    try {
      for (const m of siteMarkers) try { m.remove() } catch {}
    } catch {}
    siteMarkers = []
    try {
      for (const m of deviceMarkers) try { m.remove() } catch {}
    } catch {}
    deviceMarkers = []
  }

  function renderSiteMarkers() {
    if (!map) return
    clearSiteMarkers()
    for (const s of (sites.value || [])) {
      const coords = parseCoordsFromLocation(s.location)
      if (!coords) continue
      const zoom = map.getZoom()

      // At high zooms show device markers around the hub
      if (zoom >= 19) {
        // create triangular markers for each assigned device
        const assigned = new Set()
        if (Array.isArray(s.site_devices)) for (const id of s.site_devices) assigned.add(id)
        if (devices && devices.value && devices.value.length) {
          for (const d of devices.value) {
            if (d.site_id === s.id) assigned.add(d.id)
          }
        }
        const ids = Array.from(assigned)
        // distribute devices in a small radius around the site
        const latRad = coords.lat * Math.PI / 180
        const metersPerDegLat = 111320
        const metersPerDegLon = 111320 * Math.cos(latRad)
        const baseRadiusMeters = (12 + Math.min(100, ids.length * 6)) / 6 // radius in meters (reduced total 6x)
        const visFactor = Math.max(0, Math.min(1, (zoom - 19))) // 0..1 across 19->20
        ids.forEach((devId, i) => {
          const angle = (i / ids.length) * Math.PI * 2 + ((i % 2) * 0.3)
          const radius = baseRadiusMeters * (0.5 + (i % 3) / 3)
          const dLat = (radius * Math.sin(angle)) / metersPerDegLat
          const dLon = (radius * Math.cos(angle)) / metersPerDegLon
          const lng = coords.lon + dLon
          const lat = coords.lat + dLat

          const el = document.createElement('div')
          el.className = 'device-rect'
          // horizontal rectangle marker — narrower (2x)
          const triSize = 24
          const rectW = Math.round(triSize) // half width compared to before
          const rectH = Math.round(triSize * 0.75)
          el.style.width = rectW + 'px'
          el.style.height = rectH + 'px'
          el.style.background = '#16a34a'
          el.style.border = '2px solid rgba(0,0,0,0.2)'
          el.style.borderRadius = '3px'
          // animation: appear from zoom 19->20
          el.style.transition = 'opacity 300ms, transform 300ms'
          const scale = 0.6 + 0.4 * visFactor
          el.style.transform = `scale(${scale})`
          el.style.opacity = String(visFactor)
          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([lng, lat])
            .addTo(map)
          // avoid native tooltip
          el.title = ''
          // show translucent gray info bubble on hover for device markers
          try {
            const devObj = (devices && devices.value) ? devices.value.find(dd => dd.id === devId) : null
            const label = devObj ? (devObj.hostname || devId) : devId
            const infoHtml = `<div style="background:rgba(80,80,80,0.78);color:#fff;padding:8px 10px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-weight:600">${label}</div>`
            const infoPopup = new maplibregl.Popup({ offset: 6, closeButton: false, closeOnClick: false, className: 'transparent-popup' }).setHTML(infoHtml)
            const elNode = marker.getElement()
            const openInfo = () => { try { if (!map) return; infoPopup.setLngLat(marker.getLngLat()); infoPopup.addTo(map); const pe = infoPopup.getElement && infoPopup.getElement(); if (pe) try { pe.style.pointerEvents = 'none' } catch {} } catch {} }
            const closeInfo = () => { try { infoPopup.remove() } catch {} }
            if (elNode) {
              elNode.addEventListener('mouseenter', openInfo)
              elNode.addEventListener('mouseleave', closeInfo)
              // track popup so we can reliably close it when cursor moves away
              _activePopups.push({ marker, popup: infoPopup })
            }
          } catch {}
          deviceMarkers.push(marker)
        })
        // skip creating the hub marker at this zoom
        continue
      }

      // Otherwise show hub marker
      const el = document.createElement('div')
      el.className = 'site-marker'
      // square marker (size and opacity depend on zoom)
      let markerSize = 36 * (zoom / 5)
      markerSize = Math.max(36, Math.min(markerSize, 144)) // clamp size
      // Fade out from zoom 10 to 20
      let opacity = 1.0
      if (zoom > 10) {
        opacity = Math.max(0, 1 - (zoom - 10) / 10)
      }
      el.style.width = markerSize + 'px'
      el.style.height = markerSize + 'px'
      el.style.background = `rgba(22,163,74,${opacity})`
      el.style.border = (markerSize / 6) + `px solid rgba(0,0,0,${0.25 * opacity})`
      el.style.boxSizing = 'border-box'
      el.style.borderRadius = '50%'
      // avoid native browser tooltip
      el.title = ''

      const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
        .setLngLat([coords.lon, coords.lat])
        .addTo(map)

      // Prepare popup with list of assigned objects (if any)
      let popupContent = ''
      if (s.site_name || s.site_tag) {
        popupContent += `<div><strong>${s.site_name || ''}${s.site_tag ? ' — ' + s.site_tag : ''}</strong></div>`
      }
      // If s.objects or s.devices or similar exists, show as list
      if (Array.isArray(s.objects) && s.objects.length > 0) {
        popupContent += '<ul style="margin:4px 0 0 0;padding-left:18px;">'
        for (const obj of s.objects) {
          popupContent += `<li>${obj.name || obj.id || obj}</li>`
        }
        popupContent += '</ul>'
      } else if (Array.isArray(s.devices) && s.devices.length > 0) {
        popupContent += '<ul style="margin:4px 0 0 0;padding-left:18px;">'
        for (const dev of s.devices) {
          popupContent += `<li>${dev.name || dev.id || dev}</li>`
        }
        popupContent += '</ul>'
      }
      // intentionally do not show popup on hover for hub markers

      // clicking recenters map to marker — disabled at high zoom (>=19)
      el.addEventListener('click', (ev) => {
        ev.stopPropagation()
        try {
          if (!map) return
          const currentZoom = map.getZoom()
          if (currentZoom >= 19) return
          map.flyTo({ center: [coords.lon, coords.lat], zoom: 20, speed: 3.0 })
        } catch {}
      })

      // show a gray translucent info bubble on hover (hub info)
      try {
        const elNode = marker.getElement()
        const infoHtml = `<div style="background:rgba(80,80,80,0.78);color:#fff;padding:8px 10px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-weight:600">${(s.site_name || '')}${s.site_tag ? ' — ' + s.site_tag : ''}</div>`
        const infoPopup = new maplibregl.Popup({ offset: 8, closeButton: false, closeOnClick: false, className: 'transparent-popup' }).setHTML(infoHtml)
        const openInfo = () => { try { if (!map) return; if (map.getZoom() >= 19) return; infoPopup.setLngLat(marker.getLngLat()); infoPopup.addTo(map); const pe = infoPopup.getElement && infoPopup.getElement(); if (pe) try { pe.style.pointerEvents = 'none' } catch {} } catch {} }
        const closeInfo = () => { try { infoPopup.remove() } catch {} }
        if (elNode) {
          elNode.addEventListener('mouseenter', openInfo)
          elNode.addEventListener('mouseleave', closeInfo)
          // also close the info bubble when the hub is clicked
          elNode.addEventListener('click', closeInfo)
          _activePopups.push({ marker, popup: infoPopup })
        }
      } catch {}
      siteMarkers.push(marker)
    }
  }

    // continent/coastline external loaders removed — map relies on base style layers

  // Load sites and devices then render; keep reactive so newly added sites/devices appear
  loadSites().then(() => {
    // try to load devices (best-effort)
    try { loadDevices().catch(() => {}) } catch (e) {}
    renderSiteMarkers()
  }).catch(() => {})
  watch(sites, () => renderSiteMarkers())
  watch(devices, () => renderSiteMarkers())

  // Update marker sizes on zoom
  map.on('zoom', () => renderSiteMarkers())

  // Close popups when cursor moves away from marker/popup: use map mousemove to detect
  _mouseMoveHandler = (e) => {
    try {
      const canvasRect = map.getCanvas().getBoundingClientRect()
      const clientX = canvasRect.left + e.point.x
      const clientY = canvasRect.top + e.point.y
      const elUnder = document.elementFromPoint(clientX, clientY)
      // iterate _activePopups and close any whose marker/popup is not under cursor
      for (let i = _activePopups.length - 1; i >= 0; i--) {
        const entry = _activePopups[i]
        try {
          const mEl = entry.marker && entry.marker.getElement()
          const pEl = entry.popup && entry.popup.getElement && entry.popup.getElement()
          const overMarker = mEl && (mEl === elUnder || mEl.contains(elUnder))
          const overPopup = pEl && (pEl === elUnder || pEl.contains(elUnder))
          if (!overMarker && !overPopup) {
            try { entry.popup.remove() } catch {}
            _activePopups.splice(i, 1)
          }
        } catch {}
      }
    } catch {}
  }
  try { map.on('mousemove', _mouseMoveHandler) } catch {}
})

onBeforeUnmount(() => {
  // remove any temporary markers and site markers
  try {
    if (markers && markers.length) { markers.forEach((m) => { try { m.remove() } catch {} }) }
  } catch {}
  markers = []
  try {
    if (siteMarkers && siteMarkers.length) { siteMarkers.forEach((m) => { try { m.remove() } catch {} }) }
  } catch {}
  siteMarkers = []
  try { window.removeEventListener('resize', handleWindowResize) } catch (e) {}
  try { if (map) map.off('zoom', onZoom) } catch (e) {}
  try { if (map && _mouseMoveHandler) map.off('mousemove', _mouseMoveHandler) } catch (e) {}
  if (map) map.remove()
})
</script>

<style scoped>
.map-container {
  width: 90%;
  height: 90%;
  display: block;
  margin: 20px;
}

.zoom-display {
  position: absolute;
  right: 12px;
  top: 12px;
  background: rgba(0,0,0,0.6);
  color: #fff;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 9999;
  pointer-events: none;
}
</style>

<style>
/* Popup overrides: remove default white background for transparent-popup */
.maplibregl-popup.transparent-popup .maplibregl-popup-content {
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
}
.maplibregl-popup.transparent-popup .maplibregl-popup-tip {
  display: none !important;
}
</style>

