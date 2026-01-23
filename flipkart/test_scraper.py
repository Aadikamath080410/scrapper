from product_detail_scraper import scrape_product
from product_list_scraper import get_product_links

links = get_product_links('office chair')[:5]
count = 0
for i, link in enumerate(links, 1):
    details = scrape_product(link)
    name = details.get('Product Name', 'ERROR')[:50]
    dims = details.get('Dimensions', 'N/A')
    print(f'{i}. {name}... | Dims: {dims}')
    if name and dims and dims != 'N/A':
        count += 1
print(f'\nValid products: {count}/{len(links)}')
