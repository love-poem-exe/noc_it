import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useSyncBatch } from '../../src/composables/useSyncBatch'

describe('useSyncBatch', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns expected shape', () => {
    const { syncProgress, syncTotal, elapsed, progressPercent, formattedElapsed, runBatch, resetProgress } = useSyncBatch()
    expect(syncProgress.value).toBe(0)
    expect(syncTotal.value).toBe(0)
    expect(elapsed.value).toBe(0)
    expect(progressPercent.value).toBe(0)
    expect(formattedElapsed.value).toBe('00:00')
    expect(typeof runBatch).toBe('function')
    expect(typeof resetProgress).toBe('function')
  })

  it('calls onEmpty when devices list is empty', async () => {
    const { runBatch } = useSyncBatch()
    const onEmpty = vi.fn()
    const result = await runBatch([], vi.fn(), onEmpty, 'Nothing to sync')
    expect(onEmpty).toHaveBeenCalledWith('Nothing to sync')
    expect(result).toBeNull()
  })

  it('syncs each device and tracks progress', async () => {
    const { syncProgress, syncTotal, runBatch } = useSyncBatch()
    const syncFn = vi.fn().mockResolvedValue(undefined)
    const devices = [{ id: '1' }, { id: '2' }, { id: '3' }]

    const result = await runBatch(devices, syncFn)

    expect(syncFn).toHaveBeenCalledTimes(3)
    expect(syncFn).toHaveBeenCalledWith('1')
    expect(syncFn).toHaveBeenCalledWith('2')
    expect(syncFn).toHaveBeenCalledWith('3')
    expect(syncProgress.value).toBe(3)
    expect(syncTotal.value).toBe(3)
    expect(result).toBeTruthy()
    expect(result.completed).toBe(3)
    expect(result.total).toBe(3)
  })

  it('resets progress after resetProgress call', async () => {
    const { syncProgress, syncTotal, resetProgress, runBatch } = useSyncBatch()
    const syncFn = vi.fn().mockResolvedValue(undefined)
    await runBatch([{ id: '1' }], syncFn)
    expect(syncProgress.value).toBe(1)
    resetProgress()
    expect(syncProgress.value).toBe(0)
    expect(syncTotal.value).toBe(0)
  })

  it('progressPercent is calculated correctly', () => {
    const { progressPercent, syncProgress, syncTotal } = useSyncBatch()
    syncTotal.value = 4
    syncProgress.value = 1
    expect(progressPercent.value).toBe(25)
    syncProgress.value = 2
    expect(progressPercent.value).toBe(50)
  })

  it('formattedElapsed formats MM:SS correctly', () => {
    const { formattedElapsed, elapsed } = useSyncBatch()
    elapsed.value = 75000  // 75 seconds in ms
    expect(formattedElapsed.value).toBe('01:15')
    elapsed.value = 5000   // 5 seconds in ms
    expect(formattedElapsed.value).toBe('00:05')
  })
})
