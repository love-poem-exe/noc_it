<template>
    <div class="cmp-measure-layout">
        <!-- List -->
        <div class="cmp-measure-list">
            <div v-if="!files.length" class="cmp-measure-list__empty">
                Brak zapisanych pomiarów
            </div>
            <div
                v-for="file in files"
                :key="file"
                class="cmp-file-row"
            >
                <button
                    class="cmp-file-btn"
                    :class="{ 'cmp-file-btn--active': activeFile === file }"
                    @click="$emit('preview', file)"
                >
                    <span class="cmp-file-btn__nms">{{ parse(file).nms }}</span>
                    <span class="cmp-file-btn__date">{{ parse(file).date }}&nbsp;&nbsp;{{ parse(file).time }}</span>
                </button>
                <button class="cmp-action-btn cmp-action-btn--compare" title="Porównaj" @click="$emit('compare', file)">&#61;</button>
                <button class="cmp-action-btn cmp-action-btn--delete"  title="Usuń"     @click="$emit('delete',  file)">&#x2715;</button>
            </div>
        </div>

        <!-- Inline preview panel -->
        <div v-if="previewFile" class="cmp-preview">
            <div class="cmp-preview__header">
                <span class="cmp-preview__title">{{ previewFile }}</span>
                <button class="cmp-popup-close" @click="$emit('closePreview')">&#x2715;</button>
            </div>
            <div v-if="previewLoading" class="cmp-preview__loading">Wczytywanie&hellip;</div>
            <pre v-else class="cmp-preview__content">{{ previewContent }}</pre>
        </div>
    </div>
</template>

<script setup>
import { parseMeasureFilename } from '../../../composables/useCmtsCompare'

const props = defineProps({
    files:          { type: Array,   required: true },
    activeFile:     { type: String,  default: null },
    previewFile:    { type: String,  default: null },
    previewContent: { type: String,  default: '' },
    previewLoading: { type: Boolean, default: false },
})
defineEmits(['preview', 'compare', 'delete', 'closePreview'])

const parse = parseMeasureFilename
</script>

<style scoped>
.cmp-measure-layout {
    display: flex;
    gap: 16px;
    flex: 1;
    min-height: 0;
    align-items: flex-start;
}

/* List */
.cmp-measure-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    overflow-y: auto;
    flex-shrink: 0;
}
.cmp-measure-list__empty {
    padding: 20px 0;
    color: #484f58;
    font-size: 0.9rem;
}

.cmp-file-row {
    display: flex;
    align-items: stretch;
    gap: 6px;
}

.cmp-file-btn {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
    width: min(15vw, 200px);
    min-width: 120px;
    text-align: left;
    background: var(--cmp-bg-surface, #161b22);
    border: 1px solid var(--cmp-border, #30363d);
    color: var(--cmp-color-text, #c9d1d9);
    padding: 7px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    overflow: hidden;
}
.cmp-file-btn:hover        { background: #1f2937; border-color: var(--cmp-color-accent, #58a6ff); }
.cmp-file-btn--active      { background: #1c2a3a; border-color: var(--cmp-color-accent, #58a6ff); }

.cmp-file-btn__nms {
    font-family: 'Courier New', monospace;
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--cmp-color-text-strong, #e6edf3);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.cmp-file-btn__date {
    font-size: 0.72rem;
    color: #8b949e;
    white-space: nowrap;
}

.cmp-action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 6px;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 700;
    background: var(--cmp-bg-surface, #161b22);
    transition: background 0.15s, border-color 0.15s;
}
.cmp-action-btn--compare { color: var(--cmp-color-accent, #58a6ff); border-color: #1f6feb; }
.cmp-action-btn--compare:hover { background: #1a2d4a; }
.cmp-action-btn--delete  { color: var(--cmp-color-danger, #f85149); border-color: #6e3535; }
.cmp-action-btn--delete:hover  { background: #3d1c1c; border-color: var(--cmp-color-danger, #f85149); }

/* Inline preview */
.cmp-preview {
    width: 40%;
    flex-shrink: 0;
    align-self: flex-start;
    position: sticky;
    top: 0;
    max-height: 40vh;
    background: var(--cmp-bg-surface, #161b22);
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.cmp-preview__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    border-bottom: 1px solid var(--cmp-border, #30363d);
    background: var(--cmp-bg-base, #0d1117);
    flex-shrink: 0;
}
.cmp-preview__title {
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
    color: #8b949e;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cmp-preview__loading { padding: 20px; color: #8b949e; font-size: 0.85rem; }
.cmp-preview__content {
    flex: 1;
    overflow-y: auto;
    padding: 12px 14px;
    margin: 0;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 0.75rem;
    line-height: 1.55;
    color: var(--cmp-color-text, #c9d1d9);
    white-space: pre;
    tab-size: 4;
}

.cmp-popup-close {
    background: none; border: none; color: #8b949e;
    cursor: pointer; font-size: 0.9rem; padding: 0 2px; line-height: 1;
}
.cmp-popup-close:hover { color: var(--cmp-color-danger, #f85149); }
</style>
