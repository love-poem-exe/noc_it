import sys
import json
import os
from typing import Dict, Optional
import asyncio
import paramiko
import socket
import time
from datetime import datetime
import traceback

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "src/data/accounts.json")
DEVICES_FILE = os.path.join(BASE_DIR, "src/data/devices.json")
TUNNEL_STATUS_FILE = os.path.join(BASE_DIR, "src/data/tunnel_status.json")
SESSIONS_FILE = os.path.join(BASE_DIR, "src/data/sessions.json")
DEBUG_LOG_FILE = os.path.join(BASE_DIR, "src/data/temp/consoles_debug.log")
CACHE_FILE = os.path.join(BASE_DIR, "src/data/temp/sessions_cache.json")

# Utwórz plik logów jeśli nie istnieje
os.makedirs(os.path.dirname(DEBUG_LOG_FILE), exist_ok=True)

# Global dictionary do cache'owania sesji w ramach procesu
_session_cache = {}

def log_debug(message: str):
    """Loguj do pliku i stderr"""
    try:
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
            f.flush()
    except:
        pass
    print(message, file=sys.stderr)

def cache_session(device_id: str, session: 'ConsoleSession'):
    """Cache sesji w pamięci i pliku"""
    _session_cache[device_id] = session
    try:
        cache_data = {"device_id": device_id, "session_id": session.id}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
    except:
        pass

def get_cached_session(device_id: str) -> Optional['ConsoleSession']:
    """Pobierz sesję z cache"""
    return _session_cache.get(device_id)

def remove_cached_session(device_id: str):
    """Usuń sesję z cache"""
    if device_id in _session_cache:
        del _session_cache[device_id]
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
    except:
        pass

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def load_devices():
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def check_tunnel():
    if os.path.exists(TUNNEL_STATUS_FILE):
        try:
            with open(TUNNEL_STATUS_FILE, "r", encoding="utf-8") as f:
                tunnel_data = json.load(f)
                if tunnel_data.get("status") == "CONNECTED":
                    return tunnel_data
        except:
            pass
    return None

def save_session_to_file(session_data):
    try:
        os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
        current_sessions = {}
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                current_sessions = json.load(f)
        current_sessions[session_data["id"]] = session_data
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(current_sessions, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(json.dumps({"error": f"Failed to save session: {str(e)}"}))

def append_output_to_session(session_id: str, output: str):
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                sessions = json.load(f)
            if session_id in sessions:
                sessions[session_id]["output"] += f"\n{output}"
                with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
                    json.dump(sessions, f, indent=2, ensure_ascii=False)
                return True
        return False
    except Exception as e:
        print(json.dumps({"error": f"Failed to append output: {str(e)}"}))
        return False

class ConsoleSession:
    def __init__(self, device_id: str, hostname: str, address: str, vendor: str = ''):
        self.id = f"console_{device_id}_{int(datetime.now().timestamp())}"
        self.device_id = device_id
        self.hostname = hostname
        self.address = address
        self.vendor = vendor.lower() if vendor else ''  # ← Track device vendor
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.shell = None
        self.is_connected = False
        self.buffer = ""
        self.last_activity = time.time()
        self.pre_commands_done = False  # ← Track if pre-commands already sent

    async def read_output(self) -> str:
        if not self.is_connected or not self.shell:
            return ""
            
        output = ""
        try:
            while self.shell.recv_ready():
                char = self.shell.recv(1).decode('utf-8', errors='ignore')
                output += char
                self.buffer += char
                self.last_activity = time.time()
                
            # Zachowaj ostatnie 1000 linii w buforze
            lines = self.buffer.splitlines()
            if len(lines) > 1000:
                self.buffer = '\n'.join(lines[-1000:])
                
        except Exception as e:
            output += f"\nError reading output: {str(e)}"
            
        return output

    async def read_initial_output(self):
        output = ""
        timeout = time.time() + 5  # 5 sekund na odczyt bannera
        while time.time() < timeout:
            if self.shell.recv_ready():
                chunk = self.shell.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                self.buffer += chunk
                timeout = time.time() + 1  # Przedłuż jeśli są dane
            else:
                await asyncio.sleep(0.1)
        return output

    async def send_command(self, command: str) -> str:
        if not self.is_connected:
            return "Not connected"
        
        try:
            def ts():
                now = datetime.now()
                return now.strftime("%H:%M:%S.%f")[:-3]
            
            start_time = time.time()
            log_debug(f"{ts()} [CMD][START] Command: {command}")
            
            # Wyczyść bufor przed wysłaniem komendy
            while self.shell.recv_ready():
                self.shell.recv(8192)
            
            # Wyślij komendy kontrolne TYLKO raz przy pierwszej komendzie
            if not self.pre_commands_done:
                log_debug(f"{ts()} [CMD][PRECONFIG] Sending pagination setup for vendor={self.vendor}...")
                
                if 'juniper' in self.vendor:
                    self.shell.send("set cli screen-length 0\n")
                    await asyncio.sleep(0.05)
                    while self.shell.recv_ready():
                        self.shell.recv(8192)
                else:
                    self.shell.send("terminal length 0\n")
                    await asyncio.sleep(0.05)
                    while self.shell.recv_ready():
                        self.shell.recv(8192)
                
                self.pre_commands_done = True
                log_debug(f"{ts()} [CMD][PRECONFIG_DONE] Pagination setup done")
            
            log_debug(f"{ts()} [CMD][SEND] Sending command to device...")
            self.shell.send(command + "\n")
            log_debug(f"{ts()} [CMD][SENT] Command sent")
            self.last_activity = time.time()
            
            # Czekaj na odpowiedź
            full_output = ""
            await asyncio.sleep(0.02)
            
            max_total_duration = 90  # allow heavy commands to stream output
            initial_wait_timeout = 20  # wait longer for first bytes
            idle_timeout = 6  # tolerate longer pauses between bursts
            
            no_data_count = 0
            recv_count = 0
            last_recv_time = time.time()
            first_recv_time = None
            
            while time.time() - start_time < max_total_duration:
                if self.shell.recv_ready():
                    chunk = self.shell.recv(8192).decode('utf-8', errors='ignore')
                    recv_count += 1
                    if first_recv_time is None:
                        first_recv_time = time.time()
                    
                    elapsed_total = time.time() - start_time
                    elapsed_first = time.time() - first_recv_time if first_recv_time else 0
                    log_debug(f"{ts()} [CMD][RECV#{recv_count}] {len(chunk)} bytes (+{elapsed_first:.3f}s from first chunk, +{elapsed_total:.3f}s total)")
                    
                    full_output += chunk
                    self.buffer += chunk
                    last_recv_time = time.time()
                    no_data_count = 0
                else:
                    if first_recv_time is None:
                        if time.time() - start_time > initial_wait_timeout:
                            log_debug(f"{ts()} [CMD][WAIT_TIMEOUT] No output for {initial_wait_timeout}s - ending")
                            break
                    elif time.time() - last_recv_time > idle_timeout:
                        log_debug(f"{ts()} [CMD][IDLE] No data for {idle_timeout}s - ending")
                        break
                    no_data_count += 1
                    await asyncio.sleep(0.01)
            
            elapsed = time.time() - start_time
            print(f"{ts()} [CMD][DONE] {len(full_output)} bytes in {recv_count} chunks, total {elapsed:.3f}s", file=sys.stderr)
            return full_output
            
        except Exception as e:
            print(f"{ts()} [CMD][ERROR] {str(e)}", file=sys.stderr)
            return f"Error sending command: {str(e)}"
            
            elapsed = time.time() - start_time
            print(f"[CMD][DONE] Total: {len(full_output)} bytes in {recv_count} chunks, took {elapsed:.2f}s", file=sys.stderr)
            return full_output
            
        except Exception as e:
            print(f"[CMD][ERROR] {str(e)}", file=sys.stderr)
            return f"Error sending command: {str(e)}"

    async def keep_alive(self):
        while self.is_connected:
            if time.time() - self.last_activity > 30:  # Co 30 sekund
                try:
                    self.shell.send("\n")  # Wyślij pusty enter
                    self.last_activity = time.time()
                except:
                    self.is_connected = False
                    break
            await asyncio.sleep(5)

    async def connect(self, skip_ping=False):
        def ts():
            now = datetime.now()
            return now.strftime("%H:%M:%S.%f")[:-3]
        
        connect_start_time = time.time()
        debug_logs = []
        debug_logs.append("=== CONNECTION DETAILS ===")
        debug_logs.append(f"{ts()} [CONNECT][START] Starting connection process...")
        log_debug(f"{ts()} [CONNECT][START] Starting connection to device...")
        
        # 1. Sprawdź tunel
        debug_logs.append(f"{ts()} [CONNECT][TUNNEL_CHECK] Checking tunnel status...")
        tunnel_data = check_tunnel()
        if tunnel_data:
            debug_logs.append(f"{ts()} [TUNNEL] Active on port: {tunnel_data.get('port')}")
            debug_logs.append(f"{ts()} [TUNNEL] Will use tunnel for connection")
        else:
            debug_logs.append(f"{ts()} [TUNNEL] Not active, using direct connection")

        # 2. Znajdź urządzenie i jego konto
        debug_logs.append(f"{ts()} [DEVICE][LOAD] Loading device data...")
        devices = load_devices()
        device = next((d for d in devices if d.get("id") == self.device_id), None)
        if not device:
            debug_logs.append(f"{ts()} [ERROR] Device {self.device_id} not found in devices.json")
            return False, debug_logs
            
        debug_logs.append(f"{ts()} [DEVICE] ID: {device.get('id')}")
        debug_logs.append(f"{ts()} [DEVICE] Hostname: {device.get('hostname')}")
        debug_logs.append(f"{ts()} [DEVICE] Address: {device.get('address')}")
        
        # 3. Spróbuj ping aby uzyskać aktualny IP (jeśli hostname != address) - tylko jeśli nie skip_ping
        hostname = device.get('hostname', '')
        original_address = device.get('address', '')
        resolved_address = original_address
        
        if not skip_ping and hostname and hostname != original_address and hostname != "N/A" and not tunnel_data:
            debug_logs.append(f"{ts()} [PING][START] Attempting to resolve hostname: {hostname}")
            ping_result = _ping_and_extract_ip(hostname, debug_logs)
            if ping_result:
                resolved_address = ping_result
                debug_logs.append(f"{ts()} [PING][SUCCESS] Resolved {hostname} → {resolved_address}")
                
                # Aktualizuj adres w devices.json jeśli się zmienił
                if resolved_address != original_address:
                    device["address"] = resolved_address
                    # Zapisz devices.json
                    try:
                        with open(DEVICES_FILE, "w", encoding="utf-8") as f:
                            json.dump(devices, f, indent=2, ensure_ascii=False)
                        debug_logs.append(f"{ts()} [UPDATE] Updated device address: {original_address} → {resolved_address}")
                    except Exception as e:
                        debug_logs.append(f"{ts()} [ERROR] Failed to update device address: {str(e)}")
            else:
                debug_logs.append(f"{ts()} [PING][FAIL] Could not resolve hostname: {hostname}")
                if original_address == "N/A":
                    debug_logs.append(f"{ts()} [ERROR] No valid address available")
                    return False, debug_logs
        
        # Użyj resolved_address dla połączenia
        self.address = resolved_address
        debug_logs.append(f"{ts()} [CONNECT] Will connect to: {self.address}")
            
        account_id = device.get("account")
        if not account_id:
            debug_logs.append(f"{ts()} [ERROR] No account assigned to device")
            return False, debug_logs
            
        # 4. Znajdź dane konta
        debug_logs.append(f"{ts()} [ACCOUNT][LOAD] Loading account data...")
        accounts = load_accounts()
        account = next((a for a in accounts if a.get("id") == account_id), None)
        if not account:
            debug_logs.append(f"{ts()} [ERROR] Account {account_id} not found in accounts.json")
            return False, debug_logs

        debug_logs.append(f"{ts()} [ACCOUNT] ID: {account.get('id')}")
        debug_logs.append(f"{ts()} [ACCOUNT] Login: {account.get('login')}")

        # 4. Próba połączenia
        try:
            debug_logs.append(f"{ts()} [SSH][INIT] Initializing SSH client...")
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if tunnel_data:
                # Połączenie przez tunel - używamy tylko manualnej metody socket
                tunnel_host = "127.0.0.1"
                tunnel_port = int(tunnel_data.get("port", 0))
                debug_logs.append(f"{ts()} [TUNNEL][CONNECT] Connecting to {tunnel_host}:{tunnel_port}...")
                tunnel_socket_start = time.time()
                
                # Utwórz socket i połącz z tunelem
                debug_logs.append(f"{ts()} [TUNNEL][SOCKET] Creating socket for tunnel...")
                sock = socket.create_connection((tunnel_host, tunnel_port), timeout=15)
                tunnel_socket_elapsed = time.time() - tunnel_socket_start
                debug_logs.append(f"{ts()} [TUNNEL][SOCKET_OK] Socket connected successfully (+{tunnel_socket_elapsed:.3f}s)")
                
                tunnel_header = {
                    "target_ip": self.address,
                    "target_port": 22
                }
                debug_logs.append(f"{ts()} [TUNNEL][HEADER] Sending header: {json.dumps(tunnel_header)}")
                header_data = (json.dumps(tunnel_header) + "\n").encode()  # ← DODAJ \n!
                header_send_start = time.time()
                sock.sendall(header_data)
                header_send_elapsed = time.time() - header_send_start
                debug_logs.append(f"{ts()} [TUNNEL][HEADER_OK] Header sent ({len(header_data)} bytes, +{header_send_elapsed:.3f}s)")
                
                # Poczekaj na odpowiedź z tunelu - krótkie sleep jak w devices_controller
                debug_logs.append(f"{ts()} [TUNNEL][WAIT] Waiting for tunnel handshake...")
                time.sleep(0.02)
                debug_logs.append(f"{ts()} [TUNNEL][PROCEED] Proceeding with SSH handshake...")
                
                # Użyj tego socketa do transportu SSH
                debug_logs.append(f"{ts()} [SSH][TRANSPORT] Creating SSH transport...")
                log_debug(f"{ts()} [SSH][TRANSPORT_START] Creating SSH transport over tunnel...")
                ssh_transport_start = time.time()
                transport = paramiko.Transport(sock)
                # Ustaw timeouty - zwiększone dla tunelu
                transport.banner_timeout = 20  # Zwiększone z 10 na 20s dla tunelu
                transport.set_keepalive(30)  # Keep-alive co 30s
                transport.use_compression(True)  # Włącz kompresję
                debug_logs.append(f"{ts()} [SSH][CONFIG] Set banner_timeout=20s, keepalive=30s, compression=True")
                
                log_debug(f"{ts()} [SSH][HANDSHAKE_START] Starting SSH handshake...")
                debug_logs.append(f"{ts()} [SSH][HANDSHAKE] Starting SSH client handshake...")
                handshake_start = time.time()
                transport.start_client()
                handshake_elapsed = time.time() - handshake_start
                log_debug(f"{ts()} [SSH][HANDSHAKE_DONE] SSH handshake done in {handshake_elapsed:.3f}s")
                ssh_handshake_start = time.time()
                
                log_debug(f"{ts()} [SSH][AUTH_START] Authenticating...")
                debug_logs.append(f"{ts()} [SSH][AUTH] Authenticating with password...")
                auth_start = time.time()
                transport.auth_password(
                    username=account["login"],
                    password=account["password"]
                )
                auth_elapsed = time.time() - auth_start
                ssh_auth_elapsed = time.time() - ssh_handshake_start
                log_debug(f"{ts()} [SSH][AUTH_DONE] Auth done in {auth_elapsed:.3f}s")
                debug_logs.append(f"{ts()} [SSH][AUTH_OK] Authentication successful (+{ssh_auth_elapsed:.3f}s)")
                
                log_debug(f"{ts()} [SSH][SHELL_START] Opening shell...")
                debug_logs.append(f"{ts()} [SSH][SHELL] Opening shell session...")
                self.shell = transport.open_session()
                self.shell.get_pty(term='xterm')
                self.shell.invoke_shell()
                ssh_transport_elapsed = time.time() - ssh_transport_start
                debug_logs.append(f"{ts()} [SSH][SHELL_OK] Shell opened successfully (+{ssh_transport_elapsed:.3f}s)")
                
                self.ssh_client._transport = transport  # Zachowaj transport dla późniejszego zamknięcia
                
            else:
                # Bezpośrednie połączenie bez tunelu
                host = self.address
                port = 22
                debug_logs.append(f"{ts()} [SSH][CONNECT] Direct SSH connection to: {host}:{port}")
                direct_ssh_start = time.time()
                
                self.ssh_client.connect(
                    host,
                    port=port,
                    username=account["login"],
                    password=account["password"],
                    timeout=30,  # TCP connect timeout
                    banner_timeout=60,  # Allow more time for SSH banner
                    auth_timeout=30,
                    allow_agent=False,
                    look_for_keys=False
                )
                direct_ssh_elapsed = time.time() - direct_ssh_start
                debug_logs.append(f"{ts()} [SSH][CONNECT_OK] SSH connection successful (+{direct_ssh_elapsed:.3f}s)")
                
                debug_logs.append(f"{ts()} [SSH][SHELL] Opening shell session...")
                self.shell = self.ssh_client.invoke_shell(term='xterm')
                debug_logs.append(f"{ts()} [SSH][SHELL_OK] Shell session opened")
            
            # Odczytaj początkowy output (banner)
            debug_logs.append(f"{ts()} [BANNER][WAIT] Waiting for initial banner...")
            banner_start = time.time()
            initial_output = await self.read_initial_output()
            banner_elapsed = time.time() - banner_start
            debug_logs.append(f"{ts()} [BANNER][RECEIVED] Initial banner received (+{banner_elapsed:.3f}s)")
            
            self.is_connected = True
            connect_elapsed = time.time() - connect_start_time
            debug_logs.append(f"{ts()} [CONNECT][SUCCESS] Connection established (+{connect_elapsed:.3f}s total)")
            debug_logs.append("=== CONNECTION SUCCESSFUL ===")
            debug_logs.append(initial_output)  # Dodaj banner do logów
            log_debug(f"{ts()} [CONNECT][SUCCESS] Connection successful in {connect_elapsed:.3f}s")
            return True, debug_logs
            
        except Exception as e:
            error_elapsed = time.time() - connect_start_time
            debug_logs.append(f"{ts()} [ERROR] Connection failed after {error_elapsed:.3f}s: {str(e)}")
            debug_logs.append(f"{ts()} [ERROR] Details: {traceback.format_exc()}")
            self.is_connected = False
            log_debug(f"{ts()} [ERROR] Connection failed: {str(e)}")
            return False, debug_logs

    def close(self):
        if self.shell:
            self.shell.close()
        if self.ssh_client:
            self.ssh_client.close()
        self.is_connected = False

class ConsolesController:
    def __init__(self):
        self.sessions: Dict[str, ConsoleSession] = {}
        self.device_connections: Dict[str, ConsoleSession] = {}  # device_id -> ConsoleSession (cache)
        self.active_sessions_file = os.path.join(BASE_DIR, "src/data/active_sessions.json")
        self._restore_sessions()

    def _restore_sessions(self):
        # Przywróć sesje z pliku po restarcie backendu (jeśli chcesz)
        if os.path.exists(self.active_sessions_file):
            try:
                with open(self.active_sessions_file, "r", encoding="utf-8") as f:
                    session_list = json.load(f)
                for s in session_list:
                    # Możesz tu dodać logikę odtwarzania sesji jeśli to możliwe
                    pass
            except Exception:
                pass

    def _save_active_sessions(self):
        # Zapisz listę aktywnych sesji do pliku (np. na potrzeby restartu backendu)
        try:
            with open(self.active_sessions_file, "w", encoding="utf-8") as f:
                json.dump(list(self.sessions.keys()), f, indent=2)
        except Exception:
            pass

    async def create_session(self, device_id: str, hostname: str, address: str) -> Optional[str]:
        session = ConsoleSession(device_id, hostname, address)
        success, debug_logs = await session.connect()

        if success:
            self.sessions[session.id] = session
            asyncio.create_task(session.keep_alive())

            # 1. Odczyt banneru (już w debug_logs)
            initial_output = ""
            for log in debug_logs:
                if not log.startswith('[') and not log.startswith('==='):
                    initial_output = log

            # 2. Wyślij polecenie show version
            try:
                version_output = await session.send_command("show version")
            except Exception as e:
                version_output = f"ERROR executing command: {str(e)}"

            # 3. Scal output z bannerem i show version
            full_output = f"{initial_output}\n\nshow version\n{version_output}"

            # 4. Zapisz do pliku
            session_data = {
                "id": session.id,
                "device_id": device_id,
                "hostname": hostname,
                "address": address,
                "created_at": datetime.now().isoformat(),
                "debug_logs": debug_logs,
                "initial_output": initial_output,
                "output": full_output
            }
            save_session_to_file(session_data)

            print(json.dumps({
                "session_id": session.id,
                "debug_logs": debug_logs,
                "initial_output": full_output
            }))
            return session.id

        else:
            print(json.dumps({"error": "Could not establish connection", "debug_logs": debug_logs}))
            return None

    async def send_command_using_session(self, device_id: str, command: str) -> str:
        """Execute command in cached session for device"""
        try:
            def ts():
                now = datetime.now()
                return now.strftime("%H:%M:%S.%f")[:-3]
            
            log_debug(f"{ts()} [SEND_CMD_SESSION][START] Executing command: {command}")
            
            # Szukaj sesji w cache (w pamięci procesu)
            session = get_cached_session(device_id)
            
            if session is None:
                log_debug(f"{ts()} [SEND_CMD_SESSION][ERROR] No cached session for device {device_id}")
                return json.dumps({"success": False, "error": "Session not found"})
            
            if not session.is_connected:
                log_debug(f"{ts()} [SEND_CMD_SESSION][ERROR] Session disconnected")
                remove_cached_session(device_id)
                return json.dumps({"success": False, "error": "Session disconnected"})
            
            start = time.time()
            output = await session.send_command(command)
            elapsed = time.time() - start
            
            log_debug(f"{ts()} [SEND_CMD_SESSION][DONE] Command done in {elapsed:.3f}s")
            
            return json.dumps({"success": True, "output": output})
        except Exception as e:
            log_debug(f"{ts()} [SEND_CMD_SESSION][ERROR] {str(e)}")
            return json.dumps({"success": False, "error": str(e)})




    def close_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id].close()
            del self.sessions[session_id]
            self._save_active_sessions()
            return True
        return False

    def close_all_sessions(self):
        for session_id in list(self.sessions.keys()):
            self.close_session(session_id)
            
        # Also close cached device connections
        for session in self.device_connections.values():
            session.close()
        self.device_connections.clear()
        
        self._save_active_sessions()
        print(json.dumps({"success": True, "message": "All sessions closed"}))

    async def send_command(self, session_id: str, command: str) -> str:
        if session_id not in self.sessions:
            return json.dumps({"success": False, "error": "Session not found"})
        session = self.sessions[session_id]
        try:
            # Wyślij komendę do otwartej sesji (utrzymywanej w pamięci)
            output = await session.send_command(command)
            append_output_to_session(session_id, f"{command}\n{output}")
            # Zwróć tylko nowy output (nie cały bufor)
            return json.dumps({"success": True, "output": output})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    async def create_session(self, device_id: str) -> str:
        """Create a new SSH session for a device and cache it"""
        try:
            def ts():
                now = datetime.now()
                return now.strftime("%H:%M:%S.%f")[:-3]
            
            log_debug(f"{ts()} [CREATE_SESSION][START] Creating session for device={device_id}")
            start_time = time.time()
            
            # Load device data
            devices = load_devices()
            device = next((d for d in devices if d['id'] == device_id), None)
            
            if not device:
                return json.dumps({"success": False, "error": f"Device not found"})
            
            # Check if we already have a cached connection for this device
            if device_id in self.device_connections:
                cached_session = self.device_connections[device_id]
                if cached_session.is_connected:
                    log_debug(f"{ts()} [CREATE_SESSION][REUSE] Reusing cached connection")
                    return json.dumps({
                        "success": True,
                        "session_id": cached_session.id,
                        "message": "Using cached connection"
                    })
                else:
                    del self.device_connections[device_id]
            
            # Create new connection
            hostname = device.get('hostname', 'unknown')
            address = device.get('address', '')
            vendor = device.get('vendor', '')
            
            session = ConsoleSession(device_id, hostname, address, vendor)
            success, debug_logs = await session.connect()
            
            if success:
                # Cache the session
                cache_session(device_id, session)
                self.device_connections[device_id] = session
                self.sessions[session.id] = session
                asyncio.create_task(session.keep_alive())
                
                elapsed = time.time() - start_time
                log_debug(f"{ts()} [CREATE_SESSION][SUCCESS] Session created in {elapsed:.3f}s: {session.id}")
                
                # Read initial banner
                initial_output = ""
                for log in debug_logs:
                    if not log.startswith('[') and not log.startswith('==='):
                        initial_output = log
                
                return json.dumps({
                    "success": True,
                    "session_id": session.id,
                    "initial_output": initial_output,
                    "debug_logs": debug_logs
                })
            else:
                elapsed = time.time() - start_time
                log_debug(f"{ts()} [CREATE_SESSION][FAILED] Failed to create session in {elapsed:.3f}s")
                return json.dumps({
                    "success": False,
                    "error": "Could not establish connection",
                    "debug_logs": debug_logs
                })
                
        except Exception as e:
            log_debug(f"{ts()} [CREATE_SESSION][ERROR] {str(e)}")
            return json.dumps({"success": False, "error": str(e)})

    async def execute_command(self, device_id: str, command: str) -> str:
        """Execute a single command on device - always creates new session"""
        try:
            def ts():
                now = datetime.now()
                return now.strftime("%H:%M:%S.%f")[:-3]
            
            log_debug(f"{ts()} [EXEC][START] Device={device_id}, Command='{command}'")
            start_exec = time.time()
            
            # Load device data
            devices = load_devices()
            device = next((d for d in devices if d['id'] == device_id), None)
            
            if not device:
                return json.dumps({"success": False, "error": f"Device not found"})
            
            if device.get('status') != 'SYNCED':
                return json.dumps({"success": False, "error": f"Device not synchronized. Status: {device.get('status')}"})
            
            # Always create new connection
            log_debug(f"{ts()} [EXEC][NEW] Creating new connection to {device.get('hostname')}")
            hostname = device.get('hostname', 'unknown')
            address = device.get('address', '')
            vendor = device.get('vendor', '')
            
            session = ConsoleSession(device_id, hostname, address, vendor)
            log_debug(f"{ts()} [EXEC][CONNECTING] Starting SSH connection...")
            success, logs = await session.connect(skip_ping=True)
            
            if not success:
                elapsed = time.time() - start_exec
                log_debug(f"{ts()} [EXEC][CONNECT_FAIL] Connection failed after {elapsed:.3f}s")
                return json.dumps({"success": False, "error": "Connection failed"})
            
            log_debug(f"{ts()} [EXEC][CONNECTED] SSH connection established")
            
            # Execute command
            log_debug(f"{ts()} [EXEC][EXECUTING] Sending command...")
            output = await session.send_command(command)
            
            # Close session immediately (no caching)
            session.close()
            log_debug(f"{ts()} [EXEC][CLOSED] Session closed")
            
            elapsed = time.time() - start_exec
            log_debug(f"{ts()} [EXEC][DONE] Total time: {elapsed:.3f}s, output: {len(output)} bytes")
            
            return json.dumps({"success": True, "output": output})
            
        except Exception as e:
            elapsed = time.time() - start_exec
            log_debug(f"{ts()} [EXEC][ERROR] {str(e)} (after {elapsed:.3f}s)")
            return json.dumps({"success": False, "error": str(e)})





    def get_sessions(self):
        try:
            if os.path.exists(SESSIONS_FILE):
                with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
                    response = {
                        "sessions": [
                            {
                                "id": session_id,
                                "deviceName": session_data["hostname"],
                                "output": session_data.get("output", "")
                            }
                            for session_id, session_data in sessions.items()
                        ]
                    }
                    print(json.dumps(response, ensure_ascii=False))
            else:
                print(json.dumps({"sessions": []}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))

    def delete_session(self, session_id: str):
        try:
            if os.path.exists(SESSIONS_FILE):
                with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
                if session_id in sessions:
                    del sessions[session_id]
                    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
                        json.dump(sessions, f, indent=2, ensure_ascii=False)
                    print(json.dumps({"success": True, "message": f"Session {session_id} deleted"}))
                else:
                    print(json.dumps({"success": False, "error": f"Session {session_id} not found"}))
            else:
                print(json.dumps({"success": False, "error": "Sessions file not found"}))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}))

def main():
    try:
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Missing arguments"}))
            return

        method = sys.argv[1]
        payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        controller = ConsolesController()

        if method == "create_session":
            result = asyncio.run(controller.create_session(
                payload["deviceId"]
            ))
            print(result)
        elif method == "close_session":
            # Akceptuj zarówno session_id jak i device_id
            session_id = payload.get("session_id")
            device_id = payload.get("device_id")
            
            if device_id:
                remove_cached_session(device_id)
                success = True
            elif session_id:
                success = controller.close_session(session_id)
            else:
                success = False
            
            print(json.dumps({"success": success}))
        elif method == "send_command":
            result = asyncio.run(controller.send_command(
                payload["session_id"],
                payload["command"]
            ))
            print(result)

        elif method == "send_command_using_session":
            result = asyncio.run(controller.send_command_using_session(
                payload["device_id"],
                payload["command"]
            ))
            print(result)
        elif method == "execute_command":
            result = asyncio.run(controller.execute_command(
                payload["deviceId"],
                payload["command"]
            ))
            print(result)
        elif method == "get_sessions":
            controller.get_sessions()
        elif method == "delete_session":
            controller.delete_session(payload["session_id"])
        elif method == "close_all_sessions":
            controller.close_all_sessions()
        else:
            print(json.dumps({"error": "Unknown method"}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))


def _ping_and_extract_ip(hostname, logs):
    """
    Wykonuje ping do hostname i wyciąga adres IP z odpowiedzi.
    Zwraca IP jako string lub None jeśli nie udało się.
    """
    import subprocess
    import re
    
    try:
        # Windows ping command
        if os.name == 'nt':
            # Windows: ping -n 1 hostname
            cmd = ["ping", "-n", "1", hostname]
        else:
            # Linux/Unix: ping -c 1 hostname
            cmd = ["ping", "-c", "1", hostname]
        
        logs.append(f"[PING][CMD] Executing: {' '.join(cmd)}")
        
        # Uruchom ping z timeoutem 5 sekund
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            output = result.stdout
            logs.append(f"[PING][OUTPUT] Ping successful")
            
            # Szukaj IP w output ping
            # Pattern dla Windows: "Pinging hostname [IP]" lub "Reply from IP:"
            # Pattern dla Linux: "PING hostname (IP)" lub "64 bytes from IP:"
            
            # Uniwersalny pattern dla IPv4
            ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\b'
            
            matches = re.findall(ip_pattern, output)
            if matches:
                # Weź pierwszy znaleziony IP (pomijając 127.x.x.x)
                for ip in matches:
                    if not ip.startswith('127.'):
                        logs.append(f"[PING][EXTRACTED] Found IP: {ip}")
                        return ip
                        
            logs.append(f"[PING][PARSE] No valid IP found in output: {output[:200]}")
        else:
            logs.append(f"[PING][ERROR] Ping failed with code {result.returncode}")
            logs.append(f"[PING][STDERR] {result.stderr[:200]}")
            
    except subprocess.TimeoutExpired:
        logs.append("[PING][TIMEOUT] Ping command timed out after 5 seconds")
    except Exception as e:
        logs.append(f"[PING][EXCEPTION] Error during ping: {str(e)}")
    
    return None


if __name__ == "__main__":
    main()
