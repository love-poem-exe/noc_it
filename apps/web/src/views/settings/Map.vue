<template>
  <div class="settings-map">
    <!-- Top bar -->
    <div class="top-bar">
      <button class="btn-sync" :disabled="syncing" @click="onSync">
        {{ syncing ? 'Synchronizing...' : 'Synchronize connections' }}
      </button>
      <input
        v-model="search"
        class="search-input"
        placeholder="Search devices / interfaces..."
      />
      <span class="conn-count" v-if="connections.length">
        {{ totalFiltered }} connections
        ({{ filteredGroups.length }} pairs)
      </span>
    </div>

    <!-- Table -->
    <div class="table-wrapper" v-if="filteredGroups.length">
      <table>
        <thead>
          <tr>
            <th @click="toggleSort('sideA')">
              Side A
              <span class="sort-arrow">{{ sortArrow('sideA') }}</span>
            </th>
            <th @click="toggleSort('sideB')">
              Side B
              <span class="sort-arrow">{{ sortArrow('sideB') }}</span>
            </th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="group in filteredGroups" :key="group.key">
            <!-- Group header -->
            <tr class="group-header" @click="toggleGroup(group.key)">
              <td colspan="3">
                <span class="chevron" :class="{ collapsed: isCollapsed(group.key) }">▶</span>
                {{ group.nameA }} &lt;&gt; {{ group.nameB }}
              </td>
            </tr>
            <!-- Connection rows -->
            <tr v-for="conn in group.items" v-show="!isCollapsed(group.key)" :key="conn.connection_id">
              <td>{{ conn.nameA }} : {{ conn.interfaceA }}</td>
              <td>{{ conn.deviceB }} : {{ conn.interfaceB }}</td>
              <td :title="conn.descriptionA">{{ truncate(conn.descriptionA, 60) }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Empty state -->
    <div class="status-msg" v-else-if="!loading">
      {{ connections.length === 0 ? 'No connections yet — click Synchronize.' : 'No results matching filter.' }}
    </div>
    <div class="status-msg" v-else>Loading connections...</div>
  </div>
</template>

<script>
import { requestJson } from '../../services/ApiClient'

export default {
  name: 'SettingsMap',

  data() {
    return {
      connections: [],
      loading: false,
      syncing: false,
      search: '',
      sortKey: 'pair',
      sortAsc: true,
      collapsedGroups: {}
    }
  },

  computed: {
    /** Group connections by device pair (sorted nameA < nameB for consistent keys) */
    grouped() {
      const map = {}
      for (const c of this.connections) {
        const [a, b] = [c.nameA, c.deviceB].sort()
        const key = `${a}|||${b}`
        if (!map[key]) map[key] = { key, nameA: a, nameB: b, items: [] }
        map[key].items.push(c)
      }
      // Sort items inside each group by interfaceA
      for (const g of Object.values(map)) {
        g.items.sort((x, y) => (x.interfaceA || '').localeCompare(y.interfaceA || ''))
      }
      return Object.values(map)
    },

    /** Apply search filter */
    filteredGroups() {
      let groups = this.grouped
      const q = this.search.trim().toLowerCase()
      if (q) {
        groups = groups
          .map(g => ({
            ...g,
            items: g.items.filter(c =>
              (c.nameA || '').toLowerCase().includes(q) ||
              (c.deviceB || '').toLowerCase().includes(q) ||
              (c.interfaceA || '').toLowerCase().includes(q) ||
              (c.interfaceB || '').toLowerCase().includes(q) ||
              (c.descriptionA || '').toLowerCase().includes(q) ||
              (c.descriptionB || '').toLowerCase().includes(q) ||
              (c.match_rule || '').toLowerCase().includes(q)
            )
          }))
          .filter(g => g.items.length > 0)
      }

      // Sort groups
      const dir = this.sortAsc ? 1 : -1
      if (this.sortKey === 'pair') {
        groups.sort((a, b) => a.key.localeCompare(b.key) * dir)
      }
      return groups
    },

    totalFiltered() {
      return this.filteredGroups.reduce((s, g) => s + g.items.length, 0)
    }
  },

  methods: {
    async fetchConnections() {
      this.loading = true
      try {
        const data = await requestJson('/api/connections')
        this.connections = Array.isArray(data) ? data : []
      } catch (e) {
        console.error('Failed to load connections', e)
      } finally {
        this.loading = false
      }
    },

    async onSync() {
      this.syncing = true
      try {
        const res = await requestJson('/api/connections/sync', { method: 'POST', timeoutMs: 120000 })
        console.log('Connections sync result:', res)
        await this.fetchConnections()
      } catch (e) {
        console.error('Connections sync failed', e)
        alert('Connections sync failed')
      } finally {
        this.syncing = false
      }
    },

    truncate(str, max) {
      if (!str) return ''
      return str.length > max ? str.slice(0, max) + '…' : str
    },

    matchClass(rule) {
      if (rule === 'exact') return 'match-exact'
      if (rule === 'normalized') return 'match-normalized'
      return 'match-other'
    },

    isCollapsed(key) {
      return this.collapsedGroups[key] !== false
    },

    toggleGroup(key) {
      this.collapsedGroups = { ...this.collapsedGroups, [key]: this.isCollapsed(key) ? false : true }
    },

    toggleSort(key) {
      if (this.sortKey === key) {
        this.sortAsc = !this.sortAsc
      } else {
        this.sortKey = key
        this.sortAsc = true
      }
    },

    sortArrow(key) {
      if (this.sortKey !== key) return ''
      return this.sortAsc ? '▲' : '▼'
    }
  },

  mounted() {
    this.fetchConnections()
  }
}
</script>

<style scoped>
/* ============================================================
   Connections table — dark theme (GitHub Dark palette)
   ============================================================ */
.settings-map {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 1rem;
  box-sizing: border-box;
  background: #0d1117;
  color: #e6edf3;
  overflow: hidden;
}

/* --- Top bar ---------------------------------------------- */
.top-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 0.75rem;
  flex-shrink: 0;
}

.top-bar button {
  padding: 7px 14px;
  background: #21262d;
  color: #e6edf3;
  border: 1px solid #30363d;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  white-space: nowrap;
}
.top-bar button:hover { background: #2d333b; border-color: #484f58; }

.btn-sync {
  background: #238636 !important;
  border-color: #238636 !important;
  color: #fff !important;
}
.btn-sync:hover { background: #3fb950 !important; border-color: #3fb950 !important; }
.btn-sync:disabled { opacity: 0.55; cursor: wait; }

.search-input {
  flex: 1;
  padding: 7px 10px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #e6edf3;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.search-input:focus { border-color: #388bfd; }
.search-input::placeholder { color: #484f58; }

.conn-count {
  font-size: 12px;
  color: #8b949e;
  white-space: nowrap;
}

/* --- Table ----------------------------------------------- */
.table-wrapper {
  flex: 1;
  overflow: auto;
  border: 1px solid #30363d;
  border-radius: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 750px;
}

th, td {
  border-bottom: 1px solid #21262d;
  padding: 8px 12px;
  text-align: left;
  color: #e6edf3;
  font-size: 12.5px;
  white-space: nowrap;
}

th {
  background: #161b22;
  color: #8b949e;
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #30363d;
  position: sticky;
  top: 0;
  z-index: 5;
  cursor: pointer;
  user-select: none;
}
th:hover { color: #e6edf3; }
th .sort-arrow { margin-left: 4px; font-size: 10px; }

tr { background: #0d1117; }
tr:nth-child(even) { background: #0f1318; }
tr:hover { background: #161b22; }

/* --- Group header row ------------------------------------ */
.group-header {
  cursor: pointer;
}
.group-header:hover td { background: #1c2129; }
.group-header td {
  background: #161b22;
  font-weight: 600;
  font-size: 13px;
  color: #388bfd;
  border-bottom: 1px solid #30363d;
  padding: 6px 12px;
}

.chevron {
  display: inline-block;
  margin-right: 6px;
  font-size: 10px;
  transition: transform 0.15s;
  transform: rotate(90deg);
}
.chevron.collapsed {
  transform: rotate(0deg);
}

/* --- Match rule badge ------------------------------------ */
.match-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.03em;
}
.match-exact      { background: rgba(63,185,80,0.15);  color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
.match-normalized { background: rgba(56,139,253,0.15); color: #388bfd; border: 1px solid rgba(56,139,253,0.3); }
.match-other      { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }

/* --- Status messages ------------------------------------- */
.status-msg {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b949e;
  font-size: 14px;
}
</style>
