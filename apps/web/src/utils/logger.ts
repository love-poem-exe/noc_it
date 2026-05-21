/**
 * Centralized logger utility with environment-aware filtering.
 *
 * In production (`import.meta.env.PROD`), debug/info/warn messages are silenced.
 * Only errors are always emitted.
 *
 * Usage:
 *   import { logger } from '@utils/logger'
 *   logger.debug('Loaded devices', devices)  // silenced in prod
 *   logger.error('Critical failure', err)    // always shown
 */

const isDev = !(import.meta as any).env?.PROD

export const LogLevel = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  SILENT: 4,
} as const

type LogLevelKey = keyof typeof LogLevel

let currentLevel: number = isDev ? LogLevel.DEBUG : LogLevel.ERROR

export const logger = {
  /** Change minimum log level at runtime (e.g. from a debug panel). */
  setLevel(level: LogLevelKey) {
    currentLevel = LogLevel[level]
  },

  debug(...args: unknown[]) {
    if (currentLevel <= LogLevel.DEBUG) console.log('[DEBUG]', ...args)
  },

  info(...args: unknown[]) {
    if (currentLevel <= LogLevel.INFO) console.info('[INFO]', ...args)
  },

  warn(...args: unknown[]) {
    if (currentLevel <= LogLevel.WARN) console.warn('[WARN]', ...args)
  },

  error(...args: unknown[]) {
    if (currentLevel <= LogLevel.ERROR) console.error('[ERROR]', ...args)
  },

  /** Timed operation — returns a function that logs elapsed ms when called. */
  time(label: string) {
    if (currentLevel > LogLevel.DEBUG) return () => {}
    const start = performance.now()
    return () => {
      const ms = (performance.now() - start).toFixed(1)
      console.log(`[DEBUG] ${label} completed in ${ms}ms`)
    }
  },
}

export default logger
