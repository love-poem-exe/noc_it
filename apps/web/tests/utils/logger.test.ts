import { describe, it, expect } from 'vitest'
import { logger, LogLevel } from '../../src/utils/logger'

describe('logger', () => {
  it('exposes all log methods', () => {
    expect(typeof logger.debug).toBe('function')
    expect(typeof logger.info).toBe('function')
    expect(typeof logger.warn).toBe('function')
    expect(typeof logger.error).toBe('function')
  })

  it('setLevel accepts valid level keys', () => {
    expect(() => logger.setLevel('ERROR')).not.toThrow()
    expect(() => logger.setLevel('DEBUG')).not.toThrow()
  })

  it('time() returns a callable end function', () => {
    logger.setLevel('DEBUG')
    const end = logger.time('test-op')
    expect(typeof end).toBe('function')
    expect(() => end()).not.toThrow()
  })

  it('time() returns noop when level is above DEBUG', () => {
    logger.setLevel('ERROR')
    const end = logger.time('test-op')
    expect(typeof end).toBe('function')
  })
})

describe('LogLevel constants', () => {
  it('has correct ordering', () => {
    expect(LogLevel.DEBUG).toBeLessThan(LogLevel.INFO)
    expect(LogLevel.INFO).toBeLessThan(LogLevel.WARN)
    expect(LogLevel.WARN).toBeLessThan(LogLevel.ERROR)
    expect(LogLevel.ERROR).toBeLessThan(LogLevel.SILENT)
  })
})
