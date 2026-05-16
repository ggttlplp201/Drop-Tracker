from unittest.mock import MagicMock, patch

from scraper import (
    fetch_all_products,
    _fetch_shopify_site,
    _fetch_homepage_site,
    _fetch_search_site,
    SHOPIFY_SITES,
    HOMEPAGE_SITES,
    SEARCH_SITES,
)


def _mock_shopify_response(products):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"products": products}
    return m


SAMPLE_PRODUCT = {
    "id": 123,
    "handle": "silver-ring",
    "title": "Silver Ring",
    "variants": [{"price": "250.00"}],
    "images": [{"src": "https://cdn.shopify.com/image.jpg"}],
}


def test_shopify_site_returns_price_and_image():
    site = SHOPIFY_SITES[0]  # Anti Promo
    with patch("scraper.requests.get", return_value=_mock_shopify_response([SAMPLE_PRODUCT])):
        products = _fetch_shopify_site(site)
    p = products[0]
    assert p["title"] == "Silver Ring"
    assert p["price"] == "250.00"
    assert p["image_url"] == "https://cdn.shopify.com/image.jpg"
    assert p["url"] == "https://antipromo.com/products/silver-ring"
    assert p["site"] == "Anti Promo"
    assert p["id"] == "Anti Promo:123"


def test_shopify_site_handles_missing_image_and_price():
    site = SHOPIFY_SITES[0]
    product = {"id": 456, "handle": "cap", "title": "Cap", "variants": [], "images": []}
    with patch("scraper.requests.get", return_value=_mock_shopify_response([product])):
        products = _fetch_shopify_site(site)
    assert products[0]["price"] is None
    assert products[0]["image_url"] is None


def test_shopify_site_falls_back_to_html():
    site = SHOPIFY_SITES[0]
    mock_shopify = MagicMock()
    mock_shopify.status_code = 404
    html = '<a href="/products/cross-pendant">Cross Pendant</a>'
    mock_html = MagicMock()
    mock_html.text = html
    with patch("scraper.requests.get", side_effect=[mock_shopify, mock_html]):
        products = _fetch_shopify_site(site)
    assert any(p["handle"] == "cross-pendant" for p in products)


def test_shopify_site_returns_empty_on_total_failure():
    site = SHOPIFY_SITES[0]
    with patch("scraper.requests.get", side_effect=Exception("network error")):
        products = _fetch_shopify_site(site)
    assert products == []


def test_homepage_site_detects_new_links():
    site = HOMEPAGE_SITES[0]  # Chrome Hearts
    html = """
    <a href="/hoodie">Hoodie</a>
    <a href="/hoodie">Hoodie</a>
    <a href="/socks">Socks</a>
    <a href="https://external.com">External</a>
    """
    mock_resp = MagicMock()
    mock_resp.text = html
    with patch("scraper.requests.get", return_value=mock_resp):
        products = _fetch_homepage_site(site)
    handles = [p["handle"] for p in products]
    assert "hoodie" in handles
    assert "socks" in handles
    assert handles.count("hoodie") == 1  # deduped
    assert all(p["url"].startswith("https://www.chromehearts.com") for p in products)


def test_homepage_site_returns_empty_on_failure():
    site = HOMEPAGE_SITES[0]
    with patch("scraper.requests.get", side_effect=Exception("timeout")):
        products = _fetch_homepage_site(site)
    assert products == []


def _product_passing_filter(site):
    p = dict(SAMPLE_PRODUCT)
    vf = site.get("vendor_filter")
    if isinstance(vf, str):
        p["vendor"] = vf
    elif vf:
        p["vendor"] = vf[0]
    return p


def _mock_search_response(products):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"resources": {"results": {"products": products}}}
    return m


def test_fetch_all_products_covers_both_sites():
    shopify_responses = [_mock_shopify_response([_product_passing_filter(s)]) for s in SHOPIFY_SITES]
    search_responses = [
        _mock_search_response([{
            "id": 999,
            "handle": "search-item",
            "title": "Search Item",
            "price": "10.00",
            "image": "https://example.com/img.jpg",
            "url": "/products/search-item",
            "vendor": "TestVendor",
        }])
        for _ in SEARCH_SITES
    ]
    html = '<a href="/hoodie">Hoodie</a>'
    homepage_responses = []
    for _ in HOMEPAGE_SITES:
        m = MagicMock()
        m.text = html
        homepage_responses.append(m)
    with patch("scraper.requests.get", side_effect=shopify_responses + search_responses + homepage_responses):
        products = fetch_all_products()
    sites = {p["site"] for p in products}
    for site in SHOPIFY_SITES:
        assert site["name"] in sites
    for site in SEARCH_SITES:
        assert site["name"] in sites
    for site in HOMEPAGE_SITES:
        assert site["name"] in sites


def test_search_site_normalizes_suggest_response():
    site = {
        "name": "Sacai",
        "search_url": "https://example.com/search/suggest.json?q=sacai",
        "base_url": "https://example.com",
    }
    raw = [{
        "id": 42,
        "handle": "abc",
        "title": "Sacai Jacket",
        "price": "199.00",
        "image": "https://example.com/img.jpg",
        "url": "/products/abc?_pos=1&_psq=sacai",
        "vendor": "Sacai",
    }]
    with patch("scraper.requests.get", return_value=_mock_search_response(raw)):
        results = _fetch_search_site(site)
    assert len(results) == 1
    p = results[0]
    assert p["id"] == "Sacai:42"
    assert p["title"] == "Sacai Jacket"
    assert p["price"] == "199.00"
    assert p["image_url"] == "https://example.com/img.jpg"
    assert p["url"] == "https://example.com/products/abc"
    assert p["site"] == "Sacai"


def test_search_site_returns_empty_on_failure():
    site = {
        "name": "Sacai",
        "search_url": "https://example.com/search/suggest.json?q=sacai",
        "base_url": "https://example.com",
    }
    with patch("scraper.requests.get", side_effect=Exception("network error")):
        assert _fetch_search_site(site) == []


def test_shopify_site_applies_vendor_filter():
    site = {
        "name": "Filtered",
        "shopify_url": "https://example.com/products.json",
        "fallback_url": "https://example.com/all",
        "base_url": "https://example.com",
        "vendor_filter": "BALENCIAGA",
    }
    products = [
        {"id": 1, "handle": "bal-shoe", "title": "Bal Shoe", "vendor": "BALENCIAGA", "variants": [], "images": []},
        {"id": 2, "handle": "nike-shoe", "title": "Nike Shoe", "vendor": "NIKE", "variants": [], "images": []},
        {"id": 3, "handle": "bal-bag", "title": "Bal Bag", "vendor": "balenciaga", "variants": [], "images": []},
    ]
    with patch("scraper.requests.get", return_value=_mock_shopify_response(products)):
        results = _fetch_shopify_site(site)
    handles = {p["handle"] for p in results}
    assert handles == {"bal-shoe", "bal-bag"}


def test_shopify_site_vendor_filter_accepts_list():
    site = {
        "name": "Junya",
        "shopify_url": "https://example.com/products.json",
        "fallback_url": "https://example.com/all",
        "base_url": "https://example.com",
        "vendor_filter": ["JUNYA WATANABE COMME des GARCONS", "JUNYA WATANABE COMME des GARCONS MAN"],
    }
    products = [
        {"id": 1, "handle": "j1", "title": "J1", "vendor": "JUNYA WATANABE COMME des GARCONS", "variants": [], "images": []},
        {"id": 2, "handle": "j2", "title": "J2", "vendor": "JUNYA WATANABE COMME des GARCONS MAN", "variants": [], "images": []},
        {"id": 3, "handle": "x",  "title": "X",  "vendor": "NIKE", "variants": [], "images": []},
    ]
    with patch("scraper.requests.get", return_value=_mock_shopify_response(products)):
        results = _fetch_shopify_site(site)
    assert {p["handle"] for p in results} == {"j1", "j2"}
