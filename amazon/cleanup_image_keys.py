#!/usr/bin/env python3
"""
cleanup_image_keys.py

Remove duplicate `Image URL` keys from amazon_combined.json and `Image URL` column from amazon_combined.csv,
standardizing on `ImageURL`.

Creates timestamped backups before writing.
"""

from __future__ import annotations
import json
import csv
import os
from datetime import datetime


def backup_file(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = f"{path}.bak.{ts}"
    os.rename(path, backup)
    return backup


def clean_json(path: str) -> int:
    arr = []
    with open(path, 'r', encoding='utf-8') as fh:
        arr = json.load(fh)
    changed = 0
    for item in arr:
        if 'Image URL' in item:
            # prefer existing ImageURL if present
            if 'ImageURL' not in item or not item.get('ImageURL'):
                item['ImageURL'] = item['Image URL']
            # if they're equal or not, remove 'Image URL'
            del item['Image URL']
            changed += 1
    if changed:
        bak = backup_file(path)
        if bak:
            print('Backed up', path, 'to', bak)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(arr, fh, ensure_ascii=False, indent=2)
    return changed


def clean_csv(path: str) -> int:
    rows = []
    with open(path, 'r', encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        has_image_url_col = 'Image URL' in fieldnames
        if has_image_url_col and 'ImageURL' not in fieldnames:
            fieldnames.append('ImageURL')
        for r in reader:
            if has_image_url_col:
                val = r.get('Image URL', '')
                if val and not r.get('ImageURL'):
                    r['ImageURL'] = val
                if 'Image URL' in r:
                    del r['Image URL']
            r.setdefault('ImageURL', '')
            rows.append(r)
    changed = 1 if has_image_url_col else 0
    if changed:
        bak = backup_file(path)
        if bak:
            print('Backed up', path, 'to', bak)
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    return changed


def main():
    base = os.path.join(os.path.dirname(__file__), 'output')
    json_path = os.path.join(base, 'amazon_combined.json')
    csv_path = os.path.join(base, 'amazon_combined.csv')

    total_json_changed = 0
    total_csv_changed = 0
    if os.path.exists(json_path):
        total_json_changed = clean_json(json_path)
        print(f"Removed 'Image URL' from {total_json_changed} JSON records.")
    else:
        print('amazon_combined.json not found')

    if os.path.exists(csv_path):
        total_csv_changed = clean_csv(csv_path)
        if total_csv_changed:
            print("Removed 'Image URL' column from CSV and consolidated to 'ImageURL'.")
        else:
            print("No 'Image URL' column found in CSV.")

    print('Done.')

if __name__ == '__main__':
    main()
