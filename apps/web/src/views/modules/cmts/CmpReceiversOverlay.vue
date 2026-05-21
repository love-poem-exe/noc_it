<template>
    <div class="cmp-overlay" @click="$emit('close')">
        <div class="cmp-receivers-box" @click.stop>
            <div class="cmp-receivers__header">
                <span>Odbiorniki &mdash; {{ data.cardKey }}</span>
                <button class="cmp-popup-close" @click="$emit('close')">&#x2715;</button>
            </div>
            <div class="cmp-receivers__list">
                <div
                    v-for="node in data.nodes"
                    :key="node.num"
                    class="cmp-fiber-node"
                >
                    <span class="cmp-fiber-node__label">Fiber-Node {{ node.num }}</span>
                    <span class="cmp-fiber-node__desc" :class="{ 'cmp-fiber-node__desc--empty': node.desc === 'EMPTY' }">
                        {{ node.desc }}
                    </span>
                    <span class="cmp-fiber-node__upstream">{{ node.upstream }}</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
defineProps({ data: { type: Object, required: true } })
defineEmits(['close'])
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

.cmp-receivers-box {
    background: var(--cmp-bg-surface, #161b22);
    border: 1px solid var(--cmp-color-accent, #58a6ff);
    border-radius: 8px;
    width: min(640px, calc(100vw - 32px));
    max-height: 70vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
    animation: cmp-popup-in 0.15s ease;
}

.cmp-receivers__header {
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

.cmp-receivers__list {
    display: flex;
    flex-direction: column;
    padding: 6px 0;
    overflow-y: auto;
}

.cmp-fiber-node {
    display: grid;
    grid-template-columns: max-content 1fr max-content;
    align-items: center;
    gap: 10px;
    padding: 6px 10px;
    border-bottom: 1px solid #21262d;
    font-size: 0.82rem;
}
.cmp-fiber-node:last-child { border-bottom: none; }

.cmp-fiber-node__label    { color: #8b949e; font-size: 0.75rem; white-space: nowrap; }
.cmp-fiber-node__desc     { font-family: 'Consolas', monospace; font-weight: 700; color: var(--cmp-color-text-strong, #e6edf3); word-break: break-all; }
.cmp-fiber-node__desc--empty  { color: #6e7681; font-style: italic; font-weight: 400; }
.cmp-fiber-node__upstream { font-family: 'Consolas', monospace; font-size: 0.75rem; color: var(--cmp-color-accent, #58a6ff); white-space: nowrap; }

.cmp-popup-close {
    background: none; border: none; color: #8b949e;
    cursor: pointer; font-size: 0.9rem; padding: 0 2px; line-height: 1;
}
.cmp-popup-close:hover { color: var(--cmp-color-danger, #f85149); }

@keyframes cmp-fadein   { from { opacity: 0; } to { opacity: 1; } }
@keyframes cmp-popup-in { from { opacity: 0; transform: scale(0.96); } to { opacity: 1; transform: scale(1); } }
</style>
