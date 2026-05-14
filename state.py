import json
import os

STATE_FILE = os.getenv("STATE_FILE", "known_products.json")


def load_known_ids() -> set[str]:
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE) as f:
        return set(json.load(f).get("ids", []))


def save_known_ids(ids: set[str]) -> None:
    tmp_path = f"{STATE_FILE}.tmp"
    with open(tmp_path, "w") as f:
        json.dump({"ids": list(ids)}, f)
    os.replace(tmp_path, STATE_FILE)
