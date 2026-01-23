import requests
from bs4 import BeautifulSoup

# Use a known product URL
url = "https://www.flipkart.com/astride-ergofit-ergonomic-high-back-synchro-tilt-mechanism-heavy-duty-metal-base-mesh-office-adjustable-arm-chair/p/itm596f97149920c?pid=OSCH29QQWTKJRWXH&lid=LSTOSCH29QQWTKJRWXHHR6HHM&marketplace=FLIPKART&q=office+chair&store=wwe%2Fy7b%2Ffoc&spotlightTagId=default_FkPickId_wwe%2Fy7b%2Ffoc&srno=s_1_1&otracker=search&fm=organic&iid=ba1a1a2b-bf3f-4f77-aa4c-81372d0e5f38.OSCH29QQWTKJRWXH.SEARCH&ppt=None&ppn=None&ssid=dzk0mm2m1s0000001769113945811&qH=4fbd54b24e553ac8"

if True:
    print(f"Fetching: {url}\n")
    
    # Try regular request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    res = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {res.status_code}")
    
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Try finding product title with various selectors
    selectors = [
        'span.B_NuCI',
        'h1',
        '[data-qa="productTitle"]',
        '.titlewrap',
        'h2.BvBATd'
    ]
    
    print("\nTesting selectors:")
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            print(f"  {sel}: FOUND - {el.get_text(strip=True)[:80]}")
        else:
            print(f"  {sel}: NOT FOUND")
    
    # Check if this is a block page
    title = soup.find('title')
    if title:
        print(f"\nPage title: {title.get_text()}")
    
    # Look for any h1 on the page
    h1 = soup.find('h1')
    if h1:
        print(f"Found h1: {h1.get_text()[:100]}")
