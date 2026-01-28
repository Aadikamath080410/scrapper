import json
import re

# Read the combined JSON file
with open('flipkart/output/flipkart_combined.json', 'r') as f:
    data = json.load(f)

# Clean dimensions by removing kg parts
for item in data:
    for dim_key in ['Dimensions', 'Dimension']:
        if dim_key in item:
            dimensions = str(item[dim_key])
            # Remove any segment with 'kg' in it
            if 'kg' in dimensions.lower():
                # Split by | and filter out segments with 'kg'
                parts = [p.strip() for p in dimensions.split('|')]
                cleaned_parts = [p for p in parts if 'kg' not in p.lower()]
                item[dim_key] = ' | '.join(cleaned_parts) if cleaned_parts else dimensions

# Save the cleaned data to flipkart folder
with open('flipkart/flipkart_combined_cleaned.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f'✓ Processed: {len(data)} products')
print(f'✓ Removed kg from dimensions')
print(f'✓ Saved to: flipkart/flipkart_combined_cleaned.json')
