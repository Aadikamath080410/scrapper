import json
import os
from pathlib import Path

def clean_text(text):
    """Remove [U+200E] and other unwanted characters"""
    if isinstance(text, str):
        # Remove U+200E (right-to-left mark) and other invisible Unicode characters
        text = text.replace('\u200e', '')
        text = text.replace('\u200f', '')
        text = text.replace('\u202a', '')
        text = text.replace('\u202b', '')
        text = text.replace('\u202c', '')
        text = text.replace('\u202d', '')
        text = text.replace('\u202e', '')
        text = text.strip()
    return text

def extract_subtype_from_filename(filename):
    """Extract subtype from filename (e.g., 'bookshelf' from 'amazon_bookshelf.json')"""
    name = filename.replace('amazon_', '').replace('.json', '')
    return name

def get_type_from_subtype(subtype):
    """Map subtype to type based on categorization"""
    type_mapping = {
        # Table types
        'dining_table': 'Table',
        'study_table': 'Table',
        'coffee_table': 'Table',
        'casual_table': 'Table',
        'tea_table': 'Table',
        
        # Chair types
        'dining_chair': 'Chair',
        'casual_chair': 'Chair',
        'gaming_chair': 'Chair',
        'office_chair': 'Chair',
        'rocking_chair': 'Chair',
        
        # Bed types
        'bed': 'Bed',
        'double_bed': 'Bed',
        'queen_size_bed': 'Bed',
        'king_size_bed': 'Bed',
        'single_bed': 'Bed',
        
        # Sofa types
        'sofa': 'Sofa',
        'recliner_sofa': 'Sofa',
        'sofa_cum_bed': 'Sofa',
        'sofa_set': 'Sofa',
        
        # Storage types
        'storage': 'Storage',
        'bookshelf': 'Storage',
        'wardrobe': 'Storage',
        'cupboard': 'Storage',
        'cabinet': 'Storage',
        'shoe_rack': 'Storage',
    }
    
    return type_mapping.get(subtype, '')

def process_output_files():
    """Process all JSON files from output folder and combine them"""
    output_dir = Path(__file__).parent / 'output'
    combined_products = []
    product_id_counter = 1
    
    # Get all JSON files sorted (exclude combined file to avoid reprocessing)
    json_files = sorted([f for f in output_dir.glob('amazon_*.json') if 'combined' not in f.name])
    
    print(f"Found {len(json_files)} files to process")
    
    for json_file in json_files:
        subtype = extract_subtype_from_filename(json_file.name)
        print(f"Processing: {json_file.name} (subtype: {subtype})")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            for product in products:
                product_name = clean_text(product.get('Product Name', ''))
                
                # Skip products with empty names
                if not product_name:
                    continue
                
                processed_product = {
                    'ID': f'A-{product_id_counter:04d}',
                    'Name': product_name,
                    'Dimension': clean_text(product.get('Dimensions', '')),
                    'Price': product.get('Price', ''),
                    'Type': get_type_from_subtype(subtype),
                    'SubType': subtype,
                    'Brand': '',  # Extract from product name if applicable
                    'ProductURL': clean_text(product.get('Product URL', ''))
                }
                
                combined_products.append(processed_product)
                product_id_counter += 1
        
        except json.JSONDecodeError as e:
            print(f"Error processing {json_file.name}: {e}")
        except Exception as e:
            print(f"Unexpected error processing {json_file.name}: {e}")
    
    return combined_products

def save_combined_output(products):
    """Save combined products to a single JSON file"""
    output_file = Path(__file__).parent / 'output' / 'amazon_combined.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    
    print(f"\nCombined {len(products)} products")
    print(f"Product IDs: A-0001 to A-{len(products):04d}")
    print(f"Saved to: {output_file}")

def save_csv_output(products):
    """Save combined products to CSV for easier viewing"""
    import csv
    output_file = Path(__file__).parent / 'output' / 'amazon_combined.csv'
    
    if not products:
        print("No products to save")
        return
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['ID', 'Name', 'Dimension', 'Price', 'Type', 'SubType', 'Brand', 'ProductURL']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(products)
    
    print(f"CSV saved to: {output_file}")

if __name__ == '__main__':
    print("Starting Amazon product finisher...\n")
    
    # Process all output files
    combined_products = process_output_files()
    
    # Save outputs
    save_combined_output(combined_products)
    save_csv_output(combined_products)
    
    print("\nFinisher completed!")
