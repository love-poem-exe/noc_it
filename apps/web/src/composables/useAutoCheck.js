/**
 * useAutoCheck — extracted from CMTS_TMPFS.vue
 *
 * Manages the auto-check timer system for periodic CMTS status verification.
 *
 * Usage:
 *   const {
 *     isAutoCheckEnabled, autoCheckInterval, autoCheckCountdown,
 *     isAutoCheckRunning, toggleAutoCheck
 *   } = useAutoCheck(tableData)
 */
import { ref, onUnmounted } from 'vue'
import { invokeAsyncScript } from '../services/DataService'

export function useAutoCheck(tableData) {
  const isAutoCheckEnabled = ref(false)
  const autoCheckInterval = ref(30)
  const autoCheckCountdown = ref(30)
  const isAutoCheckRunning = ref(false)

  let autoCheckTimer = null
  let countdownTimer = null

  function toggleAutoCheck() {
    isAutoCheckEnabled.value = !isAutoCheckEnabled.value
    if (isAutoCheckEnabled.value) {
      startAutoCheck()
    } else {
      stopAutoCheck()
    }
  }

  function startAutoCheck() {
    autoCheckCountdown.value = autoCheckInterval.value

    if (countdownTimer) clearInterval(countdownTimer)
    countdownTimer = setInterval(() => {
      if (!isAutoCheckEnabled.value) return
      if (autoCheckCountdown.value <= 1) {
        autoCheckCountdown.value = autoCheckInterval.value
        return
      }
      autoCheckCountdown.value -= 1
    }, 1000)

    // Immediate first check
    performStatusCheck()

    // Recurring checks
    autoCheckTimer = setInterval(() => {
      performStatusCheck()
    }, autoCheckInterval.value * 1000)
  }

  function stopAutoCheck() {
    if (autoCheckTimer) {
      clearInterval(autoCheckTimer)
      autoCheckTimer = null
    }
    if (countdownTimer) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
    autoCheckCountdown.value = autoCheckInterval.value
  }

  async function performStatusCheck() {
    if (isAutoCheckRunning.value) return

    isAutoCheckRunning.value = true
    try {
      await invokeAsyncScript({
        script: 'modules-cmts_tmpfs_controller',
        method: 'auto_check_statuses',
        payload: { tableData: tableData.value },
      })
    } catch {
      // Silently continue — auto-check is best-effort
    } finally {
      isAutoCheckRunning.value = false
    }
  }

  onUnmounted(() => {
    stopAutoCheck()
  })

  return {
    isAutoCheckEnabled,
    autoCheckInterval,
    autoCheckCountdown,
    isAutoCheckRunning,
    toggleAutoCheck,
    stopAutoCheck,
  }
}
