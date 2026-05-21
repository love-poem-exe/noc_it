interface CacheItem {
  data: any
  timestamp: number
  ttl: number // Time to live w milisekundach
}

interface CacheConfig {
  devices: number
  accounts: number
  tunnelStatus: number
  devicesInfo: number
}

class CacheService {
  private cache = new Map<string, CacheItem>()
  private readonly config: CacheConfig = {
    devices: 5 * 60 * 1000,    // 5 minut
    accounts: 10 * 60 * 1000,  // 10 minut
    tunnelStatus: 2 * 1000,    // 2 sekundy (często się zmienia)
    devicesInfo: 30 * 60 * 1000 // 30 minut
  }

  /**
   * Pobiera dane z cache lub wykonuje funkcję ładującą
   */
  async get<T>(key: string, loader: () => Promise<T>, ttl?: number): Promise<T> {
    const now = Date.now()
    const cached = this.cache.get(key)

    // Sprawdź czy dane są w cache i nie wygasły
    if (cached && (now - cached.timestamp) < cached.ttl) {
      // Loguj tylko dla ważnych cache, nie dla tunelu
      if (key !== 'tunnelStatus') {
        console.log(`[CACHE] HIT: ${key}`)
      }
      return cached.data as T
    }

    // Dane nie są w cache lub wygasły - pobierz nowe
    // Loguj tylko dla ważnych cache, nie dla tunelu
    if (key !== 'tunnelStatus') {
      console.log(`[CACHE] MISS: ${key} - loading data...`)
    }
    
    try {
      const data = await loader()
      const cacheTtl = ttl || this.config[key as keyof CacheConfig] || 5 * 60 * 1000
      
      this.cache.set(key, {
        data,
        timestamp: now,
        ttl: cacheTtl
      })

      // Loguj tylko dla ważnych cache, nie dla tunelu
      if (key !== 'tunnelStatus') {
        console.log(`[CACHE] STORED: ${key} (TTL: ${cacheTtl}ms)`)
      }
      return data
    } catch (error) {
      console.error(`[CACHE] ERROR loading ${key}:`, error)
      // Jeśli mamy stare dane w cache, zwróć je mimo błędu
      if (cached) {
        console.log(`[CACHE] FALLBACK: ${key} (using stale data)`)
        return cached.data as T
      }
      throw error
    }
  }

  /**
   * Usuwa dane z cache (po aktualizacji danych)
   */
  invalidate(key: string): void {
    // Loguj tylko dla ważnych cache, nie dla tunelu
    if (key !== 'tunnelStatus') {
      console.log(`[CACHE] INVALIDATE: ${key}`)
    }
    this.cache.delete(key)
  }

  /**
   * Usuwa wszystkie dane z cache
   */
  clear(): void {
    console.log(`[CACHE] CLEAR ALL`)
    this.cache.clear()
  }

  /**
   * Sprawdza czy dane są w cache
   */
  has(key: string): boolean {
    const cached = this.cache.get(key)
    if (!cached) return false
    
    const now = Date.now()
    const isValid = (now - cached.timestamp) < cached.ttl
    
    if (!isValid) {
      this.cache.delete(key)
      return false
    }
    
    return true
  }

  /**
   * Pobiera informacje o cache
   */
  getStats(): Record<string, any> {
    const stats: Record<string, any> = {}
    const now = Date.now()
    
    for (const [key, item] of this.cache.entries()) {
      const age = now - item.timestamp
      const remaining = item.ttl - age
      stats[key] = {
        age: Math.round(age / 1000) + 's',
        remaining: remaining > 0 ? Math.round(remaining / 1000) + 's' : 'expired',
        size: JSON.stringify(item.data).length + ' bytes'
      }
    }
    
    return stats
  }
}

// Eksportuj singleton instance
export const cacheService = new CacheService()
export default cacheService