<style src="../../styles/settings/devices.css"></style>
<template>
  <div class="devices-container">
    <!-- LEWY PANEL -->
    <div class="left-panel">
      <template v-if="!editingParams">
        <p v-if="duplicateWarning" class="warning-text">
          Urządzenie jest już na liście.
        </p>

        <input v-model="address" placeholder="Adres IP / host (np. 192.168.1.1 lub pl-waw16a-ra1)" @input="duplicateWarning = false" />
        <div style="display:flex; gap:8px; align-items:center;">
          <button @click="submit">Dodaj urządzenie</button>
          <button @click="addAndSync" style="background:#1f6feb;">Dodaj urządzenie i synchronizuj</button>
        </div>
        
        <div class="info-text">
          <small>💡 Możesz dodać urządzenie podając adres IP lub nazwę hosta. System automatycznie spróbuje rozwiązać nazwy DNS.</small>
        </div>

        <input type="file" ref="fileInput" style="display: none" @change="handleImport" accept=".txt" />
        <button @click="triggerImport">Importuj urządzenia</button>

        <button class="edit-params-button" @click="startEditing">
          Edycja parametrów
        </button>
      </template>

      <template v-else>
        <div class="spacer"></div>
        <button class="back-button" @click="stopEditing">
          Powrót
        </button>
      </template>
    </div>

    <!-- PRAWY PANEL -->
    <div class="right-panel">
      <template v-if="!editingParams">
        <div class="fixed-header">
          <input v-model="searchQuery" class="search-input" placeholder="Wyszukaj..." />

          <div class="burger-menu">
            <button class="burger-button" @click="toggleMenu">☰</button>
            <div v-if="menuOpen" class="dropdown">              <button @click="onSyncAll">Synchronizuj wszystkie</button>
              <button @click="onSyncUnsync">Synchronizuj UNSYNC</button>              <button @click="onSyncError">Synchronizuj ERROR</button>
              <button @click="onSyncIncomplete">Synchronizuj niekompletne</button>
              <button @click="fixHostnameAddresses" style="color: orange;">Napraw adresy hostname</button>
              <button @click="removeAllErrorDevices" style="color: red;">Usuń wszystkie ERROR</button>
              <button @click="removeAllUnsyncDevices" style="color: red;">Usuń wszystkie UNSYNC</button>
            </div>
          </div>
        </div>

        <div class="table-container">
          <table v-if="filteredDevices.length > 0">
            <thead>
              <tr>
                <th>Hostname</th>
                <th>Status</th>
                <th>Akcje</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="device in filteredDevices" :key="device.id" :class="{ incomplete: hasEmptyField(device) }">
                <td>{{ device.hostname }}</td>
                <td>                  <span class="status" :class="{
                    'status-unsync': device.status === 'UNSYNC',
                    'status-syncing': device.status === 'SYNCING',
                    'status-synced': device.status === 'SYNCED',
                    'status-error': device.status === 'ERROR'
                  }">
                    {{ device.status }}
                  </span>
                </td>
                <td>
                  <template v-if="device.status === 'SYNCED'">
                    <button @click="showInfo(device)">ℹ️</button>
                    <button @click="openEdit(device)">✏️</button>
                  </template>
                  <template v-else>
                    <button @click="syncDeviceSingle(device.id)">🔄</button>
                  </template>
                  <button @click="removeDevice(device.id)">❌</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="no-devices-text">Brak urządzeń do wyświetlenia.</p>
        </div>
      </template>

      <!-- PANEL EDYCJI PARAMETRÓW devices_info.json -->
      <template v-else>
        <div class="params-editor">
          <!-- Sekcja Vendor -->
          <div class="section-block">
            <div class="collapsible-header" @click="toggleSection('vendor')">
              <svg v-if="!collapsibleSections.vendor" xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                fill="currentColor" class="bi bi-chevron-right" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M6.646 12.146a.5.5 0 0 1 0-.708L9.793 
                    8 6.646 4.854a.5.5 0 1 1 .708-.708l3.5 
                    3.5a.5.5 0 0 1 0 .708l-3.5 3.5a.5.5 
                    0 0 1-.708 0z" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
                class="bi bi-chevron-down" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 
                    .708 0L8 10.293l5.646-5.647a.5.5 
                    0 0 1 .708.708l-6 6a.5.5 
                    0 0 1-.708 0l-6-6a.5.5 
                    0 0 1 0-.708z" />
              </svg>
              <span class="section-title">Vendor</span>
            </div>
            <div class="section-content" v-show="collapsibleSections.vendor">
              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>Wartość</th>
                    <th>Aliasów</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(aliases, value) in editableDevicesInfo.vendorKeysMap" :key="value">
                    <td>
                      <button class="delete-row-button" @click="removeSectionRow('vendor', value)">❌</button>
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.vendorValueMap[value]" type="text" />
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.vendorKeysMap[value]" type="text" />
                    </td>
                  </tr>
                </tbody>
              </table>
              <button class="add-button" @click="addSectionRow('vendor')">+ Dodaj</button>
            </div>
          </div>

          <!-- Sekcja Model -->
          <div class="section-block">
            <div class="collapsible-header" @click="toggleSection('model')">
              <svg v-if="!collapsibleSections.model" xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                fill="currentColor" class="bi bi-chevron-right" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M6.646 12.146a.5.5 0 0 1 0-.708L9.793 
                    8 6.646 4.854a.5.5 0 1 1 
                    .708-.708l3.5 3.5a.5.5 
                    0 0 1 0 .708l-3.5 3.5a.5.5 
                    0 0 1-.708 0z" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
                class="bi bi-chevron-down" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 
                    .708 0L8 10.293l5.646-5.647a.5.5 
                    0 0 1 .708.708l-6 6a.5.5 
                    0 0 1-.708 0l-6-6a.5.5 
                    0 0 1 0-.708z" />
              </svg>
              <span class="section-title">Model</span>
            </div>
            <div class="section-content" v-show="collapsibleSections.model">
              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>Wartość</th>
                    <th>Aliasów</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(aliases, value) in editableDevicesInfo.modelKeysMap" :key="value">
                    <td>
                      <button class="delete-row-button" @click="removeSectionRow('model', value)">❌</button>
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.modelValueMap[value]" type="text" />
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.modelKeysMap[value]" type="text" />
                    </td>
                  </tr>
                </tbody>
              </table>
              <button class="add-button" @click="addSectionRow('model')">+ Dodaj</button>
            </div>
          </div>

          <!-- Sekcja Software -->
          <div class="section-block">
            <div class="collapsible-header" @click="toggleSection('software')">
              <svg v-if="!collapsibleSections.software" xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                fill="currentColor" class="bi bi-chevron-right" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M6.646 12.146a.5.5 0 0 1 
                    0-.708L9.793 8 6.646 4.854a.5.5 
                    0 1 1 .708-.708l3.5 3.5a.5.5 
                    0 0 1 0 .708l-3.5 3.5a.5.5 
                    0 0 1-.708 0z" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
                class="bi bi-chevron-down" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 
                    .708 0L8 10.293l5.646-5.647a.5.5 
                    0 0 1 .708.708l-6 6a.5.5 
                    0 0 1-.708 0l-6-6a.5.5 
                    0 0 1 0-.708z" />
              </svg>
              <span class="section-title">Software</span>
            </div>
            <div class="section-content" v-show="collapsibleSections.software">
              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>Wartość</th>
                    <th>Aliasów</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(aliases, value) in editableDevicesInfo.softwareKeysMap" :key="value">
                    <td>
                      <button class="delete-row-button" @click="removeSectionRow('software', value)">❌</button>
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.softwareValueMap[value]" type="text" />
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.softwareKeysMap[value]" type="text" />
                    </td>
                  </tr>
                </tbody>
              </table>
              <button class="add-button" @click="addSectionRow('software')">+ Dodaj</button>
            </div>
          </div>

          <!-- Sekcja Typ urządzenia -->
          <div class="section-block">
            <div class="collapsible-header" @click="toggleSection('type')">
              <svg v-if="!collapsibleSections.type" xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                fill="currentColor" class="bi bi-chevron-right" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M6.646 12.146a.5.5 0 0 1 
                    0-.708L9.793 8 6.646 4.854a.5.5 
                    0 1 1 .708-.708l3.5 3.5a.5.5 
                    0 0 1 0 .708l-3.5 3.5a.5.5 
                    0 0 1-.708 0z" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
                class="bi bi-chevron-down" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 
                    .708 0L8 10.293l5.646-5.647a.5.5 
                    0 0 1 .708.708l-6 6a.5.5 
                    0 0 1-.708 0l-6-6a.5.5 
                    0 0 1 0-.708z" />
              </svg>
              <span class="section-title">Typ urządzenia</span>
            </div>
            <div class="section-content" v-show="collapsibleSections.type">
              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>Wartość</th>
                    <th>Aliasów</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(aliases, value) in editableDevicesInfo.typeKeysMap" :key="value">
                    <td>
                      <button class="delete-row-button" @click="removeSectionRow('type', value)">❌</button>
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.typeValueMap[value]" type="text" />
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.typeKeysMap[value]" type="text" />
                    </td>
                  </tr>
                </tbody>
              </table>
              <button class="add-button" @click="addSectionRow('type')">+ Dodaj</button>
            </div>
          </div>

          <!-- Sekcja Hostname (regex) -->
          <div class="section-block">
            <div class="collapsible-header" @click="toggleSection('hostname')">
              <svg v-if="!collapsibleSections.hostname" xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                fill="currentColor" class="bi bi-chevron-right" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M6.646 12.146a.5.5 0 0 1 
                    0-.708L9.793 8 6.646 4.854a.5.5 
                    0 1 1 .708-.708l3.5 3.5a.5.5 
                    0 0 1 0 .708l-3.5 3.5a.5.5 
                    0 0 1-.708 0z" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
                class="bi bi-chevron-down" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 
                    .708 0L8 10.293l5.646-5.647a.5.5 
                    0 0 1 .708.708l-6 6a.5.5 
                    0 0 1-.708 0l-6-6a.5.5 
                    0 0 1 0-.708z" />
              </svg>
              <span class="section-title">Hostname (regex)</span>
            </div>
            <div class="section-content" v-show="collapsibleSections.hostname">
              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>Regex</th>
                    <th>Wartość</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(val, regex) in editableDevicesInfo.hostnameRegexMap" :key="regex">
                    <td>
                      <button class="delete-row-button" @click="removeSectionRow('hostname', regex)">❌</button>
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.hostnameRegexMap[regex]" type="text" />
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.hostnameRegexMap[regex]" type="text" />
                    </td>
                  </tr>
                </tbody>
              </table>
              <button class="add-button" @click="addSectionRow('hostname')">+ Dodaj</button>
            </div>
          </div>

          <!-- Sekcja Address (regex) -->
          <div class="section-block">
            <div class="collapsible-header" @click="toggleSection('address')">
              <svg v-if="!collapsibleSections.address" xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                fill="currentColor" class="bi bi-chevron-right" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M6.646 12.146a.5.5 0 0 1 
                    0-.708L9.793 8 6.646 4.854a.5.5 
                    0 1 1 .708-.708l3.5 3.5a.5.5 
                    0 0 1 0 .708l-3.5 3.5a.5.5 
                    0 0 1-.708 0z" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
                class="bi bi-chevron-down" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 
                    .708 0L8 10.293l5.646-5.647a.5.5 
                    0 0 1 .708.708l-6 6a.5.5 
                    0 0 1-.708 0l-6-6a.5.5 
                    0 0 1 0-.708z" />
              </svg>
              <span class="section-title">Address (regex)</span>
            </div>
            <div class="section-content" v-show="collapsibleSections.address">
              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>Regex</th>
                    <th>Wartość</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(val, regex) in editableDevicesInfo.addressRegexMap" :key="regex">
                    <td>
                      <button class="delete-row-button" @click="removeSectionRow('address', regex)">❌</button>
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.addressRegexMap[regex]" type="text" />
                    </td>
                    <td>
                      <input v-model="editableDevicesInfo.addressRegexMap[regex]" type="text" />
                    </td>
                  </tr>
                </tbody>
              </table>
              <button class="add-button" @click="addSectionRow('address')">+ Dodaj</button>
            </div>
          </div>

          <div class="params-actions">
            <button class="save-button" @click="saveParams">Zapisz parametry</button>
            <button class="cancel-button" @click="stopEditing">Anuluj</button>
          </div>
        </div>
      </template>
    </div>

    <!-- MODAL INFO (szczegóły urządzenia) -->
    <div v-if="selectedDevice" class="device-modal">
      <div class="modal-content">
        <button class="close-button" @click="selectedDevice = null">✕</button>
        <ul class="device-details-list">
          <li>
            <span class="detail-label">Hostname:&nbsp;</span>
            <span class="detail-value">{{ selectedDevice.hostname || '-' }}</span>
          </li>
          <li>
            <span class="detail-label">Adres:&nbsp;</span>
            <span class="detail-value">{{ selectedDevice.address }}</span>
          </li>
          <li>
            <span class="detail-label">Status:&nbsp;</span>
            <span class="detail-value">{{ selectedDevice.status }}</span>
          </li>
          <li>
            <span class="detail-label">Vendor:&nbsp;</span>
            <span class="detail-value">{{ selectedDevice.vendor || '-' }}</span>
          </li>
          <li>
            <span class="detail-label">Model:&nbsp;</span>
            <span class="detail-value">{{ selectedDevice.model || '-' }}</span>
          </li>
          <li>
            <span class="detail-label">Software:&nbsp;</span>
            <span class="detail-value">{{ selectedDevice.software || '-' }}</span>
          </li>
          <li>
            <span class="detail-label">Typ urządzenia:&nbsp;</span>
            <span class="detail-value">{{ selectedDevice.type || '-' }}</span>
          </li>
          <li>
            <span class="detail-label">Konto:&nbsp;</span>
            <span class="detail-value">{{ accountName(selectedDevice.account) || '-' }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- MODAL EDYCJI URZĄDZENIA + SHOW VERSION PO KLIKNIĘCIU -->
    <div v-if="editModalOpen" class="device-modal">
      <!-- 
        Główna klasa "modal-content" + dynamiczna klasa:
        - small, gdy showVersionVisible=false
        - large, gdy showVersionVisible=true
      -->
      <div class="modal-content" :class="showVersionVisible ? 'large' : 'small'">
        <!-- Gdy showVersionVisible=true: po lewej widzimy output -->
        <div v-if="showVersionVisible" class="show-version-output">
          <div v-if="isLoadingVersion">Pobieranie danych...</div>
          <pre v-else-if="showVersionResult">{{ showVersionResult }}</pre>
        </div>

        <!-- Formularz edycji (po prawej w układzie flex, gdy showVersionVisible=true) -->
        <div class="edit-form" :style="{ flex: showVersionVisible ? '1' : 'auto' }">
          <button class="close-button" @click="closeEdit">✕</button>
          <h3>Edytuj urządzenie</h3>
          <form @submit.prevent="saveEdit">
            <div class="form-row">
              <label>Hostname:</label>
              <input v-model="editDevice.hostname" type="text" />
            </div>
            <div class="form-row">
              <label>Adres:</label>
              <input v-model="editDevice.address" type="text" />
            </div>
            <div class="form-row">
              <label>Vendor:</label>
              <select v-model="editDevice.vendor" :class="{
                'field-empty': isFieldChanged('vendor') === 'empty',
                'field-changed': isFieldChanged('vendor') === 'changed',
                'field-confirmed': isFieldChanged('vendor') === 'confirmed'
              }">
                <option value="">— wybierz —</option>
                <option v-for="opt in vendorOptions" :key="opt" :value="opt">
                  {{ opt }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>Model:</label>
              <select v-model="editDevice.model" :class="{
                'field-empty': isFieldChanged('model') === 'empty',
                'field-changed': isFieldChanged('model') === 'changed',
                'field-confirmed': isFieldChanged('model') === 'confirmed'
              }">
                <option value="">— wybierz —</option>
                <option v-for="opt in modelOptions" :key="opt" :value="opt">
                  {{ opt }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>Software:</label>
              <select v-model="editDevice.software" :class="{
                'field-empty': isFieldChanged('software') === 'empty',
                'field-changed': isFieldChanged('software') === 'changed',
                'field-confirmed': isFieldChanged('software') === 'confirmed'
              }">
                <option value="">— wybierz —</option>
                <option v-for="opt in softwareOptions" :key="opt" :value="opt">
                  {{ opt }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>Typ urządzenia:</label>
              <select v-model="editDevice.type" :class="{ 
                'field-empty': isFieldChanged('type') === 'empty',
                'field-changed': isFieldChanged('type') === 'changed',
                'field-confirmed': isFieldChanged('type') === 'confirmed'
              }">
                <option value="">— wybierz —</option>
                <option v-for="opt in typeOptions" :key="opt" :value="opt">
                  {{ opt }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>Konto:</label>
              <select v-model="editDevice.account">
                <option value="">— brak —</option>
                <option v-for="acc in accounts" :key="acc.id" :value="acc.id">
                  {{ acc.name }}
                </option>
              </select>
            </div>

            <div class="modal-actions">
              <button type="button" @click="runShowVersion">Show version</button>
              <button type="submit">Zapisz</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- ALERT / IMPORT / PROGRESS -->
    <div v-if="alertMessage" class="custom-alert">{{ alertMessage }}</div>    <!-- Pasek postępu synchronizacji/importu -->
    <div v-if="syncTotal > 0" class="progress-overlay">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        <div class="progress-text">{{ progressPercent }}%</div>
      </div>
      <div class="progress-info">
        <span>Postęp: {{ syncProgress }} / {{ syncTotal }}</span>
        <span>Czas: {{ formattedElapsed }}</span>
      </div>
    </div>

    <div v-if="showImportMessage" class="import-message" :style="{ backgroundColor: importMessageColor }">
      {{ importMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, computed } from 'vue'
import { requestJson } from '../../services/ApiClient'
import devicesInfo from '../../../src/data/devices_info.json'
import useData from '../../composables/useData'
import { useSyncBatch } from '../../composables/useSyncBatch'

// --- SYNC SCRIPT HELPER (no chunks, waits for full result) ---
async function invokeAsyncScript({ script, method, payload }) {
  const result = await requestJson('/api/scripts/run', {
    method: 'POST',
    body: { script, method, payload },
    timeoutMs: 60000
  })
  return typeof result === 'string' ? result : JSON.stringify(result)
}

// Użyj composable z cache
const {
  devices,
  accounts,
  loadDevices,
  loadAccounts,
  addDevice: addDeviceToCache,
  removeDevice: removeDeviceFromCache,
  removeAllErrorDevices: removeAllErrorDevicesFromCache,
  removeAllUnsyncDevices: removeAllUnsyncDevicesFromCache,
  syncDevice,
  getAccountName
} = useData()

// STANY OGÓLNE
const address = ref('')
const selectedDevice = ref(null)
const alertMessage = ref('')
const duplicateWarning = ref(false)
const fileInput = ref(null)
const searchQuery = ref('')
// Track syncing devices individually to allow concurrent single-device syncs
const syncingSet = ref(new Set()) // contains device ids currently syncing

// Batch sync progress tracking (from composable)
const {
  syncProgress, syncTotal, elapsed,
  progressPercent, formattedElapsed,
  runBatch, resetProgress,
} = useSyncBatch()

// Local refs for processImportText timer (separate from runBatch)
const startTime = ref(null)
let timerInterval = null

const showImportMessage = ref(false)
const importMessage = ref('')
const importMessageColor = ref('green')

const menuOpen = ref(false)

// MODAL EDYCJI URZĄDZENIA
const editModalOpen = ref(false)
const editDevice = ref(null)

// EDYCJA PARAMETRÓW devices_info.json
const editingParams = ref(false)
const editableDevicesInfo = ref({})

// PANEL SHOW VERSION (w modalu edycji)
const showVersionVisible = ref(false)
const showVersionResult = ref('')
const isLoadingVersion = ref(false)

const collapsibleSections = ref({
  vendor: false,
  model: false,
  software: false,
  type: false,
  hostname: false,
  address: false,
})

const toggleSection = (key) => {
  collapsibleSections.value[key] = !collapsibleSections.value[key]
}

const vendorOptions = computed(() => Object.keys(devicesInfo.vendor).sort())
const modelOptions = computed(() => Object.keys(devicesInfo.model).sort())
const softwareOptions = computed(() => Object.keys(devicesInfo.software).sort())
const typeOptions = computed(() => Object.keys(devicesInfo.type).sort())

function buildValueAndKeysMapsFromTargetAsKey(data) {
  const valueMap = {}
  const keysMap = {}
  Object.entries(data).forEach(([value, aliases]) => {
    const keys = aliases.split(',').map(k => k.trim()).filter(Boolean)
    if (keys.length === 0) return
    valueMap[value] = value
    keysMap[value] = keys.join(', ')
  })
  return { valueMap, keysMap }
}

const startEditing = () => {
  const vendor = buildValueAndKeysMapsFromTargetAsKey(devicesInfo.vendor)
  const model = buildValueAndKeysMapsFromTargetAsKey(devicesInfo.model)
  const software = buildValueAndKeysMapsFromTargetAsKey(devicesInfo.software)
  const type = buildValueAndKeysMapsFromTargetAsKey(devicesInfo.type)

  editableDevicesInfo.value = {
    vendorValueMap: vendor.valueMap,
    vendorKeysMap: vendor.keysMap,
    modelValueMap: model.valueMap,
    modelKeysMap: model.keysMap,
    softwareValueMap: software.valueMap,
    softwareKeysMap: software.keysMap,
    typeValueMap: type.valueMap,
    typeKeysMap: type.keysMap,
    hostnameRegexMap: { ...devicesInfo.hostname },
    addressRegexMap: { ...devicesInfo.address }
  }

  editingParams.value = true
}

const stopEditing = () => {
  editingParams.value = false
}

const saveParams = async () => {
  const newDevicesInfo = {
    vendor: {}, model: {}, software: {}, type: {}, hostname: {}, address: {}
  }

  for (const section of ['vendor', 'model', 'software', 'type']) {
    const valueMap = editableDevicesInfo.value[`${section}ValueMap`] || {}
    const keysMap = editableDevicesInfo.value[`${section}KeysMap`] || {}

    Object.entries(keysMap).forEach(([value, aliasesStr]) => {
      const finalValue = (valueMap[value] || '').trim()
      if (!finalValue) return
      const aliases = aliasesStr.split(',').map(k => k.trim()).filter(Boolean)
      if (aliases.length > 0) {
        newDevicesInfo[section][finalValue] = aliases.join(', ')
      }
    })
  }

  const hostnameMap = editableDevicesInfo.value.hostnameRegexMap || {}
  for (const [key, val] of Object.entries(hostnameMap)) {
    if (key.trim() && val.trim()) {
      newDevicesInfo.hostname[key.trim()] = val.trim()
    }
  }

  const addressMap = editableDevicesInfo.value.addressRegexMap || {}
  for (const [key, val] of Object.entries(addressMap)) {
    if (key.trim() && val.trim()) {
      newDevicesInfo.address[key.trim()] = val.trim()
    }
  }

  try {
    await invokeAsyncScript({
      script: 'settings-devices_controller',
      method: 'save_devices_info',
      payload: { newContent: JSON.stringify(newDevicesInfo) }
    })
    Object.assign(devicesInfo, newDevicesInfo)
    showAlert('Parametry zostały zapisane.')
    stopEditing()
  } catch (err) {
    console.error('Błąd przy zapisie devices_info.json:', err)
    showAlert('Nie udało się zapisać parametrów.')
  }
}

// --- FUNKCJE POBIERAJĄCE DANE ---
const accountName = (id) => {
  return getAccountName(id) || ''
}

const hasEmptyField = (device) => {
  return ['hostname', 'address', 'status', 'vendor', 'model', 'software', 'type', 'account']
    .some((field) => device[field] === '' || device[field] === '-')
}

const isValidIpOrHostname = (input) => {
  // Sprawdź czy to poprawny adres IP
  const ipRegex = /^(25[0-5]|2[0-4][0-9]|1?\d{1,2})(\.(25[0-5]|2[0-4][0-9]|1?\d{1,2})){3}$/
  if (ipRegex.test(input)) {
    return true
  }
  
  // Sprawdź czy to poprawna nazwa hosta (RFC 1123)
  const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/
  if (hostnameRegex.test(input) && input.length <= 253) {
    return true
  }
  
  return false
}

const showAlert = (message) => {
  alertMessage.value = message
  setTimeout(() => {
    alertMessage.value = ''
  }, 3000)
}

// --- DODAWANIE / USUWANIE URZĄDZEŃ ---
const submit = async () => {
  const trimmed = address.value.trim()
  if (!isValidIpOrHostname(trimmed)) {
    showAlert('Niepoprawny adres IP lub nazwa hosta.')
    return
  }
  // Sprawdzamy duplikaty zarówno w address jak i hostname
  const exists = devices.value.some((dev) => 
    dev.address === trimmed || dev.hostname === trimmed
  )
  if (exists) {
    duplicateWarning.value = true
    return
  }
  
  try {
    console.log(`[ADD-DEVICE] Adding device: ${trimmed}`)
    await addDeviceToCache(trimmed)
    console.log(`[ADD-DEVICE] Device added successfully, refreshing list...`)
    // Wymuś dodatkowe odświeżenie listy aby upewnić się że urządzenie jest widoczne
    await loadDevices(true)
    console.log(`[ADD-DEVICE] List refreshed successfully`)
    address.value = ''
  } catch (error) {
    console.error(`[ADD-DEVICE] Error adding device:`, error)
    showAlert('Błąd podczas dodawania urządzenia.')
  }
}

// Add device and immediately trigger sync (uses backend combined endpoint)
const addAndSync = async () => {
  const trimmed = address.value.trim()
  if (!isValidIpOrHostname(trimmed)) {
    showAlert('Niepoprawny adres IP lub nazwa hosta.')
    return
  }

  try {
    // Add using the existing composable so cache and behaviour stay consistent
    await addDeviceToCache(trimmed)

    // Refresh immediately after add (before sync) so the table shows the new row
    await loadDevices(true)

    // Find the added device record
    const device = devices.value.find(d => d.hostname === trimmed || d.address === trimmed)
    if (!device) {
      showAlert('Urządzenie dodane, ale nie znaleziono w liście.')
      address.value = ''
      return
    }

    // Trigger synchronization for the newly added device
    await syncDevice(device.id)

    // Refresh after sync to show updated status
    await loadDevices(true)

    showAlert('Urządzenie dodane i zsynchronizowane.')
    address.value = ''
  } catch (err) {
    console.error('[ADD-AND-SYNC] Exception:', err)
    showAlert('Błąd podczas dodawania i synchronizacji urządzenia.')
  }
}

const removeDevice = async (id) => {
  try {
    console.log(`[REMOVE-DEVICE] Removing device: ${id}`)
    await removeDeviceFromCache(id)
    console.log(`[REMOVE-DEVICE] Device removed successfully, refreshing list...`)
    // Wymuś dodatkowe odświeżenie listy aby upewnić się że urządzenie zostało usunięte
    await loadDevices(true)
    console.log(`[REMOVE-DEVICE] List refreshed successfully`)
  } catch (error) {
    console.error(`[REMOVE-DEVICE] Error removing device:`, error)
    showAlert('Błąd podczas usuwania urządzenia.')
  }
}

const removeAllErrorDevices = async () => {
  const errorCount = devices.value.filter(d => d.status === 'ERROR').length
  if (errorCount === 0) {
    showAlert('Brak urządzeń ze statusem ERROR.')
    menuOpen.value = false
    return
  }
  try {
    console.log(`[REMOVE-ALL-ERROR] Removing ${errorCount} devices with ERROR status`)
    await removeAllErrorDevicesFromCache()
    console.log(`[REMOVE-ALL-ERROR] Devices removed and list refreshed successfully`)
  } catch (error) {
    console.error(`[REMOVE-ALL-ERROR] Error removing devices:`, error)
    showAlert('Błąd podczas usuwania urządzeń ERROR.')
  }
  menuOpen.value = false
}

const removeAllUnsyncDevices = async () => {
  const unsyncCount = devices.value.filter(d => d.status === 'UNSYNC').length
  if (unsyncCount === 0) {
    showAlert('Brak urządzeń ze statusem UNSYNC.')
    menuOpen.value = false
    return
  }
  try {
    console.log(`[REMOVE-ALL-UNSYNC] Removing ${unsyncCount} devices with UNSYNC status`)
    await removeAllUnsyncDevicesFromCache()
    console.log(`[REMOVE-ALL-UNSYNC] Devices removed and list refreshed successfully`)
  } catch (error) {
    console.error(`[REMOVE-ALL-UNSYNC] Error removing devices:`, error)
    showAlert('Błąd podczas usuwania urządzeń UNSYNC.')
  }
  menuOpen.value = false
}

// --- PODGLĄD I EDIcja URZĄDZENIA ---
const showInfo = (device) => {
  selectedDevice.value = device
}

const originalDevice = ref(null)

const openEdit = (device) => {
  // Ukrywamy poprzedni panel Show version i czyścimy wynik
  showVersionVisible.value = false
  showVersionResult.value = ''
  isLoadingVersion.value = false

  wasShowVersionClicked.value = false
  showVersionValues.value = null

  originalDevice.value = { ...device }
  editDevice.value = { ...device }
  editModalOpen.value = true
}

const closeEdit = () => {
  editModalOpen.value = false
  editDevice.value = null

  // Resetujemy także panel Show version
  showVersionVisible.value = false
  showVersionResult.value = ''
  isLoadingVersion.value = false
}

const wasShowVersionClicked = ref(false)
const showVersionValues = ref(null)  // Add this ref to store initial values after show version

const isFieldChanged = (field) => {
  if (!showVersionValues.value || !editDevice.value || !wasShowVersionClicked.value) return false
  
  const newValue = editDevice.value[field]
  const initialValue = showVersionValues.value[field]
  
  console.log(`[${field}] Initial: "${initialValue}" -> Current: "${newValue}"`, {
    isEmptyNew: !newValue,
    isEqual: newValue === initialValue,
    newValue,
    initialValue
  })
  
  // If empty after show version, show red
  if (!newValue) {
    return 'empty'
  }
  
  // If matches initial show version value, show green
  if (String(newValue).toLowerCase() === String(initialValue).toLowerCase()) {
    return 'confirmed'
  }
  
  // If different than initial show version value, show yellow
  return 'changed'
}

const saveEdit = async () => {
  try {
    await invokeAsyncScript({
      script: 'settings-devices_controller',
      method: 'update_device',
      payload: { device: editDevice.value }
    })
    // Zaktualizuj dane urządzenia w tablicy bez pełnego przeładowania
    const idx = devices.value.findIndex(d => d.id === editDevice.value.id)
    if (idx !== -1) {
      devices.value[idx] = { ...editDevice.value }
      devices.value = [...devices.value]
    }
    showAlert('Zapisano zmiany w urządzeniu.')
  } catch (err) {
    console.error('Błąd podczas zapisu zmian:', err)
    showAlert('Nie udało się zapisać zmian.')
  }
  closeEdit()
}

// --- WYWOŁANIE KOMENDY SHOW VERSION ---
const runShowVersion = async () => {
  // Jeśli panel jest już widoczny – ukrywamy i czyścimy wynik
  if (showVersionVisible.value) {
    showVersionVisible.value = false
    showVersionResult.value = ''
    return
  }

  const device = editDevice.value
  if (!device || !device.id) {
    console.warn('[SHOW VERSION] Brak wybranego urządzenia.')
    return
  }

  showVersionVisible.value = true
  isLoadingVersion.value = true
  showVersionResult.value = ''

  try {
    console.log('[SHOW VERSION] Starting show version command...')
    console.log('[SHOW VERSION] Device:', device)
    
    const resultRaw = await invokeAsyncScript({
      script: 'settings-devices_controller',
      method: 'execute_command_on_device',
      payload: {
        device,
        command: 'show version'
      }
    })

    console.log('[SHOW VERSION] Raw result from backend:', resultRaw)
    console.log('[SHOW VERSION] Raw result type:', typeof resultRaw)
    
    const parsed = typeof resultRaw === 'string' ? JSON.parse(resultRaw) : resultRaw
    
    console.log('[SHOW VERSION] Parsed result:', parsed)
    console.log('[SHOW VERSION] Parsed result keys:', Object.keys(parsed))
    console.log('[SHOW VERSION] Output content:', parsed.output)
    console.log('[SHOW VERSION] Output type:', typeof parsed.output)
    console.log('[SHOW VERSION] Output length:', parsed.output?.length)
    
    if (parsed.output) {
      showVersionResult.value = parsed.output
      console.log('Show version output:', parsed.output)

      // Store initial values before any changes
      showVersionValues.value = { ...editDevice.value }
      
      const output = parsed.output.toLowerCase()
      const suggestedFields = []

      // Detect IOS vs IOS XR first from output
      const isIosXr = output.includes('ios xr')
      
      // Process model detection with exact matches
      for (const [value, aliases] of Object.entries(devicesInfo.model)) {
        const aliasArray = aliases.split(',').map(a => a.trim().toLowerCase())
        const matchingPattern = aliasArray.find(pattern => output.includes(pattern))
        if (matchingPattern) {
          console.log('Found matching model:', value, 'with pattern:', matchingPattern)
          editDevice.value.model = value // This will be ASR9K not ASRR9K
          suggestedFields.push('model')
          break
        }
      }

      // Process software with IOS vs IOS XR distinction
      if (isIosXr) {
        editDevice.value.software = 'IOS XR'
        suggestedFields.push('software')
      }

      // Then process other fields
      for (const [section, patterns] of Object.entries(devicesInfo)) {
        if (section === 'hostname' || section === 'model' || section === 'software') continue
        
        for (const [value, aliases] of Object.entries(patterns)) {
          const aliasArray = aliases.split(',').map(a => a.trim().toLowerCase())
          if (aliasArray.some(pattern => output.includes(pattern))) {
            editDevice.value[section] = value
            suggestedFields.push(section)
            break
          }
        }
      }

      // Enable highlighting only after processing all fields
      wasShowVersionClicked.value = true

      if (suggestedFields.length > 0) {
        const fieldsText = suggestedFields.map(f => f.charAt(0).toUpperCase() + f.slice(1)).join(', ')
        showAlert(`Automatycznie ustawiono: ${fieldsText}`)
      }
    } else if (parsed.error) {
      showVersionResult.value = '(Błąd: ' + parsed.error + ')'
      console.error('[SHOW VERSION] Error from backend:', parsed.error)
    } else {
      showVersionResult.value = '(Brak danych)'
      console.warn('[SHOW VERSION] No output or error in response')
    }
  } catch (err) {
    console.error('[SHOW VERSION] Wyjątek:', err)
    console.error('[SHOW VERSION] Exception details:', err.toString())
    console.error('[SHOW VERSION] Exception stack:', err.stack)
    showVersionResult.value = '(Błąd)'
  } finally {
    isLoadingVersion.value = false
  }
}

// --- SYNCHRONIZACJA URZĄDZEŃ ---
// Core sync logic (no mutex) — used by batch operations
const syncDeviceCore = async (id) => {
  const deviceIndex = devices.value.findIndex(d => d.id === id)
  if (deviceIndex !== -1) {
    devices.value[deviceIndex] = { ...devices.value[deviceIndex], status: 'SYNCING' }
    devices.value = [...devices.value]
  }
  try {
    await syncDevice(id)
  } catch (error) {
    console.error(`[SYNC] Error during device ${id} sync:`, error)
    const idx = devices.value.findIndex(d => d.id === id)
    if (idx !== -1) {
      devices.value[idx] = { ...devices.value[idx], status: 'ERROR' }
      devices.value = [...devices.value]
    }
  }
}

const syncDeviceSingle = async (id) => {
  // If this specific device is already syncing, skip
  if (syncingSet.value.has(id)) {
    console.log(`[SYNC] ⏳ Device ${id} is already syncing`)
    return
  }

  // Mark this device as syncing and run core sync without blocking others
  try {
    syncingSet.value.add(id)
    // ensure Vue notices the Set change
    syncingSet.value = new Set(syncingSet.value)
    await syncDeviceCore(id)
  } finally {
    // remove from set
    const s = new Set(syncingSet.value)
    s.delete(id)
    syncingSet.value = s
  }
}

const onSyncAll = async () => {
  const allDevices = devices.value
  const result = await runBatch(
    allDevices,
    (id) => syncDeviceCore(id),
    (msg) => showAlert(msg),
    'Brak urządzeń do synchronizacji.',
    1
  )
  if (result) {
    showImportMessage.value = true
    importMessage.value = `All devices sync complete: ${result.total} devices (time: ${result.elapsed})`
    importMessageColor.value = 'green'
    setTimeout(() => { resetProgress(); showImportMessage.value = false; importMessage.value = '' }, 3000)
  }
  menuOpen.value = false
}

const fixHostnameAddresses = async () => {
  try {
    console.log(`[FIX-HOSTNAMES] Starting hostname address fix...`)
    showAlert('Naprawiam adresy hostname...')
    await invokeAsyncScript({
      script: 'settings-devices_controller',
      method: 'fix_hostname_addresses',
      payload: {}
    })
    console.log(`[FIX-HOSTNAMES] Hostname addresses fixed, refreshing list...`)
    await loadDevices(true)
    console.log(`[FIX-HOSTNAMES] List refreshed successfully`)
    showAlert('Naprawiono adresy hostname.')
  } catch (error) {
    console.error('[FIX-HOSTNAMES] Błąd podczas naprawy adresów:', error)
    showAlert('Błąd podczas naprawy adresów.')
  }
  menuOpen.value = false
}

const onSyncUnsync = async () => {
  const unsyncedDevices = devices.value.filter(d => d.status === 'UNSYNC')
  const result = await runBatch(
    unsyncedDevices,
    (id) => syncDeviceCore(id),
    (msg) => showAlert(msg),
    'Brak urządzeń ze statusem UNSYNC.',
    1
  )
  if (result) {
    showImportMessage.value = true
    importMessage.value = `UNSYNC sync complete: ${result.total} devices (time: ${result.elapsed})`
    importMessageColor.value = 'green'
    setTimeout(() => { resetProgress(); showImportMessage.value = false; importMessage.value = '' }, 3000)
  }
  menuOpen.value = false
}

const onSyncError = async () => {
  const errorDevices = devices.value.filter(d => d.status === 'ERROR')
  const result = await runBatch(
    errorDevices,
    (id) => syncDeviceCore(id),
    (msg) => showAlert(msg),
    'Brak urządzeń ze statusem ERROR.',
    1
  )
  if (result) {
    showImportMessage.value = true
    importMessage.value = `ERROR sync complete: ${result.total} devices (time: ${result.elapsed})`
    importMessageColor.value = 'green'
    setTimeout(() => { resetProgress(); showImportMessage.value = false; importMessage.value = '' }, 3000)
  }
  menuOpen.value = false
}

const onSyncIncomplete = async () => {
  const incompleteDevices = devices.value.filter(d =>
    ['hostname', 'address', 'status', 'vendor', 'model', 'software', 'type', 'account']
      .some(field => d[field] === '')
  )
  const result = await runBatch(
    incompleteDevices,
    (id) => syncDeviceCore(id),
    (msg) => showAlert(msg),
    'Brak urządzeń z niekompletnymi danymi.',
    1
  )
  if (result) {
    showImportMessage.value = true
    importMessage.value = `Incomplete sync complete: ${result.total} devices (time: ${result.elapsed})`
    importMessageColor.value = 'green'
    setTimeout(() => { resetProgress(); showImportMessage.value = false; importMessage.value = '' }, 3000)
  }
  menuOpen.value = false
}

const toggleMenu = () => {
  menuOpen.value = !menuOpen.value
}

// --- IMPORT URZĄDZEŃ Z PLIKU ---
const triggerImport = async () => {
  if (fileInput.value) fileInput.value.click()
}

const handleImport = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  const text = await file.text()
  event.target.value = ''
  await processImportText(text)
}

const processImportText = async (text) => {

  // Rozpocznij pokazywanie paska postępu
  syncProgress.value = 0
  syncTotal.value = 0
  startTime.value = Date.now()
  elapsed.value = 0
  timerInterval = setInterval(() => {
    elapsed.value = Date.now() - startTime.value
  }, 1000)

  try {
    const lines = text.split('\n').map((line) => line.trim()).filter(Boolean)
    syncTotal.value = lines.length // Całkowita liczba linii do przetworzenia
    
    const validItems = []
    const existingAddresses = new Set(devices.value.map(dev => dev.address))
    const existingHostnames = new Set(devices.value.map(dev => dev.hostname))
    let skippedCount = 0

    // Zbieramy wszystkie poprawne, nieunikalne pozycje do importu.
    // Jeśli linia zawiera IP — dodajemy IP. Jeśli linia ma tylko jeden token i nie jest IP,
    // traktujemy go jako hostname i dodajemy jako pojedynczy wpis.
    for (const [index, line] of lines.entries()) {
      syncProgress.value = index + 1 // Aktualizuj pasek postępu

      const match = line.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/)
      if (match) {
        const ip = match[0]
        if (!isValidIpOrHostname(ip)) continue
        if (existingAddresses.has(ip)) {
          skippedCount++
          continue
        }
        validItems.push(ip)
        existingAddresses.add(ip)
        continue
      }

      // Jeśli nie znaleziono IP, sprawdź czy linia zawiera dokładnie jeden token — wtedy to hostname
      const tokens = line.split(/\s+/).filter(Boolean)
      if (tokens.length === 1) {
        const token = tokens[0]
        // pomijamy jeżeli już istnieje hostname w bazie
        if (existingHostnames.has(token)) {
          skippedCount++
          continue
        }
        // zaakceptuj token jako hostname
        validItems.push(token)
        existingHostnames.add(token)
      }
      // jeśli linia ma więcej niż 1 token i nie zawiera IP — ignorujemy (może być format "ip hostname" już obsługiwany przez IP branch)
    }

    if (validItems.length === 0) {
      clearInterval(timerInterval)
      syncProgress.value = 0
      syncTotal.value = 0
      
      const message = skippedCount > 0 
        ? `Wszystkie znalezione pozycje (${skippedCount}) już istnieją w bazie.`
        : 'Nie znaleziono żadnych poprawnych wpisów do zaimportowania.'
      showAlert(message)
      return
    }

    // Aktualizuj tekst postępu na dodawanie urządzeń
    importMessage.value = 'Dodawanie urządzeń...'
    showImportMessage.value = true
    importMessageColor.value = '#1976d2' // niebieski

    // Importujemy wszystkie urządzenia w jednym wywołaniu
    console.log(`[BULK-IMPORT] Adding ${validItems.length} devices to backend...`)
    await invokeAsyncScript({
      script: 'settings-devices_controller',
      method: 'add_devices_bulk',
      payload: { addresses: validItems }
    })

    console.log(`[BULK-IMPORT] Devices added successfully, refreshing list...`)
    await loadDevices(true)
    console.log(`[BULK-IMPORT] List refreshed successfully`)

    // Zakończ pokazywanie paska postępu
    clearInterval(timerInterval)
    elapsed.value = Date.now() - startTime.value
    syncProgress.value = 0
    syncTotal.value = 0

    const message = skippedCount > 0
      ? `Zaimportowano ${validIps.length} urządzeń (pominięto ${skippedCount} duplikatów) w czasie ${formattedElapsed.value}.`
      : `Zaimportowano ${validIps.length} urządzeń w czasie ${formattedElapsed.value}.`
    
    showImportMessage.value = true
    importMessage.value = message
    importMessageColor.value = 'green'
    setTimeout(() => {
      showImportMessage.value = false
      importMessage.value = ''
    }, 3000)
  } catch (err) {
    console.error('Błąd podczas importu urządzeń:', err)
    showAlert('Wystąpił błąd podczas importowania urządzeń.')
    clearInterval(timerInterval)
    syncProgress.value = 0
    syncTotal.value = 0
  }
}

const contains = (text, substr) => {
  return text.toLowerCase().includes(substr.toLowerCase())
}

function matchesQuery(device, query) {
  if (!query.trim()) return true
  const normalized = query
    .replace(/\|\|/gi, 'OR')
    .replace(/&&/gi, 'AND')
    .replace(/!/g, 'NOT ')
    .toUpperCase()

  const orTerms = normalized.split(/\bOR\b/).map((term) => term.trim()).filter((t) => t)

  return orTerms.some((term) => {
    const andParts = term.split(/\bAND\b/).map((p) => p.trim()).filter((p) => p)
    return andParts.every((part) => {
      if (part.startsWith('NOT ')) {
        const word = part.slice(4).trim()
        return !contains(JSON.stringify(device), word)
      } else {
        return contains(JSON.stringify(device), part)
      }
    })
  })
}

const filteredDevices = computed(() => {
  return devices.value.filter((device) => matchesQuery(device, searchQuery.value))
})

// progressPercent & formattedElapsed are provided by useSyncBatch composable

onMounted(async () => {
  console.log('[Devices.vue] Force loading fresh data...')
  await loadDevices(true)  // Force reload devices
  await loadAccounts(true) // Force reload accounts
  console.log('[Devices.vue] Fresh data loaded')
})

onActivated(async () => {
  console.log('[Devices.vue] Component activated, refreshing data...')
  await loadDevices(true)  // Force reload devices on activation
  await loadAccounts(true) // Force reload accounts on activation
  console.log('[Devices.vue] Data refreshed on activation')
})

const addSectionRow = (section) => {
  const timestamp = Date.now()
  const newId = `new_${timestamp}`

  switch (section) {
    case 'vendor':
      editableDevicesInfo.value.vendorValueMap[newId] = ''
      editableDevicesInfo.value.vendorKeysMap[newId] = ''
      break
    case 'model':
      editableDevicesInfo.value.modelValueMap[newId] = ''
      editableDevicesInfo.value.modelKeysMap[newId] = ''
      break
    case 'software':
      editableDevicesInfo.value.softwareValueMap[newId] = ''
      editableDevicesInfo.value.softwareKeysMap[newId] = ''
      break
    case 'type':
      editableDevicesInfo.value.typeValueMap[newId] = ''
      editableDevicesInfo.value.typeKeysMap[newId] = ''
      break
    case 'hostname':
      editableDevicesInfo.value.hostnameRegexMap[newId] = ''
      break
    case 'address':
      editableDevicesInfo.value.addressRegexMap[newId] = ''
      break
  }
}

const removeSectionRow = (section, key) => {
  switch (section) {
    case 'vendor':
      delete editableDevicesInfo.value.vendorValueMap[key]
      delete editableDevicesInfo.value.vendorKeysMap[key]
      break
    case 'model':
      delete editableDevicesInfo.value.modelValueMap[key]
      delete editableDevicesInfo.value.modelKeysMap[key]
      break
    case 'software':
      delete editableDevicesInfo.value.softwareValueMap[key]
      delete editableDevicesInfo.value.softwareKeysMap[key]
      break
    case 'type':
      delete editableDevicesInfo.value.typeValueMap[key]
      delete editableDevicesInfo.value.typeKeysMap[key]
      break
    case 'hostname':
      delete editableDevicesInfo.value.hostnameRegexMap[key]
      break
    case 'address':
      delete editableDevicesInfo.value.addressRegexMap[key]
      break
  }
}
</script>

<style>
.devices-container {
  display: flex;
  width: 100%;
  height: 100%;
  gap: 2rem;
}

.left-panel {
  width: 30%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.spacer {
  flex: 1;
}

.edit-params-button {
  margin-top: auto;
  background-color: #ffa000; /* pomarańczowy, aby wyróżnić */
}

.back-button {
  background-color: #e53935; /* czerwony, żeby odróżnić */
  margin-bottom: 10px;
}

.right-panel {
  width: 70%;
  position: relative;
  overflow-x: auto;
}

.fixed-header {
  position: sticky;
  top: 0;
  background: #161b22;
  display: flex;
  align-items: center;
  padding: 6px 4px;
  gap: 8px;
  z-index: 10;
  border-bottom: 1px solid #30363d;
}

.search-input {
  flex-grow: 1;
  padding: 5px 9px;
  font-size: 12px;
  border-radius: 5px;
  border: 1px solid #30363d;
  background: #0d1117;
  color: #e6edf3;
}

.burger-menu {
  position: relative;
}

.burger-button {
  padding: 8px;
  background-color: #1976d2;
  color: white;
  font-weight: bold;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.burger-button:hover {
  background-color: #1565c0;
}

.dropdown {
  position: absolute;
  top: 110%;
  right: 0;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  display: flex;
  flex-direction: column;
  z-index: 20;
  min-width: 160px;
  overflow: hidden;
}

.dropdown button {
  padding: 8px 14px;
  background: transparent;
  color: #e6edf3;
  border: none;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
}

.dropdown button:hover {
  background: #21262d;
}

.table-container {
  margin-top: 1rem;
}

input {
  padding: 10px;
  font-size: 1rem;
  border-radius: 5px;
  border: 1px solid #30363d;
}

button {
  padding: 7px 14px;
  background: #21262d;
  color: #e6edf3;
  border: 1px solid #30363d;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
button:hover { background: #2d333b; border-color: #484f58; }

table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }

th, td {
  border-bottom: 1px solid #21262d;
  padding: 10px 14px; text-align: center;
  color: #e6edf3; font-size: 13px;
}

th {
  background: #161b22; color: #8b949e;
  font-weight: 600; font-size: 11.5px;
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid #30363d;
}

.incomplete { background: rgba(218,54,51,0.1) !important; color: #e6edf3; }

.device-modal {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.65);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; backdrop-filter: blur(2px);
}

.modal-content {
  position: relative;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 10px;
  padding: 1.5rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  color: #e6edf3;
  box-shadow: 0 16px 48px rgba(0,0,0,0.5);
}

.close-button {
  position: absolute; top: 12px; right: 12px;
  background: #da3633; border: none; color: #fff;
  width: 26px; height: 26px; font-size: 14px;
  line-height: 26px; text-align: center;
  cursor: pointer; padding: 0; border-radius: 50%;
}
.close-button:hover { background: #f85149; }

.device-details-list { list-style: none; padding: 0; margin: 0.75rem 0; }

.device-details-list li {
  display: flex; gap: 0.5rem;
  padding: 7px 0; border-bottom: 1px solid #21262d; font-size: 13px;
}
.device-details-list li:last-child { border-bottom: none; }

.detail-label {
  user-select: none; font-weight: 600;
  color: #8b949e; min-width: 130px; flex-shrink: 0;
}
.detail-value { user-select: text; color: #e6edf3; }

.status {
  font-weight: 600; font-size: 11.5px;
  padding: 3px 8px; border-radius: 12px;
  letter-spacing: 0.04em; display: inline-block;
}
.status-unsync  { background: rgba(139,148,158,0.15); color: #8b949e; border: 1px solid #30363d; }
.status-syncing { background: rgba(56,139,253,0.15); color: #388bfd; border: 1px solid rgba(56,139,253,0.3); }
.status-synced  { background: rgba(63,185,80,0.15); color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
.status-error   { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }

.custom-alert {
  position: fixed; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  background: #161b22; border: 1px solid #30363d;
  color: #e6edf3; font-weight: 600;
  padding: 1rem 2rem; border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5); z-index: 9999;
}

.warning-text { color: #f85149; font-weight: 600; margin-bottom: -4px; }

.progress-overlay {
  position: fixed; top: 20%; left: 50%; transform: translate(-50%, -20%);
  width: 55%; background: #161b22; border: 1px solid #30363d;
  padding: 20px 24px; border-radius: 10px; z-index: 9999;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.6); pointer-events: none;
}
.progress-bar, .progress-info { pointer-events: auto; }

.progress-bar {
  position: relative; background: #21262d;
  width: 100%; height: 28px; border-radius: 6px;
  overflow: hidden; border: 1px solid #30363d; margin-bottom: 0;
}
.progress-fill { background: linear-gradient(90deg, #1f6feb, #388bfd); height: 100%; transition: width 0.3s ease; }
.progress-text {
  position: absolute; top: 0; left: 50%; transform: translateX(-50%);
  color: #e6edf3; font-weight: 600; font-size: 12px; line-height: 28px;
}
.progress-info { color: #8b949e; font-size: 12.5px; display: flex; gap: 1.5rem; }

.import-message {
  position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
  background: #238636; border: 1px solid #3fb950; color: #fff;
  padding: 1rem 2.5rem; border-radius: 8px; font-size: 1rem; font-weight: 600;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  animation: fadeOut 3s ease-out 1 forwards; z-index: 99999;
}

@keyframes fadeOut { 0%, 70% { opacity: 1; } 100% { opacity: 0; } }

.no-devices-text { padding: 1.5rem; color: #484f58; text-align: center; font-size: 13px; }

.form-row { display: flex; align-items: center; margin-bottom: 10px; gap: 0.75rem; }
.form-row label { width: 130px; flex-shrink: 0; font-weight: 600; font-size: 13px; color: #8b949e; }
.form-row input, .form-row select {
  flex: 1; padding: 7px 10px;
  background: #0d1117; border: 1px solid #30363d;
  border-radius: 6px; color: #e6edf3; font-size: 13px;
}

.modal-actions {
  display: flex; justify-content: flex-end;
  gap: 8px; margin-top: 1rem;
  padding-top: 0.75rem; border-top: 1px solid #21262d;
}
.modal-actions button { padding: 6px 14px; font-size: 13px; border-radius: 6px; }

.section-block { margin-bottom: 10px; border: 1px solid #30363d; border-radius: 6px; overflow: hidden; }

.collapsible-header {
  display: flex; align-items: center;
  padding: 8px 12px; background: #161b22;
  color: #8b949e; font-weight: 600; font-size: 12px;
  text-transform: uppercase; letter-spacing: 0.05em;
  cursor: pointer; user-select: none; transition: background 0.15s;
}
.collapsible-header:hover { background: #21262d; color: #e6edf3; }
.collapsible-header span.section-title { margin-left: 0.5rem; }

.section-content { padding: 10px 12px; background: #0d1117; border-top: 1px solid #30363d; }

.params-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px; }

.save-button   { background: #238636 !important; border-color: #238636 !important; color: #fff !important; }
.save-button:hover { background: #3fb950 !important; border-color: #3fb950 !important; }
.cancel-button { background: #da3633 !important; border-color: #da3633 !important; color: #fff !important; }
.cancel-button:hover { background: #f85149 !important; border-color: #f85149 !important; }

.horizontal-layout { display: flex; flex-direction: row; gap: 1rem; max-width: 1000px; width: 100%; }

.show-version-container {
  width: 40%; background: #161b22; border: 1px solid #30363d;
  border-radius: 6px; padding: 1rem; overflow-y: auto; max-height: 80vh;
}
.show-version-container pre {
  background: #0d1117; border: 1px solid #30363d;
  padding: 0.75rem; border-radius: 5px; white-space: pre-wrap;
  font-family: 'Cascadia Code','Consolas',monospace; font-size: 12px; color: #c9d1d9;
  max-height: 300px; overflow-y: auto;
}
.show-version-output {
  flex: 1; background: #0d1117; border: 1px solid #30363d;
  border-radius: 5px; padding: 1rem; max-height: 400px;
  overflow-y: auto; white-space: pre-wrap;
  font-family: 'Cascadia Code','Consolas',monospace; font-size: 12px; color: #c9d1d9;
}
.edit-form { flex: 1; position: relative; }

.modal-content.small { max-width: 460px; width: 60%; padding: 1.25rem; display: block; }
.modal-content.large { max-width: 820px; width: 95%; padding: 1.5rem; display: flex; gap: 1rem; }

.field-empty     { border-color: #f85149 !important; background: rgba(248,81,73,0.06) !important; }
.field-changed   { border-color: #d29922 !important; background: rgba(210,153,34,0.06) !important; }
.field-confirmed { border-color: #3fb950 !important; background: rgba(63,185,80,0.06) !important; }
</style>


