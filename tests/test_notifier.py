import os
from unittest.mock import patch

os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test")

from notifier import notify, send_discord

PRODUCT = {
    "title": "Silver Ring",
    "handle": "silver-ring",
    "price": "250.00",
    "image_url": "https://cdn.shopify.com/image.jpg",
    "url": "https://www.chromehearts.com/products/silver-ring",
    "site": "Chrome Hearts",
}

PRODUCT_NO_IMAGE = {**PRODUCT, "image_url": None, "price": None}


def test_notify_sends_discord_per_product():
    products = [PRODUCT, {**PRODUCT, "title": "Chain", "site": "Anti Promo"}]
    with patch("notifier.send_discord") as mock_discord:
        notify(products)
    assert mock_discord.call_count == 2


def test_discord_embed_includes_image_and_price(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test")
    with patch("notifier.requests.post") as mock_post:
        send_discord(PRODUCT)
    embed = mock_post.call_args[1]["json"]["embeds"][0]
    assert embed["title"] == "Silver Ring"
    assert embed["image"]["url"] == "https://cdn.shopify.com/image.jpg"
    assert "$250.00" in embed["description"]


def test_discord_embed_skips_image_when_none(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test")
    with patch("notifier.requests.post") as mock_post:
        send_discord(PRODUCT_NO_IMAGE)
    embed = mock_post.call_args[1]["json"]["embeds"][0]
    assert "image" not in embed
    assert "Price N/A" in embed["description"]
