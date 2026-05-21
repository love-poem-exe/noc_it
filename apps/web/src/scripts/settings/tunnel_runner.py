import os
import json
import paramiko
import socket
import threading
import random
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
TUNNEL_FILE = os.path.join(BASE_DIR, "src/data/tunnel.json")
TUNNEL_STATUS_FILE = os.path.join(BASE_DIR, "src/data/tunnel_status.json")
LOG_FILE = os.path.join(BASE_DIR, "src/data/temp/tunnel_runner.log")

TUNNELING = False
_ssh_client = None
_active_port = None
_lock = threading.Lock()

def load_config():
    if os.path.exists(TUNNEL_FILE):
        with open(TUNNEL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print("[TunnelRunner] Nie znaleziono pliku tunnel.json.")
        return {}

def save_status(status: dict):
    with open(TUNNEL_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def log(message: str) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass
    print(message)

def create_tunnel():
    global _ssh_client, _active_port, TUNNELING

    config = load_config()
    address = config.get("address")
    login = config.get("login")
    password = config.get("password")
    auth_mode = config.get("authMode")
    key_path = config.get("keyPath")

    # Accept either password-based auth or key-based auth (requires key file present)
    if not address or not login:
        log("[TunnelRunner] Brak wymaganych danych (address/login).")
        save_status({"status": "NOT CONNECTED", "error": "Missing address/login"})
        return

    use_key = (auth_mode == 'key' or (not password and key_path))

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Use explicit connection options to avoid agent lookups and give a sensible timeout
        connect_kwargs = {
            "username": login,
            "timeout": 10,
            "banner_timeout": 10,
            "look_for_keys": False,
            "allow_agent": False,
        }

        if use_key and key_path:
            # Try to locate key in src/data/keys, src/data/temp or use provided path
            possible_paths = [
                os.path.join(BASE_DIR, 'src', 'data', 'keys', key_path),
                os.path.join(BASE_DIR, 'src', 'data', 'temp', key_path),
                key_path
            ]
            loaded_key = None
            for kp in possible_paths:
                try:
                    if not kp or not os.path.exists(kp):
                        continue
                    # Try common key types; first without passphrase, then with passphrase if provided
                    for KeyClass in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey):
                        try:
                            # try without passphrase
                            loaded_key = KeyClass.from_private_key_file(kp)
                            if loaded_key:
                                log(f"[TunnelRunner] Loaded private key from {kp} (no passphrase)")
                                break
                        except Exception:
                            # if password/passphrase is available, try with it
                            if password:
                                try:
                                    loaded_key = KeyClass.from_private_key_file(kp, password=password)
                                    if loaded_key:
                                        log(f"[TunnelRunner] Loaded private key from {kp} using passphrase")
                                        break
                                except Exception:
                                    loaded_key = None
                            else:
                                loaded_key = None
                    if loaded_key:
                        break
                except Exception as e:
                    log(f"[TunnelRunner] Error loading key {kp}: {e}")

            if loaded_key:
                try:
                    client.connect(address, pkey=loaded_key, **connect_kwargs)
                except Exception as e:
                    log(f"[TunnelRunner] SSH connect with key failed: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
            else:
                raise Exception("Private key not found or unsupported format")
        else:
            try:
                client.connect(address, password=password, **connect_kwargs)
            except Exception as e:
                log(f"[TunnelRunner] SSH connect with password failed: {e}")
                import traceback
                traceback.print_exc()
                raise

        _ssh_client = client
        _active_port = random.randint(10000, 60000)
        TUNNELING = True

        log(f"[TunnelRunner] Połączono z {address}")
        log(f"[TunnelRunner] Otwarto tunel lokalny: 127.0.0.1:{_active_port}")

        save_status({
            "status": "CONNECTED",
            "port": _active_port,
            "address": address,
            "login": login
        })

        thread = threading.Thread(
            target=start_forwarding_listener,
            args=(_active_port,),
            daemon=True
        )
        thread.start()

    except Exception as e:
        TUNNELING = False
        log(f"[TunnelRunner] Błąd połączenia: {e}")
        save_status({"status": "NOT CONNECTED", "error": str(e)})

def start_forwarding_listener(local_port):
    try:
        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", local_port))
        server.listen(5)
        log(f"[TunnelRunner] Nasłuchiwanie na localhost:{local_port} – gotowe do proxy")
        log(f"[TunnelRunner] TUNNELING={TUNNELING}")

        while TUNNELING:
            log(f"[TunnelRunner] Waiting for connection...")
            server.settimeout(1.0)  # 1s timeout to check TUNNELING flag
            try:
                client_socket, addr = server.accept()
                log(f"[TunnelRunner] Odebrano połączenie od {addr} – oczekuję danych docelowych")
            except socket.timeout:
                continue  # Check TUNNELING flag again
            
            # Handle connection in separate thread
            threading.Thread(
                target=handle_tunnel_connection,
                args=(client_socket,),
                daemon=True
            ).start()

    except Exception as e:
        print(f"[TunnelRunner] Błąd nasłuchiwania: {e}")
        import traceback
        traceback.print_exc()

def handle_tunnel_connection(client_socket):
    """Handle a single tunnel connection"""
    try:
        log(f"[TunnelRunner] Handling connection, reading header...")
        # Czekamy na dane docelowe od klienta (własny protokół - json linii)
        header_line = ""
        while not header_line.endswith("\n"):
            chunk = client_socket.recv(1)
            if not chunk:
                raise Exception("Connection closed before header")
            header_line += chunk.decode()
        
        target_info = json.loads(header_line.strip())
        target_ip = target_info.get("target_ip")
        target_port = int(target_info.get("target_port", 22))
        log(f"[TunnelRunner] Przekierowuję do {target_ip}:{target_port}")
    except Exception as e:
        log(f"[TunnelRunner] Błąd odczytu danych docelowych: {e}")
        import traceback
        traceback.print_exc()
        client_socket.close()
        return

    try:
        chan = _ssh_client.get_transport().open_channel(
            "direct-tcpip",
            (target_ip, target_port),
            client_socket.getsockname()
        )
        log(f"[TunnelRunner] SSH channel opened to {target_ip}:{target_port}")

        def forward_data(src, dst, direction):
            """Forward data from src to dst"""
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        log(f"[TunnelRunner] {direction} EOF")
                        break
                    dst.sendall(data)
            except Exception as e:
                    log(f"[TunnelRunner] {direction} pipe error: {e}")
            finally:
                try:
                    src.shutdown(socket.SHUT_RD)
                except:
                    pass
                try:
                    dst.shutdown(socket.SHUT_WR)
                except:
                    pass

        # Dwa wątki dla dwukierunkowego przekazywania
        t1 = threading.Thread(
            target=forward_data, 
            args=(client_socket, chan, "client->remote"),
            daemon=True
        )
        t2 = threading.Thread(
            target=forward_data,
            args=(chan, client_socket, "remote->client"),
            daemon=True
        )
        t1.start()
        t2.start()
        log(f"[TunnelRunner] Forwarding threads started")

    except Exception as e:
        log(f"[TunnelRunner] Błąd tunelowania: {e}")
        import traceback
        traceback.print_exc()
        client_socket.close()

if __name__ == "__main__":
    log("[TunnelRunner] Uruchamiam tunel...")
    create_tunnel()
    log("[TunnelRunner] Tunel działa. Wszystkie połączenia kieruj na localhost:<port z tunnel_status.json>")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("[TunnelRunner] Przerwano.")
        save_status({"status": "NOT CONNECTED"})
