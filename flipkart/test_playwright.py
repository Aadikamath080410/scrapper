from playwright.sync_api import sync_playwright

url = "https://www.flipkart.com/astride-ergofit-ergonomic-high-back-synchro-tilt-mechanism-heavy-duty-metal-base-mesh-office-adjustable-arm-chair/p/itm596f97149920c?pid=OSCH29QQWTKJRWXH"

print(f"Fetching with Playwright: {url}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_navigation_timeout(30000)
    page.goto(url)
    page.wait_for_timeout(2000)  # Wait for JS rendering
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page.content(), "html.parser")
    
    # Test various selectors
    selectors = [
        'span.B_NuCI',
        'h1',
        '[data-qa="productTitle"]',
        '.titlewrap',
        'h2.BvBATd',
        'span[itemprop="name"]',
        '.XiG87f',  # Random modern class
        '[data-test="product-title"]',
    ]
    
    print("Testing selectors:")
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(strip=True)[:80]
            print(f"  ✓ {sel}: {text}")
        else:
            print(f"  ✗ {sel}: NOT FOUND")
    
    # Look for all text nodes that might be the title
    print("\n\nLooking for any h-tags:")
    for tag in ['h1', 'h2', 'h3', 'h4']:
        for el in soup.find_all(tag):
            text = el.get_text(strip=True)
            if text and len(text) > 20:  # Likely title
                print(f"{tag}: {text[:100]}")
                break
    
    # Try to find title in meta tags
    title_meta = soup.find('meta', {'property': 'og:title'})
    if title_meta and title_meta.get('content'):
        print(f"\nog:title: {title_meta.get('content')[:100]}")
    
    browser.close()
