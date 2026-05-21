<template>
    <!-- ── Main view ──────────────────────────────────────────────────── -->
    <div class="cmp-root">
        <div class="cmp-layout">
            <div class="cmp-layout__header">
                <h1 class="cmp-layout__title">CMTS Compare</h1>
            </div>
            <CmpMeasureList
                :files="measureFiles"
                :active-file="previewFile"
                :preview-file="previewFile"
                :preview-content="previewContent"
                :preview-loading="previewLoading"
                @preview="loadPreview"
                @compare="startCompare"
                @delete="requestDeleteFile"
                @close-preview="previewFile = null"
            />
        </div>
        <button class="cmp-fab" @click="addingMeasure = true">&#43; Dodaj pomiar</button>
    </div>

    <!-- ── Delete confirmation modal ──────────────────────────────────── -->
    <CmpDeleteModal
        v-if="confirmDelete"
        :file="confirmDelete"
        @confirm="executeDelete"
        @cancel="confirmDelete = null"
    />

    <!-- ── Add measurement overlay (fullscreen) ───────────────────────── -->
    <div v-if="addingMeasure" class="cmp-add-overlay">
        <div class="cmp-add-panel" @click.stop>
            <div class="cmp-add-panel__header">
                <span>Nowy pomiar</span>
                <button class="cmp-popup-close" @click="addingMeasure = false">&#x2715;</button>
            </div>
            <div class="cmp-add-panel__body">
                <!-- Left: device selector + receiver search -->
                <div class="cmp-add-left">
                    <label class="cmp-label">Wybierz urządzenia CMTS</label>
                    <CmpDeviceDropdown
                        v-model="selectedDeviceIds"
                        :devices="cmtsDevices"
                        @remove="removeDevice"
                    />
                    <button
                        class="cmp-btn cmp-btn--verify"
                        :disabled="!selectedDevices.length || isExecuting"
                        @click="onVerify"
                    >
                        <span v-if="isExecuting" class="cmp-spinner"></span>
                        {{ isExecuting ? 'Weryfikacja…' : 'Weryfikuj' }}
                    </button>

                    <template v-if="hasResults">
                        <label class="cmp-label" style="margin-top:18px">Szukaj odbiorników</label>
                        <div class="cmp-receiver-search">
                            <textarea
                                v-model="receiverSearch"
                                class="cmp-input cmp-receiver-search__area"
                                rows="4"
                                @keydown.ctrl.enter="searchReceiver"
                            />
                            <button class="cmp-receiver-search__btn" @click="searchReceiver" title="Szukaj">&#128269;</button>
                        </div>
                        <div v-if="receiverResult" class="cmp-receiver-results">
                            <div
                                v-for="(item, i) in receiverResult"
                                :key="i"
                                class="cmp-receiver-result"
                                :class="item.found ? 'cmp-receiver-result--found' : 'cmp-receiver-result--not-found'"
                            >
                                <strong>{{ item.query }}</strong>
                                <span v-if="item.found">&nbsp;&rarr; {{ item.cards.join(', ') }}</span>
                                <span v-else>&nbsp;&mdash; nie znaleziono</span>
                            </div>
                        </div>
                    </template>
                </div>

                <!-- Right: result cards per device -->
                <div class="cmp-add-right">
                    <div v-if="!selectedDevices.length || !hasResults" class="cmp-empty">
                        Wybierz urządzenia i kliknij „Weryfikuj”
                    </div>
                    <CmpResultCard
                        v-for="device in selectedDevices"
                        :key="device.id"
                        :device="device"
                        :result="results[device.id] ?? null"
                        :is-executing="isExecuting"
                        :expanded-cards="expandedCards"
                        :checked-ifaces="checkedIfaces"
                        :active-popup-key="popupData?.cardKey ?? null"
                        :is-card-checked="isCardChecked"
                        :is-card-indeterminate="isCardIndeterminate"
                        :toggle-card="toggleCard"
                        :is-device-checked="isDeviceChecked"
                        :is-device-indeterminate="isDeviceIndeterminate"
                        :toggle-device="toggleDevice"
                        :device-checked-iface-keys="deviceCheckedIfaceKeys"
                        :device-checked-modem-count="deviceCheckedModemCount"
                        @fetch-modems="fetchModems"
                        @show-popup="showCardPopup"
                    />
                </div>
            </div>
        </div>
    </div>

    <!-- ── Receivers popup ────────────────────────────────────────────── -->
    <CmpReceiversOverlay v-if="popupData" :data="popupData" @close="popupData = null" />

    <!-- ── Modem NMS dialog ───────────────────────────────────────────── -->
    <CmpNmsDialog
        v-if="nmsDialog"
        :dialog="nmsDialog"
        @close="nmsDialog = null"
        @save="confirmSave"
        @update:nmsInput="v => nmsDialog && (nmsDialog.nmsInput = v)"
    />

    <!-- ── Compare diff dialog ────────────────────────────────────────── -->
    <CmpCompareDialog v-if="compareDialog" :dialog="compareDialog" @close="compareDialog = null" />
</template>

<script setup>
import { computed } from 'vue'
import { useCmtsCompare } from '../../composables/useCmtsCompare'
import CmpDeleteModal      from './cmts/CmpDeleteModal.vue'
import CmpDeviceDropdown   from './cmts/CmpDeviceDropdown.vue'
import CmpResultCard       from './cmts/CmpResultCard.vue'
import CmpNmsDialog        from './cmts/CmpNmsDialog.vue'
import CmpReceiversOverlay from './cmts/CmpReceiversOverlay.vue'
import CmpCompareDialog    from './cmts/CmpCompareDialog.vue'
import CmpMeasureList      from './cmts/CmpMeasureList.vue'

const {
    selectedDeviceIds, isExecuting, results, expandedCards, checkedIfaces,
    popupData, nmsDialog, measureFiles, addingMeasure, confirmDelete,
    previewFile, previewContent, previewLoading, compareDialog,
    receiverSearch, receiverResult,
    cmtsDevices, selectedDevices,
    loadPreview, requestDeleteFile, executeDelete,
    removeDevice,
    isCardChecked, isCardIndeterminate, toggleCard,
    isDeviceChecked, isDeviceIndeterminate, toggleDevice,
    deviceCheckedIfaceKeys, deviceCheckedModemCount,
    showCardPopup, onVerify,
    fetchModems, confirmSave,
    startCompare, searchReceiver,
} = useCmtsCompare()

const hasResults = computed(() => Object.keys(results).length > 0)
</script>

<style>
/* ── CSS custom properties — global so child cmp-* components can inherit —— */
:root {
    --cmp-color-text:        #c9d1d9;
    --cmp-color-text-strong: #e6edf3;
    --cmp-color-muted:       #8b949e;
    --cmp-color-accent:      #58a6ff;
    --cmp-color-ok:          #3fb950;
    --cmp-color-warn:        #d29922;
    --cmp-color-danger:      #f85149;
    --cmp-bg-base:           #0d1117;
    --cmp-bg-surface:        #161b22;
    --cmp-bg-raised:         #1c2333;
    --cmp-border:            #30363d;
    --cmp-z-dropdown:        50;
    --cmp-z-fab:             40;
    --cmp-z-overlay:         150;
    --cmp-z-modal:           200;
    --cmp-radius:            6px;
    --cmp-radius-lg:         10px;
    --cmp-gap:               16px;
    --cmp-gap-sm:            8px;
}
</style>

<style scoped>
/* layout */
.cmp-root {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 20px;
    color: var(--cmp-color-text);
    position: relative;
}
.cmp-layout { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.cmp-layout__header { display: flex; align-items: center; margin-bottom: 20px; }
.cmp-layout__title  { font-size: 1.3rem; font-weight: 600; color: var(--cmp-color-text-strong); margin: 0; }

/* FAB */
.cmp-fab {
    position: fixed; bottom: 24px; right: 24px;
    background: #238636; color: #fff; border: none; border-radius: 50px;
    padding: 12px 24px; font-size: 1rem; font-weight: 600; cursor: pointer;
    box-shadow: 0 4px 16px rgba(0,0,0,.4);
    z-index: var(--cmp-z-fab);
    transition: background .15s, transform .1s;
}
.cmp-fab:hover { background: #2ea043; transform: translateY(-1px); }

/* Add overlay */
.cmp-add-overlay {
    position: fixed; inset: 0; z-index: var(--cmp-z-overlay);
    background: var(--cmp-bg-base); display: flex; flex-direction: column; overflow: hidden;
}
.cmp-add-panel { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 0 20px 20px; }
.cmp-add-panel__header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 0 12px; border-bottom: 1px solid var(--cmp-border);
    margin-bottom: var(--cmp-gap); font-size: 1.1rem; font-weight: 600;
    color: var(--cmp-color-text-strong); flex-shrink: 0;
}
.cmp-add-panel__body { display: flex; gap: 24px; flex: 1; min-height: 0; }
.cmp-add-left {
    display: flex; flex-direction: column; gap: 12px;
    width: min(340px, 35vw); flex-shrink: 0;
}
.cmp-add-right { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; min-width: 0; }

/* forms */
.cmp-label { font-size: .85rem; color: var(--cmp-color-muted); font-weight: 500; }
.cmp-input {
    width: 100%; box-sizing: border-box; padding: 7px 10px;
    background: var(--cmp-bg-base); border: 1px solid var(--cmp-border);
    border-radius: var(--cmp-radius); color: var(--cmp-color-text);
    font-size: .85rem; outline: none; transition: border-color .15s;
}
.cmp-input:focus { border-color: var(--cmp-color-accent); }
.cmp-btn {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 20px; border: none; border-radius: var(--cmp-radius);
    font-size: .85rem; font-weight: 500; cursor: pointer; transition: background .15s;
}
.cmp-btn--verify { align-self: flex-start; background: #238636; color: #fff; }
.cmp-btn--verify:hover:not(:disabled) { background: #2ea043; }
.cmp-btn--verify:disabled             { opacity: .4; cursor: not-allowed; }
.cmp-spinner {
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,.3); border-top-color: #fff;
    border-radius: 50%; animation: cmp-spin .6s linear infinite; flex-shrink: 0;
}
@keyframes cmp-spin { to { transform: rotate(360deg); } }

/* receiver search */
.cmp-receiver-search { display: flex; gap: 6px; align-items: flex-start; }
.cmp-receiver-search__area {
    flex: 1; resize: vertical;
    font-family: 'Consolas', monospace; font-size: .82rem; line-height: 1.5;
}
.cmp-receiver-search__btn {
    background: #21262d; border: 1px solid var(--cmp-border); border-radius: var(--cmp-radius);
    color: var(--cmp-color-muted); cursor: pointer; font-size: .9rem; padding: 5px 9px;
    transition: border-color .15s, color .15s;
}
.cmp-receiver-search__btn:hover { border-color: var(--cmp-color-accent); color: var(--cmp-color-accent); }
.cmp-receiver-results { display: flex; flex-direction: column; gap: 3px; margin-top: 6px; }
.cmp-receiver-result  { font-size: .78rem; padding: 4px 8px; border-radius: 4px; font-family: 'Consolas', monospace; }
.cmp-receiver-result--found     { background: #1a3a2a; color: var(--cmp-color-ok);     border: 1px solid #2ea043; }
.cmp-receiver-result--not-found { background: #2d1b1b; color: var(--cmp-color-danger); border: 1px solid #6e2020; }

/* misc */
.cmp-empty {
    display: flex; align-items: center; justify-content: center;
    height: 100%; color: #484f58; font-size: .9rem;
}
.cmp-popup-close {
    background: none; border: none; color: var(--cmp-color-muted);
    cursor: pointer; font-size: 1.1rem; padding: 0 2px; line-height: 1;
}
.cmp-popup-close:hover { color: var(--cmp-color-danger); }
</style>
