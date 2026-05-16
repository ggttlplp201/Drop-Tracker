import logging
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Shopify sites: fetched via /products.json with HTML fallback
SHOPIFY_SITES = [
    {
        "name": "Anti Promo",
        "shopify_url": "https://antipromo.com/products.json",
        "fallback_url": "https://antipromo.com/collections/all",
        "base_url": "https://antipromo.com",
    },
    {
        "name": "Lukes",
        "shopify_url": "https://lukes.store/collections/newest-items/products.json",
        "fallback_url": "https://lukes.store/collections/newest-items?usf_take=56",
        "base_url": "https://lukes.store",
    },
]

# Homepage-monitored sites: new drops appear as new links on the homepage
HOMEPAGE_SITES = [
    {
        "name": "Chrome Hearts",
        "homepage_url": "https://www.chromehearts.com/",
        "base_url": "https://www.chromehearts.com",
    },
]


def fetch_all_products() -> list[dict]:
    results = []
    for site in SHOPIFY_SITES:
        results.extend(_fetch_shopify_site(site))
    for site in HOMEPAGE_SITES:
        results.extend(_fetch_homepage_site(site))
    return results


def _fetch_shopify_site(site: dict) -> list[dict]:
    try:
        r = requests.get(site["shopify_url"], timeout=10, headers=HEADERS)
        if r.status_code == 200:
            return [
                {
                    "id": f"{site['name']}:{p['id']}",
                    "handle": p["handle"],
                    "title": p["title"],
                    "price": p["variants"][0]["price"] if p.get("variants") else None,
                    "image_url": p["images"][0]["src"] if p.get("images") else None,
                    "url": f"{site['base_url']}/products/{p['handle']}",
                    "site": site["name"],
                }
                for p in r.json().get("products", [])
            ]
    except Exception as e:
        log.debug("Could not fetch Shopify JSON for %s: %s", site["name"], e)
    try:
        return _scrape_shopify_html(site)
    except Exception as e:
        log.warning("Could not fetch %s: %s", site["name"], e)
        return []


def _scrape_shopify_html(site: dict) -> list[dict]:
    r = requests.get(site["fallback_url"], timeout=10, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    seen = set()
    products = []
    for a in soup.select("a[href*='/products/']"):
        href = a.get("href", "")
        handle = href.split("/products/")[-1].split("?")[0].strip("/")
        if not handle or handle in seen:
            continue
        seen.add(handle)
        products.append({
            "id": f"{site['name']}:{handle}",
            "handle": handle,
            "title": a.get_text(strip=True) or handle,
            "price": None,
            "image_url": None,
            "url": f"{site['base_url']}/products/{handle}",
            "site": site["name"],
        })
    return products


def _fetch_homepage_site(site: dict) -> list[dict]:
    try:
        r = requests.get(site["homepage_url"], timeout=10, headers=HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        products = []
        for a in soup.find_all("a", href=True):
            href = a["href"].split("?")[0].rstrip("/")
            if not href.startswith("/"):
                continue
            if href in seen:
                continue
            seen.add(href)
            title = a.get_text(strip=True) or href.strip("/").replace("-", " ").title()
            products.append({
                "id": f"{site['name']}:{href}",
                "handle": href.strip("/"),
                "title": title,
                "price": None,
                "image_url": None,
                "url": f"{site['base_url']}{href}",
                "site": site["name"],
            })
        return products
    except Exception as e:
        log.warning("Could not fetch %s: %s", site["name"], e)
        return []
