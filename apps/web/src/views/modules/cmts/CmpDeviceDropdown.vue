<template>
    <!-- Dropdown trigger -->
    <div class="cmp-dropdown" ref="wrapperRef">
        <div class="cmp-dropdown__trigger" @click="open = !open">
            <span v-if="!selectedDevices.length" class="cmp-dropdown__placeholder">Wybierz urządzenia...</span>
            <span v-else class="cmp-dropdown__summary">
                {{ selectedDevices.length }} {{ selectedDevices.length === 1 ? 'urządzenie' : 'urządzeń' }}
            </span>
            <span class="cmp-dropdown__arrow" :class="{ 'cmp-dropdown__arrow--open': open }">&#9662;</span>
        </div>

        <div v-if="open" class="cmp-dropdown__menu">
            <input
                v-model="query"
                type="text"
                class="cmp-dropdown__search"
                placeholder="Szukaj..."
                @click.stop
            />
            <div class="cmp-dropdown__list">
                <label
                    v-for="device in filtered"
                    :key="device.id"
                    class="cmp-dropdown__item"
                    @click.stop
                >
                    <input
                        type="checkbox"
                        :value="device.id"
                        :checked="modelValue.includes(device.id)"
                        @change="toggle(device.id, $event.target.checked)"
                    />
                    <span class="cmp-dd-hostname">{{ device.hostname }}</span>
                    <span v-if="device.vendor" class="cmp-dd-vendor">{{ device.vendor }}</span>
                    <span class="cmp-dd-address">{{ device.address }}</span>
                </label>
                <div v-if="!filtered.length" class="cmp-dropdown__empty">Brak wyników</div>
            </div>
        </div>
    </div>

    <!-- Selected tags -->
    <div v-if="selectedDevices.length" class="cmp-tags">
        <span v-for="device in selectedDevices" :key="device.id" class="cmp-tag">
            {{ device.hostname }}
            <span v-if="device.vendor" class="cmp-tag__vendor"> · {{ device.vendor }}</span>
            <span class="cmp-tag__remove" @click="$emit('remove', device.id)">&times;</span>
        </span>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
    devices:     { type: Array,  required: true },
    modelValue:  { type: Array,  required: true },   // selected IDs
})
const emit = defineEmits(['update:modelValue', 'remove'])

const open       = ref(false)
const query      = ref('')
const wrapperRef = ref(null)

const filtered = computed(() => {
    if (!query.value) return props.devices
    const q = query.value.toLowerCase()
    return props.devices.filter(d =>
        d.hostname.toLowerCase().includes(q) || d.address.includes(q))
})

const selectedDevices = computed(() =>
    props.devices.filter(d => props.modelValue.includes(d.id)))

function toggle(id, checked) {
    const next = checked
        ? [...props.modelValue, id]
        : props.modelValue.filter(i => i !== id)
    emit('update:modelValue', next)
}

function onOutside(e) {
    if (wrapperRef.value && !wrapperRef.value.contains(e.target)) open.value = false
}
onMounted(()         => document.addEventListener('click', onOutside))
onBeforeUnmount(()   => document.removeEventListener('click', onOutside))
</script>

<style scoped>
.cmp-dropdown {
    position: relative;
}

.cmp-dropdown__trigger {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 6px;
    background: var(--cmp-bg-surface, #161b22);
    cursor: pointer;
    user-select: none;
    transition: border-color 0.15s;
}
.cmp-dropdown__trigger:hover { border-color: var(--cmp-color-accent, #58a6ff); }

.cmp-dropdown__placeholder { color: #484f58; }
.cmp-dropdown__summary     { color: var(--cmp-color-text, #c9d1d9); }
.cmp-dropdown__arrow {
    font-size: 0.7rem;
    color: #8b949e;
    transition: transform 0.15s;
}
.cmp-dropdown__arrow--open { transform: rotate(180deg); }

.cmp-dropdown__menu {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    background: var(--cmp-bg-surface, #161b22);
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 6px;
    z-index: var(--cmp-z-dropdown, 50);
    max-height: 280px;
    display: flex;
    flex-direction: column;
}

.cmp-dropdown__search {
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid var(--cmp-border, #30363d);
    background: transparent;
    color: var(--cmp-color-text, #c9d1d9);
    font-size: 0.85rem;
    outline: none;
}
.cmp-dropdown__search::placeholder { color: #484f58; }

.cmp-dropdown__list {
    overflow-y: auto;
    max-height: 230px;
}

.cmp-dropdown__item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 0.85rem;
    transition: background 0.1s;
}
.cmp-dropdown__item:hover { background: #1c2333; }
.cmp-dropdown__item input[type="checkbox"] { accent-color: var(--cmp-color-accent, #58a6ff); cursor: pointer; }

.cmp-dropdown__empty {
    padding: 12px;
    text-align: center;
    color: #484f58;
    font-size: 0.85rem;
}

.cmp-dd-hostname { color: var(--cmp-color-text-strong, #e6edf3); flex: 1; }
.cmp-dd-address  { color: #484f58; font-size: 0.78rem; font-family: monospace; }
.cmp-dd-vendor {
    font-size: 0.72rem;
    color: var(--cmp-color-accent, #58a6ff);
    background: rgba(88, 166, 255, 0.1);
    padding: 1px 5px;
    border-radius: 4px;
}

/* Tags */
.cmp-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.cmp-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    background: #1c2333;
    border: 1px solid var(--cmp-border, #30363d);
    border-radius: 4px;
    font-size: 0.78rem;
    color: var(--cmp-color-text, #c9d1d9);
}
.cmp-tag__vendor { color: var(--cmp-color-accent, #58a6ff); opacity: 0.8; }
.cmp-tag__remove { cursor: pointer; color: #8b949e; font-size: 0.9rem; margin-left: 2px; }
.cmp-tag__remove:hover { color: var(--cmp-color-danger, #f85149); }
</style>
