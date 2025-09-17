#!/usr/bin/env python3
"""
Script to drop all existing tables and recreate the database schema from scratch.
This will completely reset the database to the new single-user quote generator schema.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def recreate_database():
    """Drop all existing tables and recreate with new schema."""
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        print("ERROR: DATABASE_URL not set in environment")
        return
    
    conn = await asyncpg.connect(dsn)
    
    try:
        print("🔄 Starting database recreation...")
        
        # Get all existing tables
        tables = await conn.fetch('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        ''')
        
        if tables:
            print(f"📋 Found {len(tables)} existing tables:")
            for table in tables:
                print(f"  - {table['table_name']}")
            
            # Drop all tables in CASCADE to handle foreign key constraints
            print("\n🗑️  Dropping all existing tables...")
            for table in tables:
                table_name = table['table_name']
                print(f"  Dropping {table_name}...")
                await conn.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
            
            print("✅ All existing tables dropped successfully")
        else:
            print("ℹ️  No existing tables found")
        
        print("\n🔧 Enabling required PostgreSQL extensions...")
        
        # Enable required extensions
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        print("  ✅ pgcrypto extension enabled")
        
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        print("  ✅ pg_trgm extension enabled")
        
        await conn.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        print("  ✅ unaccent extension enabled")
        
        # Try to enable vector extension with graceful failure
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("  ✅ vector extension enabled")
        except Exception as e:
            print(f"  ⚠️  vector extension not available: {e}")
            print("  ℹ️  System will work with deterministic search only")
        
        print("\n🏗️  Creating new tables...")
        
        # Create brands table
        await conn.execute('''
            CREATE TABLE brands (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL UNIQUE,
                slug TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        print("  ✅ brands table created")
        
        # Create product_uploads table
        await conn.execute('''
            CREATE TABLE product_uploads (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                brand_id VARCHAR(36) REFERENCES brands(id) ON DELETE SET NULL,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                row_count INTEGER,
                status TEXT NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded','processing','processed','failed')),
                message TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                processed_at TIMESTAMP WITH TIME ZONE
            )
        ''')
        print("  ✅ product_uploads table created")
        
        # Create product_import_batches table
        await conn.execute('''
            CREATE TABLE product_import_batches (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                brand_id VARCHAR(36) REFERENCES brands(id) ON DELETE SET NULL,
                upload_id VARCHAR(36) REFERENCES product_uploads(id) ON DELETE SET NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        print("  ✅ product_import_batches table created")
        
        # Create products table
        await conn.execute('''
            CREATE TABLE products (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                brand_id VARCHAR(36) REFERENCES brands(id) ON DELETE SET NULL,
                sku TEXT NOT NULL,
                description TEXT NOT NULL,
                price NUMERIC(12,2) NOT NULL,
                currency TEXT NOT NULL,
                family TEXT NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                form_factor TEXT,
                outdoor BOOLEAN,
                poe BOOLEAN,
                poe_plus BOOLEAN,
                ir_range_m INTEGER,
                resolution_mp NUMERIC,
                vandal_ik10 BOOLEAN,
                nvr_channels INTEGER,
                switch_ports INTEGER,
                is_accessory BOOLEAN NOT NULL DEFAULT FALSE,
                accessory_type TEXT,
                search_text TEXT,
                raw_json JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                UNIQUE(brand_id, sku)
            )
        ''')
        print("  ✅ products table created")
        
        # Add computed tsvector column for products
        await conn.execute('''
            ALTER TABLE products 
            ADD COLUMN ts tsvector 
            GENERATED ALWAYS AS (to_tsvector('simple', coalesce(search_text, ''))) STORED
        ''')
        print("  ✅ products tsvector column added")
        
        # Create product_embeddings table
        try:
            await conn.execute('''
                CREATE TABLE product_embeddings (
                    product_id VARCHAR(36) PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
                    embedding vector(1536)
                )
            ''')
            print("  ✅ product_embeddings table created with vector column")
        except Exception as e:
            # Fallback without vector column
            await conn.execute('''
                CREATE TABLE product_embeddings (
                    product_id VARCHAR(36) PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
                    embedding TEXT
                )
            ''')
            print("  ✅ product_embeddings table created (without vector column)")
        
        # Create quotes table
        await conn.execute('''
            CREATE TABLE quotes (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT,
                prompt TEXT NOT NULL,
                extracted_intent JSONB,
                currency TEXT,
                total_amount NUMERIC(12,2),
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sent','accepted','rejected','expired')),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        print("  ✅ quotes table created")
        
        # Create quote_items table
        await conn.execute('''
            CREATE TABLE quote_items (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                quote_id VARCHAR(36) NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                product_id VARCHAR(36) REFERENCES products(id) ON DELETE SET NULL,
                sku TEXT NOT NULL,
                description TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 1),
                unit_price NUMERIC(12,2) NOT NULL,
                currency TEXT NOT NULL,
                subtotal NUMERIC(12,2) NOT NULL,
                metadata JSONB,
                position INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        print("  ✅ quote_items table created")
        
        # Create quote_feedback table
        await conn.execute('''
            CREATE TABLE quote_feedback (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                quote_id VARCHAR(36) NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                rating INTEGER CHECK (rating BETWEEN 1 AND 5),
                comment TEXT,
                labels JSONB,
                corrections JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        print("  ✅ quote_feedback table created")
        
        # Create rule_sets table
        await conn.execute('''
            CREATE TABLE rule_sets (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL UNIQUE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                priority INTEGER NOT NULL DEFAULT 100,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        print("  ✅ rule_sets table created")
        
        # Create rules table
        await conn.execute('''
            CREATE TABLE rules (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                rule_set_id VARCHAR(36) NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                scope TEXT NOT NULL CHECK (scope IN ('global','item')),
                priority INTEGER NOT NULL DEFAULT 100,
                condition JSONB NOT NULL,
                actions JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        print("  ✅ rules table created")
        
        # Create rule_executions table
        await conn.execute('''
            CREATE TABLE rule_executions (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                quote_id VARCHAR(36) NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                rule_id VARCHAR(36) NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
                fired BOOLEAN NOT NULL,
                details JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        print("  ✅ rule_executions table created")
        
        # Create prompt_runs table
        await conn.execute('''
            CREATE TABLE prompt_runs (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
                prompt TEXT NOT NULL,
                extracted_intent JSONB,
                rules_applied JSONB,
                result_quote_id VARCHAR(36) REFERENCES quotes(id) ON DELETE SET NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        print("  ✅ prompt_runs table created")
        
        print("\n📊 Creating indexes...")
        
        # Create indexes for products table
        await conn.execute('CREATE INDEX ix_products_brand_id ON products (brand_id)')
        await conn.execute('CREATE INDEX ix_products_family ON products (family)')
        await conn.execute('CREATE INDEX ix_products_price ON products (price)')
        await conn.execute('CREATE INDEX ix_products_active ON products (active)')
        await conn.execute('CREATE INDEX ix_products_is_accessory ON products (is_accessory)')
        await conn.execute('CREATE INDEX ix_products_nvr_channels ON products (nvr_channels)')
        await conn.execute('CREATE INDEX ix_products_switch_ports ON products (switch_ports)')
        await conn.execute('CREATE INDEX ix_products_ts ON products USING gin (ts)')
        await conn.execute('CREATE INDEX ix_products_description_trgm ON products USING gin (description gin_trgm_ops)')
        print("  ✅ products indexes created")
        
        # Create indexes for other tables
        await conn.execute('CREATE INDEX ix_quote_items_quote_id ON quote_items (quote_id)')
        await conn.execute('CREATE INDEX ix_quote_feedback_quote_id ON quote_feedback (quote_id)')
        await conn.execute('CREATE INDEX ix_rules_rule_set_id ON rules (rule_set_id)')
        await conn.execute('CREATE INDEX ix_rule_executions_quote_id ON rule_executions (quote_id)')
        print("  ✅ other table indexes created")
        
        print("\n🎉 Database recreation completed successfully!")
        print("\n📋 New schema includes:")
        print("  - brands")
        print("  - product_uploads")
        print("  - product_import_batches")
        print("  - products (with full-text search)")
        print("  - product_embeddings")
        print("  - quotes")
        print("  - quote_items")
        print("  - quote_feedback")
        print("  - rule_sets")
        print("  - rules")
        print("  - rule_executions")
        print("  - prompt_runs")
        
    except Exception as e:
        print(f"❌ Error during database recreation: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(recreate_database())
