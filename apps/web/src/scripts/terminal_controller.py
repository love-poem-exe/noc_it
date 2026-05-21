#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terminal Controller - zarządzanie sesjami SSH dla terminala
"""

import sys
import json
import os
import paramiko
import socket
from datetime import datetime
from typing import Dict, Optional

# Ścieżki
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DATA_DIR = os.path.join(BASE_DIR, "src/data")

# Aktywne sesje SSH
active_sessions: Dict[str, paramiko.SSHClient] = {}
active_channels: Dict[str, paramiko.Channel] = {}


def load_json_file(filename):
    """Wczytaj plik JSON z katalogu data"""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def create_terminal_session(payload):
    """
    Tworzy sesję terminala SSH
    Payload: {"deviceId": str, "hostname": str, "address": str, "port": int}
    """
    try:
        device_id = payload.get("deviceId")
        hostname = payload.get("hostname")
        address = payload.get("address")
        port = payload.get("port", 22)
        
        # Wczytaj urządzenie
        devices = load_json_file("devices.json") or []
        device = next((d for d in devices if d["id"] == device_id), None)
        if not device:
            return {"success": False, "error": f"Device not found: {device_id}"}
        
        # Wczytaj konto
        accounts = load_json_file("accounts.json") or []
        account = next((a for a in accounts if a["id"] == device["account"]), None)
        if not account:
            return {"success": False, "error": f"Account not found: {device['account']}"}
        
        # Sprawdź czy tunel jest aktywny
        tunnel_status = load_json_file("tunnel_status.json")
        use_tunnel = tunnel_status and tunnel_status.get("status") == "CONNECTED"
        
        # Parametry połączenia
        if use_tunnel:
            connect_host = "127.0.0.1"
            connect_port = tunnel_status.get("port")
            print(f"[TERMINAL] Using tunnel: {connect_host}:{connect_port}", file=sys.stderr)
        else:
            connect_host = address
            connect_port = port
            print(f"[TERMINAL] Direct connection: {connect_host}:{connect_port}", file=sys.stderr)
        
        # Utwórz klienta SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"[TERMINAL] Connecting to {connect_host}:{connect_port} as {account['login']}", file=sys.stderr)
        
        # Jeśli używamy tunelu, musimy wysłać header z informacją o docelowym urządzeniu
        if use_tunnel:
            print(f"[TERMINAL] Setting up tunnel proxy for {address}:22", file=sys.stderr)
            
            # Utwórz surowy socket do tunelu
            tunnel_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tunnel_sock.settimeout(10)

            # Spróbuj nawiązać połączenie z tunelem z retry/backoff
            max_attempts = 3
            attempt = 0
            connected = False
            while attempt < max_attempts and not connected:
                try:
                    attempt += 1
                    print(f"[TERMINAL] Connecting to tunnel at {connect_host}:{connect_port} (attempt {attempt})", file=sys.stderr)
                    tunnel_sock.connect((connect_host, connect_port))
                    connected = True
                    print(f"[TERMINAL] Connected to tunnel", file=sys.stderr)
                except Exception as conn_err:
                    print(f"[TERMINAL] Tunnel connect attempt {attempt} failed: {str(conn_err)}", file=sys.stderr)
                    import time
                    time.sleep(0.5 * attempt)

            if not connected:
                # Nie można połączyć się z tunelem — zamykamy socket i przechodzimy do połączenia bez tunelu
                try:
                    tunnel_sock.close()
                except:
                    pass
                print(f"[TERMINAL] Tunnel unavailable, falling back to direct connection to {address}:22", file=sys.stderr)
                use_tunnel = False
                connect_host = address
                connect_port = 22
            
            else:
                # Wyślij header z docelowym hostem (protokół tunelu)
                target_info = json.dumps({
                    "target_ip": address,
                    "target_port": 22
                })
                header = f"{target_info}\n"
                print(f"[TERMINAL] Sending tunnel header: {header.strip()}", file=sys.stderr)
                tunnel_sock.sendall(header.encode('utf-8'))
                print(f"[TERMINAL] Header sent", file=sys.stderr)

                # Krótkie opóźnienie aby tunel zdążył otworzyć kanał (jak w devices_controller.py)
                import time
                time.sleep(0.02)

                print(f"[TERMINAL] Starting SSH handshake using Transport (devices_controller method)", file=sys.stderr)

                # Użyj Transport bezpośrednio (jak w devices_controller.py - działa!)
                transport = paramiko.Transport(tunnel_sock)
                transport.banner_timeout = 20
                transport.set_keepalive(30)
                transport.use_compression(True)
                print(f"[TERMINAL] Transport configured", file=sys.stderr)

                transport.start_client()
                print(f"[TERMINAL] Transport started, authenticating", file=sys.stderr)

                transport.auth_password(account["login"], account["password"])
            print(f"[TERMINAL] Authentication successful", file=sys.stderr)
            
            # Przypisz Transport do SSHClient (dla kompatybilności z resztą kodu)
            ssh._transport = transport
        else:
            # Bezpośrednie połączenie
            ssh.connect(
                hostname=connect_host,
                port=connect_port,
                username=account["login"],
                password=account["password"],
                timeout=15,
                banner_timeout=10,
                auth_timeout=10,
                look_for_keys=False,
                allow_agent=False
            )
        
        # Otwórz kanał shell
        channel = ssh.invoke_shell(term="xterm", width=80, height=24)
        channel.settimeout(0.1)  # Non-blocking reads
        
        print(f"[TERMINAL] Channel opened for {hostname}", file=sys.stderr)
        
        # Wygeneruj session_id (używamy device_id jako klucza)
        session_id = f"terminal_{device_id}_{int(datetime.now().timestamp() * 1000)}"
        
        # Zapisz sesję
        active_sessions[session_id] = ssh
        active_channels[session_id] = channel
        
        # Odczytaj banner
        import time
        time.sleep(0.5)  # Czekaj na banner
        banner = ""
        try:
            while channel.recv_ready():
                chunk = channel.recv(4096).decode('utf-8', errors='ignore')
                banner += chunk
        except:
            pass
        
        return {
            "success": True,
            "sessionId": session_id,
            "hostname": hostname,
            "address": address,
            "login": account["login"],
            "useTunnel": use_tunnel,
            "banner": banner
        }
        
    except Exception as e:
        print(f"[TERMINAL] Error creating session: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {"success": False, "error": str(e)}


def send_terminal_command(payload):
    """
    Wysyła komendę do sesji terminala i zwraca output
    Payload: {"sessionId": str, "command": str}
    """
    try:
        session_id = payload.get("sessionId")
        command = payload.get("command")
        
        if session_id not in active_channels:
            return {"success": False, "error": "Session not found"}
        
        channel = active_channels[session_id]
        
        # Wyślij komendę
        channel.send(command + "\n")
        
        # Czekaj na output (max 5 sekund)
        import time
        output = ""
        max_wait = 5
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if channel.recv_ready():
                chunk = channel.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                # Jeśli znaleziono prompt (heurystyka), zakończ
                if '#' in chunk or '>' in chunk:
                    time.sleep(0.1)  # Krótkie opóźnienie aby upewnić się że wszystko przyszło
                    # Zbierz resztę
                    while channel.recv_ready():
                        output += channel.recv(4096).decode('utf-8', errors='ignore')
                    break
            time.sleep(0.05)
        
        return {
            "success": True,
            "output": output
        }
        
    except Exception as e:
        print(f"[TERMINAL] Error sending command: {str(e)}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def close_terminal_session(payload):
    """
    Zamyka sesję terminala
    Payload: {"sessionId": str}
    """
    try:
        session_id = payload.get("sessionId")
        
        if session_id in active_channels:
            channel = active_channels[session_id]
            channel.close()
            del active_channels[session_id]
        
        if session_id in active_sessions:
            ssh = active_sessions[session_id]
            ssh.close()
            del active_sessions[session_id]
        
        return {"success": True}
        
    except Exception as e:
        print(f"[TERMINAL] Error closing session: {str(e)}", file=sys.stderr)
        return {"success": False, "error": str(e)}


# Mapa metod
METHODS = {
    "create_terminal_session": create_terminal_session,
    "send_terminal_command": send_terminal_command,
    "close_terminal_session": close_terminal_session,
}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: terminal_controller.py <method> <payload_json>"}))
        sys.exit(1)
    
    method = sys.argv[1]
    payload_json = sys.argv[2]
    
    try:
        payload = json.loads(payload_json)
    except:
        payload = {}
    
    if method not in METHODS:
        print(json.dumps({"error": f"Unknown method: {method}"}))
        sys.exit(1)
    
    result = METHODS[method](payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
