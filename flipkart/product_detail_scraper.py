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
            soup = None
            
            # Use Playwright if enabled (for JavaScript rendering)
            if USE_PLAYWRIGHT:
                print(f"ℹ️ FLIPKART | Fetching product page with Playwright: {url}")
                html = _fetch_with_playwright(url)
                if html and not is_blocked(html):
                    soup = BeautifulSoup(html, "html.parser")
            
            # Fallback to regular requests if Playwright failed or disabled
            if not soup:
                proxy = random.choice(PROXIES) if PROXIES else None
                proxies = {"http": proxy, "https": proxy} if proxy else None
                res = _session.get(url, timeout=TIMEOUT, proxies=proxies)
                
                if is_blocked(res.text):
                    print(f"⚠️ FLIPKART | Block detected when fetching product page: {url}")
                    _save_debug_product_html(pid, url, res.text)
                    
                    tries += 1
                    time.sleep((2 ** tries) + random.uniform(0.5, 1.5))
                    continue
                
                if res.status_code != 200:
                    print(f"⚠️ FLIPKART | Non-200 response ({res.status_code}) for product page: {url}")
                    tries += 1
                    time.sleep((2 ** tries) + random.uniform(0.5, 1.5))
                    continue
                
                soup = BeautifulSoup(res.text, "html.parser")
            
            # If soup is still None, skip this product
            if not soup:
                tries += 1
                time.sleep((2 ** tries) + random.uniform(0.5, 1.5))
                continue

            def safe_text(sel):
                el = soup.select_one(sel)
                return el.get_text(strip=True) if el else None

            def extract_meta(attr, content_attr='content'):
                """Extract value from meta tag"""
                meta = soup.find('meta', {attr: True})
                if meta and meta.get(content_attr):
                    return meta.get(content_attr)
                return None

            def extract_meta_content(property_or_name, value):
                """Extract content from meta tag by property or name"""
                meta = soup.find('meta', {property_or_name: value})
                if meta and meta.get('content'):
                    return meta.get('content')
                return None

            # Product details
            name = safe_text('span.B_NuCI') or safe_text('h1') or safe_text('[data-qa="productTitle"]') or "NA"
            
            # Rating - try multiple approaches (may not be available in static HTML)
            rating = None
            rating_selectors = [
                'span[data-test-id="average-rating"]',  # Most reliable
                'span._2d4ZZ5',                          # Rating display class
                'div._3LWZlK',                           # Old class
                '[data-qa="reviewRatingDiv"]',
                'span[data-qa="cellReviewRating"]',
                'span.hGSR34',                           # Rating text class
                'div.qMqkX2 span:first-child'           # Context with value
            ]
            for sel in rating_selectors:
                elem = soup.select_one(sel)
                if elem:
                    val = elem.get_text(strip=True)
                    # Clean up the value - should be a number, possibly with "★" or similar
                    val_clean = val.replace('★', '').replace('Rating:', '').strip()
                    if val_clean and val_clean not in ('0', '', 'NA'):
                        try:
                            float(val_clean)
                            rating = val_clean
                            break
                        except:
                            pass
            
            # Set default to 'NA' if not found (ratings may not be available in static HTML)
            if not rating:
                rating = 'NA'
            
            # Price extraction (prioritize meta tags, then DOM)
            price = None
            # Try meta description first (usually contains "Rs.XXXX")
            meta_desc = extract_meta_content('property', 'og:description')
            if meta_desc and 'Rs.' in meta_desc:
                import re as regex_module
                price_match = regex_module.search(r'Rs\.(\d+(?:,\d+)?)', meta_desc)
                if price_match:
                    price = 'Rs.' + price_match.group(1)
            
            # Fallback to DOM selectors
            if not price:
                price_selectors = [
                    'div.Nx9bqj',           # Current class
                    'div.hZ3P6w',           # Variant
                    '[data-qa="finalPrice"]', # Data attribute
                    'div._30jeq3._16Jk6d',  # Old specific
                    'div._30jeq3'           # Old generic
                ]
                for sel in price_selectors:
                    val = safe_text(sel)
                    if val and val != '0':
                        price = val
                        break
            
            # Image extraction (prioritize og:image meta tag)
            img = None
            og_image = extract_meta_content('property', 'og:image')
            if og_image and og_image.startswith('http'):
                img = og_image
            
            # Fallback to DOM selectors
            if not img:
                img_selectors = [
                    'img.xD43kG',       # Observed main image class
                    'img[alt*="product"]',  # Alt attribute match
                    'img.DByuf4',       # Common class
                    'img.UCc1lI',       # Observed class
                    'img[data-qa="productImage"]'
                ]
                for sel in img_selectors:
                    img_tag = soup.select_one(sel)
                    if img_tag:
                        src = img_tag.get('src') or img_tag.get('data-src')
                        if src and src.startswith('http'):
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
    # Look for specification sections with dimension-related content
    # Avoid footer/navigation content by being more selective
    
    candidates = []
    
    # Look for spec titles/labels that contain dimension keywords
    spec_labels = soup.find_all(['div', 'span', 'td', 'th'], 
                                text=lambda t: t and any(kw in t.lower() for kw in ['dimension', 'width', 'height', 'depth', 'length', 'size']))
    
    for label_elem in spec_labels:
        # Get parent context to find the associated value
        parent = label_elem.parent
        if parent:
            # Look for sibling or nearby element with the actual value
            text = label_elem.get_text(strip=True)
            lower_text = text.lower()
            
            # If this is a label (like "Dimensions:"), try to get the value from next element
            if any(x in lower_text for x in ['dimension', 'width', 'height', 'depth', 'length', 'size']):
                # Get text from parent or siblings
                for sibling in parent.find_all(['div', 'span', 'td']):
                    sibling_text = sibling.get_text(strip=True)
                    # Filter out navigation/brand text - should have measurements or numbers
                    if any(measure in sibling_text.lower() for measure in ['cm', 'mm', 'inch', 'ft', 'x ', ' x ', 'l x w x h']):
                        candidates.append(sibling_text)
                    elif any(char.isdigit() for char in sibling_text):  # Has numbers
                        # Avoid long text that looks like page content
                        if len(sibling_text) < 100 and not any(nav_word in sibling_text.lower() 
                             for nav_word in ['brand directory', 'most searched', 'top stories', 'read more', 'online']):
                            candidates.append(sibling_text)
    
    # Clean and deduplicate
    unique_candidates = []
    for c in candidates:
        if c not in unique_candidates and len(c) < 150:  # Reasonable length for dimension specs
            unique_candidates.append(c)
    
    if unique_candidates:
        return " | ".join(unique_candidates[:3])  # Return up to 3 relevant spec lines

    return 'NA'
