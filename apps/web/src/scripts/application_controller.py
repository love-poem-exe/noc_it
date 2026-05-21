import json
import os
import sys
import shutil

# ——————————————————————————————————————————————————————————————————————
# Wymuśmy UTF-8 na stdout, żeby nie było UnicodeEncodeError przy drukowaniu nie-ASCII znaków
if hasattr(sys.stdout, "reconfigure"):
    # dla Pythona ≥3.7
    sys.stdout.reconfigure(encoding="utf-8")
else:
    os.environ["PYTHONIOENCODING"] = "utf-8"
# ——————————————————————————————————————————————————————————————————————

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def cleanup_temp_folder(payload=None):
    """Usuwa cały folder temp i jego zawartość, potem odtwarza pusty folder"""
    try:
        temp_dir = os.path.join(BASE_DIR, "src/data/temp")
        
        if os.path.exists(temp_dir):
            # Usuń cały folder i jego zawartość
            shutil.rmtree(temp_dir)
            print(f"[CLEANUP] Removed temp folder: {temp_dir}")
        
        # Odtwórz pusty folder
        os.makedirs(temp_dir, exist_ok=True)
        print(f"[CLEANUP] Created empty temp folder: {temp_dir}")
        
        print(json.dumps({"status": "OK", "message": "Temp folder cleaned successfully"}, ensure_ascii=False))
        
    except Exception as e:
        error_msg = f"Error cleaning temp folder: {str(e)}"
        print(f"[CLEANUP] {error_msg}")
        print(json.dumps({"status": "ERROR", "message": error_msg}, ensure_ascii=False))


def default(payload=None):
    """Nieznana metoda"""
    print(json.dumps({"status": "ERROR", "message": "Unknown method"}, ensure_ascii=False))


if __name__ == "__main__":
    method = sys.argv[1] if len(sys.argv) > 1 else "default"
    raw_payload = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        payload = {}

    # Mapa metod CLI do funkcji
    methods = {
        "cleanup_temp_folder": cleanup_temp_folder,
    }

    func = methods.get(method, default)
    func(payload)
