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
    {
        "name": "2nd Street USA (Balenciaga)",
        "shopify_url": "https://ec.2ndstreetusa.com/products.json?limit=250",
        "fallback_url": "https://ec.2ndstreetusa.com/pages/search-results-page?q=balenciaga&sort_by=created",
        "base_url": "https://ec.2ndstreetusa.com",
        "vendor_filter": "BALENCIAGA",
    },
    {
        "name": "2nd Street USA (Junya Watanabe)",
        "shopify_url": "https://ec.2ndstreetusa.com/collections/comme-des-garcons-1/products.json?limit=250",
        "fallback_url": "https://ec.2ndstreetusa.com/pages/search-results-page?q=junya%20watanabe",
        "base_url": "https://ec.2ndstreetusa.com",
        "vendor_filter": ["JUNYA WATANABE COMME des GARCONS", "JUNYA WATANABE COMME des GARCONS MAN"],
    },
    {
        "name": "2nd Street USA (Yohji Yamamoto)",
        "shopify_url": "https://ec.2ndstreetusa.com/collections/yohji-yamamoto/products.json?limit=250",
        "fallback_url": "https://ec.2ndstreetusa.com/pages/search-results-page?q=yohji%20yamamoto",
        "base_url": "https://ec.2ndstreetusa.com",
        "vendor_filter": [
            "YOHJI YAMAMOTO",
            "B Yohji Yamamoto",
            "yohji yamamoto POUR HOMME",
            "Yohji Yamamoto D'URBAN A.A.R",
        ],
    },
    {
        "name": "2nd Street USA (Maison Margiela)",
        "shopify_url": "https://ec.2ndstreetusa.com/collections/maison-margiela/products.json?limit=250",
        "fallback_url": "https://ec.2ndstreetusa.com/collections/maison-margiela?sort_by=published",
        "base_url": "https://ec.2ndstreetusa.com",
        "vendor_filter": ["Maison Margiela", "Maison Martin Margiela"],
    },
]

# Sites tracked via Shopify's /search/suggest.json (used when a brand has no
# dedicated collection and its items are too sparse in /products.json).
SEARCH_SITES = [
    {
        "name": "2nd Street USA (Sacai)",
        "search_url": "https://ec.2ndstreetusa.com/search/suggest.json?q=sacai&resources[type]=product&resources[limit]=10",
        "base_url": "https://ec.2ndstreetusa.com",
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
    for site in SEARCH_SITES:
        results.extend(_fetch_search_site(site))
    for site in HOMEPAGE_SITES:
        results.extend(_fetch_homepage_site(site))
    return results


def _fetch_shopify_site(site: dict) -> list[dict]:
    raw_filter = site.get("vendor_filter")
    if isinstance(raw_filter, str):
        vendor_filter = {raw_filter.upper()}
    elif raw_filter:
        vendor_filter = {v.upper() for v in raw_filter}
    else:
        vendor_filter = set()
    try:
        r = requests.get(site["shopify_url"], timeout=10, headers=HEADERS)
        if r.status_code == 200:
            products = r.json().get("products", [])
            if vendor_filter:
                products = [p for p in products if (p.get("vendor") or "").upper() in vendor_filter]
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
                for p in products
            ]
    except Exception as e:
        log.debug("Could not fetch Shopify JSON for %s: %s", site["name"], e)
    if vendor_filter:
        log.warning("Could not fetch %s: JSON endpoint failed and HTML fallback cannot apply vendor filter", site["name"])
        return []
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


def _fetch_search_site(site: dict) -> list[dict]:
    try:
        r = requests.get(site["search_url"], timeout=10, headers=HEADERS)
        r.raise_for_status()
        products = r.json().get("resources", {}).get("results", {}).get("products", [])
        return [
            {
                "id": f"{site['name']}:{p['id']}",
                "handle": p.get("handle"),
                "title": p.get("title"),
                "price": p.get("price"),
                "image_url": p.get("image") or p.get("featured_image"),
                "url": f"{site['base_url']}{p['url'].split('?')[0]}" if p.get("url") else None,
                "site": site["name"],
            }
            for p in products
        ]
    except Exception as e:
        log.warning("Could not fetch %s: %s", site["name"], e)
        return []


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
