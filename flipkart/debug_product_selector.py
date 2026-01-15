import requests
from bs4 import BeautifulSoup

URL = "https://www.flipkart.com/iafa-diego-mid-back-ergonomic-office-heavy-duty-black-metal-base-mesh-arm-chair/p/itm1c2aebbc7770d?pid=OSCHYGJDKFJZRPG8&lid=LSTOSCHYGJDKFJZRPG8TLG0PX&marketplace=FLIPKART"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def fetch_and_analyze():
    print(f"Fetching {URL}...")
    try:
        res = requests.get(URL, headers=HEADERS, timeout=15)
        print(f"Status: {res.status_code}")
        
        with open("flipkart/debug_product_page.html", "w", encoding="utf-8") as f:
            f.write(res.text)
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Current selectors check
        price = soup.select_one('div._30jeq3._16Jk6d') or soup.select_one('div._30jeq3')
        print(f"Current Price Selector: {price.get_text() if price else 'NOT FOUND'}")
        
        img = soup.select_one('img._396cs4') or soup.select_one('img.q6DClP')
        print(f"Current Image Selector: {img.get('src') if img else 'NOT FOUND'}")

        # Try to find price broadly
        # New Flipkart price class is often Nx9bqj CxhGGd
        price_candidates = soup.find_all(string=lambda t: '₹' in t if t else False)
        print("\n--- Price Candidates ---")
        for p in price_candidates[:5]:
            parent = p.parent
            print(f"Found '₹': {p} inside <{parent.name} class='{' '.join(parent.get('class', []))}'>")

        # Try to find images
        print("\n--- Image Candidates ---")
        imgs = soup.select('img')
        for i, img in enumerate(imgs):
            src = img.get('src', '')
            if 'image' in src and 'http' in src:
                 print(f"Img {i}: Class={img.get('class')} Src={src[:100]}...")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_and_analyze()
