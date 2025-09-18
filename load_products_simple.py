#!/usr/bin/env python3
"""
Simple script to load product data from CSV files into the database.
This version focuses on loading the basic required fields first.
"""
import asyncio
import asyncpg
import csv
import json
import os
import re
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

async def load_products():
    """Load products from CSV files."""
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        print("❌ ERROR: DATABASE_URL not set in environment")
        return
    
    conn = await asyncpg.connect(dsn)
    
    try:
        print("🚀 Starting product data loading...")
        
        # Define the CSV files and their brands
        csv_files = {
            "data/Axis_price_list_formatted_with_families.csv": "Axis",
            "data/hanwha_price_list_formatted_with_families_fixed.csv": "Hanwha", 
            "data/i-pro_price_list_formatted_with_families_clean.csv": "I-Pro"
        }
        
        total_loaded = 0
        
        for file_path, brand_name in csv_files.items():
            if not os.path.exists(file_path):
                print(f"⚠️  File not found: {file_path}")
                continue
                
            print(f"\n📁 Loading {Path(file_path).name} (Brand: {brand_name})")
            
            # Create or get brand
            brand_id = await conn.fetchval(
                'SELECT id FROM brands WHERE name = $1', brand_name
            )
            if not brand_id:
                brand_id = await conn.fetchval(
                    'INSERT INTO brands (name, slug) VALUES ($1, $2) RETURNING id',
                    brand_name, brand_name.lower().replace(' ', '-')
                )
                print(f"  ✅ Created brand: {brand_name}")
            else:
                print(f"  ✅ Found existing brand: {brand_name}")
            
            # Load products from CSV
            loaded_count = 0
            with open(file_path, 'r', encoding='utf-8') as file:
                # Detect delimiter
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(file, delimiter=delimiter)
                
                for row in reader:
                    try:
                        # Extract basic fields
                        sku = row.get('sku', '').strip()
                        description = row.get('description', '').strip()
                        price_str = row.get('price', '0')
                        currency = row.get('currency', 'USD').strip().upper()
                        family = row.get('family', '').strip()
                        status = row.get('status', 'active').strip().lower()
                        
                        if not sku or not description:
                            continue
                        
                        # Parse price
                        try:
                            price = float(re.sub(r'[^\d.]', '', str(price_str)))
                        except ValueError:
                            price = 0.0
                        
                        # Convert status to boolean
                        active = status == 'active'
                        
                        # Create search text
                        search_text = f"{sku} {description} {family}".strip()
                        
                        # Insert product
                        await conn.execute('''
                            INSERT INTO products (
                                brand_id, sku, description, price, currency, family, active,
                                search_text, raw_json
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9
                            )
                        ''', brand_id, sku, description, price, currency, family, active,
                            search_text, json.dumps(dict(row)))
                        
                        loaded_count += 1
                        
                        if loaded_count % 100 == 0:
                            print(f"  📊 Loaded {loaded_count} products...")
                            
                    except Exception as e:
                        print(f"  ❌ Error loading product: {e}")
                        continue
            
            print(f"  ✅ Loaded {loaded_count} products from {Path(file_path).name}")
            total_loaded += loaded_count
        
        print(f"\n🎉 Data loading completed!")
        print(f"📊 Total products loaded: {total_loaded}")
        
        # Verify the data
        total_products = await conn.fetchval('SELECT COUNT(*) FROM products')
        total_brands = await conn.fetchval('SELECT COUNT(*) FROM brands')
        
        print(f"\n🔍 Verification:")
        print(f"  📊 Total products in database: {total_products}")
        print(f"  🏷️  Total brands in database: {total_brands}")
        
        # Show brands and counts
        brands = await conn.fetch('''
            SELECT b.name, COUNT(p.id) as product_count 
            FROM brands b 
            LEFT JOIN products p ON b.id = p.brand_id 
            GROUP BY b.id, b.name 
            ORDER BY b.name
        ''')
        
        print(f"\n🏷️  Brands and product counts:")
        for brand in brands:
            print(f"  - {brand['name']}: {brand['product_count']} products")
        
    except Exception as e:
        print(f"❌ Error during data loading: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(load_products())
