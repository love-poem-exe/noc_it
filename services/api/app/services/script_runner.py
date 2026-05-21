import importlib.util
import io
import json
import sys
import threading
import asyncio
from pathlib import Path
from types import ModuleType
from typing import Any


# Thread-local storage so each request captures its own stdout independently.
_thread_local = threading.local()

_SCRIPT_MAP = {
    "application_controller": "apps/web/src/scripts/application_controller.py",
    "consoles_controller": "apps/web/src/scripts/consoles_controller.py",
    "settings-devices_controller": "apps/web/src/scripts/settings/devices_controller.py",
    "settings-accounts_controller": "apps/web/src/scripts/settings/accounts_controller.py",
    "settings-sites_controller": "apps/web/src/scripts/settings/sites_controller.py",
    "settings-tunnel_controller": "apps/web/src/scripts/settings/tunnel_controller.py",
    "settings-modules_controller": "apps/web/src/scripts/settings/modules_controller.py",
    "modules-cmts_tmpfs_controller": "apps/web/src/scripts/modules/cmts_tmpfs_controller.py",
    "modules-console_controller": "apps/web/src/scripts/modules/console_controller.py",
}

_MODULE_CACHE: dict[str, ModuleType] = {}
_MODULE_MTIME: dict[str, float] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_module(script_key: str) -> ModuleType:
    rel_path = _SCRIPT_MAP.get(script_key)
    if not rel_path:
        raise ValueError(f"Unknown script: {script_key}")

    script_path = _repo_root() / rel_path
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    current_mtime = script_path.stat().st_mtime
    cached_mtime = _MODULE_MTIME.get(script_key, -1)

    if script_key in _MODULE_CACHE and current_mtime == cached_mtime:
        return _MODULE_CACHE[script_key]

    spec = importlib.util.spec_from_file_location(script_key, script_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Failed to load spec for {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[script_key] = module
    spec.loader.exec_module(module)
    _MODULE_CACHE[script_key] = module
    _MODULE_MTIME[script_key] = current_mtime
    return module


def _resolve_handler(module: ModuleType, method: str):
    if hasattr(module, "METHODS"):
        methods = getattr(module, "METHODS")
        if isinstance(methods, dict) and method in methods:
            return methods[method]
    if hasattr(module, method):
        return getattr(module, method)
    if hasattr(module, "default"):
        return getattr(module, "default")
    return None


def _run_consoles_controller(module: ModuleType, method: str, payload: dict) -> Any:
    if not hasattr(module, "ConsolesController"):
        return None

    controller = module.ConsolesController()
    if method == "create_session":
        return asyncio.run(controller.create_session(payload.get("deviceId")))
    if method == "send_command_using_session":
        return asyncio.run(controller.send_command_using_session(
            payload.get("device_id"),
            payload.get("command")
        ))
    if method == "execute_command":
        return asyncio.run(controller.execute_command(
            payload.get("deviceId"),
            payload.get("command")
        ))
    if method == "close_session":
        device_id = payload.get("device_id")
        session_id = payload.get("session_id")
        if device_id:
            if hasattr(module, "remove_cached_session"):
                module.remove_cached_session(device_id)
            return {"success": True}
        if session_id:
            return {"success": controller.close_session(session_id)}
        return {"success": False}
    return None


def _try_parse_json(text: str) -> Any:
    if not text:
        return None
    stripped = text.lstrip("\ufeff").strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    obj_start = stripped.find("{")
    obj_end = stripped.rfind("}")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        try:
            return json.loads(stripped[obj_start:obj_end + 1])
        except json.JSONDecodeError:
            pass

    arr_start = stripped.find("[")
    arr_end = stripped.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        try:
            return json.loads(stripped[arr_start:arr_end + 1])
        except json.JSONDecodeError:
            pass

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    candidate = lines[-1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def run_script(script: str, method: str, payload: dict | None = None) -> dict:
    module = _load_module(script)
    handler = _resolve_handler(module, method)
    if not handler:
        if script == "consoles_controller":
            payload = payload or {}
            try:
                result = _run_consoles_controller(module, method, payload)
                return {"ok": True, "result": result, "stdout": ""}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        return {"ok": False, "error": f"Method not found: {method}"}

    payload = payload or {}
    stdout_buf = io.StringIO()

    # Thread-safe stdout capture: monkey-patch sys.stdout for this thread only
    # using thread-local storage so concurrent requests don't interfere.
    _thread_local.stdout_buf = stdout_buf
    old_stdout = sys.stdout

    class _ThreadLocalWriter(io.TextIOBase):
        """Redirects writes to the thread-local buffer if set, else to real stdout."""

        def write(self, s: str) -> int:
            buf = getattr(_thread_local, "stdout_buf", None)
            if buf is not None:
                return buf.write(s)
            return old_stdout.write(s)

        def flush(self) -> None:
            buf = getattr(_thread_local, "stdout_buf", None)
            if buf is not None:
                buf.flush()
            old_stdout.flush()

    sys.stdout = _ThreadLocalWriter()  # type: ignore[assignment]
    try:
        result = handler(payload)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        _thread_local.stdout_buf = None
        sys.stdout = old_stdout

    stdout_text = stdout_buf.getvalue()
    parsed = _try_parse_json(stdout_text)

    if result is not None:
        return {"ok": True, "result": result, "stdout": stdout_text}

    if parsed is not None:
        return {"ok": True, "result": parsed, "stdout": stdout_text}

    return {"ok": True, "result": stdout_text, "stdout": stdout_text}
