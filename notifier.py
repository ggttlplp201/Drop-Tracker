import os
import logging
import time
import requests

log = logging.getLogger(__name__)

# Optional catch-all webhook. Stores without a dedicated channel webhook fall
# back to this; it can be unset once every tracked store has its own channel.
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Per-channel webhooks. Each store's drops post to the store's own Discord
# channel (identified by that channel's webhook URL). Any store without a
# dedicated webhook falls back to DISCORD_WEBHOOK_URL. The several
# "2nd Street USA (...)" sites all share one channel.
CHANNEL_WEBHOOKS = {
    "antipromo": os.getenv("DISCORD_WEBHOOK_ANTIPROMO"),
    "lukes": os.getenv("DISCORD_WEBHOOK_LUKES"),
    "2ndstreet": os.getenv("DISCORD_WEBHOOK_2NDSTREET"),
    "chromehearts": os.getenv("DISCORD_WEBHOOK_CHROMEHEARTS"),
}


def _channel_for(site: str) -> str:
    """Map a product's `site` name to a channel key."""
    s = (site or "").strip().lower()
    if s.startswith("2nd street"):
        return "2ndstreet"
    if "anti promo" in s or "antipromo" in s:
        return "antipromo"
    if "luke" in s:
        return "lukes"
    if "chrome" in s:
        return "chromehearts"
    return "default"


def _webhook_for(site: str):
    """Resolve the Discord webhook URL for a site, falling back to the default.

    Returns None if neither a channel-specific webhook nor the catch-all is set.
    """
    return CHANNEL_WEBHOOKS.get(_channel_for(site)) or DISCORD_WEBHOOK_URL


def send_discord(product: dict) -> None:
    webhook = _webhook_for(product["site"])
    if not webhook:
        log.warning("No Discord webhook configured for site %r; skipping %s",
                    product["site"], product.get("title"))
        return
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
        webhook,
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
