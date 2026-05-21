#!/usr/bin/env python3
"""
SSH Gateway — asynchroniczny serwer WebSocket zarządzający sesjami SSH.

Uruchomienie:
    python ssh_gateway.py [--port 3001]

Protokół WebSocket (JSON):
    → { action: "connect",    deviceId, hostname, address, port? }
    ← { type: "connected",    sessionId, hostname, address, login, useTunnel, banner }
    ← { type: "error",        message }

    → { action: "command",    sessionId, command }
    ← { type: "output",       sessionId, data }

    → { action: "disconnect", sessionId }
    ← { type: "disconnected", sessionId }

    ← { type: "output",       sessionId, data }   — streaming chunks (asynchronous)
"""

import argparse
import asyncio
import json
import logging
import os
import socket
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import paramiko

try:
    import websockets
    from websockets.asyncio.server import serve as ws_serve
except ImportError:
    print("FATAL: 'websockets' package is required. Install with: pip install websockets", file=sys.stderr)
    sys.exit(1)

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2] / "apps" / "web"
DATA_DIR = BASE_DIR / "src" / "data"
SESSIONS_DIR = DATA_DIR / "terminal_sessions"

LOG = logging.getLogger("ssh_gateway")

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_json(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_tunnel_info():
    """Return (host, port) for tunnel proxy if active, else None."""
    status = _load_json("tunnel_status.json")
    if status and status.get("status") == "CONNECTED":
        port = status.get("port")
        if port:
            return ("127.0.0.1", int(port))
    return None


def _is_ip_address(value: str) -> bool:
    """Check if value is an IP address."""
    try:
        socket.inet_aton(value)
        return True
    except (socket.error, OSError):
        return False


_INVALID_HOSTNAMES = {"unknown", "none", "n/a", "localhost", ""}


def _pick_tunnel_target(hostname: str, address: str) -> str:
    """Choose target_ip for tunnel header.
    Prefer DNS hostname over raw IP — the tunnel proxy resolves internally.
    """
    if hostname and not _is_ip_address(hostname) and hostname.lower() not in _INVALID_HOSTNAMES and len(hostname) >= 2:
        return hostname
    if address and address.strip():
        return address
    return hostname


# ─── Session ──────────────────────────────────────────────────────────────────

@dataclass
class SSHSession:
    session_id: str
    device_id: str
    hostname: str
    address: str
    login: str
    use_tunnel: bool
    ssh_client: paramiko.SSHClient
    channel: paramiko.Channel
    created_at: float = field(default_factory=time.time)
    output_buffer: str = ""


# ─── Session Manager ─────────────────────────────────────────────────────────

class SessionManager:
    """Manages SSH sessions and their lifecycle."""

    def __init__(self):
        self._sessions: dict[str, SSHSession] = {}
        self._reader_tasks: dict[str, asyncio.Task] = {}

    @property
    def sessions(self):
        return self._sessions

    async def create_session(self, device_id: str, hostname: str, address: str, port: int = 22) -> SSHSession:
        """Open SSH connection and interactive shell, return SSHSession."""

        # Load device & account
        devices = _load_json("devices.json") or []
        device = next((d for d in devices if d["id"] == device_id), None)
        if not device:
            raise ValueError(f"Device not found: {device_id}")

        accounts = _load_json("accounts.json") or []
        account = next((a for a in accounts if a["id"] == device.get("account")), None)
        if not account:
            raise ValueError(f"Account not found for device: {device_id}")

        login = account["login"]
        password = account["password"]

        # Determine connection target
        tunnel_info = _get_tunnel_info()
        use_tunnel = False

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if tunnel_info:
            t_host, t_port = tunnel_info

            # Verify tunnel reachability first (like devices_controller)
            reachable = await asyncio.to_thread(self._check_tunnel_reachable, t_host, t_port)

            if reachable:
                target_ip = _pick_tunnel_target(hostname, address)
                try:
                    transport = await asyncio.to_thread(
                        self._create_tunnel_transport, t_host, t_port, target_ip, login, password
                    )
                    ssh._transport = transport
                    use_tunnel = True
                    LOG.info("Connected via tunnel to %s (target: %s)", hostname, target_ip)
                except Exception as e:
                    LOG.warning("Tunnel failed for %s: %s — falling back to direct", hostname, e)
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    await asyncio.to_thread(
                        ssh.connect,
                        hostname=address, port=port,
                        username=login, password=password,
                        timeout=15, banner_timeout=10, auth_timeout=10,
                        look_for_keys=False, allow_agent=False,
                    )
                    LOG.info("Connected directly to %s", hostname)
            else:
                LOG.warning("Tunnel port %d unreachable — connecting directly to %s", t_port, hostname)
                await asyncio.to_thread(
                    ssh.connect,
                    hostname=address, port=port,
                    username=login, password=password,
                    timeout=15, banner_timeout=10, auth_timeout=10,
                    look_for_keys=False, allow_agent=False,
                )
                LOG.info("Connected directly to %s", hostname)
        else:
            await asyncio.to_thread(
                ssh.connect,
                hostname=address, port=port,
                username=login, password=password,
                timeout=15, banner_timeout=10, auth_timeout=10,
                look_for_keys=False, allow_agent=False,
            )
            LOG.info("Connected directly to %s", hostname)

        # Open interactive shell
        channel = ssh.invoke_shell(term="xterm", width=120, height=40)
        channel.settimeout(0.1)

        # Read initial banner
        banner = await asyncio.to_thread(self._read_banner, channel)

        session_id = f"ssh_{device_id}_{uuid.uuid4().hex[:8]}"
        session = SSHSession(
            session_id=session_id,
            device_id=device_id,
            hostname=hostname,
            address=address,
            login=login,
            use_tunnel=use_tunnel,
            ssh_client=ssh,
            channel=channel,
            output_buffer=banner,
        )
        self._sessions[session_id] = session
        LOG.info("Session %s created for %s (%s)", session_id, hostname, address)
        return session

    def _check_tunnel_reachable(self, host: str, port: int, attempts: int = 3) -> bool:
        """Verify tunnel port is accepting connections (blocking)."""
        for attempt in range(attempts):
            try:
                test_sock = socket.create_connection((host, port), timeout=1)
                test_sock.close()
                return True
            except Exception:
                time.sleep(0.05)
        return False

    def _create_tunnel_transport(self, t_host, t_port, target_ip, login, password) -> paramiko.Transport:
        """Create SSH transport through tunnel (blocking, run via to_thread)."""
        sock = socket.create_connection((t_host, t_port), timeout=3)

        # Send tunnel header with target (hostname preferred over IP)
        header = json.dumps({"target_ip": target_ip, "target_port": 22}) + "\n"
        sock.sendall(header.encode("utf-8"))
        time.sleep(0.02)

        transport = paramiko.Transport(sock)
        transport.banner_timeout = 15
        transport.set_keepalive(30)
        transport.use_compression(True)
        transport.start_client()
        transport.auth_password(login, password)

        if not transport.is_authenticated():
            raise Exception("Authentication failed through tunnel")

        return transport

    def _read_banner(self, channel: paramiko.Channel, timeout: float = 2.0) -> str:
        """Read initial banner/prompt (blocking)."""
        banner = ""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if channel.recv_ready():
                chunk = channel.recv(4096).decode("utf-8", errors="ignore")
                banner += chunk
                deadline = time.time() + 0.5  # extend if data still coming
            else:
                time.sleep(0.05)
        return banner

    async def send_command(self, session_id: str, command: str):
        """Send command to session channel. Output is streamed asynchronously."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        await asyncio.to_thread(session.channel.send, command + "\n")

    async def send_raw(self, session_id: str, data: str):
        """Send raw data to session channel (no newline appended)."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        await asyncio.to_thread(session.channel.send, data)

    async def read_output(self, session_id: str) -> Optional[str]:
        """Non-blocking read of any available output from channel."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        return await asyncio.to_thread(self._read_available, session.channel)

    def _read_available(self, channel: paramiko.Channel) -> str:
        """Read all available data from channel (blocking but fast)."""
        output = ""
        try:
            while channel.recv_ready():
                chunk = channel.recv(4096).decode("utf-8", errors="ignore")
                output += chunk
        except Exception:
            pass
        return output

    async def close_session(self, session_id: str):
        """Close SSH session and clean up."""
        # Stop reader task if exists
        task = self._reader_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        session = self._sessions.pop(session_id, None)
        if not session:
            return

        # Save session history
        await asyncio.to_thread(self._save_history, session)

        try:
            session.channel.close()
        except Exception:
            pass
        try:
            session.ssh_client.close()
        except Exception:
            pass
        LOG.info("Session %s closed", session_id)

    def _save_history(self, session: SSHSession):
        """Save session output to file."""
        try:
            SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(session.created_at))
            filename = f"{session.hostname}_{ts}_{session.session_id[-8:]}.log"
            path = SESSIONS_DIR / filename
            path.write_text(session.output_buffer, encoding="utf-8")
            LOG.info("History saved: %s", path)
        except Exception as e:
            LOG.error("Failed to save history for %s: %s", session.session_id, e)

    def start_reader(self, session_id: str, send_callback):
        """Start background task that streams SSH output to WebSocket."""
        if session_id in self._reader_tasks:
            return

        async def reader_loop():
            session = self._sessions.get(session_id)
            if not session:
                return
            try:
                while session_id in self._sessions:
                    output = await asyncio.to_thread(self._read_available, session.channel)
                    if output:
                        session.output_buffer += output
                        try:
                            await send_callback(json.dumps({
                                "type": "output",
                                "sessionId": session_id,
                                "data": output,
                            }))
                        except Exception:
                            break
                    # Check if channel is closed
                    if session.channel.closed or session.channel.exit_status_ready():
                        try:
                            await send_callback(json.dumps({
                                "type": "disconnected",
                                "sessionId": session_id,
                                "reason": "channel_closed",
                            }))
                        except Exception:
                            pass
                        break
                    await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                LOG.error("Reader error for %s: %s", session_id, e)

        self._reader_tasks[session_id] = asyncio.create_task(reader_loop())

    async def close_all(self):
        """Close all sessions (for graceful shutdown)."""
        for sid in list(self._sessions.keys()):
            await self.close_session(sid)


# ─── WebSocket Handler ────────────────────────────────────────────────────────

manager = SessionManager()


async def handle_client(websocket):
    """Handle a single WebSocket client connection."""
    client_sessions: list[str] = []  # Track sessions opened by this client
    LOG.info("Client connected: %s", websocket.remote_address)

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            action = msg.get("action")

            if action == "connect":
                await _handle_connect(websocket, msg, client_sessions)

            elif action == "command":
                await _handle_command(websocket, msg)

            elif action == "input":
                await _handle_input(websocket, msg)

            elif action == "disconnect":
                await _handle_disconnect(websocket, msg, client_sessions)

            elif action == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

            else:
                await websocket.send(json.dumps({"type": "error", "message": f"Unknown action: {action}"}))

    except websockets.exceptions.ConnectionClosed:
        LOG.info("Client disconnected")
    except Exception as e:
        LOG.error("Client handler error: %s", e)
    finally:
        # Clean up all sessions opened by this client
        for sid in client_sessions:
            await manager.close_session(sid)
        LOG.info("Client cleanup done (%d sessions closed)", len(client_sessions))


async def _handle_connect(ws, msg, client_sessions):
    device_id = msg.get("deviceId")
    hostname = msg.get("hostname", "")
    address = msg.get("address", "")
    port = msg.get("port", 22)

    if not device_id:
        await ws.send(json.dumps({"type": "error", "message": "Missing deviceId"}))
        return

    try:
        session = await manager.create_session(device_id, hostname, address, port)
        client_sessions.append(session.session_id)

        await ws.send(json.dumps({
            "type": "connected",
            "sessionId": session.session_id,
            "hostname": session.hostname,
            "address": session.address,
            "login": session.login,
            "useTunnel": session.use_tunnel,
            "banner": session.output_buffer,
        }))

        # Start streaming output in background
        manager.start_reader(session.session_id, ws.send)

    except Exception as e:
        LOG.error("Connect failed for %s: %s", hostname or device_id, e)
        await ws.send(json.dumps({
            "type": "error",
            "message": str(e),
            "deviceId": device_id,
        }))


async def _handle_command(ws, msg):
    session_id = msg.get("sessionId")
    command = msg.get("command", "")

    if not session_id:
        await ws.send(json.dumps({"type": "error", "message": "Missing sessionId"}))
        return

    try:
        await manager.send_command(session_id, command)
    except Exception as e:
        await ws.send(json.dumps({
            "type": "error",
            "message": str(e),
            "sessionId": session_id,
        }))


async def _handle_input(ws, msg):
    """Handle raw input — send characters to SSH channel without newline."""
    session_id = msg.get("sessionId")
    data = msg.get("data", "")

    if not session_id:
        await ws.send(json.dumps({"type": "error", "message": "Missing sessionId"}))
        return

    try:
        await manager.send_raw(session_id, data)
    except Exception as e:
        await ws.send(json.dumps({
            "type": "error",
            "message": str(e),
            "sessionId": session_id,
        }))


async def _handle_disconnect(ws, msg, client_sessions):
    session_id = msg.get("sessionId")
    if not session_id:
        return

    await manager.close_session(session_id)
    if session_id in client_sessions:
        client_sessions.remove(session_id)

    await ws.send(json.dumps({
        "type": "disconnected",
        "sessionId": session_id,
    }))


# ─── Idle session cleanup ────────────────────────────────────────────────────

async def cleanup_idle_sessions(timeout_minutes: int = 30):
    """Periodically close sessions that have been idle too long."""
    while True:
        await asyncio.sleep(60)
        now = time.time()
        threshold = timeout_minutes * 60
        for sid, session in list(manager.sessions.items()):
            if now - session.created_at > threshold:
                LOG.info("Closing idle session: %s (age: %dm)", sid, int((now - session.created_at) / 60))
                await manager.close_session(sid)


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main(host: str = "0.0.0.0", port: int = 3001):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy paramiko logs
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("paramiko.transport").setLevel(logging.WARNING)

    LOG.info("SSH Gateway starting on ws://%s:%d", host, port)

    # Start cleanup task
    asyncio.create_task(cleanup_idle_sessions())

    async with ws_serve(handle_client, host, port):
        LOG.info("SSH Gateway ready — accepting connections")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SSH Gateway WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=3001, help="Port (default: 3001)")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        LOG.info("SSH Gateway stopped")
