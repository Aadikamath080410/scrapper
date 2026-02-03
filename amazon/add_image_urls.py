#!/usr/bin/env python3
"""
add_image_urls.py

Scan all category JSON files in amazon/output, build a mapping of Product ID -> Image URL
and add an `ImageURL` field to entries in amazon_combined.json and a new `ImageURL` column
in amazon_combined.csv. Does not run any normalizers.

Usage:
    python add_image_urls.py [--output-dir path/to/amazon/output] [--dry-run]

"""

from __future__ import annotations
import os
import json
import csv
import re
import argparse
from datetime import datetime

ID_RE = re.compile(r"/dp/([^/?#]+)")


def extract_asin_from_url(url: str) -> str | None:
    if not url:
        return None
    m = ID_RE.search(url)
    if m:
        return m.group(1)
    # fallback: last path segment
    parts = url.rstrip('/').split('/')
    if parts:
        cand = parts[-1]
        if len(cand) >= 5:
            return cand
    return None


def load_json_file(path: str) -> list[dict]:
    with open(path, 'r', encoding='utf-8') as fh:
        try:
            data = json.load(fh)
            if isinstance(data, list):
                return data
            # Some files might contain dict wrapper
            return data.get('products', []) if isinstance(data, dict) else []
        except Exception as e:
            print(f"WARN: failed to parse JSON {path}: {e}")
            return []


def build_image_map(output_dir: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    for fname in files:
        if fname.startswith('amazon_combined'):
            continue
        path = os.path.join(output_dir, fname)
        arr = load_json_file(path)
        for item in arr:
            # try several possible keys
            pid = None
            for k in ('Product ID', 'ProductID', 'product_id', 'asin'):
                if k in item and item[k]:
                    pid = str(item[k]).strip()
                    break
            if not pid:
                # try to extract from Product URL
                url_keys = ('Product URL', 'ProductURL', 'product_url', 'ProductUrl')
                for uk in url_keys:
                    if uk in item and item[uk]:
                        pid = extract_asin_from_url(item[uk])
                        break
            if not pid:
                continue
            # image url key
            img = None
            for ik in ('Image URL', 'ImageURL', 'image_url', 'image'):
                if ik in item and item[ik]:
                    img = item[ik].strip()
                    break
            if img:
                # prefer the first found image for a given pid
                if pid not in mapping:
                    mapping[pid] = img
    return mapping


def backup_file(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = f"{path}.bak.{ts}"
    os.rename(path, backup)
    return backup


def update_combined_json(output_dir: str, mapping: dict[str, str], dry_run: bool = False) -> int:
    combined_path = os.path.join(output_dir, 'amazon_combined.json')
    if not os.path.exists(combined_path):
        print('ERROR: combined JSON not found at', combined_path)
        return 0
    arr = load_json_file(combined_path)
    updated = 0
    for item in arr:
        # find product URL or ID
        pid = None
        if 'ProductURL' in item and item['ProductURL']:
            pid = extract_asin_from_url(item['ProductURL'])
        if not pid and 'ProductURL' in item and item['ProductURL']:
            pid = extract_asin_from_url(item['ProductURL'])
        if not pid and 'ID' in item and item['ID']:
            # ID in combined is internal like A-0001, so skip
            pid = None
        img = mapping.get(pid) if pid else None
        if img:
            # add both forms for compatibility
            if item.get('ImageURL') != img:
                item['ImageURL'] = img
                item['Image URL'] = img
                updated += 1
    if not dry_run:
        bak = backup_file(combined_path)
        if bak:
            print('Backed up', combined_path, 'to', bak)
        with open(combined_path, 'w', encoding='utf-8') as fh:
            json.dump(arr, fh, ensure_ascii=False, indent=2)
    return updated


def update_combined_csv(output_dir: str, mapping: dict[str, str], dry_run: bool = False) -> int:
    csv_path = os.path.join(output_dir, 'amazon_combined.csv')
    if not os.path.exists(csv_path):
        print('WARN: combined CSV not found at', csv_path)
        return 0
    updated = 0
    rows = []
    with open(csv_path, 'r', encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        # add ImageURL if missing
        if 'ImageURL' not in fieldnames:
            fieldnames.append('ImageURL')
        for r in reader:
            url = r.get('ProductURL') or r.get('Product URL') or ''
            pid = extract_asin_from_url(url)
            img = mapping.get(pid) if pid else ''
            if img:
                r['ImageURL'] = img
                updated += 1
            else:
                r.setdefault('ImageURL', '')
            rows.append(r)
    if not dry_run:
        bak = backup_file(csv_path)
        if bak:
            print('Backed up', csv_path, 'to', bak)
        with open(csv_path, 'w', encoding='utf-8', newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    return updated


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output-dir', default=os.path.join(os.path.dirname(__file__), 'output'))
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    output_dir = args.output_dir
    print(f"Scanning JSON files in {output_dir} to build product image mapping...")
    mapping = build_image_map(output_dir)
    print(f"Found {len(mapping)} products with images in output files. ✅")

    print('Updating amazon_combined.json...')
    jupdated = update_combined_json(output_dir, mapping, dry_run=args.dry_run)
    print(f"Updated {jupdated} records in amazon_combined.json.")

    print('Updating amazon_combined.csv...')
    cupdated = update_combined_csv(output_dir, mapping, dry_run=args.dry_run)
    print(f"Updated {cupdated} records in amazon_combined.csv.")

    print('\nDone.')
    print('Notes:')
    print('- A backup is created for any updated combined file (timestamped .bak).')
    print('- Use --dry-run to preview actions without writing files.')


if __name__ == '__main__':
    main()
