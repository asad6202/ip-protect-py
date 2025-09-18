#!/usr/bin/env python3
"""
Script to check the loaded product data.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_data():
    """Check the loaded product data."""
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        print("❌ ERROR: DATABASE_URL not set in environment")
        return
    
    conn = await asyncpg.connect(dsn)
    
    try:
        print("🔍 Checking loaded product data...")
        
        # Check some sample products
        products = await conn.fetch('''
            SELECT p.sku, p.description, p.price, p.currency, p.family, p.active, b.name as brand_name
            FROM products p 
            JOIN brands b ON p.brand_id = b.id 
            ORDER BY p.created_at 
            LIMIT 5
        ''')
        
        print('📋 Sample products:')
        for p in products:
            print(f'  - {p["brand_name"]} {p["sku"]}: {p["description"][:50]}... (${p["price"]} {p["currency"]})')
        
        # Check family distribution
        families = await conn.fetch('''
            SELECT family, COUNT(*) as count 
            FROM products 
            GROUP BY family 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        
        print(f'\n📊 Top product families:')
        for f in families:
            print(f'  - {f["family"]}: {f["count"]} products')
        
        # Check active vs inactive
        active_stats = await conn.fetchrow('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN active = true THEN 1 END) as active_count,
                COUNT(CASE WHEN active = false THEN 1 END) as inactive_count
            FROM products
        ''')
        
        print(f'\n📈 Product status:')
        print(f'  - Total products: {active_stats["total"]}')
        print(f'  - Active: {active_stats["active_count"]}')
        print(f'  - Inactive: {active_stats["inactive_count"]}')
        
        # Check brands
        brands = await conn.fetch('''
            SELECT b.name, COUNT(p.id) as product_count 
            FROM brands b 
            LEFT JOIN products p ON b.id = p.brand_id 
            GROUP BY b.id, b.name 
            ORDER BY product_count DESC
        ''')
        
        print(f'\n🏷️  Brands:')
        for brand in brands:
            print(f'  - {brand["name"]}: {brand["product_count"]} products')
        
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_data())
