import hashlib

def _clean(text):
    if not text:
        return ""
    return (
        text.lower()
            .replace(" ", "")
            .replace(",", "")
            .strip()
    )

def make_key(product):
    name = _clean(product.get("product_name", ""))
    dims = _clean(product.get("dimensions", "NA"))
    raw_key = f"{name}::{dims}"
    return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

def deduplicate(products):
    seen = set()
    unique_products = []

    for product in products:
        key = make_key(product)
        if key not in seen:
            seen.add(key)
            unique_products.append(product)

    return unique_products
