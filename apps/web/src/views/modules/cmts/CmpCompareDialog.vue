<template>
    <div class="cmp-overlay" @click.self="$emit('close')">
        <div class="cmp-compare-box">
            <!-- Header -->
            <div class="cmp-compare__header">
                <div>
                    <span class="cmp-compare__title">Porównanie</span>
                    <span class="cmp-compare__subtitle">
                        &nbsp;{{ dialog.header?.cmts }} &mdash; {{ dialog.header?.date }}
                    </span>
                </div>
                <button class="cmp-popup-close" @click="$emit('close')">&#x2715;</button>
            </div>

            <!-- States -->
            <div v-if="dialog.loading" class="cmp-compare__loading">
                Pobieranie aktualnych danych&hellip;
            </div>
            <div v-else-if="dialog.error" class="cmp-compare__error">{{ dialog.error }}</div>

            <template v-else-if="dialog.diff">
                <!-- Summary badges -->
                <div class="cmp-compare__summary">
                    <span class="cmp-cbadge cmp-cbadge--offline">&#8595; offline: {{ dialog.diff.wentOffline.length }}</span>
                    <span class="cmp-cbadge cmp-cbadge--online">&#8593; online: {{ dialog.diff.cameOnline.length }}</span>
                    <span class="cmp-cbadge cmp-cbadge--gone">zniknęło: {{ dialog.diff.disappeared.length }}</span>
                    <span class="cmp-cbadge cmp-cbadge--new">nowe: {{ dialog.diff.appeared.length }}</span>
                    <span class="cmp-cbadge cmp-cbadge--total">{{ dialog.diff.totalOld }} &rarr; {{ dialog.diff.totalNew }}</span>
                </div>

                <div v-if="hasChanges" class="cmp-compare__body">
                    <div class="cmp-diff-head">
                        <span>Zmiana</span><span>MAC</span><span>IP</span><span>Interfejs</span>
                    </div>
                    <div v-for="r in dialog.diff.wentOffline"  :key="'off-'+r.mac"  class="cmp-diff-row cmp-diff-row--offline">
                        <span class="cmp-diff-tag">&#8595; offline</span><span>{{ r.mac }}</span><span>{{ r.ip }}</span><span>{{ r.iface }}</span>
                    </div>
                    <div v-for="r in dialog.diff.cameOnline"   :key="'on-'+r.mac"   class="cmp-diff-row cmp-diff-row--online">
                        <span class="cmp-diff-tag">&#8593; online</span><span>{{ r.mac }}</span><span>{{ r.ip }}</span><span>{{ r.iface }}</span>
                    </div>
                    <div v-for="r in dialog.diff.disappeared"  :key="'gone-'+r.mac" class="cmp-diff-row cmp-diff-row--gone">
                        <span class="cmp-diff-tag">zniknął</span><span>{{ r.mac }}</span><span>{{ r.ip }}</span><span>{{ r.iface }}</span>
                    </div>
                    <div v-for="r in dialog.diff.appeared"     :key="'new-'+r.mac"  class="cmp-diff-row cmp-diff-row--new">
                        <span class="cmp-diff-tag">nowy</span><span>{{ r.mac }}</span><span>{{ r.ip }}</span><span>{{ r.iface }}</span>
                    </div>
                </div>
                <div v-else class="cmp-compare__nochange">
                    Brak zmian — stan identyczny
                </div>
            </template>
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ dialog: { type: Object, required: true } })
defineEmits(['close'])

const hasChanges = computed(() => {
    const d = props.dialog.diff
    return d && (d.wentOffline.length || d.cameOnline.length || d.disappeared.length || d.appeared.length)
})
</script>

<style scoped>
.cmp-overlay {
    position: fixed;
    inset: 0;
    z-index: var(--cmp-z-overlay, 150);
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
}

.cmp-compare-box {
    background: var(--cmp-bg-surface, #161b22);
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 10px;
    width: min(700px, calc(100vw - 32px));
    max-height: 85vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.cmp-compare__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    border-bottom: 1px solid var(--cmp-border, #30363d);
    background: var(--cmp-bg-base, #0d1117);
    flex-shrink: 0;
}
.cmp-compare__title    { font-size: 1rem; font-weight: 700; color: var(--cmp-color-text-strong, #e6edf3); }
.cmp-compare__subtitle { font-size: 0.8rem; color: #8b949e; }

.cmp-compare__loading {
    padding: 24px 18px;
    color: #8b949e;
    font-size: 0.88rem;
}
.cmp-compare__error { padding: 14px 18px; color: var(--cmp-color-danger, #f85149); font-size: 0.82rem; }

/* Summary badges */
.cmp-compare__summary {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px 18px;
    border-bottom: 1px solid #21262d;
    flex-shrink: 0;
}
.cmp-cbadge {
    font-size: 0.78rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid;
}
.cmp-cbadge--offline { color: #f85149; border-color: #6e3535; background: #1a0a0a; }
.cmp-cbadge--online  { color: #3fb950; border-color: #1a4731; background: #0a1a0a; }
.cmp-cbadge--gone    { color: #d29922; border-color: #5a3e00; background: #1a1200; }
.cmp-cbadge--new     { color: #58a6ff; border-color: #1f4080; background: #0a1525; }
.cmp-cbadge--total   { color: #8b949e; border-color: var(--cmp-border, #30363d); background: var(--cmp-bg-surface, #161b22); }

/* Diff table */
.cmp-compare__body { overflow-y: auto; flex: 1; padding: 0 0 12px; }
.cmp-diff-head {
    display: grid;
    grid-template-columns: 90px 160px 130px 1fr;
    padding: 3px 18px;
    font-size: 0.72rem;
    color: #6e7681;
    font-weight: 600;
    text-transform: uppercase;
}
.cmp-diff-row {
    display: grid;
    grid-template-columns: 90px 160px 130px 1fr;
    padding: 4px 18px;
    font-family: 'Consolas', monospace;
    font-size: 0.8rem;
    border-bottom: 1px solid var(--cmp-bg-base, #0d1117);
}
.cmp-diff-tag {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    align-self: center;
}
.cmp-diff-row--offline { background: #1a0a0a; color: #ffa198; }
.cmp-diff-row--online  { background: #0a1a0a; color: #7ee787; }
.cmp-diff-row--gone    { background: #1a1200; color: #e3b341; }
.cmp-diff-row--new     { background: #0a1525; color: #79c0ff; }

.cmp-compare__nochange { padding: 24px 18px; color: var(--cmp-color-ok, #3fb950); font-size: 0.9rem; }

.cmp-popup-close {
    background: none; border: none; color: #8b949e;
    cursor: pointer; font-size: 0.9rem; padding: 0 2px; line-height: 1;
}
.cmp-popup-close:hover { color: var(--cmp-color-danger, #f85149); }
</style>
