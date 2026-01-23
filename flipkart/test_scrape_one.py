from product_detail_scraper import scrape_product
from product_list_scraper import get_product_links

print("Getting product links...")
links = get_product_links('office chair')[:1]

if links:
    print(f"Scraping first product...")
    result = scrape_product(links[0])
    if result:
        print(f"Product Name: {result.get('product_name')[:80] if result.get('product_name') else 'N/A'}")
        print(f"Price: {result.get('price')}")
        print(f"Dimensions: {result.get('dimensions')}")
        print(f"Rating: {result.get('rating')}")
        print(f"Image URL: {result.get('image_url')[:80] if result.get('image_url') else 'N/A'}")
    else:
        print("ERROR: scrape_product returned None")
else:
    print("ERROR: No links found")
