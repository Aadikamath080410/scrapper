HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1"
}

BASE_URL = "https://www.flipkart.com"
SEARCH_URL = "https://www.flipkart.com/search?q="

# Network/config tuning
REQUEST_DELAY = 2
TIMEOUT = 30
RETRIES = 3

# Reduce defaults to limit per-category scraping to ~200-250 items
MIN_PRODUCTS = 100
MAX_PRODUCTS = 100
MAX_RETRIES = 3

# Optional proxy list (leave empty to not use proxies). Format examples:
# ["http://user:pass@host:port", "http://host:port"]
PROXIES = []

# If True and Playwright is installed, the scraper will attempt a headless-browser fallback when
# requests appear blocked. Install with: `pip install playwright` and run `playwright install`.
USE_PLAYWRIGHT = True

# Playwright navigation timeout (ms)
PLAYWRIGHT_TIMEOUT = 30000
