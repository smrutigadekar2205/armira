#!/usr/bin/env python3
"""
Script to download sample clothing images and generate sensible metadata.
"""

import os
import json
import random
import time
import requests
from pathlib import Path

# Configuration
GARMENT_FOLDER = os.path.join(os.path.dirname(__file__), 'web', 'static', 'uploads', 'garments')
METADATA_FILE = os.path.join(GARMENT_FOLDER, 'metadata.json')

# Free clothing image URLs (Unsplash)
CLOTHING_IMAGES = {
    # Tops
    'white_tshirt_s.jpg': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop',
    'white_tshirt_m.jpg': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop',
    'white_tshirt_l.jpg': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop',
    'black_tshirt_s.jpg': 'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400&h=400&fit=crop',
    'black_tshirt_m.jpg': 'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400&h=400&fit=crop',
    'black_tshirt_l.jpg': 'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400&h=400&fit=crop',
    'striped_shirt_m.jpg': 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop',
    'denim_shirt_l.jpg': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=400&h=400&fit=crop',
    'hoodie_xl.jpg': 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=400&h=400&fit=crop',

    # Bottoms
    'blue_jeans_30.jpg': 'https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop',
    'blue_jeans_32.jpg': 'https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop',
    'blue_jeans_34.jpg': 'https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop',
    'black_chinos_32.jpg': 'https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=400&h=400&fit=crop',
    'khaki_shorts_32.jpg': 'https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=400&h=400&fit=crop',

    # Dresses
    'floral_dress_s.jpg': 'https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=400&h=400&fit=crop',
    'floral_dress_m.jpg': 'https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=400&h=400&fit=crop',
    'little_black_dress_m.jpg': 'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=400&fit=crop',
    'maxi_dress_l.jpg': 'https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=400&h=400&fit=crop',

    # Outerwear
    'denim_jacket_m.jpg': 'https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=400&h=400&fit=crop',
    'leather_jacket_l.jpg': 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400&h=400&fit=crop',
    'winter_coat_xl.jpg': 'https://images.unsplash.com/photo-1544923246-77307dd628b1?w=400&h=400&fit=crop',
    'blazer_m.jpg': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop',

    # Accessories/Other
    'polo_shirt_m.jpg': 'https://images.unsplash.com/photo-1625910513413-5fc2a643c9a7?w=400&h=400&fit=crop',
    'sweater_l.jpg': 'https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=400&h=400&fit=crop',
    'tank_top_s.jpg': 'https://images.unsplash.com/photo-1562157873-818bc0726f68?w=400&h=400&fit=crop',
    'cardigan_m.jpg': 'https://images.unsplash.com/photo-1620799140408-ed5341cd2431?w=400&h=400&fit=crop',
}

# Size measurements (in cm)
SIZE_MEASUREMENTS = {
    'S': {'chest': (84, 92), 'waist': (68, 76), 'length': (64, 70)},
    'M': {'chest': (92, 100), 'waist': (76, 84), 'length': (68, 74)},
    'L': {'chest': (100, 110), 'waist': (84, 94), 'length': (72, 78)},
    'XL': {'chest': (110, 120), 'waist': (94, 104), 'length': (74, 80)},
}

# Price ranges by category (in USD)
PRICE_RANGES = {
    'Tops': (25, 89),
    'Bottoms': (35, 120),
    'Dresses': (45, 180),
    'Outerwear': (60, 250),
    'Accessories': (15, 75),
}

# Materials by category
MATERIALS = {
    'Tops': ['100% Cotton', 'Cotton Blend', 'Premium Modal', 'Organic Cotton', 'Bamboo Fiber'],
    'Bottoms': ['Denim', 'Cotton Twill', 'Stretch Cotton', 'Polyester Blend', 'Canvas'],
    'Dresses': ['Silk Blend', 'Cotton Poplin', 'Rayon', 'Linen', 'Viscose'],
    'Outerwear': ['Wool Blend', 'Cotton Canvas', 'Polyester Fleece', 'Genuine Leather', 'Technical Fabric'],
    'Accessories': ['Cotton', 'Merino Wool', 'Cashmere Blend', 'Synthetic Blend'],
}

def get_size_from_filename(filename):
    """Extract size from filename."""
    filename_lower = filename.lower()

    # Check for standard sizes
    if '_s.jpg' in filename_lower or '_s.png' in filename_lower:
        return 'S'
    elif '_m.jpg' in filename_lower or '_m.png' in filename_lower:
        return 'M'
    elif '_l.jpg' in filename_lower or '_l.png' in filename_lower:
        return 'L'
    elif '_xl.jpg' in filename_lower or '_xl.png' in filename_lower:
        return 'XL'

    # Check for pant sizes (waist in inches)
    for waist in range(28, 42):
        if f'_{waist}.' in filename_lower:
            # Convert waist inches to size
            if waist <= 30:
                return 'S'
            elif waist <= 32:
                return 'M'
            elif waist <= 34:
                return 'L'
            else:
                return 'XL'

    return 'M'  # Default

def get_category_from_filename(filename):
    """Extract category from filename."""
    filename_lower = filename.lower()

    if 'tshirt' in filename_lower or 'shirt' in filename_lower or 'hoodie' in filename_lower or 'sweater' in filename_lower or 'top' in filename_lower or 'polo' in filename_lower or 'tank' in filename_lower or 'cardigan' in filename_lower:
        return 'Tops'
    elif 'jeans' in filename_lower or 'chinos' in filename_lower or 'shorts' in filename_lower or 'pant' in filename_lower:
        return 'Bottoms'
    elif 'dress' in filename_lower:
        return 'Dresses'
    elif 'jacket' in filename_lower or 'coat' in filename_lower or 'blazer' in filename_lower:
        return 'Outerwear'

    return 'Tops'  # Default

def generate_measurements(size):
    """Generate random measurements for a given size."""
    ranges = SIZE_MEASUREMENTS[size]
    return {
        'chest': random.randint(ranges['chest'][0], ranges['chest'][1]),
        'waist': random.randint(ranges['waist'][0], ranges['waist'][1]),
        'length': random.randint(ranges['length'][0], ranges['length'][1])
    }

def generate_price(category):
    """Generate a random price for a category."""
    price_range = PRICE_RANGES.get(category, (30, 100))
    return random.randint(price_range[0], price_range[1])

def generate_material(category):
    """Generate a material for a category."""
    materials = MATERIALS.get(category, MATERIALS['Tops'])
    return random.choice(materials)

def download_image(url, filepath):
    """Download an image from URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            f.write(response.content)

        print(f"✓ Downloaded: {os.path.basename(filepath)}")
        return True
    except Exception as e:
        print(f"✗ Failed to download {url}: {e}")
        return False

def generate_metadata(filename):
    """Generate metadata for a garment."""
    size = get_size_from_filename(filename)
    category = get_category_from_filename(filename)

    # Decide if standard or custom (80% standard)
    is_custom = random.random() < 0.2

    metadata = {
        'size_type': 'custom' if is_custom else 'standard',
        'category': category,
        'size': size,
        'uploaded_at': time.time(),
        'price': f"${generate_price(category)}.00",
        'material': generate_material(category)
    }

    if is_custom:
        metadata['measurements'] = generate_measurements(size)

    return metadata

def main():
    """Main function."""
    print("📦 Downloading clothing dataset...")
    print(f"   Target folder: {GARMENT_FOLDER}")
    print(f"   Images to download: {len(CLOTHING_IMAGES)}")
    print()

    # Ensure folder exists
    os.makedirs(GARMENT_FOLDER, exist_ok=True)

    # Load existing metadata
    existing_metadata = {}
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            existing_metadata = json.load(f)
        print(f"📋 Loaded {len(existing_metadata)} existing metadata entries")

    # Download images
    downloaded = 0
    failed = 0

    for filename, url in CLOTHING_IMAGES.items():
        filepath = os.path.join(GARMENT_FOLDER, filename)

        # Skip if already exists
        if os.path.exists(filepath):
            print(f"⊘ Skipping (exists): {filename}")
            continue

        if download_image(url, filepath):
            downloaded += 1
            time.sleep(0.5)  # Be nice to the server
        else:
            failed += 1

    print()
    print(f"📊 Download summary:")
    print(f"   Downloaded: {downloaded}")
    print(f"   Failed: {failed}")
    print(f"   Skipped (already exists): {len(CLOTHING_IMAGES) - downloaded - failed}")
    print()

    # Generate metadata for all images
    print("📝 Generating metadata...")

    # Update metadata for downloaded images
    for filename in CLOTHING_IMAGES.keys():
        if filename not in existing_metadata:
            existing_metadata[filename] = generate_metadata(filename)

    # Save metadata
    with open(METADATA_FILE, 'w') as f:
        json.dump(existing_metadata, f, indent=4)

    print(f"✓ Metadata saved to {METADATA_FILE}")
    print(f"✓ Total garments in database: {len(existing_metadata)}")
    print()

    # Print summary
    print("📋 Dataset Summary:")
    by_category = {}
    for filename, meta in existing_metadata.items():
        cat = meta.get('category', 'Unknown')
        by_category[cat] = by_category.get(cat, 0) + 1

    for cat, count in sorted(by_category.items()):
        print(f"   {cat}: {count}")

    print()
    print("✅ Dataset setup complete!")

if __name__ == '__main__':
    main()
