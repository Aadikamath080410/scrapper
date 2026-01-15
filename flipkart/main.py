import argparse
from query_loader import load_queries
from product_list_scraper import get_product_links
from product_detail_scraper import scrape_product
from normalizer import normalize
from deduplicator import deduplicate
from storage import save_json
from utils import to_float, to_int
import config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Maximum number of products to collect per query (for testing)')
    parser.add_argument('--verbose', action='store_true', help='Show per-product progress')
    parser.add_argument('--use-playwright', action='store_true', help='Enable Playwright fallback if available')
    parser.add_argument('--proxies-file', type=str, help='Path to a newline-separated proxy list (optional)')
    args = parser.parse_args()

    cfg = load_queries()
    queries = [q["query"] for q in cfg["searchQueries"]]
    min_rating = cfg["settings"]["minRating"]
    # allow runtime override of config module flags
    if args.use_playwright:
        config.USE_PLAYWRIGHT = True

    if args.proxies_file:
        try:
            with open(args.proxies_file, 'r', encoding='utf-8') as pf:
                proxies = [l.strip() for l in pf.readlines() if l.strip()]
                config.PROXIES = proxies
                print(f"🔁 Loaded {len(proxies)} proxies from {args.proxies_file}")
        except Exception as e:
            print(f"⚠️ Could not read proxies file: {e}")

    limit = args.limit if args.limit is not None else config.MIN_PRODUCTS

    for query in queries:
        print(f"\n🟦 FLIPKART | {query}")
        results = []

        links = get_product_links(query)
        print(f"🔗 Found {len(links)} product links for query: {query}")

        for idx, link in enumerate(links, start=1):
            if args.verbose or idx % 10 == 0:
                print(f"  → Processing {idx}/{len(links)} — collected {len(results)}/{limit}")

            try:
                raw = scrape_product(link)
                clean = normalize(raw)
            except Exception as e:
                print(f"⚠️ FLIPKART | Error scraping {link}: {e}")
                continue

            if not clean:
                continue

            rating = to_float(clean["rating"]) if clean.get("rating") is not None else None
            if rating and rating < min_rating:
                continue

            clean["rating"] = rating
            # price already normalized to int in normalize
            results.append(clean)

            if args.verbose:
                name = clean.get("product_name") or "(no-name)"
                print(f"    + {len(results)}: {name[:80]} — {clean.get('product_id')}")

            if len(results) >= limit:
                break

        final = deduplicate(results)
        if not final:
            print(f"⚠️ FLIPKART | No products collected for '{query}' (skipping save).")
            continue
        save_json(final, "flipkart", query)
        print(f"✅ Flipkart {query}: {len(final)} products")

if __name__ == "__main__":
    main()
