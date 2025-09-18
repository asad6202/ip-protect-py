#!/usr/bin/env python3
"""
Script to load product data from CSV files into the database.
Extracts brand names from filenames and loads all products with proper relationships.
"""
import asyncio
import asyncpg
import csv
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class ProductDataLoader:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.conn = None
        self.brand_cache: Dict[str, str] = {}  # brand_name -> brand_id
        
    async def connect(self):
        """Connect to the database."""
        self.conn = await asyncpg.connect(self.dsn)
        
    async def disconnect(self):
        """Disconnect from the database."""
        if self.conn:
            await self.conn.close()
            
    def extract_brand_from_filename(self, filename: str) -> str:
        """Extract brand name from filename."""
        # Remove file extension and common suffixes
        name = Path(filename).stem
        name = re.sub(r'_price_list.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_formatted.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_with_families.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_fixed.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_clean.*$', '', name, flags=re.IGNORECASE)
        
        # Handle specific cases
        if name.lower() == 'i-pro':
            return 'I-Pro'
        elif name.lower() == 'hanwha':
            return 'Hanwha'
        elif name.lower() == 'axis':
            return 'Axis'
        
        # Capitalize first letter of each word
        return ' '.join(word.capitalize() for word in name.split('-'))
    
    async def create_or_get_brand(self, brand_name: str) -> str:
        """Create or get existing brand and return brand_id."""
        if brand_name in self.brand_cache:
            return self.brand_cache[brand_name]
            
        # Check if brand exists
        result = await self.conn.fetchrow(
            'SELECT id FROM brands WHERE name = $1', brand_name
        )
        
        if result:
            brand_id = result['id']
        else:
            # Create new brand
            brand_id = await self.conn.fetchval(
                'INSERT INTO brands (name, slug) VALUES ($1, $2) RETURNING id',
                brand_name, brand_name.lower().replace(' ', '-')
            )
            print(f"  ✅ Created brand: {brand_name}")
            
        self.brand_cache[brand_name] = brand_id
        return brand_id
    
    def parse_price(self, price_str: str) -> float:
        """Parse price string to float."""
        if not price_str or price_str.strip() == '':
            return 0.0
        # Remove any non-numeric characters except decimal point
        price_clean = re.sub(r'[^\d.]', '', str(price_str))
        try:
            return float(price_clean)
        except ValueError:
            return 0.0
    
    def determine_form_factor(self, description: str, sku: str) -> Optional[str]:
        """Determine form factor from description and SKU."""
        desc_lower = description.lower()
        sku_lower = sku.lower()
        
        if any(word in desc_lower for word in ['dome', 'dome camera']):
            return 'dome'
        elif any(word in desc_lower for word in ['bullet', 'bullet camera']):
            return 'bullet'
        elif any(word in desc_lower for word in ['ptz', 'pan tilt', 'pan-tilt']):
            return 'ptz'
        elif any(word in desc_lower for word in ['turret', 'turret camera']):
            return 'turret'
        elif any(word in desc_lower for word in ['box', 'box camera', 'box pc']):
            return 'box'
        elif any(word in desc_lower for word in ['switch', 'network switch']):
            return 'switch'
        elif any(word in desc_lower for word in ['nvr', 'recorder']):
            return 'nvr'
        
        return None
    
    def determine_accessory_type(self, description: str, family: str) -> Optional[str]:
        """Determine accessory type from description and family."""
        desc_lower = description.lower()
        family_lower = family.lower()
        
        if any(word in desc_lower for word in ['mount', 'bracket', 'mounting']):
            return 'mount'
        elif any(word in desc_lower for word in ['license', 'licensing', 'software']):
            return 'license'
        elif any(word in desc_lower for word in ['power', 'supply', 'injector', 'adapter']):
            return 'power'
        elif any(word in desc_lower for word in ['cable', 'connector']):
            return 'cable'
        elif any(word in desc_lower for word in ['storage', 'card', 'ssd', 'nvme']):
            return 'storage'
        
        return None
    
    def extract_features(self, description: str) -> Dict[str, bool]:
        """Extract boolean features from description."""
        desc_lower = description.lower()
        
        return {
            'outdoor': any(word in desc_lower for word in ['outdoor', 'ip66', 'ip67', 'nema']),
            'poe': any(word in desc_lower for word in ['poe', 'power over ethernet']),
            'poe_plus': any(word in desc_lower for word in ['poe+', 'poe plus', '802.3at']),
            'vandal_ik10': 'ik10' in desc_lower,
        }
    
    def extract_numeric_features(self, description: str) -> Dict[str, Optional[float]]:
        """Extract numeric features from description."""
        desc_lower = description.lower()
        
        # Extract IR range
        ir_match = re.search(r'ir.*?(\d+)\s*m', desc_lower)
        ir_range = float(ir_match.group(1)) if ir_match else None
        
        # Extract resolution in MP
        mp_match = re.search(r'(\d+(?:\.\d+)?)\s*mp', desc_lower)
        resolution_mp = float(mp_match.group(1)) if mp_match else None
        
        # Extract NVR channels
        nvr_match = re.search(r'(\d+)\s*ch', desc_lower)
        nvr_channels = int(nvr_match.group(1)) if nvr_match else None
        
        # Extract switch ports
        port_match = re.search(r'(\d+)\s*port', desc_lower)
        switch_ports = int(port_match.group(1)) if port_match else None
        
        return {
            'ir_range_m': ir_range,
            'resolution_mp': resolution_mp,
            'nvr_channels': nvr_channels,
            'switch_ports': switch_ports,
        }
    
    async def load_csv_file(self, file_path: str) -> Tuple[int, int]:
        """Load products from a single CSV file."""
        filename = Path(file_path).name
        brand_name = self.extract_brand_from_filename(filename)
        brand_id = await self.create_or_get_brand(brand_name)
        
        print(f"\n📁 Loading {filename} (Brand: {brand_name})")
        
        loaded_count = 0
        error_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as file:
            # Detect delimiter
            sample = file.read(1024)
            file.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(file, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because of header
                try:
                    # Clean and validate data
                    sku = row.get('sku', '').strip()
                    description = row.get('description', '').strip()
                    price = self.parse_price(row.get('price', '0'))
                    currency = row.get('currency', 'USD').strip().upper()
                    family = row.get('family', '').strip()
                    status = row.get('status', 'active').strip().lower()
                    
                    if not sku or not description:
                        print(f"  ⚠️  Row {row_num}: Skipping - missing SKU or description")
                        error_count += 1
                        continue
                    
                    # Convert status to boolean
                    active = status == 'active'
                    
                    # Determine form factor and accessory type
                    form_factor = self.determine_form_factor(description, sku)
                    accessory_type = self.determine_accessory_type(description, family)
                    is_accessory = accessory_type is not None or family.lower() in ['access', 'accessories', 'power supply']
                    
                    # Extract features
                    features = self.extract_features(description)
                    numeric_features = self.extract_numeric_features(description)
                    
                    # Create search text
                    search_text = f"{sku} {description} {family} {accessory_type or ''}".strip()
                    
                    # Insert product
                    product_id = await self.conn.fetchval('''
                        INSERT INTO products (
                            brand_id, sku, description, price, currency, family, active,
                            form_factor, outdoor, poe, poe_plus, vandal_ik10,
                            ir_range_m, resolution_mp, nvr_channels, switch_ports,
                            is_accessory, accessory_type, search_text, raw_json
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                        ) RETURNING id
                    ''', brand_id, sku, description, price, currency, family, active,
                        form_factor, features['outdoor'], features['poe'], features['poe_plus'], features['vandal_ik10'],
                        numeric_features['ir_range_m'], numeric_features['resolution_mp'], 
                        numeric_features['nvr_channels'], numeric_features['switch_ports'],
                        is_accessory, accessory_type, search_text, dict(row))
                    
                    loaded_count += 1
                    
                    if loaded_count % 100 == 0:
                        print(f"  📊 Loaded {loaded_count} products...")
                        
                except Exception as e:
                    print(f"  ❌ Row {row_num}: Error loading product - {e}")
                    error_count += 1
                    continue
        
        print(f"  ✅ Loaded {loaded_count} products, {error_count} errors")
        return loaded_count, error_count
    
    async def load_all_data(self, data_dir: str = "data") -> Dict[str, int]:
        """Load all CSV files from the data directory."""
        if not self.conn:
            await self.connect()
        
        print("🚀 Starting product data loading...")
        
        # Find all CSV files
        data_path = Path(data_dir)
        csv_files = list(data_path.glob("*.csv"))
        
        if not csv_files:
            print(f"❌ No CSV files found in {data_dir}")
            return {}
        
        print(f"📁 Found {len(csv_files)} CSV files:")
        for file in csv_files:
            print(f"  - {file.name}")
        
        total_loaded = 0
        total_errors = 0
        results = {}
        
        for csv_file in csv_files:
            try:
                loaded, errors = await self.load_csv_file(str(csv_file))
                total_loaded += loaded
                total_errors += errors
                results[csv_file.name] = {'loaded': loaded, 'errors': errors}
            except Exception as e:
                print(f"❌ Error processing {csv_file.name}: {e}")
                results[csv_file.name] = {'loaded': 0, 'errors': 1}
        
        print(f"\n🎉 Data loading completed!")
        print(f"📊 Total products loaded: {total_loaded}")
        print(f"❌ Total errors: {total_errors}")
        
        # Show summary by file
        print(f"\n📋 Summary by file:")
        for filename, stats in results.items():
            print(f"  {filename}: {stats['loaded']} loaded, {stats['errors']} errors")
        
        return results

async def main():
    """Main function to run the data loader."""
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        print("❌ ERROR: DATABASE_URL not set in environment")
        return
    
    loader = ProductDataLoader(dsn)
    
    try:
        await loader.connect()
        results = await loader.load_all_data()
        
        # Verify the data was loaded
        print(f"\n🔍 Verifying loaded data...")
        total_products = await loader.conn.fetchval('SELECT COUNT(*) FROM products')
        total_brands = await loader.conn.fetchval('SELECT COUNT(*) FROM brands')
        
        print(f"  📊 Total products in database: {total_products}")
        print(f"  🏷️  Total brands in database: {total_brands}")
        
        # Show brands
        brands = await loader.conn.fetch('SELECT name, COUNT(*) as product_count FROM brands b LEFT JOIN products p ON b.id = p.brand_id GROUP BY b.id, b.name ORDER BY b.name')
        print(f"\n🏷️  Brands and product counts:")
        for brand in brands:
            print(f"  - {brand['name']}: {brand['product_count']} products")
        
    except Exception as e:
        print(f"❌ Error during data loading: {e}")
        raise
    finally:
        await loader.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
