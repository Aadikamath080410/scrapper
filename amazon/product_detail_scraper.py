import re, json, time, random
import requests
from bs4 import BeautifulSoup
from config import HEADERS, TIMEOUT, RETRIES, BASE_URL, PROXIES, USE_PLAYWRIGHT, PLAYWRIGHT_TIMEOUT

_session = requests.Session()
_session.headers.update(HEADERS)


def _fetch_with_playwright(url):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("⚠️ Playwright not available. Install with: pip install playwright && playwright install")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_navigation_timeout(PLAYWRIGHT_TIMEOUT)
            page.goto(url)
            content = page.content()
            browser.close()
            return content
    except Exception as e:
        print(f"⚠️ Playwright fetch failed for {url}: {e}")
        return None

def is_blocked(text):
    blockers = [
        "detected unusual traffic",
        "enter the characters you see",
        "robot check",
        "type the characters",
        "are you a human"
    ]
    low = (text or "").lower()
    return any(b in low for b in blockers)

def _save_debug_product_html(asin, url, html):
    import os
    os.makedirs("debug", exist_ok=True)
    safe_asin = asin or "unknown"
    path = os.path.join("debug", f"product_{safe_asin}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!-- URL: {url} -->\n")
        f.write(html)
    print(f"🧪 Saved product debug HTML → {path}")


def scrape_product(url):
    # Always canonicalize to BASE_URL/dp/ASIN if ASIN present
    m0 = re.search(r"/dp/([A-Z0-9]{8,})", url)
    asin = m0.group(1) if m0 else None
    if asin:
        url = f"{BASE_URL}/dp/{asin}"

    tries = 0
    while tries < RETRIES:
        try:
            proxy = random.choice(PROXIES) if PROXIES else None
            proxies = {"http": proxy, "https": proxy} if proxy else None
            res = _session.get(url, timeout=TIMEOUT, proxies=proxies)
            if is_blocked(res.text):
                print(f"⚠️ AMAZON | Block detected when fetching product page: {url} — status {res.status_code}")
                _save_debug_product_html(asin or 'unknown', url, res.text)

                if USE_PLAYWRIGHT:
                     print(f"ℹ️ AMAZON | Attempting Playwright fallback for product page: {url}")
                     html = _fetch_with_playwright(url)
                     if html and not is_blocked(html):
                         soup = BeautifulSoup(html, "html.parser")
                         # break out of retry loop to process soup
                         break
                
                tries += 1
                wait = (2 ** tries) + random.uniform(0.5, 1.5)
                time.sleep(wait)
                continue
            # If we get non-200, save HTML for inspection
            if res.status_code != 200:
                print(f"⚠️ AMAZON | Non-200 response ({res.status_code}) for product page: {url}")
                _save_debug_product_html(asin or 'unknown', url, res.text)
                # attempt Playwright fallback if enabled
                if USE_PLAYWRIGHT:
                    html = _fetch_with_playwright(url)
                    if html:
                        soup = BeautifulSoup(html, "html.parser")
                    else:
                        soup = BeautifulSoup(res.text, "html.parser")
                else:
                    soup = BeautifulSoup(res.text, "html.parser")
            # normal case: parse response text
            if 'soup' not in locals():
                soup = BeautifulSoup(res.text, "html.parser")

            def safe_text(sel):
                el = soup.select_one(sel)
                return el.get_text(strip=True) if el else None

            # Product ID (ASIN) — prefer the canonical one
            m = re.search(r"/dp/([A-Z0-9]{8,})", url)
            asin = m.group(1) if m else None

            # Product name
            name = safe_text('#productTitle') or safe_text('span#title') or safe_text('h1') or "NA"

            # Rating: try multiple places, then fallback to ld+json
            rating = safe_text('span.a-icon-alt') or safe_text('#acrPopover')
            if not rating:
                # JSON-LD
                ld = soup.find('script', type='application/ld+json')
                if ld:
                    try:
                        data = json.loads(ld.string)
                        if isinstance(data, dict):
                            ar = data.get('aggregateRating') or {}
                            rating = ar.get('ratingValue')
                    except Exception:
                        rating = None

            # Price
            price = safe_text('#priceblock_ourprice') or safe_text('#priceblock_dealprice') or safe_text('span.a-price > span.a-offscreen') or safe_text('span.a-price-whole') or None

            # Image
            img = None
            img_tag = soup.select_one('#imgTagWrapperId img') or soup.select_one('#landingImage') or soup.select_one('img#imgBlkFront')
            if img_tag:
                img = img_tag.get('data-old-hires') or img_tag.get('data-a-dynamic-image') or img_tag.get('src')
                if isinstance(img, str) and img.startswith('{'):
                    # sometimes data-a-dynamic-image is JSON
                    try:
                        d = json.loads(img)
                        img = list(d.keys())[0] if d else None
                    except Exception:
                        pass

            # Dimensions
            dimensions = extract_dimensions(soup)

            return {
                'product_id': asin,
                'product_name': name,
                'product_url': url,
                'rating': rating or 'NA',
                'price': price or 'NA',
                'dimensions': dimensions or 'NA',
                'image_url': img or 'NA'
            }
        except Exception as e:
            tries += 1
            time.sleep((2 ** tries) + random.uniform(0.1, 0.5))
    print(f"⚠️ AMAZON | Failed to fetch product page: {url}")
    return None

def extract_dimensions(soup):
    # Look through product details tables
    selectors = [
        '#productDetails_techSpec_section_1',
        '#productDetails_detailBullets_sections1',
        '#productDetailsTable',
        '#detailBullets_feature_div',
        '#technicalSpecifications_feature_div'
    ]

    for sel in selectors:
        node = soup.select_one(sel)
        if node:
            text = node.get_text(separator=' ').strip()
            for label in ['Product Dimensions', 'Dimensions', 'Item Dimensions', 'Package Dimensions']:
                if label.lower() in text.lower():
                    m = re.search(r"(Product Dimensions|Dimensions|Item Dimensions|Package Dimensions)[^:\n]*[:\n\t]*([^\n\r]+)", text, re.IGNORECASE)
                    if m:
                        return m.group(2).strip()
            # fallback: try to find 'cm' with 'x'
            if 'cm' in text.lower() and 'x' in text.lower():
                m2 = re.search(r"([0-9\.,]+\s?cm[^;\n\r]*)", text, re.IGNORECASE)
                if m2:
                    return m2.group(1).strip()

    # Last resort: scan rows and list items
    for row in soup.select('tr'):
        if 'dimensions' in row.get_text(strip=True).lower() or 'product dimensions' in row.get_text(strip=True).lower():
            return row.get_text(separator=' ').strip()

    for li in soup.select('li'):
        t = li.get_text(strip=True)
        if ('cm' in t.lower() and 'x' in t.lower()) or 'dimensions' in t.lower():
            return t

    return 'NA' 
