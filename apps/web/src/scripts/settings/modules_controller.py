import json
import os
import sys

# ——————————————————————————————————————————————————————————————————————
# Wymuśmy UTF-8 na stdout, żeby nie było UnicodeEncodeError przy drukowaniu nie-ASCII znaków
if hasattr(sys.stdout, "reconfigure"):
    # dla Pythona ≥3.7
    sys.stdout.reconfigure(encoding="utf-8")
else:
    os.environ["PYTHONIOENCODING"] = "utf-8"
# ——————————————————————————————————————————————————————————————————————

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
SETTINGS_FILE = os.path.join(BASE_DIR, "src/data/settings.json")

def save_app_settings(payload):
    """Zapisuje ustawienia aplikacji do pliku settings.json"""
    try:
        # Upewnij się że katalog istnieje
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        
        # Zapisz ustawienia do pliku
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)
        
        print(f"[SAVE APP SETTINGS] Settings saved to {SETTINGS_FILE}")
        print(json.dumps({"success": True, "message": "Ustawienia zostały zapisane"}, ensure_ascii=False))
        
    except Exception as e:
        error_msg = f"Error saving app settings: {e}"
        print(f"[SAVE APP SETTINGS] {error_msg}")
        print(json.dumps({"success": False, "error": error_msg}, ensure_ascii=False))

def load_app_settings(payload=None):
    """Wczytuje ustawienia aplikacji z pliku settings.json"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                print(f"[LOAD APP SETTINGS] Settings loaded from {SETTINGS_FILE}")
                print(json.dumps(settings, ensure_ascii=False))
                return settings
        else:
            # Domyślne ustawienia
            default_settings = {
                "cmtsTmpfs": {
                    "hoursBack": 24
                },
                "general": {
                    "autoRefresh": True,
                    "debugMode": False
                }
            }
            print(f"[LOAD APP SETTINGS] No settings file found, using defaults")
            print(json.dumps(default_settings, ensure_ascii=False))
            return default_settings
    except Exception as e:
        error_msg = f"Error loading app settings: {e}"
        print(f"[LOAD APP SETTINGS] {error_msg}")
        print(json.dumps({"success": False, "error": error_msg}, ensure_ascii=False))

def default(payload=None):
    """Domyślna funkcja - wczytuj ustawienia"""
    return load_app_settings(payload)

if __name__ == "__main__":
    method = sys.argv[1] if len(sys.argv) > 1 else "load_app_settings"
    raw_payload = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        payload = {}

    # Mapa metod CLI do funkcji
    methods = {
        "save_app_settings": save_app_settings,
        "load_app_settings": load_app_settings,
    }

    func = methods.get(method, default)
    func(payload)