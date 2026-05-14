import json
import os

STATE_FILE = os.getenv("STATE_FILE", "known_products.json")


def load_known_ids() -> set[str]:
    path = os.getenv("STATE_FILE", STATE_FILE)
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(json.load(f).get("ids", []))


def save_known_ids(ids: set[str]) -> None:
    path = os.getenv("STATE_FILE", STATE_FILE)
    with open(path, "w") as f:
        json.dump({"ids": list(ids)}, f)
