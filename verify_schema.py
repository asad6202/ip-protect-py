#!/usr/bin/env python3
"""
Script to verify the new database schema after recreation.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def verify_schema():
    """Verify the new database schema is correctly created."""
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        print("ERROR: DATABASE_URL not set in environment")
        return
    
    conn = await asyncpg.connect(dsn)
    
    try:
        print("🔍 Verifying new database schema...")
        
        # Get all tables
        tables = await conn.fetch('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        ''')
        
        expected_tables = [
            'brands', 'product_uploads', 'product_import_batches', 'products',
            'product_embeddings', 'quotes', 'quote_items', 'quote_feedback',
            'rule_sets', 'rules', 'rule_executions', 'prompt_runs'
        ]
        
        print(f"📋 Found {len(tables)} tables:")
        found_tables = []
        for table in tables:
            table_name = table['table_name']
            found_tables.append(table_name)
            status = "✅" if table_name in expected_tables else "❌"
            print(f"  {status} {table_name}")
        
        # Check if all expected tables exist
        missing_tables = set(expected_tables) - set(found_tables)
        extra_tables = set(found_tables) - set(expected_tables)
        
        if missing_tables:
            print(f"\n❌ Missing tables: {missing_tables}")
        if extra_tables:
            print(f"\n⚠️  Extra tables: {extra_tables}")
        
        if not missing_tables and not extra_tables:
            print("\n✅ All expected tables are present!")
        
        # Check products table structure
        if 'products' in found_tables:
            print("\n🔍 Checking products table structure...")
            columns = await conn.fetch('''
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'products'
                ORDER BY ordinal_position
            ''')
            
            key_columns = ['id', 'sku', 'description', 'price', 'family', 'active', 'ts']
            for col in key_columns:
                found = any(row['column_name'] == col for row in columns)
                status = "✅" if found else "❌"
                print(f"  {status} {col}")
        
        # Check indexes
        print("\n🔍 Checking indexes...")
        indexes = await conn.fetch('''
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        ''')
        
        expected_indexes = [
            'ix_products_brand_id', 'ix_products_family', 'ix_products_price',
            'ix_products_active', 'ix_products_ts', 'ix_products_description_trgm'
        ]
        
        found_indexes = [idx['indexname'] for idx in indexes]
        for expected_idx in expected_indexes:
            found = expected_idx in found_indexes
            status = "✅" if found else "❌"
            print(f"  {status} {expected_idx}")
        
        # Check extensions
        print("\n🔍 Checking extensions...")
        extensions = await conn.fetch('''
            SELECT extname FROM pg_extension
        ''')
        
        expected_extensions = ['pgcrypto', 'pg_trgm', 'unaccent']
        found_extensions = [ext['extname'] for ext in extensions]
        
        for expected_ext in expected_extensions:
            found = expected_ext in found_extensions
            status = "✅" if found else "❌"
            print(f"  {status} {expected_ext}")
        
        # Check vector extension separately
        vector_available = 'vector' in found_extensions
        status = "✅" if vector_available else "⚠️"
        print(f"  {status} vector (optional)")
        
        print("\n🎉 Schema verification completed!")
        
    except Exception as e:
        print(f"❌ Error during schema verification: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(verify_schema())
