<template>
    <div class="cmp-overlay" @click.self="$emit('close')">
        <div class="cmp-nms-box" @click.stop>
            <!-- Header -->
            <div class="cmp-nms__header">
                <span>
                    Modemy &mdash; {{ dialog.deviceHostname }}
                    <small class="cmp-nms__ifaces">{{ dialog.ifaces.join(', ') }}</small>
                </span>
                <button class="cmp-popup-close" @click="$emit('close')">&#x2715;</button>
            </div>

            <!-- Loading / error -->
            <div v-if="dialog.loading" class="cmp-nms__loading">Pobieranie modemów&hellip;</div>
            <div v-else-if="dialog.fetchError" class="cmp-nms__error">{{ dialog.fetchError }}</div>

            <!-- Table -->
            <template v-else-if="dialog.rows">
                <div class="cmp-modem-head">
                    <span>MAC</span><span>IP</span><span>Interfejs</span><span>Status</span><span>dBmV</span>
                </div>
                <div class="cmp-modem-body">
                    <div
                        v-for="(row, i) in dialog.rows"
                        :key="i"
                        class="cmp-modem-row"
                        :class="{ 'cmp-modem-row--offline': !row.status.includes('online') }"
                    >
                        <span class="cmp-modem-mac">{{ row.mac }}</span>
                        <span>{{ row.ip }}</span>
                        <span class="cmp-modem-iface">{{ row.iface }}</span>
                        <span :class="row.status.includes('online') ? 'cmp-val--ok' : 'cmp-val--warn'">
                            {{ row.status.includes('online') ? '1' : '0' }}
                        </span>
                        <span>{{ row.dBmV }}</span>
                    </div>
                    <div v-if="dialog.rows.length === 0" class="cmp-nms__empty">Brak modemów</div>
                </div>

                <!-- Save footer -->
                <div class="cmp-nms__footer">
                    <template v-if="!dialog.saveOk">
                        <input
                            :value="dialog.nmsInput"
                            @input="$emit('update:nmsInput', $event.target.value)"
                            type="text"
                            class="cmp-input cmp-nms__input"
                            placeholder="Numer NMS, np. 368158"
                            @keydown.enter="$emit('save')"
                        />
                        <small class="cmp-nms__hint">{{ dialog.nmsInput || 'NMS' }}-{{ dialog.timestamp }}.txt</small>
                        <button
                            class="cmp-btn cmp-btn--primary"
                            :disabled="!dialog.nmsInput?.trim() || dialog.saving"
                            @click="$emit('save')"
                        >
                            {{ dialog.saving ? 'Zapisywanie…' : 'Zapisz' }}
                        </button>
                        <div v-if="dialog.saveError" class="cmp-nms__error" style="margin:0">{{ dialog.saveError }}</div>
                    </template>
                    <div v-else class="cmp-nms__success">
                        &#10003; Zapisano: <code>{{ dialog.savedPath }}</code>
                    </div>
                </div>
            </template>
        </div>
    </div>
</template>

<script setup>
defineProps({ dialog: { type: Object, required: true } })
defineEmits(['close', 'save', 'update:nmsInput'])
</script>

<style scoped>
.cmp-overlay {
    position: fixed;
    inset: 0;
    z-index: var(--cmp-z-modal, 200);
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.45);
    animation: cmp-fadein 0.15s ease;
}

.cmp-nms-box {
    background: var(--cmp-bg-surface, #161b22);
    border: 1px solid var(--cmp-color-accent, #58a6ff);
    border-radius: 8px;
    width: min(700px, calc(100vw - 32px));
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
    animation: cmp-popup-in 0.15s ease;
}

.cmp-nms__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid var(--cmp-border, #30363d);
    font-size: 0.82rem;
    color: var(--cmp-color-accent, #58a6ff);
    font-weight: 600;
    flex-shrink: 0;
}
.cmp-nms__ifaces { color: #8b949e; font-weight: 400; margin-left: 4px; }

.cmp-nms__loading,
.cmp-nms__empty {
    padding: 20px;
    text-align: center;
    color: #8b949e;
    font-size: 0.85rem;
}
.cmp-nms__error { padding: 14px; color: var(--cmp-color-danger, #f85149); font-size: 0.82rem; }

/* Modem table */
.cmp-modem-head,
.cmp-modem-row {
    display: grid;
    grid-template-columns: 160px 130px 140px 1fr 60px;
    padding: 4px 14px;
    align-items: center;
    font-size: 0.8rem;
    gap: 4px;
}
.cmp-modem-head {
    border-bottom: 1px solid var(--cmp-border, #30363d);
    color: #8b949e;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    position: sticky;
    top: 0;
    background: var(--cmp-bg-surface, #161b22);
    flex-shrink: 0;
}
.cmp-modem-body { overflow-y: auto; }
.cmp-modem-row:nth-child(even)    { background: var(--cmp-bg-base, #0d1117); }
.cmp-modem-row--offline           { opacity: 0.65; }
.cmp-modem-mac  { font-family: 'Consolas', monospace; color: var(--cmp-color-text, #c9d1d9); }
.cmp-modem-iface { font-family: 'Consolas', monospace; font-size: 0.75rem; color: #8b949e; }

/* Footer */
.cmp-nms__footer {
    border-top: 1px solid var(--cmp-border, #30363d);
    padding: 10px 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
    flex-wrap: wrap;
}
.cmp-nms__input { flex: 1; min-width: 160px; }
.cmp-nms__hint {
    color: #6e7680;
    font-size: 0.74rem;
    font-family: 'Consolas', monospace;
}
.cmp-nms__success {
    background: #1a3a2a;
    border: 1px solid #2ea043;
    border-radius: 5px;
    color: var(--cmp-color-ok, #3fb950);
    font-size: 0.82rem;
    padding: 8px 12px;
    line-height: 1.6;
    width: 100%;
}
.cmp-nms__success code { font-family: 'Consolas', monospace; color: #79c0ff; }

/* Shared */
.cmp-popup-close {
    background: none; border: none; color: #8b949e;
    cursor: pointer; font-size: 0.9rem; padding: 0 2px; line-height: 1;
}
.cmp-popup-close:hover { color: var(--cmp-color-danger, #f85149); }

.cmp-input {
    padding: 7px 10px;
    background: var(--cmp-bg-base, #0d1117);
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 6px;
    color: var(--cmp-color-text, #c9d1d9);
    font-size: 0.85rem;
    outline: none;
    transition: border-color 0.15s;
    box-sizing: border-box;
}
.cmp-input:focus { border-color: var(--cmp-color-accent, #58a6ff); }

.cmp-btn {
    padding: 7px 20px;
    border-radius: 6px;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    border: none;
    transition: background 0.15s;
    white-space: nowrap;
}
.cmp-btn--primary { background: #238636; color: #fff; }
.cmp-btn--primary:hover:not(:disabled) { background: #2ea043; }
.cmp-btn--primary:disabled { opacity: 0.4; cursor: not-allowed; }

.cmp-val--ok   { color: var(--cmp-color-ok,   #3fb950); }
.cmp-val--warn { color: var(--cmp-color-warn,  #d29922); }

@keyframes cmp-fadein   { from { opacity: 0; } to { opacity: 1; } }
@keyframes cmp-popup-in { from { opacity: 0; transform: scale(0.96); } to { opacity: 1; transform: scale(1); } }
</style>
