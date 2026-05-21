<template>
  <div class="shell">

    <!-- â”€â”€â”€ TOP BAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ -->
    <header class="topbar">

      <!-- Logo -->
      <div class="topbar-logo">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="2.8" fill="#22c55e"/>
          <circle cx="3"  cy="4"  r="1.8" fill="#4b5563"/>
          <circle cx="17" cy="4"  r="1.8" fill="#4b5563"/>
          <circle cx="3"  cy="16" r="1.8" fill="#4b5563"/>
          <circle cx="17" cy="16" r="1.8" fill="#4b5563"/>
          <line x1="7.8" y1="8.2"  x2="4.6"  y2="5.5"  stroke="#374151" stroke-width="1.4"/>
          <line x1="12.2" y1="8.2" x2="15.4" y2="5.5"  stroke="#374151" stroke-width="1.4"/>
          <line x1="7.8" y1="11.8" x2="4.6"  y2="14.5" stroke="#374151" stroke-width="1.4"/>
          <line x1="12.2" y1="11.8" x2="15.4" y2="14.5" stroke="#374151" stroke-width="1.4"/>
        </svg>
        <span class="logo-text">NOC-IT</span>
      </div>

      <!-- Search -->
      <div class="topbar-search">
        <svg class="search-icon" width="13" height="13" viewBox="0 0 20 20" fill="none"
             stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="9" cy="9" r="6"/>
          <path d="M15 15 L19 19"/>
        </svg>
        <input
          type="text"
          class="search-input"
          placeholder="Search device or IP..."
          autocomplete="off"
          spellcheck="false"
        />
      </div>

      <!-- Right controls -->
      <div class="topbar-right">
        <div class="tunnel-badge" :class="tunnelConnected ? 'badge-on' : 'badge-off'">
          <span class="tunnel-dot"></span>
          <span>Tunnel: {{ tunnelConnected ? 'On' : 'Off' }}</span>
        </div>

        <button class="icon-btn" title="Notifications">
          <svg width="15" height="15" viewBox="0 0 20 20" fill="none"
               stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <path d="M10 2a6 6 0 0 0-6 6v3l-2 2v1h16v-1l-2-2V8a6 6 0 0 0-6-6z"/>
            <path d="M8 17a2 2 0 0 0 4 0"/>
          </svg>
        </button>

        <button class="avatar-btn" title="Account">U</button>
      </div>
    </header>

    <!-- â”€â”€â”€ BODY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ -->
    <div class="body-layout">

      <!-- SIDEBAR WRAPPER -->
      <div class="sidebar-wrapper" :class="{ collapsed: sidebarCollapsed }">
      <!-- SIDEBAR -->
      <nav class="sidebar">
        <div class="nav-primary">
          <button
            v-for="item in primaryNav"
            :key="item.id"
            class="nav-item"
            :class="{ active: isItemActive(item) }"
            @click="navigate(item)"
          >
            <span class="nav-icon" v-html="item.icon"></span>
            <span class="nav-label">{{ item.label }}</span>
          </button>

          <!-- Settings sub-items: moved to nav-footer as floating panel -->

          <!-- Modules sub-items -->
          <div v-if="modulesVisible" class="subnav">
            <button
              v-for="sub in modulesSubnav"
              :key="sub.path"
              class="subnav-item"
              :class="{ active: route.path === sub.path }"
              @click="selectModule(sub.path)"
            >{{ sub.label }}</button>
          </div>
        </div>

        <div class="nav-footer">
          <div class="nav-divider"></div>
            <div class="settings-box">
              <div v-if="settingsVisible" class="subnav">
                <button
                  v-for="sub in settingsSubnav"
                  :key="sub.path"
                  class="subnav-item"
                  :class="{ active: route.path === sub.path }"
                  @click="selectSettings(sub.path)"
                >{{ sub.label }}</button>
              </div>

              <button
                class="nav-item"
                :class="{ active: isSettingsOpen }"
                @click="settingsVisible = !settingsVisible"
              >
                <span class="nav-icon" v-html="icons.settings"></span>
                <span class="nav-label">Settings</span>
              </button>
            </div>
          <button class="nav-item exit-item" @click="$router.push('/')">
            <span class="nav-icon" v-html="icons.exit"></span>
            <span class="nav-label">Exit</span>
          </button>
        </div>
      </nav>
      </div><!-- /sidebar-wrapper -->

      <!-- SIDEBAR TOGGLE -->
      <button class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? 'Rozwiń menu' : 'Zwiń menu'">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline v-if="!sidebarCollapsed" points="7,2 3,6 7,10"/>
          <polyline v-else points="5,2 9,6 5,10"/>
        </svg>
      </button>

      <!-- CONTENT -->
        <main class="content">
          <keep-alive v-if="route.path === '/'">
            <PolandMap />
          </keep-alive>
          <router-view v-else />
        </main>

      <!-- App footer removed (map attribution is handled in map component if needed) -->

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { requestJson } from '../services/ApiClient'
import PolandMap from '../components/PolandMap.vue'

const router = useRouter()
const route  = useRoute()

// â”€â”€â”€ Tunnel status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const tunnelConnected = ref(false)
let tunnelTimer = null

const checkTunnel = async () => {
  try {
    const s = await requestJson('/api/tunnel/status', { timeoutMs: 10000 })
    tunnelConnected.value = s?.status === 'CONNECTED'
  } catch {
    tunnelConnected.value = false
  }
}

onMounted(() => {
  checkTunnel()
  tunnelTimer = setInterval(checkTunnel, 5000)
})
onUnmounted(() => clearInterval(tunnelTimer))

// â”€â”€â”€ Route helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const isSettingsOpen = computed(() => route.path.startsWith('/settings'))
const settingsVisible = ref(false)

// ─── Sidebar collapse ────────────────────────────────────────────────────────
const SIDEBAR_KEY = 'noc-it:sidebar-collapsed'
const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_KEY) === 'true')
watch(sidebarCollapsed, (v) => localStorage.setItem(SIDEBAR_KEY, v))

const selectSettings = (path) => {
  settingsVisible.value = false
  router.push(path)
}

// Modules visibility: local toggle so menu can hide after selecting an option
const modulesVisible = ref(false)
const selectModule = (path) => {
  modulesVisible.value = false
  router.push(path)
}

const isModulesOpen  = computed(() => route.path.startsWith('/modules'))

// â”€â”€â”€ SVG icons â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const icons = {
  home: `<svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"><path d="M3 9.5L10 3l7 6.5"/><path d="M5 8.5V17h4v-4h2v4h4V8.5"/></svg>`,
  terminal: `<svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 7 9 12 4 17"/><line x1="11" y1="17" x2="16" y2="17"/></svg>`,
  modules: `<svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><rect x="3" y="3" width="5.5" height="5.5" rx="1"/><rect x="11.5" y="3" width="5.5" height="5.5" rx="1"/><rect x="3" y="11.5" width="5.5" height="5.5" rx="1"/><rect x="11.5" y="11.5" width="5.5" height="5.5" rx="1"/></svg>`,
  settings: `<svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="10" cy="10" r="2.5"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.22 4.22l1.42 1.42M14.36 14.36l1.42 1.42M4.22 15.78l1.42-1.42M14.36 5.64l1.42-1.42"/></svg>`,
  exit: `<svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 16h3a1 1 0 0 0 1-1V5a1 1 0 0 0-1-1h-3"/><polyline points="9 14 13 10 9 6"/><line x1="13" y1="10" x2="3" y2="10"/></svg>`,
}

// â”€â”€â”€ Navigation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const primaryNav = [
  { id: 'home',     label: 'Main',     path: '/',        icon: icons.home     },
  { id: 'terminal', label: 'Terminal', path: '/terminal', icon: icons.terminal },
  { id: 'modules',  label: 'Modules',  path: '/modules/cmts-swapper', icon: icons.modules },
]

const settingsSubnav = [
  { path: '/settings/general',  label: 'General'    },
  { path: '/settings/accounts', label: 'Accounts'   },
  { path: '/settings/sites',    label: 'Sites'      },
  { path: '/settings/devices',  label: 'Devices'    },
  { path: '/settings/tunnel',   label: 'Tunneling'  },
  { path: '/settings/modules',  label: 'Modules'    },
    { path: '/settings/raports',  label: 'Reports'    },
    { path: '/settings/map',      label: 'Map'        },
]

const modulesSubnav = [
  { path: '/modules/cmts-swapper',      label: 'CMTS Swapper'      },
  { path: '/modules/cmts-tmpfs',        label: 'CMTS TMPFS'        },
  { path: '/modules/cmts-modem-reset',  label: 'CMTS Modem Reset'  },
  { path: '/modules/ssh-executor',      label: 'SSH Executor'      },
  { path: '/modules/cmts-compare',      label: 'CMTS Compare'      },
  { path: '/modules/wo-raport',          label: 'WO Raport'         },
]

const isItemActive = (item) => {
  if (item.id === 'home')     return route.path === '/' && !isSettingsOpen.value && !isModulesOpen.value
  if (item.id === 'terminal') return route.path === '/terminal'
  if (item.id === 'modules')  return isModulesOpen.value
  return false
}

const navigate = (item) => {
  if (item.id === 'modules') {
    modulesVisible.value = !modulesVisible.value
    return
  }
  router.push(item.path)
}
</script>

<style scoped>
/* â”€â”€ Layout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: #1c1f24;
  overflow: hidden;
}

/* â”€â”€ Top Bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.topbar {
  flex-shrink: 0;
  height: 46px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  background: #252a30;
  border-bottom: 1px solid #323841;
  z-index: 100;
}

.topbar-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  min-width: 100px;
}

.logo-text {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #e5e7eb;
  text-transform: uppercase;
}

.topbar-search {
  flex: 1;
  max-width: 360px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: #6b7280;
  pointer-events: none;
}

.search-input {
  width: 100%;
  height: 30px;
  padding: 0 12px 0 32px;
  background: #1c1f24;
  border: 1px solid #323841;
  border-radius: 6px;
  color: #e5e7eb;
  font-size: 12px;
  outline: none;
  transition: border-color 0.15s;
}
.search-input::placeholder { color: #4b5563; }
.search-input:focus { border-color: #4b5563; }

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.tunnel-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 5px;
  font-size: 11.5px;
  font-weight: 500;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
}

.tunnel-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.badge-on {
  background: rgba(34,197,94,0.08);
  border-color: rgba(34,197,94,0.2);
  color: #22c55e;
}
.badge-on .tunnel-dot { background: #22c55e; }

.badge-off {
  background: rgba(239,68,68,0.08);
  border-color: rgba(239,68,68,0.2);
  color: #ef4444;
}
.badge-off .tunnel-dot { background: #ef4444; }

.icon-btn {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid #323841;
  border-radius: 6px;
  color: #9ca3af;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.icon-btn:hover {
  color: #e5e7eb;
  border-color: #4b5563;
  background: #2d333b;
}

.avatar-btn {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2d333b;
  border: 1px solid #4b5563;
  border-radius: 50%;
  color: #9ca3af;
  font-size: 12px;
  font-weight: 600;
  transition: border-color 0.15s;
}
.avatar-btn:hover { border-color: #6b7280; color: #e5e7eb; }

/* Footer */
.app-footer {
  height: 34px;
  background: #0f1724;
  border-top: 1px solid #24292f;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 12px;
  flex-shrink: 0;
}
.footer-inner { max-width: 1200px; width: 100%; padding: 0 16px; text-align: center }

/* â”€â”€ Body layout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.body-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ── Sidebar wrapper (handles slide animation) ─────────────────────────────── */
.sidebar-wrapper {
  flex-shrink: 0;
  width: 200px;
  transition: width 0.28s cubic-bezier(.4,0,.2,1);
  overflow: hidden;
}
.sidebar-wrapper.collapsed {
  width: 0;
}

/* Toggle tab button – sits as a sibling flex item between sidebar and content */
.sidebar-toggle {
  flex-shrink: 0;
  align-self: center;
  width: 14px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #323841;
  border: none;
  border-radius: 0 6px 6px 0;
  color: #9ca3af;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  padding: 0;
}
.sidebar-toggle:hover {
  background: #3d444e;
  color: #e5e7eb;
}

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
.sidebar {
  flex-shrink: 0;
  width: 200px;
  height: 100%;
  background: #252a30;
  border-right: 1px solid #323841;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 8px 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-primary { display: flex; flex-direction: column; }
.nav-footer  { display: flex; flex-direction: column; padding-bottom: 4px; }

.nav-divider {
  height: 1px;
  background: #323841;
  margin: 6px 12px 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 14px;
  background: transparent;
  border: none;
  border-left: 2px solid transparent;
  color: #9ca3af;
  font-size: 12.5px;
  font-weight: 500;
  text-align: left;
  transition: color 0.12s, background 0.12s, border-color 0.12s;
  white-space: nowrap;
}
.nav-item:hover {
  color: #e5e7eb;
  background: #2d333b;
}
.nav-item.active {
  color: #e5e7eb;
  background: #2d333b;
  border-left-color: #22c55e;
}

.exit-item { color: #6b7280; }
.exit-item:hover { color: #9ca3af; }

.nav-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  opacity: 0.7;
}
.nav-item:hover .nav-icon,
.nav-item.active .nav-icon { opacity: 1; }

/* Sub-nav */
.subnav {
  display: flex;
  flex-direction: column;
  margin: 2px 0 4px;
  padding-left: 28px;
  border-left: 1px solid #323841;
  margin-left: 16px;
}

.subnav-item {
  padding: 6px 10px;
  background: transparent;
  border: none;
  color: #6b7280;
  font-size: 12px;
  text-align: left;
  border-radius: 4px;
  transition: color 0.12s, background 0.12s;
  white-space: nowrap;
}
.subnav-item:hover  { color: #e5e7eb; background: #2d333b; }
.subnav-item.active { color: #22c55e; }

/* Make nav-footer a positioning context for the floating panel */
.nav-footer { position: relative; }

/* Floating settings panel that animates up from below the Settings button */
.subnav-floating {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 56px; /* sits just above the settings button */
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 8px;
  box-shadow: 0 12px 32px rgba(0,0,0,0.6);
  transform: translateY(10px);
  opacity: 0;
  pointer-events: none;
  transition: transform 220ms cubic-bezier(.2,.8,.2,1), opacity 180ms ease;
  z-index: 50;
}
.subnav-floating.show {
  transform: translateY(0);
  opacity: 1;
  pointer-events: auto;
}
.subnav-floating .subnav-item.floating {
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  background: transparent;
  border-radius: 6px;
}
.subnav-floating .subnav-item.floating:hover { background: #21262d; }

/* â”€â”€ Content â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.content > * {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}
</style>