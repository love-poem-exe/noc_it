# 🚀 Tokio Async Implementation - Quick Start Guide

## ✅ Co Zostało Zrobione

### 1. **Cargo.toml** - Tokio Runtime
```toml
tokio = { version = "1.40", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
thiserror = "1.0"
log = "0.4"
```

### 2. **src-tauri/src/main.rs** - Async Backend
- ✅ Async `run_script_async_impl()` z timeout'ami
- ✅ Error handling z `ScriptError` enum
- ✅ Tokio task spawning zamiast `std::thread`
- ✅ Graceful cleanup na exit

### 3. **DataService.ts** - Frontend z Timeout'ami
```typescript
invokeAsyncScript({ 
  script, 
  method, 
  payload,
  timeoutMs: 60000  // Nowy parametr!
})
```

### 4. **Timeout'y dla Każdej Operacji**
| Operacja | Timeout |
|----------|---------|
| Devices read | 60s |
| Add device | 45s |
| Delete | 30s |
| Sync (SSH) | 120s |
| Tunnel | 300s |

### 5. **Paging dla Dużych List**
```python
# Python
get_devices_paginated(payload={"page": 1, "limit": 100})

# TypeScript
getDevicesPaginated(page, limit)
```

### 6. **Nowy SSH Executor Component**
- ✅ [SSHExecutor.vue](src/views/modules/SSHExecutor.vue) - Terminal do SSH komend
- ✅ Integrated w menu (Modules → SSH Executor)
- ✅ Progress bar i timeout'y
- ✅ Stats execution

---

## 📋 Co Zmienić Aby Uruchomić

### 1. Build Cargo
```bash
cd src-tauri
cargo build --release
```

### 2. Uruchom Dev
```bash
npm run dev
```

---

## 🔧 Integracja z Istniejącymi Komponentami

### Jeśli masz component, który czeka na wynik skryptu:

**Przed (❌ Zawieszenie bez timeout'u):**
```typescript
const result = await invoke('run_script', { script, method, payload })
```

**Po (✅ Z timeout'ami i cleanupem):**
```typescript
import { dataService, invokeAsyncScript } from '../services/DataService'

const result = await invokeAsyncScript({
  script: 'settings-tunnel_controller',
  method: 'get_status',
  payload: {},
  timeoutMs: 30000  // 30 sekund
})
```

---

## 📊 Stronicowanie - Jak Używać

### W Vue Component'ie:

```typescript
// Zamiast loadować wszystkie urządzenia naraz
// const allDevices = await dataService.getDevices()

// Użyj paging:
const page1 = await dataService.getDevicesPaginated(1, 100)
console.log(`Page 1: ${page1.data.length}/${page1.total}`)

// Załaduj następną stronę on-demand
if (hasMorePages) {
  const page2 = await dataService.getDevicesPaginated(2, 100)
}
```

---

## 🎯 Best Practices

### 1. Zawsze Ustawiaj Timeout
```typescript
// ❌ BAD - brak timeout'u
await invokeAsyncScript({ script, method })

// ✅ GOOD
await invokeAsyncScript({ script, method, timeoutMs: 60000 })
```

### 2. Obsługuj Timeout'y
```typescript
try {
  const result = await operation()
} catch (e) {
  if (e.message.includes('TIMEOUT')) {
    showToast('Operation timed out - try again')
  }
}
```

### 3. Paginuj Duże Listy
```typescript
// ❌ 10,000 urządzeń naraz
const devices = await dataService.getDevices()

// ✅ 100 na stronę
const page1 = await dataService.getDevicesPaginated(1, 100)
```

### 4. Cleanup w Unmount
```typescript
onUnmounted(() => {
  if (isExecuting.value) {
    // Anuluj operację jeśli komponenty się zamyka
    isExecuting.value = false
  }
})
```

---

## 🔍 Debugging

### Voir Tokio logs
```bash
RUST_LOG=debug npm run dev
```

### Verbose Python output
```python
print("[DEBUG] Message here")  # Pojawi się w stderr
```

### Browser dev tools
- F12 → Console
- Szukaj `[RUST]`, `[TIMEOUT]`, `[SCRIPT ERROR]`

---

## 📚 Pliki do Przejrzenia

1. **[TOKIO_MIGRATION.md](TOKIO_MIGRATION.md)** - Pełna dokumentacja zmian
2. **[src-tauri/src/main.rs](src-tauri/src/main.rs)** - Backend Tokio implementation
3. **[src/services/DataService.ts](src/services/DataService.ts)** - Frontend timeout'ami
4. **[src/views/modules/SSHExecutor.vue](src/views/modules/SSHExecutor.vue)** - Przykład komponentu
5. **[src/scripts/settings/devices_controller.py](src/scripts/settings/devices_controller.py)** - Python paging

---

## 🚀 Deployment

### Production Build
```bash
npm run build
cargo tauri build
```

### Output: `src-tauri/target/release/`

---

## ⚠️ Known Issues & Solutions

### Timeout'y za Krótkie?
Zwiększ w DataService.ts:
```typescript
timeoutMs: 120000  // 120 sekund zamiast 60
```

### Python Hanging?
Dodaj signal handler:
```python
import signal

def timeout_handler(sig, frame):
    raise TimeoutError("Command timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # 5 minut

# Your code here

signal.alarm(0)  # Cancel
```

### Out of Memory?
Włącz paging dla dużych list:
```typescript
const paginatedResult = await dataService.getDevicesPaginated(page, 100)
```

---

## 📞 Support

**Problem?** Sprawdź:
1. Czy Tokio się skompilował? `cargo build --release`
2. Czy timeout'y są ustawione? Szukaj `timeoutMs`
3. Czy Python timeout'uje? Patrz stderr
4. Czy SSHExecutor się renderuje? Router updated?

---

## 🎉 Gotowe!

Aplikacja teraz ma:
- ✅ **Async/await** - Modernowy Rust
- ✅ **Timeout'y** - Nie zawisną
- ✅ **Paging** - Duże listy OK
- ✅ **SSH Executor** - Terminal w UI
- ✅ **Error Handling** - Structured errors

**Happy coding! 🚀**
