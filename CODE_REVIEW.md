# NOC-IT Full Codebase Review

## Executive Summary

**Project type:** Tauri + Vue 3 + FastAPI network operations center (NOC) tool for SSH terminal management, CMTS device monitoring, and tunnel management.

**Tech stack:** Vue 3 (Vite) + Pinia | FastAPI + Celery | Tauri (Rust) | Python scripts (paramiko SSH)

**Overall assessment:** The codebase is functional but has significant architectural debt from a Tauri → web backend migration. There are critical runtime bugs, extensive dead code, heavy code duplication (especially in SSH connection logic), and a mixed JS/TS frontend that negates TypeScript's value.

---

## 1. Changes Applied (Safe, Behavior-Preserving)

### Critical Bug Fixes

| # | Fix | File | Impact |
|---|-----|------|--------|
| 1 | **Fixed infinite recursion** — `sendCommand` shadowed its own import, causing stack overflow on every command | `src/views/Terminal.vue` | **CRITICAL** — terminal was completely broken |
| 2 | **Fixed method call on wrong object** — `dataService.invokeAsyncScript()` → `invokeAsyncScript()` (standalone function) | `src/views/modules/SSHExecutor.vue` | **HIGH** — SSH executor threw at runtime |
| 3 | **Merged orphaned routes** — `/settings/cache-debug` and `/modules/ssh-executor` were unreachable | `src/router.js` | **MEDIUM** — two views were inaccessible |

### Dead Code Removed

| File | Reason |
|------|--------|
| `src/services/ViewStateService.ts` | Entirely commented out (55 lines of `//`) |
| `src/services/FileAccessTest.ts` | Tauri-only artifact, never imported |
| `src/utils/stateManager.ts` | Never imported by any file |
| `src/types/ViewState.ts` | Only used by dead `stateManager.ts` |
| `src/views/settings/Settings.vue` | Empty file (0 bytes) |
| `src/views/ExampleView.vue` | Placeholder, not in any router |
| `src/views/Tunnel.vue.backup` | Old backup file |
| `src/index.html.bak` | Backup file |
| `src/router/index.js` | Orphaned — shadowed by `src/router.js` |
| `src-tauri/src/ssh/device.rs` | Empty stub, never implemented |
| `src-tauri/src/ssh/jump.rs` | Empty stub, never implemented |

### Code Cleanup

| Change | File |
|--------|------|
| Removed `import os` (replaced `os.path.basename` → `Path.name`) | `backend/app/api/routes.py` |
| Removed dead comment about removed endpoint | `backend/app/api/routes.py` |
| Removed unused `asyncio` import | `src/scripts/terminal_controller.py` |
| Removed unused `select` import | `src/scripts/settings/tunnel_runner.py` |
| Removed dead `_connected` variable (set but never read) | `src/scripts/settings/tunnel_runner.py` |
| Removed dead `_load_tunnel_status()` function (never called) | `src/scripts/settings/devices_controller.py` |
| Removed unused `getStatusClass()` function | `src/views/settings/Tunnel.vue` |
| Removed 6 debug `console.log` statements | `src/main.js` |
| Translated Polish comments to English | `src/main.js` |

---

## 2. Issues NOT Fixed (Require Design Decisions)

### Architecture

#### A. God Components
- **`CMTS_TMPFS.vue`** — **3,215 lines**. Mixes template (~500 lines), business logic (~2,000 lines), API calls, progress tracking, multiple modals, and CSS in one file.
- **`Devices.vue`** — **2,082 lines**. Same pattern. Contains 4 nearly-identical batch sync functions (`onSyncAll`, `onSyncUnsync`, `onSyncError`, `onSyncIncomplete` — ~50 lines each, differing only in filter).
- **Recommendation:** Extract into sub-components (Modal, ProgressBar, DeviceList) + composables for business logic.

#### B. Empty Components Folder
`src/components/` is empty. All UI is inline in views. Common patterns (modals, lists, inputs) are duplicated.

#### C. Inconsistent Data Access (4 Competing Patterns)

| Pattern | Used By |
|---------|---------|
| `useData()` composable | Terminal, Accounts, Devices, Tunnel, CacheDebug |
| `dataService` direct | SSHExecutor, Tunnel, CMTS_TMPFS |
| `cmtsTmpfsStore` (Pinia) | CMTS_TMPFS only |
| Raw `fetch()` / `requestJson()` | CMTS_Swapper, cmtsTmpfsStore |

**Recommendation:** Standardize on `useData()` composable as the single entry point.

#### D. Backend "God Router"
`backend/app/api/routes.py` (292 lines, 25+ endpoints) handles 6 unrelated domains in one file.

**Recommendation:** Split into sub-routers:
```
api/
  routes/
    __init__.py      # combine all routers
    devices.py       # /devices/*
    accounts.py      # /accounts/*
    tunnel.py        # /tunnel/*
    modules.py       # /modules/*
    terminal.py      # /terminal/*
    system.py        # /health, /system/*
```

#### E. Python Scripts: Massive Duplication

SSH connection logic (paramiko + socket + tunnel header) is duplicated **5 times**:
- `consoles_controller.py`
- `terminal_controller.py`
- `terminal_server.py`
- `devices_controller.py`
- `cmts_tmpfs_controller.py`

Helper functions duplicated:
- `_load_devices()` / `_load_accounts()` — **6 copies**
- `_read_full_output()` — **4 copies** (3 variants in devices_controller alone)
- `is_ip_address()` — **3 inline definitions**

**Recommendation:** Create `src/scripts/shared/ssh_utils.py` containing:
```python
def load_devices() -> list[dict]: ...
def load_accounts() -> list[dict]: ...
def create_ssh_connection(device, account, tunnel_config=None) -> paramiko.SSHClient: ...
def read_full_output(channel, timeout=30) -> str: ...
def is_ip_address(value: str) -> bool: ...
```

#### F. Tauri Legacy Code (Unused)
- `src-tauri/src/ssh_manager.rs` (270 lines) — not imported by `main.rs`
- `src-tauri/src/terminal_manager.rs` (310 lines) — not imported by `main.rs`

Both are complete implementations but never registered as Tauri commands. If the migration to web backend is final, these should be removed.

#### G. Frontend JS/TS Split Negates Type Safety
Services are TypeScript, but **all 17 Vue SFCs use plain JavaScript `<script setup>`** (only dead `ExampleView.vue` had `lang="ts"`). The TypeScript types in the service layer provide zero safety at the view boundary.

**Recommendation:** Either convert all SFCs to `lang="ts"` or move services to `.js`.

---

### Security

| Issue | Severity | Location |
|-------|----------|----------|
| Plaintext credentials in JSON files | **HIGH** | `accounts.json`, `tunnel.json` |
| No auth on TCP server (port 9876) | MEDIUM | `terminal_server.py` |
| No auth on WebSocket server (port 9877) | MEDIUM | `terminal_ws_server.py` |
| Accept all SSH host keys (no verification) | MEDIUM | All SSH scripts + Rust files |
| Debug print leaks credentials to stderr | MEDIUM | `accounts_controller.py` |
| Flask `debug=True` in `modules_settings_controller.py` | MEDIUM | Likely legacy/unused |
| No thread safety on `redirect_stdout` | MEDIUM | `backend/app/services/script_runner.py` |

---

### Bugs Still Present

| # | Bug | File | Severity |
|---|-----|------|----------|
| 1 | `consoles_controller.py` has duplicate `create_session` — second definition overwrites first | `src/scripts/consoles_controller.py:510,601` | MEDIUM |
| 2 | `console_controller.py` uses `account['username']` instead of `account['login']` | `src/scripts/modules/console_controller.py` | HIGH (KeyError) |
| 3 | `console_controller.py` creates unconnected socket passed to paramiko | `src/scripts/modules/console_controller.py` | HIGH (broken) |
| 4 | `terminal_controller.py` indentation bug — prints "Auth successful" even on failure | `src/scripts/terminal_controller.py:143` | LOW |
| 5 | `devices_controller.py` has two `if __name__ == "__main__"` blocks | `src/scripts/settings/devices_controller.py:939,1189` | LOW |
| 6 | `General.vue` has no `v-model` bindings — settings UI is non-functional | `src/views/settings/General.vue` | MEDIUM |
| 7 | `script_runner.py` `asyncio.run()` inside sync context will crash if route is `async def` | `backend/app/services/script_runner.py:72` | MEDIUM |
| 8 | `script_runner.py` `redirect_stdout` is not thread-safe | `backend/app/services/script_runner.py:139` | HIGH |

---

## 3. Dependency Audit

### Python (`requirements.txt`)

| Package | Status | Action |
|---------|--------|--------|
| `fastapi==0.115.6` | OK | Current |
| `uvicorn[standard]==0.30.6` | OK | Current |
| `celery==5.4.0` | OK | Current |
| `redis==5.0.8` | Conditional | Only needed if Celery runs non-eager. Keep. |
| `pydantic==2.9.2` | OK | Current |
| **`psycopg[binary]==3.2.13`** | **UNUSED** | **Remove** — no database code exists |
| `paramiko==3.4.0` | Used by scripts | Keep (not imported in backend directly, but used by `src/scripts/`) |

### Node.js (`package.json`)

| Package | Status | Notes |
|---------|--------|-------|
| `vue@^3.4.0` | OK | |
| `vue-router@^4.5.1` | OK | |
| `pinia@^3.0.3` | OK | |
| `pinia-plugin-persistedstate@^4.7.1` | OK | Used in main.js |
| `@tauri-apps/api@^1.6.0` | **UNUSED** | Used only by deleted `FileAccessTest.ts`. May still be needed if Tauri build is active. |
| `xlsx@^0.18.5` | OK | Used by CMTS_Swapper |
| `vite@^6.3.5` | OK | |
| `typescript@^5.8.3` | OK | |
| `vue-tsc@^1.6.5` | **Outdated** | Should be `^2.x` for Vue 3.4+ / TypeScript 5.x compatibility |

### Rust (`Cargo.toml`)

| Crate | Status | Notes |
|-------|--------|-------|
| `tauri@1.8.2` | OK | Current Tauri v1 |
| `serde@1.0` | OK | |
| `serde_json@1.0` | OK | |
| `chrono@0.4` | OK | Used for session history timestamps |

---

## 4. Proposed Improved Structure

```
noc-it/
├── index.html
├── package.json
├── vite.config.js
├── tsconfig.json
│
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── schemas.py
│       ├── core/
│       │   ├── config.py          # Use BaseSettings
│       │   └── logging.py
│       ├── api/
│       │   ├── __init__.py        # Combines all routers
│       │   ├── devices.py         # /devices/* endpoints
│       │   ├── accounts.py        # /accounts/* endpoints
│       │   ├── tunnel.py          # /tunnel/* endpoints
│       │   ├── modules.py         # /modules/* endpoints
│       │   ├── terminal.py        # /terminal/* endpoints
│       │   └── system.py          # /health, /system/*
│       ├── services/
│       │   └── script_runner.py
│       ├── tasks/
│       │   ├── celery_app.py
│       │   └── tasks.py
│       └── ws/
│           ├── jobs.py
│           └── terminal.py        # Implement or remove stub
│
├── src/
│   ├── main.ts                    # Convert to TypeScript
│   ├── router.ts
│   ├── components/                # NEW: Shared components
│   │   ├── BaseModal.vue
│   │   ├── ProgressBar.vue
│   │   ├── DeviceList.vue
│   │   ├── SearchInput.vue
│   │   └── StatusBadge.vue
│   ├── composables/
│   │   ├── useData.ts
│   │   ├── useDeviceSync.ts       # Extract from Devices.vue
│   │   └── useTunnelMonitoring.ts
│   ├── services/
│   │   ├── ApiClient.ts
│   │   ├── CacheService.ts
│   │   ├── DataService.ts
│   │   ├── JobService.ts
│   │   ├── TerminalApi.ts
│   │   └── TerminalService.ts
│   ├── stores/
│   │   └── cmtsTmpfsStore.ts      # Convert to TypeScript
│   ├── types/
│   │   ├── Device.ts              # NEW: Shared types
│   │   ├── Account.ts
│   │   └── Tunnel.ts
│   ├── views/
│   │   ├── App.vue
│   │   ├── Home.vue
│   │   ├── Main.vue
│   │   ├── Terminal.vue
│   │   ├── modules/
│   │   │   ├── CmtsSwapper.vue    # Rename PascalCase
│   │   │   └── CmtsTmpfs.vue     # Rename PascalCase
│   │   └── settings/
│   │       ├── Accounts.vue
│   │       ├── CacheDebug.vue
│   │       ├── Devices.vue        # Decompose (2082→~500 lines)
│   │       ├── General.vue        # Wire up with v-model
│   │       ├── Modules.vue
│   │       ├── Reports.vue        # Fix spelling
│   │       └── Tunnel.vue
│   ├── styles/
│   │   └── settings/
│   │       └── devices.css
│   └── scripts/
│       ├── shared/                # NEW: Extract duplicated logic
│       │   ├── ssh_utils.py       # SSH connection, read_full_output
│       │   ├── data_loader.py     # load_devices, load_accounts
│       │   └── ip_utils.py        # is_ip_address
│       ├── terminal_controller.py
│       ├── terminal_ws_server.py
│       ├── terminal_server.py
│       ├── consoles_controller.py
│       ├── modules/
│       │   └── cmts_tmpfs_controller.py
│       └── settings/
│           ├── accounts_controller.py
│           ├── devices_controller.py
│           ├── modules_controller.py
│           └── tunnel_controller.py
│
├── src-tauri/                     # Keep only if Tauri build active
│   ├── src/
│   │   └── main.rs
│   └── Cargo.toml
│
└── data/                          # Move runtime data out of src/
    ├── accounts.json
    ├── devices.json
    ├── settings.json
    ├── tunnel.json
    └── keys/
```

### Files to Remove (Proposed)

| File | Reason |
|------|--------|
| `src-tauri/src/ssh_manager.rs` | 270 lines, not used by main.rs |
| `src-tauri/src/terminal_manager.rs` | 310 lines, not used by main.rs |
| `src/scripts/modules/console_controller.py` | Broken (wrong field names, stubs) |
| `src/scripts/settings/modules_settings_controller.py` | Legacy Flask server, superseded by FastAPI |
| `src/scripts/test_ws_client.py` | Manual test script |
| `IMPLEMENTATION_SUMMARY.md` | Migration artifact |
| `TOKIO_MIGRATION.md` | Migration artifact |
| `TOKIO_QUICKSTART.md` | Migration artifact |
| `TUNNEL_DIAGNOSTICS.md` | Diagnostic notes |
| `python_logs.txt` | Debug output |
| `wynik.txt` | Debug output |
| `test_command.json` | Test artifact |

---

## 5. Risk Assessment

| Change Type | Risk | Mitigation |
|-------------|------|------------|
| Bug fixes (Terminal.vue, SSHExecutor.vue) | **Low** | These were already broken; fixes restore correct behavior |
| Dead file deletion | **Low** | None were imported/used |
| Router merge | **Low** | Added missing routes to active router |
| Import cleanup (Python) | **None** | Removed only verified unused imports |
| Future: Split routes.py | **Low** | Mechanical refactor, same behavior |
| Future: Extract SSH utilities | **Medium** | Must test all 5 scripts that use SSH connections |
| Future: Decompose God Components | **Medium** | Template and reactivity changes need careful testing |
| Future: Remove Rust SSH files | **Low** | If Tauri build is abandoned; otherwise keep |

---

## 6. Console.log Inventory

**100+ debug `console.log` calls** across the frontend with no log-level abstraction. Recommendation:

```typescript
// src/utils/logger.ts
const isDev = import.meta.env.DEV

export const logger = {
  debug: (...args: unknown[]) => isDev && console.log(...args),
  info: (...args: unknown[]) => console.info(...args),
  warn: (...args: unknown[]) => console.warn(...args),
  error: (...args: unknown[]) => console.error(...args),
}
```

Replace all `console.log` calls with `logger.debug()` to silence them in production.

---

## 7. Performance Suggestions

1. **Tunnel status polling:** Currently 3 independent pollers (Main.vue 5s, Tunnel.vue 5s, useTunnelMonitoring 30s). Consolidate into a single reactive source.
2. **CMTS_Swapper.vue** ships **340KB** of JavaScript — the `xlsx` library is the main contributor. Consider lazy loading it only when the import dialog opens.
3. **Device list rendering** in Devices.vue and Terminal.vue doesn't use `v-memo` or virtual scrolling. For large device lists, this will cause jank.
4. **Module cache in script_runner.py** never invalidates — acceptable for production but hinders development. Add a `--reload` flag or check `mtime`.

---

## 8. Test Coverage

**No tests exist.** No test files, no test configuration, no test runner.

### Recommended Test Strategy

| Layer | Tool | Priority |
|-------|------|----------|
| Backend API | `pytest` + `httpx` (TestClient) | **HIGH** — test all 25 endpoints |
| Python scripts | `pytest` | **HIGH** — test SSH connection logic, device sync |
| Vue components | `vitest` + `@vue/test-utils` | MEDIUM — test composables first |
| E2E | `playwright` | LOW — after unit tests exist |

### Critical Test Cases to Add First

1. `run_script()` in `script_runner.py` — test module loading, stdout capture, error handling
2. `devices_controller.py::sync_device` — test SSH failure paths
3. `tunnel_controller.py` — test connect/disconnect/status lifecycle
4. `useData` composable — test caching, error handling
5. API routes — test all endpoints return expected shapes

---

## 9. Phase 2 — Changes Applied (Fixes for Deferred Issues)

The following fixes address the 8 items from Section 2 that were originally marked as "Require Design Decisions":

### Fix 1: Centralized Logger (`src/utils/logger.ts`) ✅

Created `src/utils/logger.ts` — environment-aware logger with `debug`, `info`, `warn`, `error` methods. In production (`import.meta.env.PROD`), debug/info/warn calls are silenced. Includes `setLevel()` and `time()` helpers.

Test: `tests/utils/logger.test.ts` (5 cases).

### Fix 2: Thread-Safe Script Runner (`backend/app/services/script_runner.py`) ✅

Replaced process-global `redirect_stdout()` with `_ThreadLocalWriter` class using `threading.local()`. Each concurrent request now captures stdout independently, preventing output corruption under concurrent API calls.

### Fix 3: Remove Unused `psycopg` (`backend/requirements.txt`) ✅

Removed `psycopg[binary]==3.2.13` — no database code exists in the project.

### Fix 4: Shared Python Script Utilities (`src/scripts/shared/script_utils.py`) ✅

Created `src/scripts/shared/script_utils.py` consolidating duplicated helpers:
- `load_devices()` / `save_devices()` — replaces 6 copies of `_load_devices`
- `load_accounts()` / `save_accounts()` — replaces 5 copies of `_load_accounts`
- `is_ip_address()` — replaces 3 inline definitions
- `read_full_output()` — replaces 4 variants, parametric (configurable timeout/keywords)
- `resolve_tunnel_target()` — shared DNS vs IP logic
- `load_json_file()` / `save_json_file()` — generic JSON I/O with error handling

Test: `tests/scripts/test_script_utils.py` (14 cases).

Scripts still have their local copies; migration should happen incrementally.

### Fix 5: General.vue Functional Rewrite (`src/views/settings/General.vue`) ✅

Rewired from a static HTML mockup to a fully functional settings page:
- Added `v-model.number` bindings on all inputs
- Added `ref<GeneralSettings>` reactive state with typed defaults
- Added `save()` calling `POST /api/settings/save`
- Added `resetDefaults()` button
- Added save confirmation message with auto-dismiss

### Fix 6: God Component Decomposition — Devices.vue Batch Sync ✅

Created `src/composables/useSyncBatch.js` extracting the identical pattern from 4 `onSync*` functions (onSyncAll, onSyncUnsync, onSyncError, onSyncIncomplete).

**Before:** 4 functions × ~50 lines each = 200 lines of near-identical code.
**After:** 4 functions × ~12 lines each + 1 composable (85 lines) = 133 lines total.

The composable provides `runBatch(devices, syncFn, onEmpty, emptyMessage)` with progress tracking, elapsed timer, `progressPercent`, and `formattedElapsed` computed properties.

Also created `src/composables/useAutoCheck.js` for CMTS_TMPFS auto-check extraction (not yet wired).

Test: `tests/composables/useSyncBatch.test.js` (6 cases).

### Fix 7: Vue SFCs → TypeScript ✅

Converted 5 Vue SFCs from `<script setup>` to `<script setup lang="ts">`:
- `Raports.vue` — trivial (empty script)
- `App.vue` — trivial (1 import)
- `General.vue` — added `GeneralSettings` interface, typed refs
- `Accounts.vue` — typed `visiblePasswords` as `boolean[]`
- `CacheDebug.vue` — typed `stats` as `Record<string, unknown>`

Remaining SFCs can be converted incrementally, starting with `Main.vue` and `Home.vue`.

### Fix 8: Test Infrastructure ⏳ (Network blocked)

Created test configuration and test files, but `npm install vitest` and `pip install pytest` are blocked by network connectivity.

**Files created:**
- `vitest.config.js` — Vitest config with happy-dom environment, path aliases
- `tests/utils/logger.test.ts` — 5 test cases for logger
- `tests/composables/useSyncBatch.test.js` — 6 test cases for batch sync composable
- `tests/scripts/test_script_utils.py` — 14 test cases for Python shared utilities

**Added to `package.json`:**
```json
"test": "vitest run",
"test:watch": "vitest",
"test:python": "cd backend && python -m pytest ../tests/scripts/ -v"
```

**To complete when network is available:**
```bash
npm install --save-dev vitest @vue/test-utils happy-dom
pip install pytest
npm test
```
