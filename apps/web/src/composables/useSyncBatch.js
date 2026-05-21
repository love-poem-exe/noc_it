/**
 * useSyncBatch — extracts the duplicated onSyncAll / onSyncUnsync / onSyncError / onSyncIncomplete
 * pattern from Devices.vue into a single, parameterized composable.
 *
 * Usage:
 *   const { syncProgress, syncTotal, elapsed, progressPercent, formattedElapsed, runBatch, resetProgress } = useSyncBatch()
 *   const result = await runBatch(filteredDevices, syncDeviceSingle, showAlert, 'Brak urządzeń')
 */
import { ref, computed } from 'vue'

export function useSyncBatch() {
  const syncProgress = ref(0)
  const syncTotal = ref(0)
  const startTime = ref(null)
  const elapsed = ref(0) // milliseconds, matching original Devices.vue behavior
  let elapsedTimer = null

  const progressPercent = computed(() =>
    syncTotal.value > 0 ? Math.round((syncProgress.value / syncTotal.value) * 100) : 0
  )

  const formattedElapsed = computed(() => {
    const totalSec = Math.floor(elapsed.value / 1000)
    const minutes = String(Math.floor(totalSec / 60)).padStart(2, '0')
    const seconds = String(totalSec % 60).padStart(2, '0')
    return `${minutes}:${seconds}`
  })

  // Serializes batch runs so that multiple callers queue — only one batch executes at a time.
  // `lastRun` is a Promise that resolves when the previous queued run finishes.
  let lastRun = Promise.resolve()

  /** Reset progress state (e.g. after showing a completion message) */
  function resetProgress() {
    syncProgress.value = 0
    syncTotal.value = 0
  }

  /**
   * Run a batch sync operation on a filtered list of devices.
   *
   * @param {Array} devices — the devices to process (already filtered by caller)
   * @param {(deviceId: string) => Promise<void>} syncFn — function to call for each device
   * @param {(msg: string) => void} [onEmpty] — called if the list is empty
   * @param {string} [emptyMessage] — message for the empty case
   * @param {number} [concurrency] — max parallel syncs at once (default 20)
   * @returns {{ completed: number, total: number, elapsed: string } | null} — null if empty
   */
  async function runBatch(devices, syncFn, onEmpty, emptyMessage = 'No devices to sync', concurrency) {
    if (!devices || devices.length === 0) {
      if (onEmpty) onEmpty(emptyMessage)
      return null
    }

    // If concurrency wasn't specified, try to read from saved general settings in localStorage
    if (typeof concurrency === 'undefined' || concurrency === null) {
      try {
        const raw = localStorage.getItem('noc-it:general-settings')
        if (raw) {
          const parsed = JSON.parse(raw)
          if (parsed && parsed.devicesConcurrency) {
            concurrency = Number(parsed.devicesConcurrency) || 20
          }
        }
      } catch (e) {
        concurrency = 20
      }
    }

    concurrency = concurrency || 20

    // The actual execution logic for a single queued run
    const exec = async () => {
      syncProgress.value = 0
      syncTotal.value = devices.length
      elapsed.value = 0
      startTime.value = Date.now()

      elapsedTimer = setInterval(() => {
        elapsed.value = Date.now() - startTime.value
      }, 1000)

      try {
        for (let i = 0; i < devices.length; i += concurrency) {
          const chunk = devices.slice(i, i + concurrency)
          await Promise.all(
            chunk.map(device =>
              syncFn(device.id).then(() => { syncProgress.value++ })
            )
          )
        }
      } finally {
        clearInterval(elapsedTimer)
        elapsedTimer = null
        elapsed.value = Date.now() - startTime.value
      }

      return {
        completed: syncProgress.value,
        total: syncTotal.value,
        elapsed: formattedElapsed.value,
      }
    }

    // Enqueue the exec to run after the previous run completes; update lastRun to the queued promise
    const queued = lastRun.then(() => exec())
    // Ensure lastRun continues the chain even if queued rejects
    lastRun = queued.catch(() => null)
    return queued
  }

  return {
    syncProgress,
    syncTotal,
    elapsed,
    progressPercent,
    formattedElapsed,
    runBatch,
    resetProgress,
  }
}
