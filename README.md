# NOC-IT (Desktop -> Web)

Ten dokument jest dla mnie: jak odtworzyc projekt, uruchomic wszystko i dlaczego dziala tak a nie inaczej.

## TL;DR uruchomienia
Frontend:
```
npm install
npm run dev
```

Backend:
```
C:/Projects/Nowe/n/noc-it/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
cd backend
C:/Projects/Nowe/n/noc-it/.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Konfiguracja frontu (plik `.env.local`):
```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## Co to jest
Migracja prywatnego NOC z Tauri/Vue na Web: SPA + backend Python. Backend uruchamia istniejace skrypty z `src/scripts`.

## Jak to dziala (przeplyw)
1) Frontend (Vue) -> REST/WS
2) Backend (FastAPI) -> adapter uruchamia kontrolery Pythona
3) Kontrolery czytaja `src/data/*.json` (tymczasowo)
4) Docelowo: DB + sekret manager

## Struktura
- `src/` - Vue UI
- `backend/` - FastAPI + WS + Celery (opcjonalnie)
- `src/scripts/` - kontrolery (logika wykonawcza)
- `src/data/` - pliki danych i temp

## Backend (endpointy)
Najwazniejsze:
- `/api/devices` (GET/POST/DELETE)
- `/api/accounts` (GET/POST/DELETE)
- `/api/tunnel` (GET/PUT)
- `/api/tunnel/status`, `/api/tunnel/toggle`, `/api/tunnel/close`, `/api/tunnel/healthcheck`
- `/api/scripts/run` (sync)
- `/api/scripts/async` (async, wymaga Redis/Celery)
- `/api/jobs/{jobId}` (status joba)
- `/ws/jobs/{jobId}` (WS status)
- `/ws/terminal` (terminal)

## Skrypty Pythona uruchamiane przez backend
Mapowanie (w `backend/app/services/script_runner.py`):
- `settings-devices_controller` -> `src/scripts/settings/devices_controller.py`
- `settings-accounts_controller` -> `src/scripts/settings/accounts_controller.py`
- `settings-tunnel_controller` -> `src/scripts/settings/tunnel_controller.py`
- `modules-cmts_tmpfs_controller` -> `src/scripts/modules/cmts_tmpfs_controller.py`
- `terminal_controller` -> `src/scripts/terminal_controller.py`
- `consoles_controller` -> `src/scripts/consoles_controller.py`
- `application_controller` -> `src/scripts/application_controller.py`

## Dane i sekrety
Pliki runtime sa ignorowane przez git:
- `src/data/tunnel.json`
- `src/data/accounts.json`
- `src/data/sessions.json`
- `src/data/tunnel_status.json`
- `src/data/tunnel_pid.json`
- `src/data/settings.json`

Przyklady do odtworzenia:
- `src/data/tunnel.example.json`
- `src/data/accounts.example.json`
- `src/data/devices.example.json`
- `src/data/settings.example.json`

## CORS
Backend akceptuje:
- http://localhost:5173
- http://127.0.0.1:5173

## Async (opcjonalne)
Async i WS jobow dzialaja tylko gdy dziala Redis + Celery.
Worker:
```
C:/Projects/Nowe/n/noc-it/.venv/Scripts/python.exe -m celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO
```

## Debug szybki
Brak urzadzen w UI:
- sprawdz `.env.local`
- sprawdz `/api/devices`

Tunel nie laczy:
- `src/data/tunnel.json` ma dane
- `src/data/temp/tunnel_runner.log` pokazuje bledy

CORS error:
- backend dziala na :8000

## Przygotowanie do repo
- `.gitignore` usuwa logi, temp, sekrety, buildy
- `.env.example` i pliki `.example` do odtworzenia danych

## Docelowo
- DB (PostgreSQL) zamiast JSON
- Sekrety w vault/envelope
- Monitoring + audit logs
