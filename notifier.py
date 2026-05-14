import os
import requests


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
    requests.post(
        os.environ["DISCORD_WEBHOOK_URL"],
        json={"content": f"**{product['site']} Drop!**", "embeds": [embed]},
        timeout=10,
    )


def notify(new_products: list[dict]) -> None:
    for product in new_products:
        send_discord(product)
