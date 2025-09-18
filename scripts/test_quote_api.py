#!/usr/bin/env python3
"""
Test script for the quote generation API.
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv
import asyncpg

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


async def test_database_setup():
    """Test that the database is properly set up with required tables and data."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        conn = await asyncpg.connect(dsn)
        
        # Check if products table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'products'
            )
        """)
        
        if not table_exists:
            print("❌ Products table does not exist")
            return False
        
        # Check if embedding column exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'products' AND column_name = 'embedding'
            )
        """)
        
        if not column_exists:
            print("❌ Embedding column does not exist. Run migrations first.")
            return False
        
        # Check product count
        count = await conn.fetchval("SELECT COUNT(*) FROM products")
        print(f"📊 Found {count} products in database")
        
        # Check products with embeddings
        embedding_count = await conn.fetchval("SELECT COUNT(*) FROM products WHERE embedding IS NOT NULL")
        print(f"📊 Found {embedding_count} products with embeddings")
        
        if embedding_count == 0:
            print("⚠️  No products have embeddings. Run backfill script first.")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


async def test_intent_extraction():
    """Test the intent extraction functionality."""
    try:
        from app.ai.intent_extractor import extract_intent
        
        test_queries = [
            "Need 4 outdoor dome cameras with IR 30m and PoE",
            "Looking for 2 bullet cameras, SKU ABC123, and 1 dome camera with 4K resolution",
            "Want 6 indoor cameras with H.265 encoding, avoid PTZ, budget $200 per camera"
        ]
        
        print("\n🧠 Testing intent extraction:")
        for i, query in enumerate(test_queries, 1):
            try:
                intent = extract_intent(query)
                print(f"✅ Query {i}: {query[:50]}...")
                print(f"   Items: {len(intent.get('items', []))}")
                if intent.get('global'):
                    print(f"   Global prefs: {list(intent['global'].keys())}")
            except Exception as e:
                print(f"❌ Query {i} failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Intent extraction test failed: {e}")
        return False


async def test_embeddings():
    """Test the embeddings functionality."""
    try:
        from app.ai.embeddings import get_embedding, get_embedding_batch
        
        print("\n🔤 Testing embeddings:")
        
        # Test single embedding
        embedding = get_embedding("outdoor dome camera with IR night vision")
        if embedding and len(embedding) == 1536:
            print("✅ Single embedding: OK")
        else:
            print("❌ Single embedding: Failed")
            return False
        
        # Test batch embeddings
        texts = ["camera", "nvr", "switch"]
        embeddings = get_embedding_batch(texts)
        if len(embeddings) == 3 and all(len(emb) == 1536 for emb in embeddings):
            print("✅ Batch embeddings: OK")
        else:
            print("❌ Batch embeddings: Failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Embeddings test failed: {e}")
        return False


async def test_retrieval():
    """Test the retrieval service."""
    try:
        from app.services.retrieval import ProductRetrieval
        
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            print("❌ DATABASE_URL not set")
            return False
        
        conn = await asyncpg.connect(dsn)
        retrieval = ProductRetrieval(conn)
        
        print("\n🔍 Testing retrieval:")
        
        # Test deterministic search
        want = {
            'family': 'camera',
            'features': ['poe', 'ir-30m'],
            'formFactor': 'dome',
            'location': 'outdoor'
        }
        
        results = await retrieval.deterministic_search(want)
        print(f"✅ Deterministic search: {len(results)} results")
        
        # Test vector fallback
        vector_results = await retrieval.vector_fallback(want, "outdoor dome camera with night vision")
        print(f"✅ Vector fallback: {len(vector_results)} results")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Retrieval test failed: {e}")
        return False


async def test_quote_generation():
    """Test the complete quote generation pipeline."""
    try:
        from app.ai.intent_extractor import extract_intent
        from app.services.retrieval import ProductRetrieval
        
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            print("❌ DATABASE_URL not set")
            return False
        
        conn = await asyncpg.connect(dsn)
        retrieval = ProductRetrieval(conn)
        
        print("\n💰 Testing quote generation:")
        
        test_prompt = "Need 2 outdoor dome cameras with IR 30m and PoE"
        
        # Extract intent
        intent = extract_intent(test_prompt)
        print(f"✅ Intent extracted: {len(intent.get('items', []))} items")
        
        # Search for products
        quote_items = []
        for item_want in intent.get('items', []):
            candidates = await retrieval.search_products(item_want, test_prompt)
            if candidates:
                best = candidates[0]
                quote_items.append({
                    'sku': best['sku'],
                    'description': best['description'],
                    'quantity': item_want.get('quantity', 1),
                    'price': best.get('price', 0)
                })
        
        print(f"✅ Quote generated: {len(quote_items)} items")
        for item in quote_items:
            print(f"   - {item['sku']}: {item['description'][:50]}... (${item['price']})")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Quote generation test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Running IP Protect API Tests\n")
    
    tests = [
        ("Database Setup", test_database_setup),
        ("Intent Extraction", test_intent_extraction),
        ("Embeddings", test_embeddings),
        ("Retrieval", test_retrieval),
        ("Quote Generation", test_quote_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The API is ready to use.")
        print("\nNext steps:")
        print("1. Run the server: python main.py")
        print("2. Test with HTTP requests: http/quote.http")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("\nCommon issues:")
        print("- Missing OPENAI_API_KEY environment variable")
        print("- Database not set up (run setup_db.py)")
        print("- Migrations not run (run migrations/*.sql)")
        print("- Embeddings not generated (run scripts/backfill_embeddings.py)")


if __name__ == "__main__":
    asyncio.run(main())
