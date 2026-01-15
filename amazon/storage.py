import json
import os

def _transform_for_schema(product):
    # Map internal keys to reference schema
    return {
        "Product ID": product.get("product_id"),
        "Product Name": product.get("product_name"),
        "Product URL": product.get("product_url"),
        "Rating": product.get("rating") if product.get("rating") is not None else 0,
        "Image URL": product.get("image_url"),
        "Dimensions": product.get("dimensions"),
        "Price": product.get("price")
    }

def save_json(data, site, query):
    os.makedirs("output", exist_ok=True)

    filename = f"{site}_{query}.json"
    filename = filename.replace(" ", "_").lower()
    path = os.path.join("output", filename)

    transformed = [_transform_for_schema(p) for p in data]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(transformed, f, indent=2, ensure_ascii=False)

    print(f"💾 Saved {len(transformed)} records → {path}")
