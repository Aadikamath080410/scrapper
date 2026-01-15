import os, requests, time, random, re
from bs4 import BeautifulSoup
from config import HEADERS, SEARCH_URL, MAX_PRODUCTS, REQUEST_DELAY, TIMEOUT, RETRIES, BASE_URL, PROXIES, USE_PLAYWRIGHT, PLAYWRIGHT_TIMEOUT

# Small set of UAs to rotate if we suspect blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
]

session = requests.Session()
session.headers.update(HEADERS)


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
            # Flipkart sometimes needs a bit of scroll or wait
            page.wait_for_timeout(2000)
            content = page.content()
            browser.close()
            return content
    except Exception as e:
        print(f"⚠️ Playwright fetch failed for {url}: {e}")
        return None

def _save_debug_html(query, page, html, prefix="search"):
    os.makedirs("debug", exist_ok=True)
    safe_q = query.replace(' ', '_').lower()
    path = os.path.join("debug", f"{prefix}_{safe_q}_page{page}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🧪 Saved debug HTML → {path}")


def is_blocked(text):
    # Flipkart specific block messages or generic Access Denied
    # "access denied" can be a false positive in normal pages (e.g. within JS or comments)
    # We should look for it in title or h1 if possible, but text search is crude.
    # Let's use more specific phrases or check title.
    if "<title>Access Denied</title>" in text or "<title>Access to this page has been denied</title>" in text:
        return True
    
    blockers = [
        "please ensure you are not using a proxy",
        "browser is being managed by your organization" 
        # Add more specific ones if discovered
    ]
    low = (text or "").lower()
    return any(b in low for b in blockers)


def has_no_results(text):
    low = (text or "").lower()
    phrases = [
        "sorry, no results found",
        "no matches found",
        "did not match any products"
    ]
    return any(p in low for p in phrases)


def _rotate_user_agent():
    ua = random.choice(USER_AGENTS)
    session.headers.update({"User-Agent": ua})


def get_product_links(query):
    product_set = set() # Store tuples of (id, url) or just URLs if unique IDs are hard to get from list
    # Actually, let's store URLs to be consistent. Flipkart URLs usually have a PID or can be unique.
    # Storing (pid, url) might be safer for deduplication if URL varies.
    
    unique_ids = set()
    links = []

    page = 1
    tries = 0
    extra_attempts = 0

    while len(links) < MAX_PRODUCTS:
        url = f"{SEARCH_URL}{query.replace(' ', '+')}&page={page}"
        try:
            # pick a proxy per-request if configured
            proxy = random.choice(PROXIES) if PROXIES else None
            proxies = {"http": proxy, "https": proxy} if proxy else None
            res = session.get(url, timeout=TIMEOUT, proxies=proxies)

            print(f"  [search] {query!r} page {page} — status {res.status_code}")

            if is_blocked(res.text):
                print(f"⚠️ FLIPKART | Block detected for '{query}' (page {page}).")
                _save_debug_html(query, page, res.text)
                
                if USE_PLAYWRIGHT:
                    print(f"ℹ️ FLIPKART | Attempting Playwright fallback after block detection for search page {page} ({query})")
                    html = _fetch_with_playwright(url)
                    if html and not is_blocked(html):
                        soup = BeautifulSoup(html, "html.parser")
                        new_links = extract_links_from_soup(soup)
                        for pid, link in new_links:
                             if pid not in unique_ids:
                                unique_ids.add(pid)
                                links.append(link)
                        
                        if len(new_links) > 0:
                            page += 1
                            time.sleep(REQUEST_DELAY + random.uniform(0.3, 1.2))
                            extra_attempts = 0
                            continue
                
                extra_attempts += 1
                if extra_attempts > RETRIES:
                    print(f"⚠️ FLIPKART | Exhausted rotate attempts for '{query}'")
                    break
                _rotate_user_agent()
                time.sleep(REQUEST_DELAY * extra_attempts + random.uniform(0.5, 1.5))
                continue

            if has_no_results(res.text):
                print(f"ℹ️ FLIPKART | No results found for '{query}' on page {page}.")
                break # usually correct to break here

            soup = BeautifulSoup(res.text, "html.parser")
            new_links = extract_links_from_soup(soup)
            
            # If no links found, might be dynamic loading or layout change
            if not new_links:
                if page == 1:
                     print(f"⚠️ FLIPKART | No product links found on page {page} for '{query}' — possible layout change or block.")
                     _save_debug_html(query, page, res.text)
                     # Attempt playwright fallback just in case
                     if USE_PLAYWRIGHT:
                        print(f"ℹ️ FLIPKART | Attempting Playwright fallback for search page {page} ({query})")
                        html = _fetch_with_playwright(url)
                        if html:
                             soup = BeautifulSoup(html, "html.parser")
                             new_links = extract_links_from_soup(soup)

            for pid, link in new_links:
                if pid not in unique_ids:
                    unique_ids.add(pid)
                    links.append(link)
                    if len(links) >= MAX_PRODUCTS:
                        break
            
            if not new_links and page > 1:
                # End of results likely
                break

            page += 1
            time.sleep(REQUEST_DELAY + random.uniform(0.3, 1.2))
        except Exception as e:
            print(f"⚠️ FLIPKART | Error fetching search page {page} for '{query}': {e}")
            tries += 1
            if tries >= RETRIES:
                break
            time.sleep(REQUEST_DELAY * tries)

    return links[:MAX_PRODUCTS]

def extract_links_from_soup(soup):
    # Flipkart product cards often have data-id attribute
    found = []
    
    # Strategy 1: data-id in div (common in grid views)
    for div in soup.select("div[data-id]"):
        pid = div.get("data-id")
        # find the anchor tag
        a = div.select_one("a")
        if a and a.get("href"):
            href = a.get("href")
            if href.startswith("/"):
                href = BASE_URL + href
            found.append((pid, href))
    
    return found
