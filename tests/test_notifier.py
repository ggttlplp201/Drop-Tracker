import os
from unittest.mock import patch

os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test")

import notifier
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


def test_routes_each_store_to_its_own_webhook(monkeypatch):
    monkeypatch.setattr(notifier, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/default")
    monkeypatch.setattr(notifier, "CHANNEL_WEBHOOKS", {
        "antipromo": "https://discord.com/api/webhooks/antipromo",
        "lukes": "https://discord.com/api/webhooks/lukes",
        "2ndstreet": "https://discord.com/api/webhooks/2ndstreet",
        "chromehearts": "https://discord.com/api/webhooks/chromehearts",
    })
    cases = {
        "Anti Promo": "https://discord.com/api/webhooks/antipromo",
        "Lukes": "https://discord.com/api/webhooks/lukes",
        "2nd Street USA (Balenciaga)": "https://discord.com/api/webhooks/2ndstreet",
        " 2nd Street USA (Sacai)": "https://discord.com/api/webhooks/2ndstreet",  # leading space tolerated
        "Chrome Hearts": "https://discord.com/api/webhooks/chromehearts",
    }
    for site, expected in cases.items():
        with patch("notifier.requests.post") as mock_post:
            notifier.send_discord({**PRODUCT, "site": site})
        assert mock_post.call_args[0][0] == expected, site


def test_unconfigured_store_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(notifier, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/default")
    monkeypatch.setattr(notifier, "CHANNEL_WEBHOOKS", {"chromehearts": None})
    with patch("notifier.requests.post") as mock_post:
        notifier.send_discord(PRODUCT)  # Chrome Hearts, no dedicated webhook set
    assert mock_post.call_args[0][0] == "https://discord.com/api/webhooks/default"


def test_skips_when_no_webhook_resolves(monkeypatch):
    # No default and no channel webhook: skip silently instead of crashing.
    monkeypatch.setattr(notifier, "DISCORD_WEBHOOK_URL", None)
    monkeypatch.setattr(notifier, "CHANNEL_WEBHOOKS", {"chromehearts": None})
    with patch("notifier.requests.post") as mock_post:
        notifier.send_discord(PRODUCT)
    mock_post.assert_not_called()
