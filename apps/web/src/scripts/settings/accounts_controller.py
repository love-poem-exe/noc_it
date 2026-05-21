import json
import os
import sys
import uuid

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DATA_FILE = os.path.join(BASE_DIR, "src/data/accounts.json")


def add_account(payload):
    name = payload.get("name")
    login = payload.get("login")
    password = payload.get("password")

    if not all([name, login, password]):
        print("Brak wymaganych danych.")
        return

    accounts = _load_accounts()

    new_account = {
        "id": str(uuid.uuid4()),
        "name": name,
        "login": login,
        "password": password
    }

    accounts.append(new_account)
    _save_accounts(accounts)

    print("Account added!")


def get_all_accounts(_=None):
    accounts = _load_accounts()
    # Print to stdout for backend to capture
    print(json.dumps(accounts, ensure_ascii=False), flush=True)


def delete_account(payload):
    account_id = payload.get("id")
    if not account_id:
        print("Brak ID do usunięcia.")
        return

    accounts = _load_accounts()
    filtered = [acc for acc in accounts if acc.get("id") != account_id]

    if len(filtered) == len(accounts):
        print(f"Konto o ID {account_id} nie istnieje.")
    else:
        _save_accounts(filtered)
        print(f"Konto {account_id} usunięte.")


def save_all_accounts(payload):
    if not isinstance(payload, list):
        print("Payload musi być listą kont.")
        return

    _save_accounts(payload)
    print("Zapisano nową listę kont.")


# --- Wewnętrzne pomocnicze funkcje ---

def _load_accounts():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def _save_accounts(accounts):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def default(_=None):
    print("Nieznana metoda.")


if __name__ == "__main__":
    method = sys.argv[1] if len(sys.argv) > 1 else "default"
    raw_payload = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        payload = {}

    # Add debug print to see what is called and with what payload
    print(f"[PYTHON] method={method} payload={payload}", file=sys.stderr, flush=True)
    globals().get(method, default)(payload)
