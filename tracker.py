import logging
import os
import time

from dotenv import load_dotenv

from notifier import notify
from scraper import fetch_all_products
from state import load_known_ids, save_known_ids

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))


def run_once() -> list[dict]:
    products = fetch_all_products()
    known = load_known_ids()
    new = [p for p in products if p["id"] not in known]
    if new:
        log.info("Found %d new product(s): %s", len(new), [p["title"] for p in new])
        notify(new)
        save_known_ids(known | {p["id"] for p in new})
    else:
        log.info("No new products found.")
    return new


def _seed():
    log.info("First run — seeding known products without notifying.")
    products = fetch_all_products()
    save_known_ids({p["id"] for p in products})
    log.info("Seeded %d products.", len(products))


def main():
    log.info("Drop tracker started. Polling every %ds.", POLL_INTERVAL)
    if not os.path.exists(os.getenv("STATE_FILE", "known_products.json")):
        _seed()
    while True:
        try:
            run_once()
        except Exception as e:
            log.error("Poll error: %s", e)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
