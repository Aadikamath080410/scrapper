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
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_navigation_timeout(PLAYWRIGHT_TIMEOUT)
            page.goto(url)
            page.wait_for_timeout(2000)
            content = page.content()
            browser.close()
            return content
    except Exception as e:
        print(f"⚠️ Playwright fetch failed for {url}: {e}")
        return None

def is_blocked(text):
    blockers = [
        "please ensure you are not using a proxy"
    ]
    if "<title>Access Denied</title>" in text:
        return True
        
    low = (text or "").lower()
    return any(b in low for b in blockers)

def _save_debug_product_html(pid, url, html):
    import os
    os.makedirs("debug", exist_ok=True)
    safe_pid = pid or "unknown"
    path = os.path.join("debug", f"flipkart_product_{safe_pid}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!-- URL: {url} -->\n")
        f.write(html)
    print(f"🧪 Saved product debug HTML → {path}")


def scrape_product(url):
    # Extract PID from URL for debugging
    # Flipkart URLs are like /.../p/itm...
    m0 = re.search(r"/(itm[a-zA-Z0-9]+)", url)
    pid = m0.group(1) if m0 else "unknown"

    tries = 0
    while tries < RETRIES:
        try:
            proxy = random.choice(PROXIES) if PROXIES else None
            proxies = {"http": proxy, "https": proxy} if proxy else None
            res = _session.get(url, timeout=TIMEOUT, proxies=proxies)
            
            if is_blocked(res.text):
                print(f"⚠️ FLIPKART | Block detected when fetching product page: {url}")
                _save_debug_product_html(pid, url, res.text)

                if USE_PLAYWRIGHT:
                     print(f"ℹ️ FLIPKART | Attempting Playwright fallback for product page: {url}")
                     html = _fetch_with_playwright(url)
                     if html and not is_blocked(html):
                         soup = BeautifulSoup(html, "html.parser")
                         break
                
                tries += 1
                time.sleep((2 ** tries) + random.uniform(0.5, 1.5))
                continue
            
            if res.status_code != 200:
                print(f"⚠️ FLIPKART | Non-200 response ({res.status_code}) for product page: {url}")
                if USE_PLAYWRIGHT:
                    html = _fetch_with_playwright(url)
                    if html:
                        soup = BeautifulSoup(html, "html.parser")
                    else:
                        soup = BeautifulSoup(res.text, "html.parser")
                else:
                    soup = BeautifulSoup(res.text, "html.parser")
            
            if 'soup' not in locals():
                soup = BeautifulSoup(res.text, "html.parser")

            def safe_text(sel):
                el = soup.select_one(sel)
                return el.get_text(strip=True) if el else None

            # Product details
            name = safe_text('span.B_NuCI') or safe_text('h1') or "NA"
            
            rating = safe_text('div._3LWZlK')
            
            # Price (Try multiple selectors from new to old)
            price = None
            price_selectors = [
                'div.Nx9bqj',       # New common class
                'div.hZ3P6w',       # Observed in debug
                'div._30jeq3._16Jk6d', # Old specific
                'div._30jeq3'       # Old generic
            ]
            for sel in price_selectors:
                val = safe_text(sel)
                if val:
                    price = val
                    break
            
            # Image
            img = None
            img_selectors = [
                 'img.xD43kG',      # Observed on main image
                 'img.DByuf4',      # Common new class
                 'img.UCc1lI',      # Observed but generic
                 'img._396cs4',     # Old
                 'img.q6DClP'       # Old
            ]
            for sel in img_selectors:
                img_tag = soup.select_one(sel)
                if img_tag and img_tag.get('src'):
                    # Filter out tiny base64 or svg if possible, though selectors usually target real imgs
                    src = img_tag.get('src')
                    if src.startswith('http'):
                        img = src
                        break

            # Dimensions
            dimensions = extract_dimensions(soup)

            return {
                'product_id': pid,
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
    
    print(f"⚠️ FLIPKART | Failed to fetch product page: {url}")
    return None

def extract_dimensions(soup):
    # Check specifications table
    # Flipkart uses tables with classes like _14cfVK ensuring rows are div._1s_Smc or tr._1s_Smc
    
    # Text search first as structure varies wildly
    # Look for "Dimensions", "Width", "Height", "Depth" in table/div rows
    
    candidates = []
    
    # Select all rows in specs
    rows = soup.select('div.row') or soup.select('tr')
    
    for row in rows:
        text = row.get_text(separator=' ').strip()
        lower_text = text.lower()
        if 'dimension' in lower_text or ('width' in lower_text and 'height' in lower_text) or ('mm' in lower_text and 'x' in lower_text):
             # Try to clean it up
             # Usually "Width: 10cm"
             candidates.append(text)
    
    if candidates:
        return " | ".join(candidates[:2]) # return top 2 relevant lines

    return 'NA'
