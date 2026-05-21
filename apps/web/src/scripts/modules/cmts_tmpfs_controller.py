import json
import os
import sys
import time
import io
import re

# ——————————————————————————————————————————————————————————————————————
# Wymuśmy UTF-8 na stdout, żeby nie było UnicodeEncodeError przy drukowaniu nie-ASCII znaków
if hasattr(sys.stdout, "reconfigure"):
    # dla Pythona ≥3.7
    sys.stdout.reconfigure(encoding="utf-8")
else:
    os.environ["PYTHONIOENCODING"] = "utf-8"
# ——————————————————————————————————————————————————————————————————————

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DEVICES_FILE       = os.path.join(BASE_DIR, "src/data/devices.json")
ACCOUNTS_FILE      = os.path.join(BASE_DIR, "src/data/accounts.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "src/data/settings.json")
TEMP_TMPFS_FILE = os.path.join(BASE_DIR, "src/data/temp/temp_module_tmpfs.json")

def _load_app_settings():
    """Wczytuje ustawienia aplikacji"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings
        else:
            # Domyślne ustawienia
            return {
                "cmtsTmpfs": {
                    "hoursBack": 2
                },
                "general": {
                    "autoRefresh": True,
                    "debugMode": False
                }
            }
    except Exception as e:
        print(f"[APP SETTINGS] Error loading settings: {e}, using defaults")
        return {
            "cmtsTmpfs": {
                "hoursBack": 2
            },
            "general": {
                "autoRefresh": True,
                "debugMode": False
            }
        }


def save_settings(payload):
    """Zapisuje ustawienia aplikacji do settings.json. Oczekuje payload w formacie
    { "cmtsTmpfs": { "hoursBack": 12 }, ... }
    """
    try:
        settings = _load_app_settings() or {}
        # Merge provided settings
        if not isinstance(payload, dict):
            print(json.dumps({"status": "ERROR", "message": "Invalid payload"}, ensure_ascii=False))
            return

        for key, val in payload.items():
            if isinstance(val, dict):
                settings.setdefault(key, {})
                settings[key].update(val)
            else:
                settings[key] = val

        # Ensure directory exists
        settings_dir = os.path.dirname(SETTINGS_FILE)
        if settings_dir and not os.path.exists(settings_dir):
            os.makedirs(settings_dir, exist_ok=True)

        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

        print(json.dumps({"status": "OK", "message": "Settings saved"}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False))


def _open_device_session(device, logs):
    """
    Otwiera sesję SSH do urządzenia przez terminal_controller (z sys.modules).
    Zwraca (session_id, channel) lub rzuca wyjątek.
    """
    tc = sys.modules.get("terminal_controller")
    if not tc:
        raise Exception("terminal_controller module not available in sys.modules")

    result = tc.create_terminal_session({
        "deviceId": device.get("id"),
        "hostname": device.get("hostname"),
        "address": device.get("address"),
    })

    if not result.get("success"):
        raise Exception(result.get("error", "create_terminal_session failed"))

    session_id = result["sessionId"]
    channel = tc.active_channels.get(session_id)
    if not channel:
        raise Exception(f"Channel not found for session {session_id}")

    logs.append(f"[TERMINAL API] Session {session_id} opened for {device.get('hostname')} (tunnel={result.get('useTunnel', False)})")
    return session_id, channel


def _close_device_session(session_id, logs):
    """Zamyka sesję SSH przez terminal_controller."""
    tc = sys.modules.get("terminal_controller")
    if tc:
        tc.close_terminal_session({"sessionId": session_id})
        logs.append(f"[TERMINAL API] Session {session_id} closed")


def _exec_command_via_devices_controller(device, command, logs):
    """Wykonuje komendę przez settings-devices_controller.execute_command_on_device (wykorzystywane przez API).
    Przechwytuje stdout (gdzie skrypt wypisuje JSON) i zwraca surowy output tekstowy.
    """
    # Prefer using the API handler if available (simulates calling POST /api/devices/command)
    try:
        routes_mod = sys.modules.get("services.api.app.api.routes")
        if routes_mod and hasattr(routes_mod, "devices_command"):
            try:
                payload = {"device": device, "command": command}
                res = routes_mod.devices_command(payload)
                logs.append(f"[DEVICES API] devices_command handler returned type={type(res)}")
                # If handler returned a dict-like result, try to extract output/logs
                if isinstance(res, dict):
                    out = res.get("output") if res.get("output") is not None else json.dumps(res, ensure_ascii=False)
                    cmd_logs = res.get("logs", []) if isinstance(res.get("logs", []), list) else []
                    return out, cmd_logs
                else:
                    return str(res), []
            except Exception as e:
                logs.append(f"[DEVICES API] devices_command handler error: {e}")
                # fall through to fallback
    except Exception:
        pass

    # Fallback: call settings-devices_controller.execute_command_on_device and capture stdout
    mod = sys.modules.get("settings-devices_controller")
    if not mod or not hasattr(mod, "execute_command_on_device"):
        raise Exception("settings-devices_controller module not available")

    buf = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buf
        # execute_command_on_device drukuje wynik jako json na stdout
        mod.execute_command_on_device({"device": device, "command": command})
    finally:
        sys.stdout = old_stdout

    out = buf.getvalue()
    logs.append(f"[DEVICES API] execute_command_on_device returned {len(out)} bytes (fallback)")

    # Spróbuj wyciągnąć JSON z outputu (najpierw najdłuższy obiekt {})
    m = re.search(r"\{[\s\S]*\}", out)
    if m:
        try:
            parsed = json.loads(m.group(0))
            # Prefer 'output' key
            if isinstance(parsed, dict) and "output" in parsed:
                return parsed.get("output", ""), parsed.get("logs", [])
        except Exception:
            pass

    return out, []


def verify_tmpfs_alarms(payload):
    """Weryfikuje alarmy TMPFS z konfigurowalnej liczby godzin wstecz"""
    device_hostnames = payload.get("devices", [])
    logs = []
    results = {}
    
    if not device_hostnames:
        print(json.dumps({"error": "Brak urządzeń do sprawdzenia"}, ensure_ascii=False))
        return
    
    # Wczytaj ustawienia aplikacji
    app_settings = _load_app_settings()
    hours_back = app_settings.get("cmtsTmpfs", {}).get("hoursBack", 2)
    
    # Pobierz aktualną datę i czas
    from datetime import datetime, timedelta
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(hours=hours_back)
    
    logs.append(f"[TMPFS VERIFICATION] Starting TMPFS alarm verification for {len(device_hostnames)} devices")
    logs.append(f"[TMPFS VERIFICATION] Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logs.append(f"[TMPFS VERIFICATION] Using {hours_back}h lookback period")
    logs.append(f"[TMPFS VERIFICATION] Filtering alarms from: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Wczytaj urządzenia i konta
    devices = _load_devices()
    accounts = _load_accounts()
    
    logs.append(f"[TMPFS VERIFICATION] Loaded {len(devices)} devices from devices.json")
    logs.append(f"[TMPFS VERIFICATION] Loaded {len(accounts)} accounts from accounts.json")
    
    # Debug: sprawdź pierwsze kilka urządzeń
    if devices:
        logs.append(f"[TMPFS VERIFICATION] First device example: {devices[0].get('hostname', 'NO_HOSTNAME')}")
    
    for hostname in device_hostnames:
        logs.append(f"[TMPFS VERIFICATION] Processing device: {hostname}")
        device_result = {
            "hostname": hostname,
            "status": "FAILED",
            "tmpfs_logs": "",
            "filtered_alarms": [],
            "alarm_count": 0,
            "error": None
        }
        
        # Znajdź urządzenie w devices.json - tylko dokładne dopasowanie
        device = None
        hostname_lower = hostname.lower().strip()
        
        for d in devices:
            device_hostname = d.get("hostname", "").lower().strip()
            device_address = d.get("address", "").lower().strip()
            device_name = d.get("name", "").lower().strip()
            
            # Sprawdź tylko dokładne dopasowanie
            if (device_hostname == hostname_lower or 
                device_address == hostname_lower or 
                device_name == hostname_lower):
                device = d
                logs.append(f"[TMPFS VERIFICATION] Found exact match for {hostname}: {device_hostname}")
                break
        
        if not device:
            # Dodaj więcej szczegółów w błędzie
            available_devices = [d.get("hostname", "N/A") for d in devices[:5]]  # Pierwsze 5 dla przykładu
            device_result["error"] = f"Urządzenie '{hostname}' nie znalezione w devices.json. Przykładowe dostępne urządzenia: {', '.join(available_devices)}"
            results[hostname] = device_result
            logs.append(f"[TMPFS VERIFICATION] Device {hostname} not found in devices.json ({len(devices)} devices available)")
            continue
        
        if device.get("status") != "SYNCED":
            device_result["error"] = f"Urządzenie nie jest zsynchronizowane (status: {device.get('status')})"
            results[hostname] = device_result
            logs.append(f"[TMPFS VERIFICATION] Device {hostname} not synced")
            continue
        
        account_id = device.get("account")
        if not account_id:
            device_result["error"] = "Brak przypisanego konta"
            results[hostname] = device_result
            logs.append(f"[TMPFS VERIFICATION] Device {hostname} has no account assigned")
            continue
        
        # Znajdź konto
        account = next((a for a in accounts if a.get("id") == account_id), None)
        if not account:
            device_result["error"] = "Nie znaleziono konta w accounts.json"
            results[hostname] = device_result
            logs.append(f"[TMPFS VERIFICATION] Account {account_id} not found")
            continue
        
        # Wykonaj połączenie SSH przez terminal_controller API i pobierz logi TMPFS
        session_id = None
        try:
            # Wykonaj komendę przez settings-devices_controller (API-like)
            # devices_controller already sends 'terminal length 0' and 'set cli screen-length 0',
            # so send only the actual show command to avoid duplicate/invalid input.
            combined_cmd = "show log | include TMPFS\n"
            logs.append(f"[TMPFS VERIFICATION] Executing via devices controller")
            raw_output, cmd_logs = _exec_command_via_devices_controller(device, combined_cmd, logs)
            logs.extend(cmd_logs or [])
            # Print input and output to stderr for visibility
            try:
                print(f"[BE] INPUT: {combined_cmd}", file=sys.stderr, flush=True)
                print(f"[BE] OUTPUT: {raw_output}", file=sys.stderr, flush=True)
            except Exception:
                pass
            logs.append(f"[TMPFS VERIFICATION] Received {len(raw_output)} bytes from {hostname}")
            
            # Parsuj i filtruj alarmy - zachowaj tylko te z okresu hours_back wstecz
            filtered_alarms = []
            all_lines = raw_output.strip().split('\n')
            
            # Pobierz aktualny rok (alarmy nie zawierają roku, zakładamy bieżący rok)
            current_year = datetime.now().year
            
            # Śledź ostatnią widzianą datę/godzinę - jeśli spadnie, przeszliśmy do poprzedniego roku
            last_alarm_datetime = None
            year_boundary_crossed = False  # Flaga że przeszliśmy granicę roku
            
            for line in all_lines:
                line = line.strip()
                if line and "TMPFS" in line and "WARNING" in line:
                    # Wyciągnij timestamp z linii (format: Feb 12 05:46:03.775)
                    time_match = re.search(r'(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})', line)
                    if time_match:
                        month_str = time_match.group(1)
                        day = int(time_match.group(2))
                        hour = int(time_match.group(3))
                        minute = int(time_match.group(4))
                        second = int(time_match.group(5))
                        
                        try:
                            # Mapowanie miesięcy
                            months = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                            }
                            month = months.get(month_str, 0)
                            
                            if month == 0:
                                continue  # Nieznany miesiąc, pomiń
                            
                            # Stwórz obiekt datetime dla alarmu
                            # Jeśli alarm ma miesiąc < bieżący, to znaczy że jest z tego samego roku
                            # Jeśli alarm ma miesiąc > bieżący, to znaczy że jest z zeszłego roku (np. Dec gdy teraz Jan)
                            alarm_year = current_year
                            if month > cutoff_time.month:
                                # Alarm ma miesiąc większy (np. Dec gdy teraz Jest Jan) - z zeszłego roku
                                alarm_year = current_year - 1
                            
                            try:
                                alarm_datetime = datetime(alarm_year, month, day, hour, minute, second)
                            except ValueError:
                                # Nieprawidłowa data (np. 30 lutego), pomiń
                                logs.append(f"[TMPFS VERIFICATION] Invalid date format on {hostname}: {month_str} {day}")
                                continue
                            
                            # Sprawdź czy ta data spadła w stosunku do poprzedniej
                            # Jeśli tak, to znaczy że przeszliśmy do poprzedniego roku - WYCZYŚĆ poprzednie alarmy
                            if last_alarm_datetime is not None and alarm_datetime < last_alarm_datetime:
                                logs.append(f"[TMPFS VERIFICATION] DateTime dropped from {last_alarm_datetime.strftime('%Y-%m-%d %H:%M')} to {alarm_datetime.strftime('%Y-%m-%d %H:%M')} - year boundary crossed, clearing previous alarms")
                                filtered_alarms = []  # Wyczyść wszystkie poprzednie alarmy
                                year_boundary_crossed = True
                            
                            last_alarm_datetime = alarm_datetime
                            
                            # Sprawdź czy alarm jest z ostatnich godzin (tylko jeśli jesteśmy w bieżącym roku)
                            if alarm_datetime >= cutoff_time:
                                filtered_alarms.append(line)
                                logs.append(f"[TMPFS VERIFICATION] Added alarm from {hostname}: {month_str} {day} {hour}:{minute:02d}")
                            elif not year_boundary_crossed:
                                # Alarm starszy niż cutoff i nie przeszliśmy jeszcze granicy roku
                                # TO ZNACZY ŻE WSZYSTKIE WCZEŚNIEJSZE ALARMY SĄ ZBYT STARE - WYCZYŚĆ
                                logs.append(f"[TMPFS VERIFICATION] Alarm older than cutoff ({alarm_datetime.strftime('%Y-%m-%d %H:%M')} < {cutoff_time.strftime('%Y-%m-%d %H:%M')}), all previous alarms are too old, clearing")
                                filtered_alarms = []  # Wyczyść listę - wszystkie poprzednie alarmy są za stare
                            else:
                                # Przeszliśmy granicę roku - dodaj wszystkie alarmy z następnego roku (starszego)
                                filtered_alarms.append(line)
                                logs.append(f"[TMPFS VERIFICATION] Added alarm after year boundary from {hostname}: {month_str} {day} {hour}:{minute:02d}")
                            
                        except Exception as e:
                            # Jeśli nie udało się sparsować, dodaj alarm anyway
                            logs.append(f"[TMPFS VERIFICATION] Parse error for {hostname}: {e}, adding alarm anyway")
                            filtered_alarms.append(line)
                    else:
                        # Nie udało się wyciągnąć timestamp, ale linia ma TMPFS WARNING - dodaj ją
                        filtered_alarms.append(line)
                        logs.append(f"[TMPFS VERIFICATION] Could not parse timestamp but adding alarm from {hostname}")
            
            # Po przetworzeniu wszystkich alarmów, wyczyść z listy wszystkie alarmy starsze niż cutoff_time
            # Iteruj od końca aby wyfiltrować alarmy ze starego okresu
            final_filtered = []
            for alarm in filtered_alarms:
                time_match = re.search(r'(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})', alarm)
                if time_match:
                    month_str = time_match.group(1)
                    day = int(time_match.group(2))
                    hour = int(time_match.group(3))
                    minute = int(time_match.group(4))
                    second = int(time_match.group(5))
                    
                    months = {
                        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                    }
                    month = months.get(month_str, 0)
                    
                    if month > 0:
                        try:
                            alarm_datetime = datetime(current_year, month, day, hour, minute, second)
                            if alarm_datetime >= cutoff_time:
                                final_filtered.append(alarm)
                        except ValueError:
                            pass
                else:
                    final_filtered.append(alarm)
            
            filtered_alarms = final_filtered
            
            device_result["status"] = "SUCCESS"
            device_result["tmpfs_logs"] = raw_output.strip()
            device_result["filtered_alarms"] = filtered_alarms
            device_result["alarm_count"] = len(filtered_alarms)
            
            # Wyciągnij karty SIP z alarmów
            sip_cards = set()
            for alarm in filtered_alarms:
                # Szukamy wzorca SIP/X gdzie X to numer karty
                sip_match = re.search(r'SIP/(\d+)', alarm)
                if sip_match:
                    sip_cards.add(f"SIP/{sip_match.group(1)}")
            
            device_result["sip_cards"] = sorted(list(sip_cards))
            
            logs.append(f"[TMPFS VERIFICATION] Found {len(filtered_alarms)} TMPFS alarms on {hostname} from last {hours_back} hours")
            if sip_cards:
                logs.append(f"[TMPFS VERIFICATION] Affected SIP cards on {hostname}: {', '.join(sorted(sip_cards))}")
            
            # 🔥 Nie wypisuj debug prints - powodują dodatkowe eventy! Zostaw w logs dla finału
            # print(f"\n=== TMPFS ALARMY dla {hostname} ===")
            # print(f"Zakres czasowy: ostatnie {hours_back} godzin")
            # print(f"Od: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
            # print(f"Do: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            # print(f"Znaleziono: {len(filtered_alarms)} alarmów\n")
            
            # if filtered_alarms:
            #     for i, alarm in enumerate(filtered_alarms, 1):
            #         # Wyciągnij datę i kartę SIP z alarmu
            #         time_match = re.search(r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\.\d+):', alarm)
            #         sip_match = re.search(r'(SIP/\d+)', alarm)
            #         
            #         timestamp = time_match.group(1) if time_match else "UNKNOWN"
            #         sip_card = sip_match.group(1) if sip_match else "UNKNOWN"
            #         
            #         print(f"{i}. {timestamp}: {sip_card}")
            #     
            #     if sip_cards:
            #         print(f"\nDotknięte karty SIP: {', '.join(sorted(sip_cards))}")
            # else:
            #     print(f"Brak alarmów TMPFS z ostatnich {hours_back} godzin")
            # print(f"=== KONIEC ALARMÓW dla {hostname} ({len(filtered_alarms)} znalezionych) ===\n")
            
        except Exception as e:
            device_result["error"] = str(e)
            logs.append(f"[TMPFS VERIFICATION] Error processing {hostname}: {e}")
            if session_id:
                _close_device_session(session_id, logs)

        results[hostname] = device_result
    
    # Zwróć wyniki
    response = {
        "results": results,
        "logs": logs,
        "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "filter_from": cutoff_time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print(json.dumps(response, ensure_ascii=False))
    return response


def _read_full_output(session, logs, wait_for_prompt=False):
    """
    Odczytuje cały dostępny output z sesji SSH, aż:
      - jeśli wait_for_prompt=True: czeka na prompt '#' na linii samodzielnie (po komendzie)
      - jeśli wait_for_prompt=False: przekroczony zostanie maksymalny czas lub idle_timeout
    Zwraca zebrany ciąg znaków.
    """
    start_time = time.time()
    last_read = time.time()
    total_timeout = 30
    idle_timeout = 8
    output = ""

    while True:
        # Jeśli czekamy na prompt, sprawdź czy się pojawił
        if wait_for_prompt:
            lines = output.split('\n')
            # Szukamy linii z promptem - hostname# lub samo #
            for line in lines:
                stripped = line.strip()
                # Prompt kończy się na '#' (z opcjonalnymi spacjami przed)
                if stripped.endswith('#'):
                    logs.append(f"[SSH] Znaleziono prompt '#': '{stripped}'")
                    break
            
            # Jeśli znaleziono prompt, wyjdź
            if any(line.strip().endswith('#') for line in lines):
                break

        if time.time() - start_time > total_timeout:
            logs.append(f"[SSH] Przekroczono total_timeout={total_timeout}s, przerywamy odczyt")
            break

        if session.recv_ready():
            try:
                chunk = session.recv(8192).decode(errors="ignore")
            except Exception as e_recv:
                logs.append(f"[SSH] Błąd podczas recv: {e_recv}")
                chunk = ""
            output += chunk
            logs.append(f"[SSH] Odebrano fragment o długości={len(chunk)}")
            last_read = time.time()
            continue

        if time.time() - last_read > idle_timeout:
            if wait_for_prompt:
                logs.append(f"[SSH] Od ostatniego odczytu minęło >{idle_timeout}s (czekamy na prompt)")
            else:
                logs.append(f"[SSH] Od ostatniego odczytu minęło >{idle_timeout}s, zakładamy, że już nic nie przyjdzie")
            break

        time.sleep(0.1)

    return output


def _load_devices():
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, "r", encoding="utf-8") as f:
                devices = json.load(f)
                return devices
        except json.JSONDecodeError as e:
            return []
    return []


def _load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def default(_=None):
    print("Nieznana metoda.", file=sys.stderr)

def get_settings(payload):
    """Pobiera ustawienia aplikacji"""
    try:
        settings = _load_app_settings()
        print(json.dumps(settings, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False))

def save_table_data(payload):
    """Zapisuje dane tabeli TMPFS do pliku temp"""
    try:
        table_data = payload.get("tableData", [])
        
        # Przygotuj dane do zapisania
        data_to_save = {
            "timestamp": payload.get("timestamp"),
            "data": table_data
        }
        
        # Upewnij się, że katalog temp istnieje
        temp_dir = os.path.dirname(TEMP_TMPFS_FILE)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Zapisz dane
        with open(TEMP_TMPFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        print(json.dumps({"status": "OK", "message": "Table data saved successfully"}, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False))

def load_table_data(payload):
    """Wczytuje dane tabeli TMPFS z pliku temp"""
    try:
        if os.path.exists(TEMP_TMPFS_FILE):
            with open(TEMP_TMPFS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if data and data.get("data") and len(data.get("data", [])) > 0:
                print(json.dumps({
                    "status": "OK", 
                    "data": data.get("data", []),
                    "timestamp": data.get("timestamp"),
                    "count": len(data.get("data", []))
                }, ensure_ascii=False))
            else:
                print(json.dumps({"status": "EMPTY", "message": "No data found in temp file"}, ensure_ascii=False))
        else:
            print(json.dumps({"status": "NOT_FOUND", "message": "Temp file does not exist"}, ensure_ascii=False))
            
    except Exception as e:
        print(json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False))

def clear_table_data(payload):
    """Usuwa dane tabeli TMPFS z pliku temp"""
    try:
        if os.path.exists(TEMP_TMPFS_FILE):
            os.remove(TEMP_TMPFS_FILE)
            print(json.dumps({"status": "OK", "message": "Table data cleared successfully"}, ensure_ascii=False))
        else:
            print(json.dumps({"status": "OK", "message": "No temp file to clear"}, ensure_ascii=False))
            
    except Exception as e:
        print(json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False))


def _load_temp_table_data():
    if os.path.exists(TEMP_TMPFS_FILE):
        try:
            with open(TEMP_TMPFS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and isinstance(data.get("data"), list):
                    return data.get("data")
        except Exception:
            return []
    return []


def _find_device_exact(devices, hostname):
    if not hostname:
        return None
    hostname_lower = hostname.lower().strip()
    for d in devices:
        device_hostname = d.get("hostname", "").lower().strip()
        device_address = d.get("address", "").lower().strip()
        device_name = d.get("name", "").lower().strip()
        if device_hostname == hostname_lower or device_address == hostname_lower or device_name == hostname_lower:
            return d
    return None


def _extract_target_slots(alarms_text):
    if not alarms_text:
        return []
    return list({match.group(1) for match in re.finditer(r"SIP/(\d+)", alarms_text)})


def _extract_slot_states(raw_output, target_slots):
    try:
        lines = raw_output.split("\n")
        slot_states = {}
        in_slot_section = False

        for line in lines:
            if "Slot" in line and "Type" in line and "State" in line:
                in_slot_section = True
                continue

            if "CPLD Version" in line or "-----" in line:
                if "CPLD Version" in line:
                    in_slot_section = False
                continue

            if in_slot_section and line.strip():
                parts = line.strip().split()
                if len(parts) >= 3:
                    slot = parts[0]
                    state = parts[2]

                    if target_slots:
                        for target in target_slots:
                            if slot == target or slot.startswith(target + "/") or target.startswith(slot + "/"):
                                slot_states[slot] = state
                                break
                    else:
                        slot_states[slot] = state

        return slot_states
    except Exception:
        return {}


def _update_alarm_lines(alarms_text, slot_states):
    if not alarms_text:
        return alarms_text

    updated_lines = []
    for line in alarms_text.split("\n"):
        sip_match = re.search(r"SIP/(\d+)", line)
        if sip_match:
            slot_number = sip_match.group(1)
            state = slot_states.get(slot_number) or slot_states.get(slot_number + "/1") or "unknown"
            updated_lines.append(f"SIP/{slot_number} {state}")
        else:
            updated_lines.append(line)

    return "\n".join(updated_lines)


def _run_show_platform(device, account=None):
    """Wykonuje 'show platform' przez terminal_controller API (jedna wysyłka).
    account param is kept for compatibility but not used.
    """
    logs = []
    session_id = None
    try:
        # devices_controller will disable pagination; send only the show command
        combined_cmd = "show platform\n"
        raw_output, cmd_logs = _exec_command_via_devices_controller(device, combined_cmd, logs)
        logs.extend(cmd_logs or [])
        try:
            print(f"[BE] INPUT: {combined_cmd}", file=sys.stderr, flush=True)
            print(f"[BE] OUTPUT: {raw_output}", file=sys.stderr, flush=True)
        except Exception:
            pass
        return raw_output
    except Exception:
        return None


def auto_check_statuses(payload):
    try:
        table_data = payload.get("tableData") or _load_temp_table_data()
        if not table_data:
            print(json.dumps({"action": "auto_check_statuses", "status": "EMPTY", "data": []}, ensure_ascii=False))
            return

        devices = _load_devices()

        for row in table_data:
            alarms = row.get("alarms", "")
            if not alarms or alarms == "-" or alarms.strip() == "" or alarms == "Brak danych" or "Błąd" in alarms:
                continue

            hostname = row.get("device") or row.get("hostname") or ""
            device = _find_device_exact(devices, hostname)
            if not device:
                row["alarms"] = f"Błąd: brak urządzenia {hostname}"
                continue

            if device.get("status") != "SYNCED":
                row["alarms"] = "Błąd: urządzenie niezsynchronizowane"
                continue

            if not device.get("account"):
                row["alarms"] = "Błąd: brak konta"
                continue

            raw_output = _run_show_platform(device)
            if not raw_output:
                row["alarms"] = "Błąd: brak output"
                continue

            target_slots = _extract_target_slots(alarms)
            slot_states = _extract_slot_states(raw_output, target_slots)
            if slot_states:
                row["alarms"] = _update_alarm_lines(alarms, slot_states)

        data_to_save = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "data": table_data
        }
        temp_dir = os.path.dirname(TEMP_TMPFS_FILE)
        os.makedirs(temp_dir, exist_ok=True)
        with open(TEMP_TMPFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)

        print(json.dumps({
            "action": "auto_check_statuses",
            "status": "OK",
            "data": table_data
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            "action": "auto_check_statuses",
            "status": "ERROR",
            "message": str(e)
        }, ensure_ascii=False))


if __name__ == "__main__":
    method = sys.argv[1] if len(sys.argv) > 1 else "default"
    raw_payload = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        payload = {}

    # Mapa metod CLI do funkcji
    methods = {
        "verify_tmpfs_alarms": verify_tmpfs_alarms,
        "auto_check_statuses": auto_check_statuses,
        "get_settings": get_settings,
        "save_table_data": save_table_data,
        "load_table_data": load_table_data,
        "clear_table_data": clear_table_data,
    }

    func = methods.get(method, default)
    func(payload)
