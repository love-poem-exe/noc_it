<template>
  <div class="map-wrap">

    <!-- â”€â”€â”€ Tooltip â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ -->
    <Transition name="tip">
      <div
        v-if="tooltip.visible"
        class="tip-box"
        :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
      >
        <div class="tip-city">{{ tooltip.city.name }}</div>
        <div class="tip-divider"></div>
        <div class="tip-row">
          <span class="tip-key">Devices</span>
          <span class="tip-val">{{ tooltip.city.devices }}</span>
        </div>
        <div class="tip-row">
          <span class="tip-key">Down</span>
          <span class="tip-val" :class="tooltip.city.down > 0 ? 'val-crit' : 'val-ok'">
            {{ tooltip.city.down }}
          </span>
        </div>
        <div class="tip-row">
          <span class="tip-key">Updated</span>
          <span class="tip-val tip-time">{{ tooltip.city.lastUpdate }}</span>
        </div>
      </div>
    </Transition>

    <!-- â”€â”€â”€ Map SVG â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ -->
    <svg
      viewBox="0 0 800 600"
      preserveAspectRatio="xMidYMid meet"
      class="poland-svg"
    >
      <!-- â”€â”€ Poland outline â”€â”€  -->
      <path
        d="M 109,125
           L 186,103 L 270,80 L 345,78
           L 365,88  L 364,100
           L 413,83  L 421,79
           L 566,83  L 644,163
           L 653,227 L 679,279
           L 673,341 L 679,395
           L 591,484 L 446,501
           L 375,477 L 358,443
           L 311,416 L 260,403
           L 181,371 L 142,357
           L 129,253 L 115,191
           L 109,149 Z"
        class="poland-fill"
      />

      <!-- â”€â”€ Network links (drawn first, under nodes) â”€â”€ -->
      <line
        v-for="link in links"
        :key="link.id"
        :x1="cityById(link.a).x" :y1="cityById(link.a).y"
        :x2="cityById(link.b).x" :y2="cityById(link.b).y"
        :class="['link', 'link-' + link.status]"
      />

      <!-- â”€â”€ City nodes â”€â”€ -->
      <g
        v-for="city in cities"
        :key="city.id"
        class="city-group"
        @mouseenter="showTooltip($event, city)"
        @mouseleave="hideTooltip"
        @mousemove="moveTooltip($event)"
      >
        <!-- Shadow ring (subtle depth, no glow) -->
        <circle
          :cx="city.x" :cy="city.y"
          :r="nodeRadius(city.devices) + 2.5"
          class="node-shadow"
        />
        <!-- Main node -->
        <circle
          :cx="city.x" :cy="city.y"
          :r="nodeRadius(city.devices)"
          :class="['node', 'node-' + city.status]"
        />
        <!-- Device count -->
        <text
          :x="city.x" :y="city.y + 0.5"
          text-anchor="middle"
          dominant-baseline="middle"
          class="node-count"
        >{{ city.devices }}</text>
        <!-- City label -->
        <text
          :x="city.x"
          :y="city.y < 200
            ? city.y - nodeRadius(city.devices) - 8
            : city.y + nodeRadius(city.devices) + 14"
          text-anchor="middle"
          class="city-label"
        >{{ city.name }}</text>
      </g>
    </svg>

  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'

// â”€â”€â”€ Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const cities = ref([
  {
    id: 'gdansk',   name: 'Gdansk',
    x: 364, y: 89,
    devices: 28, down: 1, status: 'warn',
    lastUpdate: '3 min ago'
  },
  {
    id: 'szczecin', name: 'Szczecin',
    x: 145, y: 163,
    devices: 17, down: 0, status: 'ok',
    lastUpdate: '1 min ago'
  },
  {
    id: 'poznan',   name: 'Poznan',
    x: 264, y: 244,
    devices: 22, down: 0, status: 'ok',
    lastUpdate: '2 min ago'
  },
  {
    id: 'wroclaw',  name: 'Wroclaw',
    x: 270, y: 348,
    devices: 38, down: 2, status: 'warn',
    lastUpdate: '4 min ago'
  },
  {
    id: 'lodz',     name: 'Lodz',
    x: 411, y: 295,
    devices: 29, down: 0, status: 'ok',
    lastUpdate: '1 min ago'
  },
  {
    id: 'warsaw',   name: 'Warszawa',
    x: 501, y: 259,
    devices: 54, down: 0, status: 'ok',
    lastUpdate: '< 1 min ago'
  },
  {
    id: 'lublin',   name: 'Lublin',
    x: 591, y: 337,
    devices: 18, down: 0, status: 'ok',
    lastUpdate: '2 min ago'
  },
  {
    id: 'katowice', name: 'Katowice',
    x: 385, y: 416,
    devices: 45, down: 0, status: 'ok',
    lastUpdate: '2 min ago'
  },
  {
    id: 'krakow',   name: 'Krakow',
    x: 439, y: 432,
    devices: 31, down: 12, status: 'crit',
    lastUpdate: '8 min ago'
  },
])

const links = [
  { id: 1, a: 'szczecin', b: 'poznan',   status: 'ok'   },
  { id: 2, a: 'poznan',   b: 'wroclaw',  status: 'ok'   },
  { id: 3, a: 'poznan',   b: 'lodz',     status: 'warn' },
  { id: 4, a: 'wroclaw',  b: 'katowice', status: 'ok'   },
  { id: 5, a: 'lodz',     b: 'warsaw',   status: 'ok'   },
  { id: 6, a: 'lodz',     b: 'katowice', status: 'warn' },
  { id: 7, a: 'warsaw',   b: 'gdansk',   status: 'ok'   },
  { id: 8, a: 'warsaw',   b: 'lublin',   status: 'ok'   },
  { id: 9, a: 'katowice', b: 'krakow',   status: 'down' },
  { id:10, a: 'lublin',   b: 'krakow',   status: 'down' },
]

// â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const cityMap = computed(() =>
  Object.fromEntries(cities.value.map(c => [c.id, c]))
)
const cityById = (id) => cityMap.value[id]

const nodeRadius = (devices) =>
  Math.max(11, Math.min(19, Math.round(8 + devices / 4.5)))

// â”€â”€â”€ Tooltip â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const tooltip = reactive({ visible: false, x: 0, y: 0, city: null })

const showTooltip = (event, city) => {
  tooltip.city = city
  tooltip.x = event.clientX + 18
  tooltip.y = event.clientY - 12
  tooltip.visible = true
}
const moveTooltip = (event) => {
  if (!tooltip.visible) return
  tooltip.x = event.clientX + 18
  tooltip.y = event.clientY - 12
}
const hideTooltip = () => { tooltip.visible = false }
</script>

<style scoped>
/* â”€â”€ Wrapper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.map-wrap {
  width: 100%;
  height: 100%;
  background: #1c1f24;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* â”€â”€ SVG â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.poland-svg {
  width: 100%;
  height: 100%;
  max-width: 900px;
  max-height: 680px;
}

/* â”€â”€ Poland fill â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.poland-fill {
  fill: #252a30;
  stroke: #3d444e;
  stroke-width: 1.2;
  stroke-linejoin: round;
}

/* â”€â”€ Links â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.link {
  fill: none;
  opacity: 0.75;
}
.link-ok   { stroke: #22c55e; stroke-width: 1.2; }
.link-warn { stroke: #f59e0b; stroke-width: 1.5; }
.link-down { stroke: #ef4444; stroke-width: 2.0; }

/* â”€â”€ Node shadow (soft depth, no glow) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.node-shadow {
  fill: rgba(0, 0, 0, 0.25);
  stroke: none;
}

/* â”€â”€ Nodes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.node {
  stroke: #1c1f24;
  stroke-width: 2;
  cursor: default;
}
.node-ok   { fill: #22c55e; }
.node-warn { fill: #f59e0b; }
.node-crit { fill: #ef4444; }
.node-none { fill: #4b5563; }

/* â”€â”€ Count text â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.node-count {
  fill: #ffffff;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: -0.01em;
  pointer-events: none;
  user-select: none;
}

/* â”€â”€ City labels â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.city-label {
  fill: #9ca3af;
  font-size: 8.5px;
  font-weight: 500;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  pointer-events: none;
  user-select: none;
}

/* â”€â”€ City group hover â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.city-group { cursor: pointer; }
.city-group:hover .node { opacity: 0.85; }
.city-group:hover .city-label { fill: #e5e7eb; }

/* â”€â”€ Tooltip â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.tip-box {
  position: fixed;
  z-index: 200;
  min-width: 148px;
  background: #252a30;
  border: 1px solid #3d444e;
  border-radius: 5px;
  padding: 10px 12px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.45);
  pointer-events: none;
}

.tip-city {
  font-size: 12px;
  font-weight: 600;
  color: #e5e7eb;
  margin-bottom: 6px;
}

.tip-divider {
  height: 1px;
  background: #323841;
  margin-bottom: 7px;
}

.tip-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 4px;
}
.tip-row:last-child { margin-bottom: 0; }

.tip-key {
  font-size: 11px;
  color: #6b7280;
}
.tip-val {
  font-size: 11px;
  font-weight: 600;
  color: #e5e7eb;
}
.val-ok   { color: #22c55e; }
.val-crit { color: #ef4444; }
.tip-time { font-weight: 400; color: #9ca3af; }

/* â”€â”€ Tooltip transition â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.tip-enter-active, .tip-leave-active { transition: opacity 0.1s; }
.tip-enter-from, .tip-leave-to       { opacity: 0; }
</style>