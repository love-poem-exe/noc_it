<template>
    <div class="cmp-overlay" @click.self="$emit('cancel')">
        <div class="cmp-modal">
            <div class="cmp-modal__title">Usuń pomiar</div>
            <div class="cmp-modal__body">
                Czy na pewno chcesz usunąć plik?<br>
                <code class="cmp-modal__filename">{{ file }}</code>
            </div>
            <div class="cmp-modal__actions">
                <button class="cmp-btn cmp-btn--ghost" @click="$emit('cancel')">Anuluj</button>
                <button class="cmp-btn cmp-btn--danger" @click="$emit('confirm')">Usuń</button>
            </div>
        </div>
    </div>
</template>

<script setup>
defineProps({ file: { type: String, required: true } })
defineEmits(['confirm', 'cancel'])
</script>

<style scoped>
.cmp-overlay {
    position: fixed;
    inset: 0;
    z-index: var(--cmp-z-modal, 200);
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
}

.cmp-modal {
    background: var(--cmp-bg-surface, #161b22);
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 10px;
    padding: 28px 32px 22px;
    width: min(480px, calc(100vw - 32px));
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.cmp-modal__title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--cmp-color-danger, #f85149);
}

.cmp-modal__body {
    font-size: 0.9rem;
    color: var(--cmp-color-text, #c9d1d9);
    line-height: 1.6;
}

.cmp-modal__filename {
    display: inline-block;
    margin-top: 6px;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: var(--cmp-color-text-strong, #e6edf3);
    background: var(--cmp-bg-base, #0d1117);
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 4px;
    padding: 3px 8px;
    word-break: break-all;
}

.cmp-modal__actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 4px;
}

.cmp-btn {
    padding: 7px 20px;
    border-radius: 6px;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid transparent;
    transition: background 0.15s;
}
.cmp-btn--ghost {
    background: #21262d;
    border-color: var(--cmp-border, #30363d);
    color: var(--cmp-color-text, #c9d1d9);
}
.cmp-btn--ghost:hover { background: #2d333b; }

.cmp-btn--danger {
    background: #b91c1c;
    border-color: var(--cmp-color-danger, #f85149);
    color: #fff;
}
.cmp-btn--danger:hover { background: #dc2626; }
</style>
