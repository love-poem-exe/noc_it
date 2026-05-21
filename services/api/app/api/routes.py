from fastapi import APIRouter, UploadFile, File, Response
import sys
from pathlib import Path
from fastapi.responses import JSONResponse
import json
from app.schemas import ScriptRequest
from app.tasks.tasks import run_script_task
from app.tasks.celery_app import celery_app
from celery.result import AsyncResult
from app.services.script_runner import run_script

router = APIRouter()


def _coerce_json(value, fallback):
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        cleaned = value.lstrip("\ufeff").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return fallback
    return fallback


@router.post("/scripts/run")
def scripts_run(req: ScriptRequest):
    result = run_script(req.script, req.method, req.payload)
    payload = result.get("result")
    if isinstance(payload, (dict, list)):
        return JSONResponse(payload)
    if payload is None:
        return Response(content="", media_type="text/plain")
    return Response(content=str(payload), media_type="text/plain")


@router.post("/scripts/async")
def scripts_async(req: ScriptRequest):
    try:
        # Special-case: for TMPFS verification run synchronously to avoid Redis/Celery dependency
        if req.script == 'modules-cmts_tmpfs_controller' and req.method == 'verify_tmpfs_alarms':
            result = run_script(req.script, req.method, req.payload)
            # Return the script's result object directly so frontend receives top-level `results`/`logs` keys
            return result.get("result")

        job = run_script_task.delay(req.script, req.method, req.payload)
        return {"jobId": job.id}
    except Exception:
        result = run_script(req.script, req.method, req.payload)
        return {"result": result.get("result")}


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    result = AsyncResult(job_id, app=celery_app)
    payload = result.result if result.ready() else None
    return {
        "jobId": job_id,
        "state": result.state,
        "ready": result.ready(),
        "result": payload,
    }


@router.get("/tunnel/status")
def tunnel_status():
    result = run_script("settings-tunnel_controller", "get_status_fast", {})
    return _coerce_json(result.get("result"), {"status": "NOT CONNECTED"})


@router.get("/tunnel")
def tunnel_get():
    result = run_script("settings-tunnel_controller", "get_tunnel", {})
    return _coerce_json(
        result.get("result"),
        {"address": "", "login": "", "authMode": "password", "keyPath": ""}
    )


@router.put("/tunnel")
def tunnel_save(payload: dict):
    result = run_script("settings-tunnel_controller", "save_tunnel", payload)
    return {"ok": result.get("ok", False)}


@router.post("/tunnel/toggle")
def tunnel_toggle():
    result = run_script("settings-tunnel_controller", "toggle_tunnel", {})
    return _coerce_json(result.get("result"), {"status": "NOT CONNECTED"})


@router.post("/tunnel/close")
def tunnel_close():
    result = run_script("settings-tunnel_controller", "close_tunnel", {})
    payload = result.get("result")
    return payload if payload else "Tunnel closed"


@router.get("/modules/cmts-compare/files")
def cmts_compare_files():
    try:
        base_dir = Path(__file__).resolve().parents[4]
        out_dir  = base_dir / "apps" / "web" / "src" / "data" / "modules" / "cmts_compare"
        out_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(
            [f.name for f in out_dir.iterdir() if f.is_file()],
            reverse=True
        )
        return {"files": files}
    except Exception as e:
        return {"files": [], "error": str(e)}


@router.get("/modules/cmts-compare/content")
def cmts_compare_content(filename: str):
    try:
        safe_name = Path(filename).name
        base_dir  = Path(__file__).resolve().parents[4]
        out_dir   = base_dir / "apps" / "web" / "src" / "data" / "modules" / "cmts_compare"
        target    = out_dir / safe_name
        if not target.exists():
            return {"ok": False, "error": "Plik nie istnieje"}
        content = target.read_text(encoding="utf-8")
        return {"ok": True, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.delete("/modules/cmts-compare/delete")
def cmts_compare_delete(payload: dict):
    try:
        filename = str(payload.get("filename", "")).strip()
        if not filename:
            return {"ok": False, "error": "Brak nazwy pliku"}
        safe_name = Path(filename).name
        base_dir  = Path(__file__).resolve().parents[4]
        out_dir   = base_dir / "apps" / "web" / "src" / "data" / "modules" / "cmts_compare"
        target = out_dir / safe_name
        if not target.exists():
            return {"ok": False, "error": "Plik nie istnieje"}
        target.unlink()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/modules/cmts-compare/save")
def cmts_compare_save(payload: dict):
    try:
        nms      = str(payload.get("nms", "unknown")).strip()
        filename = str(payload.get("filename", "export.txt")).strip()
        content  = str(payload.get("content", ""))
        # sanitize
        safe_name = Path(filename).name
        base_dir  = Path(__file__).resolve().parents[4]
        out_dir   = base_dir / "apps" / "web" / "src" / "data" / "modules" / "cmts_compare"
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / safe_name
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": str(target)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/tunnel/key")
def tunnel_key_upload(key: UploadFile = File(...)):
    try:
        base_dir = Path(__file__).resolve().parents[3]
        keys_dir = base_dir / "src" / "data" / "keys"
        keys_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(key.filename).name
        target_path = keys_dir / filename
        # Save key file permanently under src/data/keys
        with open(target_path, "wb") as f:
            f.write(key.file.read())

        # Also update tunnel.json to reference this keyPath
        tunnel_file = base_dir / "src" / "data" / "tunnel.json"
        if tunnel_file.exists():
            try:
                with open(tunnel_file, "r", encoding="utf-8") as tf:
                    data = json.load(tf)
            except Exception:
                data = {}
            data["keyPath"] = filename
            try:
                with open(tunnel_file, "w", encoding="utf-8") as tf:
                    json.dump(data, tf, ensure_ascii=False, indent=2)
            except Exception:
                pass

        return {"ok": True, "filename": filename, "path": str(target_path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/tunnel/logs")
def tunnel_logs(lines: int = 1000):
    """Return tunnel runner log content (optionally last N lines)."""
    try:
        base_dir = Path(__file__).resolve().parents[3]
        log_path = base_dir / "src" / "data" / "temp" / "tunnel_runner.log"
        if not log_path.exists():
            return {"logs": ""}
        text = log_path.read_text(encoding="utf-8")
        if lines and lines > 0:
            all_lines = text.splitlines()
            if len(all_lines) > lines:
                text = "\n".join(all_lines[-lines:])
        return {"logs": text}
    except Exception as e:
        return {"logs": f"Error reading logs: {e}"}


@router.get("/devices")
def devices_list():
    result = run_script("settings-devices_controller", "get_all_devices", {})
    return result.get("result") or []


@router.get("/devices/info")
def devices_info():
    result = run_script("settings-devices_controller", "get_devices_info", {})
    return result.get("result") or {}


@router.post("/devices")
def devices_add(payload: dict):
    run_script("settings-devices_controller", "add_device", payload)
    return {"ok": True}


@router.post("/devices/add-and-sync")
def devices_add_and_sync(payload: dict):
    """Add a device by hostname and immediately trigger its synchronization.

    Payload: { "hostname": "<hostname>" }
    """
    hostname = payload.get("hostname") or payload.get("address")
    if not hostname:
        return {"ok": False, "error": "Missing hostname in payload"}

    # Attempt to add the device (controller will ignore if already exists)
    try:
        run_script("settings-devices_controller", "add_device", {"address": hostname})
    except Exception as e:
        return {"ok": False, "error": f"add_device_failed: {e}"}

    # Reload devices and locate the newly added (or existing) device by hostname/address
    devices_res = run_script("settings-devices_controller", "get_all_devices", {})
    devices_list = devices_res.get("result") or []
    device = next((d for d in devices_list if d.get("hostname") == hostname or d.get("address") == hostname), None)
    if not device:
        return {"ok": False, "error": "device_not_found_after_add", "hostname": hostname}

    device_id = device.get("id")

    # Trigger sync for the device
    # Log to stderr so dev console shows the sync attempt
    try:
        print(f"[BE] Rozpoczęto próbę synchronizacji: {hostname}", file=sys.stderr)
        sync_res = run_script("settings-devices_controller", "sync_device", {"id": device_id})
    except Exception as e:
        return {"ok": False, "error": f"sync_failed: {e}", "device": device}

    return {"ok": True, "device": device, "sync": sync_res.get("result")}


@router.post("/devices/add-batch-and-sync")
def devices_add_batch_and_sync(payload: dict):
    """Add multiple devices (by hostname/address) and trigger synchronization for each.

    Payload: { "hostnames": ["h1","h2"] }
    """
    hostnames_raw = payload.get("hostnames") or payload.get("addresses") or payload.get("data") or payload.get("hosts")
    if not hostnames_raw or not isinstance(hostnames_raw, list):
        return {"ok": False, "error": "Missing or invalid host list in payload (expected 'hostnames' or 'addresses')"}

    # Accept list of strings or list of objects { hostname: '', address: '' }
    hostnames = []
    for item in hostnames_raw:
        if isinstance(item, str):
            hostnames.append(item)
        elif isinstance(item, dict):
            hn = item.get("hostname") or item.get("address")
            if hn:
                hostnames.append(hn)
    # Deduplicate while preserving order
    seen = set()
    dedup = []
    for h in hostnames:
        key = (h or "").strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        dedup.append(key)
    hostnames = dedup
    if not hostnames:
        return {"ok": False, "error": "No valid hostnames found in payload"}

    # Try bulk add via controller if available
    try:
        add_res = run_script("settings-devices_controller", "add_devices_bulk", {"addresses": hostnames})
    except Exception:
        # Fallback: call add_device for each hostname
        add_res = {"ok": True}
        for h in hostnames:
            try:
                run_script("settings-devices_controller", "add_device", {"address": h})
            except Exception:
                # continue on individual add errors
                pass

    # Reload devices and map hostnames to ids
    devices_res = run_script("settings-devices_controller", "get_all_devices", {})
    devices_list = devices_res.get("result") or []

    # Build map (case-insensitive) from hostname/address to id
    hostname_to_id = {}
    for d in devices_list:
        hn = d.get("hostname") or d.get("address")
        if hn:
            hostname_to_id[(hn or "").strip().lower()] = d.get("id")

    results = []
    completed = 0
    for h in hostnames:
        key = (h or "").strip().lower()
        device_id = hostname_to_id.get(key)
        if not device_id:
            results.append({"hostname": h, "ok": False, "error": "not_found_after_add"})
            continue
        try:
            print(f"[BE] Rozpoczęto próbę synchronizacji: {h}", file=sys.stderr)
            sync_res = run_script("settings-devices_controller", "sync_device", {"id": device_id})
            results.append({"hostname": h, "ok": True, "sync": sync_res.get("result")})
            completed += 1
        except Exception as e:
            results.append({"hostname": h, "ok": False, "error": str(e)})

    return {"ok": True, "requested": len(hostnames), "completed": completed, "results": results}


@router.delete("/devices/{device_id}")
def devices_delete(device_id: str):
    run_script("settings-devices_controller", "delete_device", {"id": device_id})
    return {"ok": True}


@router.post("/devices/cleanup")
def devices_cleanup(payload: dict):
    status = payload.get("status")
    if status == "ERROR":
        run_script("settings-devices_controller", "deleteAllWithError", {})
    elif status == "UNSYNC":
        run_script("settings-devices_controller", "deleteAllWithUnsync", {})
    return {"ok": True}


@router.post("/devices/{device_id}/sync")
def devices_sync(device_id: str):
    result = run_script("settings-devices_controller", "sync_device", {"id": device_id})
    return result.get("result") or {"ok": True, "id": device_id}


@router.get("/connections")
def connections_list():
    """Return all connections from connections.json."""
    connections_file = Path(__file__).resolve().parents[4] / "apps" / "web" / "src" / "data" / "connections.json"
    if connections_file.exists():
        try:
            data = json.loads(connections_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


@router.post("/connections/sync")
def connections_sync():
    result = run_script("settings-devices_controller", "sync_connections", {})
    return result.get("result") or {"ok": True}


@router.get("/devices/command")
def devices_command_get(device_id: str = None, command: str = None):
    """Execute a command on a specific device and return its output.

    Query parameters:
    - device_id: the device id from `devices.json`
    - command: the command to run (e.g. 'show version')

    The handler will look up the device record and call the controller script to perform the command.
    """
    if not device_id or not command:
        return {"error": "Missing required query parameters: device_id and command"}

    # Load devices from controller and find the requested device
    devices_res = run_script("settings-devices_controller", "get_all_devices", {})
    devices_list = devices_res.get("result") or []
    device = next((d for d in devices_list if d.get("id") == device_id), None)
    if not device:
        return {"error": f"Device not found: {device_id}"}

    payload = {"device": device, "command": command}
    result = run_script("settings-devices_controller", "execute_command_on_device", payload)
    return result.get("result") or {"ok": True}


@router.get("/accounts")
def accounts_list():
    result = run_script("settings-accounts_controller", "get_all_accounts", {})
    return result.get("result") or []


@router.post("/accounts")
def accounts_add(payload: dict):
    run_script("settings-accounts_controller", "add_account", payload)
    return {"ok": True}


@router.delete("/accounts/{account_id}")
def accounts_delete(account_id: str):
    run_script("settings-accounts_controller", "delete_account", {"id": account_id})
    return {"ok": True}


@router.post("/accounts/reorder")
def accounts_reorder(payload: dict):
    accounts = payload.get("accounts", [])
    run_script("settings-accounts_controller", "save_all_accounts", accounts)
    return {"ok": True, "count": len(accounts)}


@router.get("/sites")
def sites_list():
    result = run_script("settings-sites_controller", "get_all_sites", {})
    return result.get("result") or []


@router.post("/sites")
def sites_add(payload: dict):
    run_script("settings-sites_controller", "add_site", payload)
    return {"ok": True}


@router.put("/sites/{site_id}")
def sites_update(site_id: str, payload: dict):
    payload_with_id = payload or {}
    payload_with_id["id"] = site_id
    run_script("settings-sites_controller", "update_site", payload_with_id)
    return {"ok": True}


@router.delete("/sites/{site_id}")
def sites_delete(site_id: str):
    run_script("settings-sites_controller", "delete_site", {"id": site_id})
    return {"ok": True}


@router.post("/sites/reorder")
def sites_reorder(payload: dict):
    sites = payload.get("sites", [])
    run_script("settings-sites_controller", "save_all_sites", sites)
    return {"ok": True, "count": len(sites)}


@router.get("/modules/settings")
def modules_settings_get():
    result = run_script("settings-modules_controller", "load_app_settings", {})
    return result.get("result") or {"cmtsTmpfs": {"hoursBack": 2}}


@router.put("/modules/settings")
def modules_settings_put(payload: dict):
    run_script("settings-modules_controller", "save_app_settings", payload)
    return {"success": True}


@router.post("/system/cleanup")
def system_cleanup():
    run_script("application_controller", "cleanup_temp_folder", {})
    return {"ok": True}


@router.post("/consoles/sessions")
def console_create(payload: dict):
    result = run_script("consoles_controller", "create_session", {"deviceId": payload.get("deviceId")})
    return result.get("result") or {"session_id": "demo", "initial_output": "", "debug_logs": []}


@router.post("/consoles/sessions/command")
def console_command(payload: dict):
    result = run_script("consoles_controller", "send_command_using_session", {
        "device_id": payload.get("deviceId"),
        "command": payload.get("command")
    })
    return result.get("result") or {"success": False, "output": "", "error": ""}


@router.post("/consoles/sessions/close")
def console_close(payload: dict):
    result = run_script("consoles_controller", "close_session", {
        "device_id": payload.get("deviceId")
    })
    return result.get("result") or {"ok": True}


@router.post("/consoles/execute")
def console_execute(payload: dict):
    result = run_script("consoles_controller", "execute_command", {
        "deviceId": payload.get("deviceId"),
        "command": payload.get("command")
    })
    return result.get("result") or {"success": False, "output": "", "error": ""}
