import sys
import os
import json
import subprocess
import traceback
import socket
import time
import signal

# Force UTF-8 for stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
else:
    import codecs
    # Only wrap stdout.buffer when it's available (not a StringIO)
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    else:
        # Running in an environment where sys.stdout is a text stream (e.g. StringIO)
        # leaving sys.stdout as-is avoids AttributeError while still preserving behaviour.
        pass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
TUNNEL_FILE = os.path.join(BASE_DIR, "src/data/tunnel.json")
TUNNEL_STATUS_FILE = os.path.join(BASE_DIR, "src/data/tunnel_status.json")
TUNNEL_PID_FILE = os.path.join(BASE_DIR, "src/data/tunnel_pid.json")


def save_tunnel(payload):
    try:
        print("[TunnelController] Zapisuje dane do tunnel.json")
        with open(TUNNEL_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print("[TunnelController] Zapis zakonczony")
    except Exception as e:
        print(f"[TunnelController] Blad zapisu: {str(e)}")
        print(f"[TunnelController] Szczegoly: {traceback.format_exc()}")


def get_tunnel(_=None):
    if os.path.exists(TUNNEL_FILE):
        with open(TUNNEL_FILE, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print(json.dumps({"address": "", "login": "", "password": ""}))


def get_status(_=None):
    if os.path.exists(TUNNEL_STATUS_FILE):
        try:
            with open(TUNNEL_STATUS_FILE, "r", encoding="utf-8") as f:
                print(f.read())
        except Exception as e:
            print(json.dumps({"status": "NOT CONNECTED", "error": str(e)}))
    else:
        print(json.dumps({"status": "NOT CONNECTED"}))


def get_status_fast(_=None):
    """Alias for get_status — kept for backward compatibility with API routes."""
    get_status(_)


def is_connected():
    if os.path.exists(TUNNEL_STATUS_FILE):
        try:
            with open(TUNNEL_STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("status") == "CONNECTED"
        except:
            return False
    return False


def check_tunnel_status(_=None):
    """Sprawdza stan tunelu i zwraca komunikat tekstowy"""
    try:
        if os.path.exists(TUNNEL_STATUS_FILE):
            with open(TUNNEL_STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                status = data.get("status")
                port = data.get("port")
                
                # Tunel jest OK jeśli status to CONNECTED
                if status == "CONNECTED":
                    # Dodatkowa weryfikacja: sprawdzenie czy port nasłuchuje
                    if port:
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(1)
                            result = sock.connect_ex(('127.0.0.1', int(port)))
                            sock.close()
                            
                            if result == 0:
                                # Port nasłuchuje - tunel działa
                                print(f"✅ Tunel OK - port {port} nasłuchuje")
                                return True
                            else:
                                # Port nie nasłuchuje - tunel upadł mimo że status mówi CONNECTED
                                print(f"⚠️ Tunel upadł - port {port} nie nasłuchuje. Uruchamiam ponownie...")
                                
                                # Uruchom tunel ponownie
                                runner_path = os.path.join(BASE_DIR, "src/scripts/settings/tunnel_runner.py")
                                subprocess.Popen(
                                    ["python", runner_path],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL
                                )
                                
                                # Czekaj aż tunel się podłączy
                                time.sleep(3)
                                
                                # Odczytaj nowy status z pliku
                                if os.path.exists(TUNNEL_STATUS_FILE):
                                    with open(TUNNEL_STATUS_FILE, "r", encoding="utf-8") as f2:
                                        new_data = json.load(f2)
                                        new_status = new_data.get("status")
                                        new_port = new_data.get("port")
                                        
                                        if new_status == "CONNECTED" and new_port:
                                            print(f"✅ Tunel ponownie uruchomiony - nowy port: {new_port}")
                                            return True
                                        else:
                                            print(f"❌ Nie udało się przywrócić tunelu")
                                            return False
                                else:
                                    print(f"❌ Plik statusu tunelu zniknął")
                                    return False
                        except Exception as e:
                            print(f"⚠️ Błąd weryfikacji portu: {str(e)}")
                            return False
                    else:
                        # Status CONNECTED ale brak portu - coś nie gra
                        print("❌ Status CONNECTED ale brak informacji o porcie")
                        return False
                else:
                    print(f"❌ Tunel rozłączony (status: {status})")
                    return False
        else:
            print("❌ Plik statusu tunelu nie istnieje")
            return False
    except Exception as e:
        print(f"⚠️ Błąd sprawdzania stanu tunelu: {str(e)}")
        return False


def connect(_=None):
    try:
        runner_path = os.path.join(BASE_DIR, "src/scripts/settings/tunnel_runner.py")
        print(f"[TunnelController] Próba uruchomienia: {runner_path}")

        process = subprocess.Popen(
            ["python", runner_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Zapisz PID procesu
        try:
            with open(TUNNEL_PID_FILE, "w", encoding="utf-8") as f:
                json.dump({"pid": process.pid}, f, ensure_ascii=False, indent=2)
            print(f"[TunnelController] Zapisano PID procesu: {process.pid}")
        except Exception as e:
            print(f"[TunnelController] Błąd zapisywania PID: {str(e)}")

        print("[TunnelController] tunnel_runner.py uruchomiony.")
    except Exception as e:
        print("[TunnelController] Błąd uruchamiania tunnel_runner.py:", e)


def disconnect(_=None):
    try:
        if os.path.exists(TUNNEL_STATUS_FILE):
            with open(TUNNEL_STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump({"status": "NOT CONNECTED"}, f, ensure_ascii=False, indent=2)
            print("[TunnelController] Tunel oznaczony jako rozłączony.")
        else:
            print("[TunnelController] Plik statusu nie istnieje.")
    except Exception as e:
        print("[TunnelController] Błąd przy rozłączaniu:", e)


def close_tunnel(_=None):
    """Zamyka tunel manualnie - zatrzymuje tunnel_runner i aktualizuje status"""
    try:
        print("[TunnelController] Zamykanie tunelu...")
        
        # Spróbuj zabić proces tunnel_runner po PID
        try:
            if os.path.exists(TUNNEL_PID_FILE):
                with open(TUNNEL_PID_FILE, "r", encoding="utf-8") as f:
                    pid_data = json.load(f)
                    pid = pid_data.get("pid")
                    
                    if pid:
                        if os.name == 'nt':  # Windows
                            subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                         capture_output=True)
                        else:  # Linux/Mac
                            import signal
                            os.kill(pid, signal.SIGTERM)
                        
                        print(f"[TunnelController] Proces tunnel_runner (PID {pid}) zatrzymany")
                        
                        # Usuń plik PID
                        try:
                            os.remove(TUNNEL_PID_FILE)
                        except:
                            pass
                    else:
                        print("[TunnelController] PID nie znaleziony w pliku")
            else:
                print("[TunnelController] Plik PID nie istnieje")
        except Exception as e:
            print(f"[TunnelController] Nie udało się zabić procesu: {str(e)}")
        
        # Aktualizuj status
        if os.path.exists(TUNNEL_STATUS_FILE):
            with open(TUNNEL_STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump({"status": "NOT CONNECTED"}, f, ensure_ascii=False, indent=2)
        
        print("✅ Tunel zamknięty pomyślnie")
    except Exception as e:
        print(f"❌ Błąd zamykania tunelu: {str(e)}")



def toggle_tunnel(_=None):
    import time
    try:
        if is_connected():
            # Rozłącz tunel
            if os.path.exists(TUNNEL_STATUS_FILE):
                with open(TUNNEL_STATUS_FILE, "w", encoding="utf-8") as f:
                    json.dump({"status": "NOT CONNECTED"}, f, ensure_ascii=False, indent=2)
        else:
            # Połącz tunel
            runner_path = os.path.join(BASE_DIR, "src/scripts/settings/tunnel_runner.py")
            subprocess.Popen(
                ["python", runner_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # ⭐ WAŻNE: Czekaj aż tunnel_runner.py zdąży się połączyć i zapisać status!
            # tunnel_runner.py potrzebuje ~2-5 sekund aby:
            # 1. Załadować konfigurację
            # 2. Nawiązać SSH
            # 3. Otworzyć socket
            # 4. Zapisać status CONNECTED
            time.sleep(3)
        
        # Zwróć aktualny status jako JSON (bez logów!)
        if os.path.exists(TUNNEL_STATUS_FILE):
            with open(TUNNEL_STATUS_FILE, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print(json.dumps({"status": "NOT CONNECTED"}))
    except Exception as e:
        print(json.dumps({"status": "NOT CONNECTED", "error": str(e)}))


def init_tunnel_status(_=None):
    """Inicjalizuj tunnel_status.json na NOT CONNECTED przy starcie aplikacji"""
    try:
        initial_status = {"status": "NOT CONNECTED"}
        with open(TUNNEL_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(initial_status, f, ensure_ascii=False, indent=2)
        print("[TunnelController] tunnel_status.json initialized to NOT CONNECTED")
        print(json.dumps(initial_status))
    except Exception as e:
        print(f"[TunnelController] Błąd inicjalizacji tunnel_status: {str(e)}")
        print(json.dumps({"status": "NOT CONNECTED", "error": str(e)}))


def default(_=None):
    print("Nieznana metoda.")


if __name__ == "__main__":
    method = sys.argv[1] if len(sys.argv) > 1 else "default"
    raw_payload = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        payload = {}

    func = globals().get(method)
    if callable(func):
        func(payload)
    else:
        default(payload)
