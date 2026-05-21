<template>
    <div class="cmp-card">
        <!-- Header row -->
        <div class="cmp-card__header">
            <input
                v-if="result?.cardList"
                type="checkbox"
                class="cmp-check"
                :checked="isDeviceChecked(device.id)"
                :indeterminate.prop="isDeviceIndeterminate(device.id)"
                @change="toggleDevice(device.id, $event.target.checked)"
            />
            <span class="cmp-card__hostname">{{ device.hostname }}</span>
            <span v-if="device.vendor" class="cmp-card__vendor">{{ device.vendor }}</span>
            <span v-if="result && !result.error" class="cmp-badge cmp-badge--ok">
                {{ result.filteredCount }} {{ result.filteredCount === 1 ? 'karta' : 'kart' }}
            </span>
            <span v-if="result" class="cmp-badge" :class="result.error ? 'cmp-badge--error' : 'cmp-badge--ok'">
                {{ result.error ? 'Błąd' : 'OK' }}
            </span>
            <span v-else-if="isExecuting" class="cmp-badge cmp-badge--pending">Oczekiwanie…</span>
            <button
                v-if="result && !result.error && deviceCheckedIfaceKeys(device.id).length"
                class="cmp-card__fetch-btn"
                @click="$emit('fetchModems', device)"
            >
                &#128205; Pobierz modemy ({{ deviceCheckedModemCount(device.id) }})
            </button>
        </div>

        <!-- Structured Cisco card table -->
        <template v-if="result?.cardList">
            <div class="cmp-table">
                <div class="cmp-table__head">
                    <span></span><span></span><span>Karta</span>
                    <span>Total</span><span>Reg</span><span>Offline</span>
                </div>
                <div v-for="card in result.cardList" :key="card.key" class="cmp-table__group">
                    <!-- Card summary row -->
                    <div
                        class="cmp-table__row cmp-table__row--summary"
                        @click.self="toggleExpand(device.id, card.key)"
                    >
                        <input
                            type="checkbox"
                            class="cmp-check"
                            :checked="isCardChecked(device.id, card)"
                            :indeterminate.prop="isCardIndeterminate(device.id, card)"
                            @click.stop
                            @change="toggleCard(device.id, card, $event.target.checked)"
                        />
                        <span class="cmp-table__expand" @click="toggleExpand(device.id, card.key)">
                            {{ expandedCards[device.id + '__' + card.key] ? '▾' : '▸' }}
                        </span>
                        <span class="cmp-table__card-key" @click="toggleExpand(device.id, card.key)">
                            {{ card.key }}
                        </span>
                        <span>{{ card.total }}</span>
                        <span :class="card.reg === card.total ? 'cmp-val--ok' : ''">
                            {{ card.reg }} <small>({{ card.total > 0 ? Math.round(card.reg / card.total * 100) : 0 }}%)</small>
                        </span>
                        <span :class="(card.total - card.reg) > 0 ? 'cmp-val--warn' : 'cmp-val--ok'">
                            {{ card.total - card.reg }} <small>({{ card.total > 0 ? Math.round((card.total - card.reg) / card.total * 100) : 0 }}%)</small>
                        </span>
                        <button
                            v-if="result.fiberMap?.[card.key]?.length"
                            class="cmp-table__popup-btn"
                            :class="{ 'cmp-table__popup-btn--active': activePopupKey === card.key }"
                            @click="$emit('showPopup', device.id, card.key, $event)"
                            title="Pokaż odbiorniki"
                        >&#128246;</button>
                    </div>

                    <!-- Expanded iface rows -->
                    <template v-if="expandedCards[device.id + '__' + card.key]">
                        <div
                            v-for="iface in card.ifaceList"
                            :key="iface.key"
                            class="cmp-table__row cmp-table__row--iface"
                        >
                            <input
                                type="checkbox"
                                class="cmp-check"
                                :checked="checkedIfaces[device.id + '__' + iface.key]"
                                @change="checkedIfaces[device.id + '__' + iface.key] = $event.target.checked"
                            />
                            <span></span>
                            <span class="cmp-table__iface-name">{{ iface.key }}</span>
                            <span>{{ iface.total }}</span>
                            <span :class="iface.reg === iface.total ? 'cmp-val--ok' : ''">
                                {{ iface.reg }} <small>({{ iface.total > 0 ? Math.round(iface.reg / iface.total * 100) : 0 }}%)</small>
                            </span>
                            <span :class="(iface.total - iface.reg) > 0 ? 'cmp-val--warn' : 'cmp-val--ok'">
                                {{ iface.total - iface.reg }}
                            </span>
                        </div>
                    </template>
                </div>
            </div>
        </template>

        <!-- Raw output (non-Cisco or error) -->
        <pre v-else-if="result" class="cmp-card__raw">{{ result.error || result.output }}</pre>
    </div>
</template>

<script setup>
const props = defineProps({
    device:                 { type: Object,  required: true },
    result:                 { type: Object,  default: null  },
    isExecuting:            { type: Boolean, default: false },
    expandedCards:          { type: Object,  required: true },
    checkedIfaces:          { type: Object,  required: true },
    activePopupKey:         { type: String,  default: null  },
    isCardChecked:          { type: Function, required: true },
    isCardIndeterminate:    { type: Function, required: true },
    toggleCard:             { type: Function, required: true },
    isDeviceChecked:        { type: Function, required: true },
    isDeviceIndeterminate:  { type: Function, required: true },
    toggleDevice:           { type: Function, required: true },
    deviceCheckedIfaceKeys: { type: Function, required: true },
    deviceCheckedModemCount:{ type: Function, required: true },
})
const emit = defineEmits(['fetchModems', 'showPopup'])

function toggleExpand(deviceId, cardKey) {
    const k = deviceId + '__' + cardKey
    props.expandedCards[k] = !props.expandedCards[k]
}
</script>

<style scoped>
.cmp-card {
    background: var(--cmp-bg-surface, #161b22);
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 6px;
    overflow: hidden;
}

/* Header */
.cmp-card__header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--cmp-border, #30363d);
    background: #1c2333;
}
.cmp-card__hostname { font-weight: 600; font-size: 0.85rem; color: var(--cmp-color-text-strong, #e6edf3); }
.cmp-card__vendor {
    font-size: 0.72rem;
    color: var(--cmp-color-accent, #58a6ff);
    background: rgba(88, 166, 255, 0.1);
    padding: 1px 6px;
    border-radius: 4px;
}
.cmp-card__fetch-btn {
    margin-left: auto;
    background: #1f3a5f;
    border: 1px solid #388bfd;
    border-radius: 5px;
    color: var(--cmp-color-accent, #58a6ff);
    cursor: pointer;
    font-size: 0.75rem;
    padding: 3px 10px;
    transition: background 0.15s;
}
.cmp-card__fetch-btn:hover { background: #264a7a; }

/* Badges */
.cmp-badge {
    font-size: 0.75rem;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 10px;
}
.cmp-badge--ok {
    background: rgba(35, 134, 54, 0.25);
    color: var(--cmp-color-ok, #3fb950);
}
.cmp-badge--error {
    background: rgba(248, 81, 73, 0.2);
    color: var(--cmp-color-danger, #f85149);
}
.cmp-badge--pending {
    background: rgba(210, 153, 34, 0.2);
    color: var(--cmp-color-warn, #d29922);
}

/* Table */
.cmp-table {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 0.78rem;
    padding: 6px 0;
}

.cmp-table__head {
    display: grid;
    grid-template-columns: 24px 20px 90px 1fr 1fr 1fr;
    padding: 4px 12px;
    color: #8b949e;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--cmp-border, #30363d);
    margin-bottom: 2px;
}

.cmp-table__group {
    border-bottom: 1px solid #21262d;
}

.cmp-table__row {
    display: grid;
    grid-template-columns: 24px 20px 90px 1fr 1fr 1fr;
    padding: 4px 12px;
    align-items: center;
}
.cmp-table__row--summary {
    grid-template-columns: 24px 20px 90px 1fr 1fr 1fr auto;
    cursor: pointer;
    user-select: none;
    color: var(--cmp-color-text, #c9d1d9);
    font-weight: 600;
    transition: background 0.1s;
}
.cmp-table__row--summary:hover { background: #1c2333; }
.cmp-table__row--iface {
    color: #8b949e;
    font-weight: 400;
    font-size: 0.75rem;
    background: rgba(0, 0, 0, 0.15);
}

.cmp-table__expand   { color: #8b949e; font-size: 0.7rem; }
.cmp-table__card-key { color: #79c0ff; }
.cmp-table__iface-name { color: var(--cmp-color-text, #c9d1d9); padding-left: 8px; }

.cmp-table__popup-btn {
    margin-left: auto;
    background: none;
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 4px;
    color: #8b949e;
    cursor: pointer;
    font-size: 0.8rem;
    padding: 1px 6px;
    line-height: 1.4;
    transition: border-color 0.15s, color 0.15s;
}
.cmp-table__popup-btn:hover,
.cmp-table__popup-btn--active {
    border-color: var(--cmp-color-accent, #58a6ff);
    color: var(--cmp-color-accent, #58a6ff);
}

/* Value coloring */
.cmp-val--ok   { color: var(--cmp-color-ok,   #3fb950); }
.cmp-val--warn { color: var(--cmp-color-warn,  #d29922); }

/* Checkbox */
.cmp-check { accent-color: var(--cmp-color-accent, #58a6ff); cursor: pointer; width: 14px; height: 14px; margin: 0; }

/* Raw output */
.cmp-card__raw {
    margin: 0;
    padding: 10px 12px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 0.78rem;
    line-height: 1.5;
    color: var(--cmp-color-text, #c9d1d9);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 300px;
    overflow-y: auto;
}
</style>
