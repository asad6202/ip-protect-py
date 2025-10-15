#!/usr/bin/env python3
"""Test NVR search directly"""
import asyncio
import asyncpg
from app.services.retrieval import ProductRetrieval

async def test_nvr_search():
    # Connect to database
    DATABASE_URL = "postgresql://neondb_owner:npg_YnpKXPV61kRw@ep-winter-paper-ae946zh9.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require"
    conn = await asyncpg.connect(DATABASE_URL)
    
    retrieval = ProductRetrieval(conn)
    
    # Test NVR search
    nvr_want = {
        "family": "nvr",
        "quantity": 1,
        "formFactor": "server",
        "location": "any",
        "features": ["recorder"],
        "notes": "NVR with at least 4 channels"
    }
    
    print("Testing NVR search with:")
    print(nvr_want)
    print()
    
    results = await retrieval.search_products(nvr_want, "Need NVR for 4 cameras")
    
    print(f"Found {len(results)} NVR products:")
    for i, product in enumerate(results[:5]):
        print(f"\n{i+1}. {product['sku']}: {product['description'][:100]}...")
        print(f"   Price: {product['price']} {product.get('currency', 'USD')}")
        print(f"   Family: {product.get('family')}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test_nvr_search())
