"""
Shared utilities for Python scripts.

Consolidates duplicated helper functions previously copy-pasted across
devices_controller, cmts_tmpfs_controller, accounts_controller, and terminal_server.

Usage from any script:
    from shared.script_utils import (
        BASE_DIR, DEVICES_FILE, ACCOUNTS_FILE, TUNNEL_STATUS_FILE,
        load_devices, save_devices, load_accounts, save_accounts,
        is_ip_address, read_full_output, resolve_tunnel_target,
        reconfigure_utf8_stdout,
    )
"""

import json
import os
import re
import sys
import time


# ── Paths ────────────────────────────────────────────────────────────────

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DEVICES_FILE = os.path.join(BASE_DIR, "src/data/devices.json")
ACCOUNTS_FILE = os.path.join(BASE_DIR, "src/data/accounts.json")
TUNNEL_STATUS_FILE = os.path.join(BASE_DIR, "src/data/tunnel_status.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "src/data/settings.json")


# ── UTF-8 stdout ─────────────────────────────────────────────────────────

def reconfigure_utf8_stdout():
    """Force UTF-8 encoding on sys.stdout (idempotent)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    else:
        import codecs
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)


# ── Data loading / saving ────────────────────────────────────────────────

def load_json_file(path, fallback=None):
    """Load a JSON file, returning *fallback* (default []) on any error."""
    if fallback is None:
        fallback = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return fallback
    return fallback


def save_json_file(path, data):
    """Atomically write *data* as pretty-printed JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_devices():
    return load_json_file(DEVICES_FILE, [])


def save_devices(devices):
    save_json_file(DEVICES_FILE, devices)


def load_accounts():
    return load_json_file(ACCOUNTS_FILE, [])


def save_accounts(accounts):
    save_json_file(ACCOUNTS_FILE, accounts)


def load_settings():
    return load_json_file(SETTINGS_FILE, {})


# ── IP utilities ─────────────────────────────────────────────────────────

_IP_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


def is_ip_address(value):
    """Return True if *value* looks like a dotted-quad IPv4 address."""
    return bool(_IP_PATTERN.match(value)) if value else False


def resolve_tunnel_target(hostname, address):
    """Pick the best target for a tunnel header — prefer DNS hostname over raw IP."""
    if hostname and not is_ip_address(hostname):
        return hostname
    if address:
        return address
    return hostname or ""


# ── SSH output reading ───────────────────────────────────────────────────

def read_full_output(
    session,
    logs,
    *,
    total_timeout=10,
    idle_timeout=2,
    wait_for_prompt=False,
    stream_lines=False,
    recv_size=8192,
):
    """
    Read all available output from a paramiko channel.

    Parameters
    ----------
    session : paramiko.Channel
        The SSH channel to read from.
    logs : list[str]
        Diagnostic messages appended here.
    total_timeout : float
        Hard cap in seconds.
    idle_timeout : float
        Max seconds since last data before giving up.
    wait_for_prompt : bool
        If True, stop early when a line ending in '#' is detected.
    stream_lines : bool
        If True, print each complete line as ``{"output": ...}`` JSON
        immediately (useful for streaming to frontend).
    recv_size : int
        Bytes per recv() call.

    Returns
    -------
    str
        The full collected output.
    """
    start_time = time.time()
    last_read = time.time()
    output = ""
    line_buf = ""

    while True:
        # Prompt detection
        if wait_for_prompt and any(
            ln.strip().endswith("#") for ln in output.split("\n") if ln.strip()
        ):
            logs.append("[SSH] Prompt '#' detected")
            break

        if time.time() - start_time > total_timeout:
            logs.append(f"[SSH] total_timeout={total_timeout}s exceeded")
            break

        if session.recv_ready():
            try:
                chunk = session.recv(recv_size).decode(errors="ignore")
            except Exception as exc:
                logs.append(f"[SSH] recv error: {exc}")
                chunk = ""

            output += chunk
            last_read = time.time()

            if stream_lines:
                line_buf += chunk
                if "\n" in line_buf:
                    parts = line_buf.split("\n")
                    for part in parts[:-1]:
                        print(json.dumps({"output": part}, ensure_ascii=False))
                        sys.stdout.flush()
                    line_buf = parts[-1]
            continue

        if time.time() - last_read > idle_timeout:
            logs.append(f"[SSH] idle > {idle_timeout}s — done reading")
            break

        time.sleep(0.05)

    # Flush remaining streamed buffer
    if stream_lines and line_buf.strip():
        print(json.dumps({"output": line_buf}, ensure_ascii=False))
        sys.stdout.flush()

    return output
