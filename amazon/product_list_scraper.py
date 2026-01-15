import os, requests, time, random, re
from bs4 import BeautifulSoup
from config import HEADERS, SEARCH_URL, MAX_PRODUCTS, REQUEST_DELAY, TIMEOUT, RETRIES, BASE_URL, PROXIES, USE_PLAYWRIGHT, PLAYWRIGHT_TIMEOUT

# Small set of UAs to rotate if we suspect blocking
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
    blockers = [
        "detected unusual traffic",
        "enter the characters you see",
        "robot check",
        "are you a human",
        "type the characters",
        "access to this page has been denied"
    ]
    low = (text or "").lower()
    return any(b in low for b in blockers)


def has_no_results(text):
    low = (text or "").lower()
    phrases = [
        "did not match any products",
        "no results for",
        "did not match any results"
    ]
    return any(p in low for p in phrases)


def _rotate_user_agent():
    ua = random.choice(USER_AGENTS)
    session.headers.update({"User-Agent": ua})


def get_product_links(query):
    asin_set = set()
    page = 1
    tries = 0
    extra_attempts = 0

    while len(asin_set) < MAX_PRODUCTS:
        url = f"{SEARCH_URL}{query.replace(' ', '+')}&page={page}"
        try:
            # pick a proxy per-request if configured
            proxy = random.choice(PROXIES) if PROXIES else None
            proxies = {"http": proxy, "https": proxy} if proxy else None
            res = session.get(url, timeout=TIMEOUT, proxies=proxies)

            # Quick status reporting
            print(f"  [search] {query!r} page {page} — status {res.status_code} — len {len(res.text)}")

            if is_blocked(res.text):
                print(f"⚠️ AMAZON | Block detected for '{query}' (page {page}).")
                _save_debug_html(query, page, res.text)
                
                if USE_PLAYWRIGHT:
                    print(f"ℹ️ AMAZON | Attempting Playwright fallback after block detection for search page {page} ({query})")
                    html = _fetch_with_playwright(url)
                    if html and not is_blocked(html):
                        soup = BeautifulSoup(html, "html.parser")
                        # attempt to extract ASINs from playwright HTML
                        for el in soup.select("[data-asin]"):
                            asin = el.get("data-asin")
                            if asin and re.match(r"^[A-Z0-9]{8,}$", asin):
                                asin_set.add(asin)
                                if len(asin_set) >= MAX_PRODUCTS:
                                    break
                        if asin_set:
                            page += 1
                            time.sleep(REQUEST_DELAY + random.uniform(0.3, 1.2))
                            # reset retries if successful
                            extra_attempts = 0
                            continue
                
                # rotate UA and retry a limited number of times
                extra_attempts += 1
                if extra_attempts > RETRIES:
                    print(f"⚠️ AMAZON | Exhausted rotate attempts for '{query}'")
                    break
                _rotate_user_agent()
                time.sleep(REQUEST_DELAY * extra_attempts + random.uniform(0.5, 1.5))
                continue

            if has_no_results(res.text):
                print(f"ℹ️ AMAZON | No results found for '{query}' on page {page}.")
                _save_debug_html(query, page, res.text)
                # try Playwright fallback for this search page if enabled
                if USE_PLAYWRIGHT:
                    print(f"ℹ️ AMAZON | Attempting Playwright fallback for search page {page} ({query})")
                    html = _fetch_with_playwright(url)
                    if html:
                        soup = BeautifulSoup(html, "html.parser")
                        # attempt to extract ASINs from playwright HTML
                        for el in soup.select("[data-asin]"):
                            asin = el.get("data-asin")
                            if asin and re.match(r"^[A-Z0-9]{8,}$", asin):
                                asin_set.add(asin)
                                if len(asin_set) >= MAX_PRODUCTS:
                                    break
                        if asin_set:
                            page += 1
                            time.sleep(REQUEST_DELAY + random.uniform(0.3, 1.2))
                            continue
                break

            soup = BeautifulSoup(res.text, "html.parser")

            # Preferred: extract ASINs from any element with data-asin attribute
            for el in soup.select("[data-asin]"):
                asin = el.get("data-asin")
                if asin and re.match(r"^[A-Z0-9]{8,}$", asin):
                    asin_set.add(asin)
                    if len(asin_set) >= MAX_PRODUCTS:
                        break

            # Fallback: anchor-based dp links (extract ASIN and canonicalize)
            if len(asin_set) < MAX_PRODUCTS:
                for a in soup.select("a[href*='/dp/']"):
                    href = a.get("href")
                    if not href:
                        continue
                    m = re.search(r"/dp/([A-Z0-9]{8,})", href)
                    if m:
                        asin_set.add(m.group(1))
                    if len(asin_set) >= MAX_PRODUCTS:
                        break

            # If we reached page 1 and found nothing, save debug HTML to investigate
            if page == 1 and not asin_set:
                print(f"⚠️ AMAZON | No product links found on page {page} for '{query}' — possible layout change or block.")
                _save_debug_html(query, page, res.text)
                # try rotating UA and retry once
                extra_attempts += 1
                if extra_attempts <= RETRIES:
                    print(f"ℹ️ AMAZON | Rotating UA and retrying for '{query}' (attempt {extra_attempts})")
                    _rotate_user_agent()
                    time.sleep(REQUEST_DELAY + random.uniform(0.5, 1.0))
                    continue
                break

            page += 1
            time.sleep(REQUEST_DELAY + random.uniform(0.3, 1.2))
        except Exception as e:
            print(f"⚠️ AMAZON | Error fetching search page {page} for '{query}': {e}")
            tries += 1
            if tries >= RETRIES:
                break
            time.sleep(REQUEST_DELAY * tries)

    # Build canonical URLs from ASINs
    links = [f"{BASE_URL}/dp/{asin}" for asin in asin_set]
    return links 
