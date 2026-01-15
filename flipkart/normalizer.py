import re

def normalize(product):
    if not product:
        return None

    name = product.get("product_name", "NA")
    if name == "NA" or not name or not name.strip():
        return None

    # Normalize product name
    product["product_name"] = " ".join(name.split())

    # Normalize rating (extract first numeric value)
    rating = product.get("rating", None)
    if rating and isinstance(rating, str):
        m = re.search(r"(\d+(?:\.\d+)?)", rating)
        product["rating"] = float(m.group(1)) if m else None
    elif isinstance(rating, (int, float)):
        product["rating"] = float(rating)
    else:
        product["rating"] = None

    # Normalize price (to integer/float)
    price = product.get("price", None)
    if price and isinstance(price, str):
        p = price.replace("₹", "").replace(",", "").strip()
        p = re.search(r"(\d+[\d\.,]*)", p)
        if p:
            val = p.group(1).replace(',', '')
            try:
                product["price"] = int(float(val))
            except Exception:
                product["price"] = None
        else:
            product["price"] = None
    elif isinstance(price, (int, float)):
        product["price"] = int(price)
    else:
        product["price"] = None

    # Normalize dimensions
    dims = product.get("dimensions", None)
    if not dims or not dims.strip() or dims == "NA":
        product["dimensions"] = "NA"
    else:
        product["dimensions"] = " ".join(dims.split())

    # Image url cleanup
    img = product.get("image_url")
    product["image_url"] = img if img and img != 'NA' else None

    return product
