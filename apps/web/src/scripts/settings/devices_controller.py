# --- Local helpers for sites.json ---
def _load_sites():
    SITES_FILE = os.path.join(BASE_DIR, "src/data/sites.json")
    if os.path.exists(SITES_FILE):
        try:
            with open(SITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def _save_sites(sites):
    SITES_FILE = os.path.join(BASE_DIR, "src/data/sites.json")
    with open(SITES_FILE, "w", encoding="utf-8") as f:
        json.dump(sites, f, ensure_ascii=False, indent=2)

import json
import os
import sys
import uuid
import paramiko
import socket
import time
import traceback
import re
import logging

# Force UTF-8 on stdout/stderr
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
else:
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DEVICES_FILE = os.path.join(BASE_DIR, "src/data/devices.json")
ACCOUNTS_FILE = os.path.join(BASE_DIR, "src/data/accounts.json")
TUNNEL_STATUS_FILE = os.path.join(BASE_DIR, "src/data/tunnel_status.json")
DEVICES_INFO_FILE = os.path.join(BASE_DIR, "src/data/devices_info.json")
SITES_FILE = os.path.join(BASE_DIR, "src/data/sites.json")
INTERFACES_FILE = os.path.join(BASE_DIR, "src/data/interfaces.json")
CONNECTIONS_FILE = os.path.join(BASE_DIR, "src/data/connections.json")

_INVALID_HOSTNAMES = {"system", "unknown", "juniper", "switch", "cisco", "none", "router", "huawei"}


def _is_ip_address(value: str) -> bool:
    """Zwraca True jeśli value jest poprawnym adresem IPv4."""
    ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return bool(re.match(ip_pattern, value) or '')


# Suppress noisy paramiko logging
try:
    logging.getLogger('paramiko').setLevel(logging.CRITICAL)
    pt_logger = logging.getLogger('paramiko.transport')
    pt_logger.setLevel(logging.CRITICAL)
    pt_logger.addHandler(logging.NullHandler())
except Exception:
    pass


def _is_valid_dns_hostname(value: str) -> bool:
    """Zwraca True jeśli value wygląda jak prawdziwy hostname DNS (nie jest IP ani słowem ogólnym)."""
    if not value:
        return False
    if _is_ip_address(value):
        return False
    if value.lower() in _INVALID_HOSTNAMES:
        return False
    return len(value) >= 2


def _pick_tunnel_target(hostname: str, address: str) -> str:
    """Wybiera target_ip dla nagłówka tunelu SSH.
    Preferuje hostname DNS nad adresem IP.
    Jeśli hostname jest słowem ogólnym lub pustym, używa address.
    """
    if _is_valid_dns_hostname(hostname):
        return hostname
    if address and address.strip():
        return address
    return hostname


def add_device(payload):
    address = payload.get("address")
    if not address:
        return

    devices = _load_devices()

    existing_device = next((d for d in devices if d.get("hostname") == address or d.get("address") == address), None)

    if existing_device:
        print(f"Urządzenie już istnieje: {address} (ID: {existing_device.get('id')})", file=sys.stderr)
        return

    new_device = {
        "id": str(uuid.uuid4()),
        "hostname": address,
        "address": "",
        "status": "UNSYNC",
        "connection": "",
        "account": "",
        "vendor": "",
        "model": "",
        "software": "",
        "type": "",
        "site_id": ""
    }
    devices.append(new_device)
    _save_devices(devices)
    print(f"Dodano nowe urządzenie: {address}", file=sys.stderr)


def add_devices_bulk(payload):
    addresses = payload.get("addresses", [])
    if not addresses:
        return

    devices = _load_devices()
    existing_hostnames = {dev["hostname"] for dev in devices}

    # Filtrujemy tylko unikalne adresy, które jeszcze nie istnieją
    new_addresses = [addr for addr in addresses if addr not in existing_hostnames]

    # Tworzymy nowe urządzenia
    new_devices = [{
        "id": str(uuid.uuid4()),
        "hostname": addr,
        "address": "",
        "status": "UNSYNC",
        "connection": "",
        "account": "",
        "vendor": "",
        "model": "",
        "software": "",
        "type": "",
        "site_id": ""
    } for addr in new_addresses]

    # Dodajemy wszystkie nowe urządzenia
    devices.extend(new_devices)
    _save_devices(devices)


def get_all_devices(_=None):
    devices = _load_devices()
    print(json.dumps(devices, ensure_ascii=False))


def get_devices_paginated(payload):
    """Zwraca urządzenia ze stronicowaniem"""
    devices = _load_devices()
    page = payload.get("page", 1)
    limit = payload.get("limit", 100)

    # Walidacja
    page = max(1, int(page))
    limit = max(1, min(500, int(limit)))  # Max 500 per page

    total = len(devices)
    start = (page - 1) * limit
    end = start + limit

    result = {
        "data": devices[start:end],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

    print(json.dumps(result, ensure_ascii=False))


def delete_device(payload):
    device_id = payload.get("id")
    if not device_id:
        return

    devices = _load_devices()
    filtered = [dev for dev in devices if dev.get("id") != device_id]
    _save_devices(filtered)


def deleteAllWithUnsync(_=None):
    devices = _load_devices()
    unsync_devices = [dev for dev in devices if dev.get("status") == "UNSYNC"]
    unsync_count = len(unsync_devices)
    
    if unsync_count > 0:
        filtered = [dev for dev in devices if dev.get("status") != "UNSYNC"]
        _save_devices(filtered)
        print(f"Usunięto {unsync_count} urządzeń ze statusem UNSYNC", file=sys.stderr)
    else:
        print("Brak urządzeń ze statusem UNSYNC do usunięcia", file=sys.stderr)


def deleteAllWithError(_=None):
    devices = _load_devices()
    error_devices = [dev for dev in devices if dev.get("status") == "ERROR"]
    error_count = len(error_devices)
    
    if error_count > 0:
        filtered = [dev for dev in devices if dev.get("status") != "ERROR"]
        _save_devices(filtered)
        print(f"Usunięto {error_count} urządzeń ze statusem ERROR", file=sys.stderr)
    else:
        print("Brak urządzeń ze statusem ERROR do usunięcia", file=sys.stderr)


def sync_device(payload):
    device_id = payload.get("id")
    logs = []

    logs.append(f"[SYNC][START] Starting device sync: {device_id}")

    if not device_id:
        logs.append("[SYNC][ERROR] Missing device_id in payload")
        result = {"status": "FAILED", "account": None, "output": "", "logs": logs}
        print(json.dumps(result, ensure_ascii=False))
        return

    devices = _load_devices()
    accounts = _load_accounts()
    device = next((d for d in devices if d["id"] == device_id), None)

    if not device:
        logs.append(f"[SYNC][ERROR] Device not found: ID={device_id}")
        result = {"status": "FAILED", "account": None, "output": "", "logs": logs}
        print(json.dumps(result, ensure_ascii=False))
        return

    hostname = device.get("hostname")
    address_original = device.get("address", "")
    logs.append(f"[SYNC][INFO] Target device hostname: {hostname}")
    logs.append(f"[SYNC][INFO] Current address: {address_original}")
    logs.append(f"[SYNC][INFO] Hostname will be used for SSH connection. Address will be updated with Loopback0 IP after successful connection.")
    
    vendor = model = software = dev_type = address_parsed = ""
    used_account = None
    connected = False
    hostname_parsed = ""
    combined_output = ""

    try:
        # Check tunnel status
        use_tunnel = False
        host = hostname
        port = 22

        if os.path.exists(TUNNEL_STATUS_FILE):
            with open(TUNNEL_STATUS_FILE, "r", encoding="utf-8") as f:
                tunnel_status = json.load(f)
                status_t = tunnel_status.get("status")
                logs.append(f"[TUNNEL][STATUS] Current status: {status_t}")
                if status_t == "CONNECTED":
                    use_tunnel = True
                    host = "127.0.0.1"
                    port = int(tunnel_status.get("port", 0))
                    logs.append(f"[TUNNEL][CONFIG] Using tunnel → host={host}, port={port}")

                    # Verify tunnel reachability before attempting long sync.
                    # If the local tunnel port is not accepting connections, fall back to direct connection.
                    reachable = False
                    for attempt in range(3):
                        try:
                            test_sock = socket.create_connection((host, port), timeout=1)
                            test_sock.close()
                            reachable = True
                            break
                        except Exception as e_conn:
                            logs.append(f"[TUNNEL][CHECK] Attempt {attempt+1} failed: {e_conn}")
                            time.sleep(0.05)

                    if not reachable:
                        logs.append("[TUNNEL][WARN] Tunnel reported CONNECTED but port is unreachable — falling back to direct connection")
                        use_tunnel = False
                        # prefer hostname (if present) otherwise address_original for direct connect
                        host = hostname if hostname else address_original
                        port = 22
        else:
            logs.append("[TUNNEL][ERROR] Tunnel status file missing or unreadable")

        # Try each account
        for acc in accounts:
            login = acc.get("login")
            password = acc.get("password")
            logs.append(f"[AUTH][ATTEMPT] Trying login: {login} @ {host}:{port}")

            try:
                sock = socket.create_connection((host, port), timeout=3)
                logs.append(f"[SOCKET][SUCCESS] Connection established: {host}:{port}")

                if use_tunnel:
                    target_ip = _pick_tunnel_target(hostname, address_original)
                    header = json.dumps({"target_ip": target_ip, "target_port": 22}) + "\n"
                    logs.append(f"[TUNNEL][HEADER] Sending tunnel header: target_ip={target_ip}")
                    try:
                        sock.sendall(header.encode())
                        time.sleep(0.02)  # Skrócone z 0.05s
                    except Exception as e_hdr:
                        logs.append(f"[TUNNEL][ERROR] Failed to send tunnel header: {e_hdr}")
                        try:
                            sock.close()
                        except:
                            pass
                        # Fall back to direct connection to device address if available
                        if address_original:
                            logs.append("[TUNNEL][FALLBACK] Retrying direct connection to device address")
                            try:
                                host = address_original
                                port = 22
                                sock = socket.create_connection((host, port), timeout=3)
                                logs.append(f"[SOCKET][SUCCESS] Direct connection established: {host}:{port}")
                                use_tunnel = False
                            except Exception as e_direct:
                                logs.append(f"[SOCKET][ERROR] Direct connection also failed: {e_direct}")
                                raise

                transport = paramiko.Transport(sock)
                transport.banner_timeout = 15  # Reduced for faster failure detection
                transport.set_keepalive(30)  # Keep-alive co 30s
                transport.use_compression(True)  # Włącz kompresję
                logs.append("[SSH][CONFIG] Set banner_timeout=20s, keepalive=30s, compression=True")

                transport.start_client()
                logs.append("[SSH][START] SSH client started")

                transport.auth_password(username=login, password=password)
                logs.append(f"[AUTH][ATTEMPT] Password auth attempt: {login}")

                if not transport.is_authenticated():
                    logs.append(f"[AUTH][FAIL] Authentication failed for {login}")
                    raise Exception("Authentication failed")
                
                logs.append(f"[AUTH][SUCCESS] Authentication successful: {login}")

                session = transport.open_session()
                session.settimeout(6)  # Reduced for faster reads
                session.get_pty()
                session.invoke_shell()
                logs.append("[SSH][SESSION] Session opened with PTY, timeout=6s")

                # Disable pagination
                session.send("terminal length 0\n")
                logs.append("[CMD][SEND] Sent: terminal length 0")

                session.send("set cli screen-length 0\n")
                logs.append("[CMD][SEND] Sent: set cli screen-length 0")

                # Send show version brief command
                session.send("show version brief\n")
                logs.append("[CMD][SEND] Sent: show version brief")

                # Read brief version output
                brief_output = _read_full_output(session, logs)
                logs.append(f"[CMD][RECEIVED] Brief version output size: {len(brief_output)} bytes")
                combined_output += brief_output

                # Send show version command
                session.send("show version\n")
                logs.append("[CMD][SEND] Sent: show version")

                # Read full version output
                full_output = _read_full_output(session, logs)
                logs.append(f"[CMD][RECEIVED] Full version output size: {len(full_output)} bytes")
                combined_output += full_output

                # Send show ip interface brief command to get Loopback0 IP address (Cisco IOS)
                session.send("show ip interface brief | include Loopback\n")
                logs.append("[CMD][SEND] Sent: show ip interface brief | include Loopback")

                # Read IP interface output
                ip_output = _read_full_output(session, logs)
                logs.append(f"[CMD][RECEIVED] IP interface output size: {len(ip_output)} bytes")
                combined_output += ip_output

                # Send IOS XR variant (for ASR9K, etc.)
                session.send("show ipv4 interface brief | include Loopback\n")
                logs.append("[CMD][SEND] Sent: show ipv4 interface brief | include Loopback")

                # Read IOS XR output
                iosxr_output = _read_full_output(session, logs)
                logs.append(f"[CMD][RECEIVED] IOS XR ipv4 interface output size: {len(iosxr_output)} bytes")
                combined_output += iosxr_output

                # Send Juniper command to get Loopback0 IP address
                session.send("show configuration interfaces lo0 | display set | match primary\n")
                logs.append("[CMD][SEND] Sent: show configuration interfaces lo0 | display set | match primary")

                # Read Juniper output
                juniper_output = _read_full_output(session, logs)
                logs.append(f"[CMD][RECEIVED] Juniper lo0 config output size: {len(juniper_output)} bytes")
                combined_output += juniper_output
                
                # Combine outputs for IP extraction (include IOS XR output as well)
                combined_ip_output = ip_output + "\n" + iosxr_output + "\n" + juniper_output

                # --- Gather interface description outputs (multiple vendor variants) ---
                try:
                    session.send("show interface description\n")
                    logs.append("[CMD][SEND] Sent: show interface description")
                    intf_out_1 = _read_full_output(session, logs)
                    logs.append(f"[CMD][RECEIVED] Interface desc output size: {len(intf_out_1)} bytes")

                    session.send("show interfaces description\n")
                    logs.append("[CMD][SEND] Sent: show interfaces description")
                    intf_out_2 = _read_full_output(session, logs)
                    logs.append(f"[CMD][RECEIVED] Interface desc alt output size: {len(intf_out_2)} bytes")

                    session.send("show interfaces descriptions\n")
                    logs.append("[CMD][SEND] Sent: show interfaces descriptions")
                    intf_out_3 = _read_full_output(session, logs)
                    logs.append(f"[CMD][RECEIVED] Juniper interface desc output size: {len(intf_out_3)} bytes")

                    combined_intf_output = intf_out_1 + "\n" + intf_out_2 + "\n" + intf_out_3
                except Exception as e:
                    logs.append(f"[INTERFACES][ERROR] Failed to collect interface descriptions: {e}")
                    combined_intf_output = ""

                # Show raw outputs used for address extraction in console (stderr)
                try:
                    print("[ADDR][RAW][ip_output]:\n" + (ip_output or ""), file=sys.stderr, flush=True)
                except Exception:
                    pass
                try:
                    print("[ADDR][RAW][juniper_output]:\n" + (juniper_output or ""), file=sys.stderr, flush=True)
                except Exception:
                    pass

                # Extract all Loopback IPs (returns list)
                temp_ips = _extract_loopback_ips(combined_ip_output)
                if not temp_ips:
                    logs.append("[CMD][INFO] No IPs found in lo0 config, trying router-id fallback")
                    session.send("show configuration routing-options router-id\n")
                    logs.append("[CMD][SEND] Sent: show configuration routing-options router-id")

                    router_id_output = _read_full_output(session, logs)
                    logs.append(f"[CMD][RECEIVED] Router-id output size: {len(router_id_output)} bytes")
                    combined_output += router_id_output
                    combined_ip_output += "\n" + router_id_output
                    # Re-run extraction after fallback
                    temp_ips = _extract_loopback_ips(combined_ip_output)

                # Parse version info - najpierw sprawdź plik, potem użyj danych z urządzenia
                device_hostname = device.get("hostname", "")
                saved_show_version = _load_show_version_from_file(device_hostname) if device_hostname else None
                
                if saved_show_version:
                    logs.append("[PARSE][MODE] Using saved show version data from file")
                    parse_output = saved_show_version
                else:
                    logs.append("[PARSE][MODE] Using live data from device")
                    parse_output = full_output

                if not parse_output.strip():
                    logs.append("[PARSE][ERROR] Empty output - using fallback values")
                    vendor = "UNKNOWN"
                    model = "UNKNOWN"
                    software = "UNKNOWN"
                    dev_type = ""
                    hostname_parsed = ""
                else:
                    info = _parse_info_from_output(parse_output)
                    if info.get("logs"):
                        logs.extend(info["logs"])
                    vendor = info.get("vendor", "")
                    model = info.get("model", "")
                    software = info.get("software", "")
                    dev_type = info.get("type", "")
                    hostname_parsed = info.get("hostname", "")
                    # Extract all loopback IPs and pick primary
                    address_parsed_list = _extract_loopback_ips(combined_ip_output)
                    primary_address = address_parsed_list[0] if address_parsed_list else ""
                    logs.append(
                        f"[PARSE][SUCCESS] Parsed info: vendor={vendor}, model={model}, "
                        f"software={software}, type={dev_type}, hostname={hostname_parsed!r}"
                    )
                    if address_parsed_list:
                        logs.append(f"[PARSE][ADDRESS] Extracted Loopback IPs: {address_parsed_list}")
                        try:
                            print(f"[ADDR][PARSED]: {address_parsed_list}", file=sys.stderr, flush=True)
                        except Exception:
                            pass
                    else:
                        logs.append("[PARSE][ADDRESS] No Loopback IP found in output")

                # Zapisz show version do pliku używając rzeczywistego hostname (jeśli został sparsowany)
                final_hostname = hostname_parsed if hostname_parsed and hostname_parsed.lower() != "none" else device_hostname
                if final_hostname:
                    _save_show_version_to_file(final_hostname, full_output)
                    logs.append(f"[FILE][SAVE] Saved show version as sv_{final_hostname}.txt")

                used_account = acc.get("id")
                connected = True

                # Close connections
                transport.close()
                logs.append("[SSH][CLOSE] Transport closed")

                break

            except paramiko.ssh_exception.SSHException as e:
                logs.append(f"[SSH][ERROR] SSH exception with account {login}: {e}")
                try:
                    transport.close()
                except:
                    pass
                time.sleep(0.5)
                continue

            except socket.timeout as e:
                logs.append(f"[SOCKET][TIMEOUT] Connection timeout: {e}")
                time.sleep(0.5)
                continue

            except Exception as e:
                logs.append(f"[ERROR] General error with account {login}: {e}")
                try:
                    transport.close()
                except:
                    pass
                time.sleep(0.5)
                continue

        # Update device status
        if connected:
            device["status"] = "SYNCED"
            device["vendor"] = vendor
            device["model"] = model
            device["software"] = software
            device["type"] = dev_type
            device["connection"] = "SSH"
            device["account"] = used_account

            # Filter out known generic words that are not valid hostnames
            INVALID_HOSTNAMES = {"system", "router", "switch", "none", "cisco", "juniper", "huawei"}
            if hostname_parsed and hostname_parsed.lower() in INVALID_HOSTNAMES:
                logs.append(f"[UPDATE][HOSTNAME] Ignoring generic word '{hostname_parsed}' - keeping original: {device.get('hostname', '')}")
                hostname_parsed = ""

            if hostname_parsed and hostname_parsed.lower() != "none":
                device["hostname"] = hostname_parsed
                logs.append(f"[UPDATE][HOSTNAME] Set hostname = {hostname_parsed}")
            else:
                logs.append(f"[UPDATE][HOSTNAME] No hostname parsed - keeping original: {device.get('hostname', '')}")

            # Save primary address (first) and all discovered addresses
            try:
                if address_parsed_list:
                    device["address"] = primary_address
                    device["addresses"] = address_parsed_list
                    logs.append(f"[UPDATE][ADDRESS] Set address = {primary_address}")
                    logs.append(f"[UPDATE][ADDRESSES] Set addresses = {address_parsed_list}")
                    try:
                        print(f"[UPDATE][ADDRESSES] Set addresses = {address_parsed_list}", file=sys.stderr, flush=True)
                    except Exception:
                        pass
                else:
                    logs.append("[UPDATE][ADDRESS] No valid IP address found")
            except Exception:
                logs.append("[UPDATE][ADDRESS] No valid IP address found")

            # Attempt to assign site_id by matching hostname against site_tag values from sites.json
            try:
                sites = _load_sites()
                if sites:
                    hn = (device.get("hostname", "") or "").lower()
                    best_tag = None
                    best_id = None
                    for s in sites:
                        tag = (s.get("site_tag") or "").lower()
                        if not tag:
                            continue
                        if tag in hn:
                            if best_tag is None or len(tag) > len(best_tag):
                                best_tag = tag
                                best_id = s.get("id")
                    if best_id:
                        device["site_id"] = best_id
                        logs.append(f"[UPDATE][SITE] Matched site_tag='{best_tag}' -> site_id={best_id}")
                        # --- update site's site_devices ---
                        sites = _load_sites()
                        for s in sites:
                            if s.get("id") == best_id:
                                if "site_devices" not in s or not isinstance(s["site_devices"], list):
                                    s["site_devices"] = []
                                if device["id"] not in s["site_devices"]:
                                    s["site_devices"].append(device["id"])
                                    _save_sites(sites)
                                break
                    else:
                        device["site_id"] = ""
                        logs.append("[UPDATE][SITE] No site_tag match found, site_id set to ''")
                else:
                    device["site_id"] = ""
                    logs.append("[UPDATE][SITE] No sites defined, site_id set to ''")
            except Exception as e:
                device["site_id"] = ""
                logs.append(f"[UPDATE][SITE] site matching failed: {e}, site_id set to ''")

            _save_devices(devices)
            logs.append("[SAVE] Device data saved to devices.json")

            # Parse and save interfaces output to interfaces.json
            try:
                interfaces_list = _parse_interfaces_from_output(combined_intf_output)
                if interfaces_list is None:
                    interfaces_list = []
                # load existing interfaces mapping (dict keyed by device id)
                interfaces_map = _load_interfaces()
                if not isinstance(interfaces_map, dict):
                    interfaces_map = {}
                final_hostname = hostname_parsed if hostname_parsed and hostname_parsed.lower() != "none" else device_hostname
                interfaces_map[device["id"]] = {
                    "id": device["id"],
                    "hostname": final_hostname,
                    "interfaces": interfaces_list
                }
                _save_interfaces(interfaces_map)
                logs.append(f"[INTERFACES][SAVE] Saved {len(interfaces_list)} interfaces for device {device.get('id')}")
            except Exception as e:
                logs.append(f"[INTERFACES][ERROR] Failed to save interfaces: {e}")

            # Reload devices and include in result
            updated_devices = _load_devices()
            result = {
                "status": "SYNCED",
                "account": used_account,
                "vendor": vendor,
                "model": model,
                "software": software,
                "hostname": device["hostname"],
                "address": device.get("address", ""),
                "addresses": device.get("addresses", []),
                "interfaces": interfaces_list if 'interfaces_list' in locals() else device.get("interfaces", []),
                "connection": "SSH",
                "type": dev_type,
                "logs": logs,
                "devices": updated_devices  # Add full devices list to response
            }
        else:
            device["status"] = "ERROR"
            _save_devices(devices)
            logs.append(f"[UPDATE] Set device {device_id} status to 'ERROR'")
            logs.append("[SYNC][FAIL] Failed to connect with any account")
            
            # Include updated devices list even on error
            updated_devices = _load_devices()
            result = {
                "status": "FAILED", 
                "account": None, 
                "output": "", 
                "logs": logs,
                "devices": updated_devices  # Add full devices list to response
            }

    except Exception as e:
        logs.append("[SYNC][CRITICAL] Critical exception - setting status=ERROR")
        try:
            device["status"] = "ERROR"
            _save_devices(devices)
            logs.append(f"[UPDATE] Set device {device_id} status to 'ERROR' (exception)")
        except Exception as ee:
            logs.append(f"[SYNC][CRITICAL] Error saving ERROR status: {ee}")

        logs.append(f"[SYNC][EXCEPTION] {e}")
        logs.append(traceback.format_exc())
        
        # Include updated devices list even after exception
        updated_devices = _load_devices()
        result = {
            "status": "FAILED", 
            "account": None, 
            "output": "", 
            "logs": logs,
            "devices": updated_devices  # Add full devices list to response
        }

    # Return only the JSON response at the end
    # Also print concise backend-friendly status messages to stderr
    try:
        hostname_for_msg = device.get("hostname") if device else device_id
    except Exception:
        hostname_for_msg = device_id

    if result.get("status") == "SYNCED":
        try:
            print(f"[BE] Synchronized device {hostname_for_msg}", file=sys.stderr, flush=True)
        except Exception:
            pass
    else:
        # pick a relevant error line from logs if available
        err = ""
        try:
            if logs:
                for l in reversed(logs):
                    if "ERROR" in l or "FAIL" in l or "CRITICAL" in l or "Exception" in l:
                        err = l
                        break
                if not err:
                    err = logs[-1]
        except Exception:
            err = ""

        try:
            print(f"[BE] Failed to synchronize device {hostname_for_msg} Error: {err}", file=sys.stderr, flush=True)
        except Exception:
            pass

    print(json.dumps(result, ensure_ascii=False))


def get_devices_info(_=None):
    """Zwraca zawartość pliku devices_info.json"""
    try:
        if os.path.exists(DEVICES_INFO_FILE):
            with open(DEVICES_INFO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(json.dumps(data, ensure_ascii=False))
        else:
            # Jeśli plik nie istnieje, zwróć pusty szablon
            empty_template = {
                "vendor": {},
                "model": {},
                "software": {},
                "type": {},
                "hostname": {}
            }
            print(json.dumps(empty_template, ensure_ascii=False))
    except Exception as e:
        print(f"Błąd podczas odczytu devices_info.json: {e}", file=sys.stderr)
        return


def _read_full_output_streaming(session, logs, command):
    """
    Odczytuje output z sesji SSH i streamuje linie od razu (print line-by-line)
    zamiast zbierać wszystko i zwracać na koniec.
    """
    start_time = time.time()
    last_read = time.time()
    total_timeout = 15  # Zwiększony dla dłuższych komend
    idle_timeout = 0.5  # Zmniejszony z 2s - przerywamy czytanie szybciej
    output = ""
    lines_buffer = ""
    
    while True:
        if time.time() - start_time > total_timeout:
            logs.append(f"[SSH] Przekroczono total_timeout={total_timeout}s")
            break

        if session.recv_ready():
            try:
                chunk = session.recv(8192).decode(errors="ignore")
            except Exception as e_recv:
                logs.append(f"[SSH] Błąd podczas recv: {e_recv}")
                chunk = ""
            
            output += chunk
            lines_buffer += chunk
            
            # Stream complete lines immediately
            if "\n" in lines_buffer:
                lines = lines_buffer.split("\n")
                for line in lines[:-1]:  # All complete lines
                    print(json.dumps({"output": line}, ensure_ascii=False))
                    sys.stdout.flush()
                lines_buffer = lines[-1]  # Keep incomplete line in buffer
            
            last_read = time.time()
            continue

        if time.time() - last_read > idle_timeout:
            logs.append(f"[SSH] Od ostatniego odczytu minęło >{idle_timeout}s")
            break

        time.sleep(0.05)  # Zmniejszony z 0.1s - szybsza pętla
    
    # Flush remaining buffer
    if lines_buffer.strip():
        print(json.dumps({"output": lines_buffer}, ensure_ascii=False))
        sys.stdout.flush()
    
    return output


def _read_full_output(session, logs, total_timeout=10):

    """
    Odczytuje cały dostępny output z sesji SSH, aż:
      - przekroczony zostanie maksymalny czas (total_timeout), lub
      - od ostatniego odczytu minie >2 s.
    Zwraca zebrany ciąg znaków.
    """
    start_time = time.time()
    last_read = time.time()
    idle_timeout = 2    # 2 sekundy bezczynności
    output = ""

    while True:
        if time.time() - start_time > total_timeout:
            logs.append(f"[SSH] Przekroczono total_timeout={total_timeout}s, przerywamy odczyt")
            break

        if session.recv_ready():
            try:
                chunk = session.recv(8192).decode(errors="ignore")  # zmniejszone z 65535 na 8192
            except Exception as e_recv:
                logs.append(f"[SSH] Błąd podczas recv: {e_recv}")
                chunk = ""
            output += chunk
            logs.append(f"[SSH] Odebrano fragment o długości={len(chunk)}")
            last_read = time.time()
            continue

        if time.time() - last_read > idle_timeout:
            logs.append(f"[SSH] Od ostatniego odczytu minęło >{idle_timeout}s, zakładamy, że już nic nie przyjdzie")
            break

        time.sleep(0.1)  # zmniejszone z 0.2s na 0.1s

    return output


def _read_full_output_terminal(session, logs):
    """
    Czyta output dla terminala - bez timeoutów, streamuje line-by-line.
    Zawsze czeka aż sessja zwróci dane lub się zamknie.
    """
    output = ""
    lines_buffer = ""
    
    while True:
        if session.recv_ready():
            try:
                chunk = session.recv(8192).decode(errors="ignore")
            except Exception as e_recv:
                logs.append(f"[SSH] Błąd podczas recv: {e_recv}")
                break
            
            if not chunk:  # SSH sesja zamknięta
                break
                
            output += chunk
            lines_buffer += chunk
            
            # Stream complete lines immediately
            if "\n" in lines_buffer:
                lines = lines_buffer.split("\n")
                for line in lines[:-1]:  # All complete lines
                    print(json.dumps({"output": line}, ensure_ascii=False))
                    sys.stdout.flush()
                lines_buffer = lines[-1]  # Keep incomplete line in buffer
        else:
            time.sleep(0.05)  # Czekaj bez timeoutu
    
    # Flush remaining buffer
    if lines_buffer.strip():
        print(json.dumps({"output": lines_buffer}, ensure_ascii=False))
        sys.stdout.flush()
    
    return output


def _extract_loopback_ips(output: str) -> list:
    """
    Extracts all loopback IPs from the provided output.
    Returns a list of IP strings (without CIDR), ordered by preference:
      1. Loopback0
      2. Loopback1
      3. Other Loopbacks in appearance order
      4. Juniper lo0 primary lines and router-id
    """
    if not output:
        return []

    ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:/\d+)?\b'
    lines = output.split('\n')
    found = []

    # Prefer Loopback0 first
    for line in lines:
        if 'loopback0' in line.lower() or 'loopback 0' in line.lower():
            match = re.search(ip_pattern, line)
            if match:
                ip = match.group(0).split('/')[0]
                if ip not in found:
                    found.append(ip)

    # Then Loopback1
    for line in lines:
        if 'loopback1' in line.lower() or 'loopback 1' in line.lower():
            if 'unassigned' not in line.lower():
                match = re.search(ip_pattern, line)
                if match:
                    ip = match.group(0).split('/')[0]
                    if ip not in found:
                        found.append(ip)

    # Then any other LoopbackN
    for line in lines:
        lb_match = re.search(r'loopback\s*(\d+)', line.lower())
        if lb_match:
            match = re.search(ip_pattern, line)
            if match:
                ip = match.group(0).split('/')[0]
                if ip not in found:
                    found.append(ip)

    # Juniper formats: 'set interfaces lo0 ... address' or router-id
    for line in lines:
        if 'set interfaces lo0' in line.lower() and 'address' in line.lower():
            match = re.search(ip_pattern, line)
            if match:
                ip = match.group(0).split('/')[0]
                if ip not in found:
                    found.append(ip)

    for line in lines:
        if 'router-id' in line.lower():
            match = re.search(ip_pattern, line)
            if match:
                ip = match.group(0).split('/')[0]
                if ip not in found:
                    found.append(ip)

    return found


def _parse_interfaces_from_output(text: str):
    """Parses various 'show interface description' outputs and returns
    list of {name, description} objects.
    """
    if not text:
        return []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    results = []

    # Heuristics: look for lines that start with interface name-like token (no spaces)
    # and contain some description later on the line. Skip header-like lines.
    for ln in lines:
        # skip JSON-like lines printed by streaming mode
        if ln.startswith("{") or ln.startswith("["):
            continue
        # common header keywords
        if any(h in ln.lower() for h in ("interface", "status", "protocol", "admin", "link", "description")) and len(ln.split()) < 3:
            continue

        parts = ln.split()
        if not parts:
            continue

        # First token is likely interface name if it contains non-digit and '/' or alphabetic
        iface = parts[0]
        # Reject lines that don't look like interface (e.g., lines starting with '[' or words like 'show')
        if iface.startswith("[") or iface.lower().startswith("show"):
            continue

        # Try to find description: assume description starts after 3rd column for many vendors
        desc = ""
        if len(parts) <= 1:
            desc = ""
        elif len(parts) <= 3:
            # no clear description columns, maybe rest of line after iface is description
            desc = " ".join(parts[1:]).strip()
        else:
            # assume first column iface, next one/two columns status/proto, remaining is description
            desc = " ".join(parts[3:]).strip()

        # Clean description: remove leading/trailing separators
        desc = desc.strip() if desc else ""

        # Accept only if iface looks plausible (contains letters or '/', '.' etc)
        if re.search(r'[A-Za-z/\.\-]', iface):
            # Try extract target info from description (pattern: NE=<hostname> and IF=<interface>)
            target = None
            try:
                # Prefer parsing from description, fallback to whole line
                src = desc or ln

                # Direct tokens
                ne_m = re.search(r'NE=([^\s\*;,]+)', src)
                if_m = re.search(r'IF=([^\s\*;,]+)', src)

                # Prepare fallback regexes: interface name patterns and pl- hostnames
                interface_re = re.compile(r"\b(?:et|xe|ge|ae|fxp|irb|lo|vt|gi|te|hu|gi|TenGigE|HundredGigE)[0-9A-Za-z/\.:_-]*\b", re.IGNORECASE)
                hostname_re = re.compile(r"\b(pl-[a-z0-9\-]+)\b", re.IGNORECASE)

                if ne_m or if_m:
                    target = {
                        "hostname": ne_m.group(1) if ne_m else None,
                        "interface": if_m.group(1) if if_m else None
                    }
                else:
                    # fallback: try to find hostname like pl-xxx anywhere
                    host_m = hostname_re.search(src)
                    intf_m = interface_re.search(src)
                    # if none found in desc, try entire line
                    if not host_m:
                        host_m = hostname_re.search(ln)
                    if not intf_m:
                        intf_m = interface_re.search(ln)

                    if host_m or intf_m:
                        target = {
                            "hostname": host_m.group(1) if host_m else None,
                            "interface": intf_m.group(0) if intf_m else None
                        }
            except Exception:
                target = None

            entry = {"name": iface, "description": desc}
            # Always include target key (null if not found) as requested
            entry["target"] = target
            results.append(entry)

    # Deduplicate by name preserving order
    seen = set()
    dedup = []
    for r in results:
        if r["name"] in seen:
            continue
        seen.add(r["name"])
        dedup.append(r)

    return dedup


def _load_interfaces():
    if os.path.exists(INTERFACES_FILE):
        try:
            with open(INTERFACES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_interfaces(data):
    try:
        with open(INTERFACES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_connections():
    if os.path.exists(CONNECTIONS_FILE):
        try:
            with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_connections(data):
    try:
        with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def sync_connections(_=None):
    """Scans src/data/interfaces.json and builds pairwise connections when
    an interface's target points to another device's interface.

    Returns JSON with count and saves to connections.json.
    """
    try:
        print('[CONN][START] Scanning interfaces for connections...', flush=True)
        interfaces_map = _load_interfaces()
        if not isinstance(interfaces_map, dict):
            interfaces_map = {}

        # Normalizers
        def _norm_host(h):
            return (h or "").strip().lower()

        def _norm_iface(name):
            if not name:
                return ""
            n = name.strip().lower()
            # remove trailing :<digits> or .<digits>
            n = re.sub(r'[:\.][0-9]+$', '', n)
            # collapse multiple spaces
            n = re.sub(r'\s+', ' ', n)
            return n

        # Build lookup: exact and normalized keys
        lookup_exact = {}   # (hostname, iface) -> (dev_id, rec, intf)
        lookup_norm = {}    # (norm_host, norm_iface) -> (dev_id, rec, intf)
        total_ifaces = 0
        for dev_id, rec in interfaces_map.items():
            hostname = rec.get("hostname") or ""
            nh = _norm_host(hostname)
            for intf in rec.get("interfaces", []):
                name = intf.get("name")
                if not name:
                    continue
                total_ifaces += 1
                lookup_exact[(hostname, name)] = (dev_id, rec, intf)
                lookup_norm[(nh, _norm_iface(name))] = (dev_id, rec, intf)

        print(f"[CONN][INFO] Loaded {len(interfaces_map)} devices, {total_ifaces} interfaces", flush=True)

        connections = []
        seen = set()

        for dev_id, rec in interfaces_map.items():
            src_host = rec.get("hostname") or ""
            for intf in rec.get("interfaces", []):
                src_iface = intf.get("name")
                tgt = intf.get("target") or {}
                th = (tgt.get("hostname") or "").strip()
                ti = (tgt.get("interface") or "").strip()

                if not th and not ti:
                    # try to parse from description/line as we did in parser already
                    continue

                # Attempt exact match first
                matched = None
                used_rule = 'none'
                if (th, ti) in lookup_exact:
                    matched = lookup_exact[(th, ti)]
                    used_rule = 'exact'
                else:
                    # try normalized match
                    nh = _norm_host(th)
                    nti = _norm_iface(ti)
                    if (nh, nti) in lookup_norm:
                        matched = lookup_norm[(nh, nti)]
                        used_rule = 'normalized'
                    else:
                        # try match by hostname only with same interface name (normalized)
                        if nh:
                            for (hkey, ifkey), val in lookup_norm.items():
                                if hkey == nh and ifkey == nti:
                                    matched = val
                                    used_rule = 'host+iface-scan'
                                    break

                if not matched:
                    print(f"[CONN][MISS] No match for target {th}/{ti} from {src_host}/{src_iface}", flush=True)
                    continue

                other_dev_id, other_rec, other_intf = matched

                # avoid self-links
                if other_dev_id == dev_id:
                    print(f"[CONN][SKIP] Ignoring self-link for {dev_id}:{src_iface}", flush=True)
                    continue

                # create symmetric normalized dedup key to avoid duplicates
                a_key = f"{dev_id}:{_norm_iface(src_iface)}"
                b_key = f"{other_dev_id}:{_norm_iface(other_intf.get('name'))}"
                pair_key = tuple(sorted([a_key, b_key]))
                if pair_key in seen:
                    print(f"[CONN][DUP] Duplicate connection skipped: {a_key} <-> {b_key}", flush=True)
                    continue
                seen.add(pair_key)

                conn = {
                    "connection_id": str(uuid.uuid4()),
                    "idA": dev_id,
                    "nameA": rec.get("hostname", ""),
                    "interfaceA": src_iface or "",
                    "descriptionA": intf.get("description", ""),
                    "positionA": intf.get("position", ""),
                    "idB": other_dev_id,
                    "deviceB": other_rec.get("hostname", ""),
                    "interfaceB": other_intf.get("name", ""),
                    "descriptionB": other_intf.get("description", ""),
                    "positionB": other_intf.get("position", ""),
                    "match_rule": used_rule
                }
                connections.append(conn)
                print(f"[CONN][FOUND] {rec.get('hostname')}:{src_iface} -> {other_rec.get('hostname')}:{other_intf.get('name')} (rule={used_rule})", flush=True)

        _save_connections(connections)
        print(f"[CONN][SAVE] Saved {len(connections)} connections to {CONNECTIONS_FILE}", flush=True)
        print(json.dumps({"ok": True, "count": len(connections)}, ensure_ascii=False), flush=True)
        return {"ok": True, "count": len(connections)}
    except Exception as e:
        print(f"[CONNECTIONS][ERROR] {e}", file=sys.stderr)
        return {"ok": False, "error": str(e)}


def _match_field(rules: dict, text: str, field_name: str = "") -> str:
    """Matches text against rules for a field to determine appropriate value."""
    logs = []
    logs.append("[MATCH] Starting pattern matching")
    
    if not rules:
        logs.append("[MATCH][ERROR] No rules provided")
        return ""
        
    # For hostname and address fields, use regex patterns directly without lowercase conversion
    if field_name in ["hostname", "address"]:
        for value, pattern in rules.items():
            if not pattern:
                continue
                
            try:
                match = re.search(pattern, text)
                if match:
                    result = match.group(1)
                    logs.append(f"[MATCH][SUCCESS] Found {field_name} match: pattern={pattern!r}, value={result!r}")
                    return result
            except re.error as e:
                logs.append(f"[MATCH][ERROR] Invalid regex pattern {pattern!r}: {e}")
                continue
    else:
        # For other fields, use the existing substring matching logic
        text_lower = text.lower()
        for value, patterns in rules.items():
            if not patterns:
                continue
                
            # Split patterns and clean them
            keywords = [k.strip().lower() for k in patterns.split(",") if k.strip()]
            logs.append(f"[MATCH] Testing value={value!r} with patterns={keywords}")
            
            # Try to match each pattern
            for pattern in keywords:
                if pattern in text_lower:
                    logs.append(f"[MATCH][SUCCESS] Found match: pattern={pattern!r}")
                    return value
                
    logs.append("[MATCH][FAIL] No patterns matched")
    return ""




def _parse_info_from_output(output: str) -> dict:
    """Parses vendor, model, software version, and device type from show version output."""
    info = {}
    logs = []    # Debug log for complete input
    logs.append(f"[PARSE][INPUT] Raw output length: {len(output)}")
    logs.append("[PARSE][INPUT] Complete output:\n" + output if output else "Empty output")

    if not output:
        logs.append("[PARSE][ERROR] Empty output received")
        return {"logs": logs}

    # Load parsing rules
    if os.path.exists(DEVICES_INFO_FILE):
        try:
            with open(DEVICES_INFO_FILE, "r", encoding="utf-8") as f:
                parsing_rules = json.load(f)
                logs.append("[PARSE][CONFIG] Successfully loaded devices_info.json")
        except json.JSONDecodeError:
            logs.append("[PARSE][ERROR] Failed to parse devices_info.json")
            return {"logs": logs}
    else:
        logs.append("[PARSE][ERROR] devices_info.json not found")
        return {"logs": logs}    # Parse each field using rules
    for field in ["vendor", "model", "software", "type", "hostname", "address"]:
        field_rules = parsing_rules.get(field, {})
        value = _match_field(field_rules, output, field)
        info[field] = value
        logs.append(f"[PARSE][FIELD] {field}={value!r}")

    # Fallback: if address is not found or equals hostname, try to extract loopback IPs
    if not info.get("address") or info.get("address") == info.get("hostname"):
        loopback_ips = _extract_loopback_ips(output)
        if loopback_ips:
            info["address"] = loopback_ips[0]
            info["addresses"] = loopback_ips
            logs.append(f"[PARSE][FALLBACK] Address set to Loopback IPs: {loopback_ips}")

    info["logs"] = logs
    return info


def save_devices_info(payload):
    """
    Zapisuje nową zawartość do devices_info.json
    payload = {'newContent': '<json string>'}
    """
    try:
        new_content = payload.get("newContent")
        if not new_content:
            raise ValueError("Brak newContent w payload")

        # Parsowanie JSON-a
        parsed = json.loads(new_content)
        
        # Weryfikacja struktury
        required_keys = {"vendor", "model", "software", "type", "hostname", "address"}
        missing_keys = required_keys - set(parsed.keys())
        if missing_keys:
            raise ValueError(f"Brakujące klucze: {missing_keys}")

        # Weryfikacja czy każda sekcja to słownik
        for key in required_keys:
            if not isinstance(parsed[key], dict):
                raise ValueError(f"Sekcja {key} musi być słownikiem")

        # Zapis do pliku
        with open(DEVICES_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)

        print(json.dumps({"status": "OK"}, ensure_ascii=False))

    except json.JSONDecodeError as e:
        print(f"Błąd parsowania JSON: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Błąd podczas zapisu devices_info.json: {e}", file=sys.stderr)


def _load_devices():
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def _save_devices(devices):
    with open(DEVICES_FILE, "w", encoding="utf-8") as f:
        json.dump(devices, f, ensure_ascii=False, indent=2)


def _load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def _load_sites():
    if os.path.exists(SITES_FILE):
        try:
            with open(SITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def update_device(payload):
    new_dev = payload.get("device")
    if not new_dev or not new_dev.get("id"):
        return

    devices = _load_devices()
    updated = False

    for idx, dev in enumerate(devices):
        if dev.get("id") == new_dev["id"]:
            dev["hostname"] = new_dev.get("hostname", dev.get("hostname", ""))
            dev["address"]  = new_dev.get("address",  dev.get("address", ""))
            dev["vendor"]   = new_dev.get("vendor",   dev.get("vendor", ""))
            dev["model"]    = new_dev.get("model",    dev.get("model", ""))
            dev["software"] = new_dev.get("software", dev.get("software", ""))
            dev["type"]     = new_dev.get("type",     dev.get("type", ""))
            dev["account"]  = new_dev.get("account",  dev.get("account", ""))

            # Handle site_id update
            if "site_id" in new_dev:
                old_site_id = dev.get("site_id", "")
                new_site_id = new_dev.get("site_id", "")
                dev["site_id"] = new_site_id
                print(f"[DEBUG] update_device: site_id={new_site_id}, dev_id={new_dev['id']}", file=sys.stderr, flush=True)

                # Update sites.json
                try:
                    from scripts.settings.sites_controller import _load_sites as _load_sites_ctrl, _save_sites as _save_sites_ctrl
                except ImportError:
                    try:
                        ctrl_dir = os.path.dirname(__file__)
                        if ctrl_dir not in sys.path:
                            sys.path.append(ctrl_dir)
                        from sites_controller import _load_sites as _load_sites_ctrl, _save_sites as _save_sites_ctrl
                    except ImportError:
                        _load_sites_ctrl = None
                        _save_sites_ctrl = None

                if _load_sites_ctrl and _save_sites_ctrl:
                    try:
                        sites = _load_sites_ctrl()
                        dev_id = new_dev["id"]
                        # Remove device from old site
                        if old_site_id:
                            for site in sites:
                                if site.get("id") == old_site_id:
                                    sd = site.get("site_devices", [])
                                    site["site_devices"] = [d for d in sd if d != dev_id]
                                    break
                        # Add device to new site
                        if new_site_id:
                            for site in sites:
                                if site.get("id") == new_site_id:
                                    sd = site.get("site_devices", [])
                                    if dev_id not in sd:
                                        sd.append(dev_id)
                                        site["site_devices"] = sd
                                    break

                        _save_sites_ctrl(sites)
                    except Exception as e:
                        print(f"[ERROR] update_device: failed to update sites.json: {e}", file=sys.stderr, flush=True)

            devices[idx] = dev
            updated = True
            break

    if updated:
        _save_devices(devices)
        print(json.dumps({"ok": True}, ensure_ascii=False))


def default(_=None):
    print("Nieznana metoda.", file=sys.stderr)


def get_show_version(payload):
    device_id = payload.get("id")
    devices = _load_devices()
    device = next((d for d in devices if d.get("id") == device_id), None)
    if device:
        print(device.get("last_show_version", ""))
    else:
        print("")


def get_show_version_brief(payload):
    device_id = payload.get("id")
    devices = _load_devices()
    device = next((d for d in devices if d.get("id") == device_id), None)
    if device:
        print(device.get("last_show_version_brief", ""))
    else:
        print("")


def execute_command_on_device(payload):
    device = payload.get("device")
    command = payload.get("command")
    logs = []

    if not device or not command:
        print(json.dumps({"error": "Brak urządzenia lub komendy"}, ensure_ascii=False))
        return

    hostname = device.get("hostname", "")
    address = device.get("address", "")
    logs.append(f"[CMD][INFO] Device hostname: {hostname}")
    logs.append(f"[CMD][INFO] Device address: {address}")

    # Determine SSH target
    if hostname and _is_valid_dns_hostname(hostname):
        host = hostname
        port = 22
        logs.append(f"[CMD][INFO] Prefer hostname for SSH connection: {hostname}")
    elif address and address.strip():
        host = address
        port = 22
        logs.append(f"[CMD][INFO] Using address (IP) for SSH connection: {address}")
    else:
        host = hostname
        port = 22
        logs.append(f"[CMD][INFO] Using hostname fallback for SSH connection: {hostname}")

    # Get account
    account_id = device.get("account", "")
    accounts = _load_accounts()
    account = next((a for a in accounts if a.get("id") == account_id), None)
    if not account:
        print(json.dumps({"error": "Nie znaleziono przypisanego konta"}, ensure_ascii=False))
        return

    # Check tunnel status
    if os.path.exists(TUNNEL_STATUS_FILE):
        try:
            with open(TUNNEL_STATUS_FILE, "r", encoding="utf-8") as f:
                tunnel = json.load(f)
                if tunnel.get("status") == "CONNECTED":
                    host = "127.0.0.1"
                    port = int(tunnel.get("port", 0))
                    logs.append(f"[TUNNEL][CONFIG] Using tunnel  host=127.0.0.1:{port}")
        except Exception as e:
            logs.append(f"Błąd tunelu: {e}")

    try:
        sock = socket.create_connection((host, port), timeout=5)
        logs.append(f"[SOCKET][SUCCESS] Connection established: {host}:{port}")

        if host == "127.0.0.1":
            target_ip = _pick_tunnel_target(hostname, address)
            header = json.dumps({"target_ip": target_ip, "target_port": 22}) + "\n"
            logs.append(f"[TUNNEL][HEADER] Sending tunnel header: target_ip={target_ip}")
            sock.sendall(header.encode())
            time.sleep(0.02)

        transport = paramiko.Transport(sock)
        transport.banner_timeout = 20
        transport.set_keepalive(30)
        transport.use_compression(True)
        logs.append("[SSH][CONFIG] Set banner_timeout=20s, keepalive=30s, compression=True")

        transport.start_client()
        logs.append("[SSH][START] SSH client started")

        transport.auth_password(username=account["login"], password=account["password"])
        logs.append(f"[AUTH][ATTEMPT] Password auth attempt: {account['login']}")

        if not transport.is_authenticated():
            logs.append("[AUTH][FAIL] Authentication failed")
            raise Exception("Błąd uwierzytelnienia")

        logs.append("[AUTH][SUCCESS] Authentication successful")

        session = transport.open_session()
        # For multi-command batches give the channel enough time per command
        num_commands = max(1, command.count('\n') + 1)
        cmd_timeout = max(10, num_commands * 8)  # 8 s per command, min 10 s
        session.settimeout(cmd_timeout)
        session.get_pty()
        session.invoke_shell()
        logs.append(f"[SSH][SESSION] Session opened with PTY, timeout={cmd_timeout}s (commands={num_commands})")
        time.sleep(0.5)

        # Disable pagination
        session.send("terminal length 0\n")
        time.sleep(0.2)
        session.send("set cli screen-length 0\n")
        time.sleep(0.2)

        # Send command
        session.send(command + "\n")
        time.sleep(0.5)

        # Read full output — allow extra time proportional to number of commands
        num_commands = max(1, command.count('\n') + 1)
        read_timeout = max(10, num_commands * 8)
        raw_output = _read_full_output(session, logs, total_timeout=read_timeout)
        transport.close()

        # Extract loopback IPs
        try:
            extracted_ips = _extract_loopback_ips(raw_output)
        except Exception:
            extracted_ips = []

        # Update device record with discovered addresses
        if extracted_ips:
            try:
                devices = _load_devices()
                dev_id = device.get("id")
                target_idx = None
                for idx, dev in enumerate(devices):
                    if dev_id and dev.get("id") == dev_id:
                        target_idx = idx
                        break
                if target_idx is None:
                    for idx, dev in enumerate(devices):
                        if dev.get("hostname") == device.get("hostname"):
                            target_idx = idx
                            break

                if target_idx is not None:
                    devices[target_idx]["addresses"] = extracted_ips
                    if not devices[target_idx].get("address") and extracted_ips:
                        devices[target_idx]["address"] = extracted_ips[0]
                    _save_devices(devices)
                    logs.append(f"[UPDATE][ADDRESSES] Persisted addresses for device: {extracted_ips}")
            except Exception as e:
                logs.append(f"[UPDATE][ADDRESSES][ERROR] Failed to persist addresses: {e}")

        try:
            host_for_msg = hostname or device.get("hostname")
        except Exception:
            host_for_msg = hostname
        try:
            print(f"[BE] Command executed on device {host_for_msg}", file=sys.stderr, flush=True)
        except Exception:
            pass

        response = {"output": raw_output, "logs": logs}
        if extracted_ips:
            response["addresses"] = extracted_ips

        print(json.dumps(response, ensure_ascii=False))

    except Exception as e:
        error_msg = f"Błąd połączenia lub wykonania komendy: {e}"
        try:
            host_for_msg = hostname or device.get("hostname")
        except Exception:
            host_for_msg = hostname or "<unknown>"
        try:
            print(f"[BE] Failed to execute command on device {host_for_msg} Error: {e}", file=sys.stderr, flush=True)
        except Exception:
            pass
        print(json.dumps({"error": error_msg, "logs": logs}, ensure_ascii=False))


SESSIONS_FILE = os.path.join(BASE_DIR, "src/data/sessions.json")

def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading sessions.json: {e}", file=sys.stderr)
    return {}

def save_sessions(data):
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving sessions.json: {e}", file=sys.stderr)
        return False

def get_session_output(payload):
    session_id = payload.get("session_id")
    sessions = load_sessions()
    session = sessions.get(session_id)
    print(json.dumps({"output": session.get("output", "") if session else ""}, ensure_ascii=False))

def append_to_session_output(payload):
    session_id = payload.get("session_id")
    text = payload.get("text", "")
    sessions = load_sessions()
    if session_id in sessions:
        current = sessions[session_id].get("output", "")
        sessions[session_id]["output"] = current + "\n" + text
        save_sessions(sessions)
        print(json.dumps({"success": True}))
    else:
        print(json.dumps({"success": False, "error": "Session not found"}))

def get_session_by_device_id(payload):
    device_id = payload.get("device_id")
    sessions = load_sessions()
    for session in sessions.values():
        if session.get("device_id") == device_id:
            print(json.dumps(session, ensure_ascii=False))
            return
    print(json.dumps({}))



if __name__ == "__main__":
    method = sys.argv[1] if len(sys.argv) > 1 else "default"
    raw_payload = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        payload = {}


def _load_show_version_from_file(hostname):
    """Wczytuje wynik komendy show version z pliku.
    Obsługuje pliki z nagłówkiem (pierwsze linie zaczynające się od '#') —
    pominie tylko blok nagłówka na początku pliku, a nie komentarze wewnątrz outputu.
    """
    try:
        show_version_dir = os.path.join(BASE_DIR, "src/data/devices_show_version")
        safe_hostname = re.sub(r'[<>:"/\\|?*]', '_', hostname)
        filename = f"sv_{safe_hostname}.txt"
        filepath = os.path.join(show_version_dir, filename)

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Pomiń początkowy blok nagłówka zaczynający się od '#'
            i = 0
            while i < len(lines) and lines[i].strip().startswith('#'):
                i += 1

            # Jeśli za nagłówkiem jest pusta linia — pomiń ją
            if i < len(lines) and lines[i].strip() == '':
                i += 1

            # Zwróć resztę pliku jako tekst
            return ''.join(lines[i:])

        return None
    except Exception:
        return None


def _save_show_version_to_file(hostname, show_version_output):
    """Zapisuje wynik komendy show version do pliku z timestamp"""
    try:
        from datetime import datetime
        
        show_version_dir = os.path.join(BASE_DIR, "src/data/devices_show_version")
        os.makedirs(show_version_dir, exist_ok=True)
        
        safe_hostname = re.sub(r'[<>:"/\\|?*]', '_', hostname)
        filename = f"sv_{safe_hostname}.txt"
        filepath = os.path.join(show_version_dir, filename)
        
        # Utwórz timestamp w formacie czytelnym
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(filepath, "w", encoding="utf-8") as f:
            # Zapisz timestamp w pierwszej linii
            f.write(f"# Data pobrania: {timestamp}\n")
            f.write(f"# Hostname: {hostname}\n")
            f.write("# " + "="*50 + "\n")
            f.write(show_version_output)
    except Exception:
        pass


def update_show_version_files_with_timestamp(payload=None):
    """Aktualizuje istniejące pliki show version dodając timestamp"""
    try:
        from datetime import datetime
        
        show_version_dir = os.path.join(BASE_DIR, "src/data/devices_show_version")
        if not os.path.exists(show_version_dir):
            print("Katalog devices_show_version nie istnieje")
            return
            
        updated_count = 0
        for filename in os.listdir(show_version_dir):
            if filename.startswith("sv_") and filename.endswith(".txt"):
                filepath = os.path.join(show_version_dir, filename)
                
                # Wczytaj plik
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Sprawdź czy już ma timestamp
                if content.startswith("# Data pobrania:"):
                    continue  # Plik już ma timestamp
                
                # Dodaj timestamp
                hostname = filename[3:-4]  # Usuń "sv_" i ".txt"
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                new_content = f"# Data pobrania: {timestamp} (aktualizacja)\n"
                new_content += f"# Hostname: {hostname}\n"
                new_content += "# " + "="*50 + "\n"
                new_content += content
                
                # Zapisz zaktualizowany plik
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                updated_count += 1
                print(f"Zaktualizowano: {filename}")
        
        print(f"Zaktualizowano {updated_count} plików")
        
    except Exception as e:
        print(f"Błąd podczas aktualizacji plików: {str(e)}")


if __name__ == "__main__":

    # Mapa metod CLI do funkcji
    methods = {
        "add_device": add_device,
        "add_devices_bulk": add_devices_bulk,
        "get_all_devices": get_all_devices,
        "get_devices_paginated": get_devices_paginated,
        "delete_device": delete_device,
        "deleteAllWithUnsync": deleteAllWithUnsync,
        "deleteAllWithError": deleteAllWithError,
        "sync_device": sync_device,
        "get_devices_info": get_devices_info,
        "save_devices_info": save_devices_info,
        "update_device": update_device,
        "get_show_version": get_show_version,
        "get_show_version_brief": get_show_version_brief,
        "execute_command_on_device": execute_command_on_device,
        "update_show_version_files_with_timestamp": update_show_version_files_with_timestamp,
        "sync_connections": sync_connections,

        # Nowe funkcje sesji
        "get_session_output": get_session_output,
        "append_to_session_output": append_to_session_output,
        "get_session_by_device_id": get_session_by_device_id,
    }

    func = methods.get(method, default)
    func(payload)


