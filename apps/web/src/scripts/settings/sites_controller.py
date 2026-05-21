import json
import os
import sys
import uuid
import re

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DATA_FILE = os.path.join(BASE_DIR, "src/data/sites.json")
POS_FILE = os.path.join(BASE_DIR, "src/data/map_info.json")


def add_site(payload):
    tag = payload.get("site_tag")
    name = payload.get("site_name")
    location = payload.get("location")

    if not all([tag, name, location]):
        print("Brak wymaganych danych.")
        return

    sites = _load_sites()

    new_site = {
        "id": str(uuid.uuid4()),
        "site_tag": tag,
        "site_name": name,
        "location": location
    }

    sites.append(new_site)
    _save_sites(sites)

    # extract coords from location and save to map_info.json
    lat, lon = _extract_coords(location)
    if lat is not None:
        positions = _load_positions()
        positions.append({"id": new_site["id"], "pozycja": {"lat": lat, "lon": lon}})
        _save_positions(positions)

    print("Site added!")


def get_all_sites(_=None):
    sites = _load_sites()
    print(json.dumps(sites, ensure_ascii=False), flush=True)


def delete_site(payload):
    site_id = payload.get("id")
    if not site_id:
        print("Brak ID do usunięcia.")
        return

    sites = _load_sites()
    filtered = [s for s in sites if s.get("id") != site_id]

    if len(filtered) == len(sites):
        print(f"Site o ID {site_id} nie istnieje.")
    else:
        _save_sites(filtered)
        # remove map_info entry as well
        positions = _load_positions()
        positions = [p for p in positions if p.get("id") != site_id]
        _save_positions(positions)
        print(f"Site {site_id} usunięte.")


def update_site(payload):
    site_id = payload.get("id")
    if not site_id:
        print("Brak ID do aktualizacji.")
        return

    sites = _load_sites()
    updated = False
    for s in sites:
        if s.get("id") == site_id:
            # only update provided fields
            for k in ("site_tag", "site_name", "location"):
                if k in payload:
                    s[k] = payload[k]
            updated = True
            break

    if not updated:
        print(f"Site o ID {site_id} nie znaleziono.")
    else:
        _save_sites(sites)
        # if location changed, update map_info.json
        if "location" in payload:
            lat, lon = _extract_coords(payload.get("location", ""))
            if lat is not None:
                positions = _load_positions()
                found = False
                for p in positions:
                    if p.get("id") == site_id:
                        p["pozycja"] = {"lat": lat, "lon": lon}
                        found = True
                        break
                if not found:
                    positions.append({"id": site_id, "pozycja": {"lat": lat, "lon": lon}})
                _save_positions(positions)
        print(f"Site {site_id} zaktualizowane.")


def save_all_sites(payload):
    if not isinstance(payload, list):
        print("Payload musi być listą sites.")
        return

    _save_sites(payload)
    print("Zapisano nową listę sites.")


def _load_sites():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def _load_positions():
    if os.path.exists(POS_FILE):
        try:
            with open(POS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def _save_positions(positions):
    with open(POS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, ensure_ascii=False, indent=2)


def _extract_coords(location):
    if not location or not isinstance(location, str):
        return None, None
    # expect coords in parentheses like "(...lat,lon)"
    m = re.search(r"\(([+-]?\d+\.\d+)\s*,\s*([+-]?\d+\.\d+)\)", location)
    if not m:
        return None, None
    try:
        lat = float(m.group(1))
        lon = float(m.group(2))
        return lat, lon
    except ValueError:
        return None, None


def _save_sites(sites):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(sites, f, ensure_ascii=False, indent=2)


def default(_=None):
    print("Nieznana metoda.")


if __name__ == "__main__":
    method = sys.argv[1] if len(sys.argv) > 1 else "default"
    raw_payload = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        payload = {}

    print(f"[PYTHON] method={method} payload={payload}", file=sys.stderr, flush=True)
    globals().get(method, default)(payload)
