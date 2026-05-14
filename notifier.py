import os
import logging
import time
import requests

log = logging.getLogger(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
if not DISCORD_WEBHOOK_URL:
    raise ValueError("DISCORD_WEBHOOK_URL environment variable is required")


def send_discord(product: dict) -> None:
    price_str = f"${product['price']}" if product.get("price") else "Price N/A"
    embed = {
        "title": product["title"],
        "url": product["url"],
        "description": price_str,
        "color": 0x000000,
        "footer": {"text": product["site"]},
    }
    if product.get("image_url"):
        embed["image"] = {"url": product["image_url"]}
    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json={"content": f"**{product['site']} Drop!**", "embeds": [embed]},
        timeout=10,
    )
    response.raise_for_status()


def notify(new_products: list[dict]) -> None:
    for index, product in enumerate(new_products):
        try:
            send_discord(product)
        except Exception as e:
            log.warning("Could not notify Discord for %s: %s", product.get("title"), e)
        if index < len(new_products) - 1:
            time.sleep(1)
