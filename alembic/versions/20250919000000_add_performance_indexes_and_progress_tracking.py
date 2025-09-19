"""Add performance indexes and progress tracking columns

Revision ID: 20250919000000  
Revises: 20241220120000
Create Date: 2024-09-19 00:00:00.000000

This migration adds:
1. Missing columns for upload progress tracking
2. Critical performance indexes for fast search and retrieval
3. Composite indexes for common query patterns
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250919000000'
down_revision = '20241220120000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Conditionally add missing columns to product_uploads table
    op.execute("""
        DO $$ 
        BEGIN 
            -- Add started_at column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name='product_uploads' AND column_name='started_at') THEN
                ALTER TABLE product_uploads 
                ADD COLUMN started_at TIMESTAMP WITH TIME ZONE;
            END IF;
            
            -- Add processed_rows column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name='product_uploads' AND column_name='processed_rows') THEN
                ALTER TABLE product_uploads 
                ADD COLUMN processed_rows INTEGER DEFAULT 0;
            END IF;
            
            -- Add error_count column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name='product_uploads' AND column_name='error_count') THEN
                ALTER TABLE product_uploads 
                ADD COLUMN error_count INTEGER DEFAULT 0;
            END IF;
        END $$;
    """)
    
    # 2. Conditionally create error tracking table
    op.execute("""
        DO $$ 
        BEGIN 
            -- Ensure pgcrypto extension exists for gen_random_uuid()
            CREATE EXTENSION IF NOT EXISTS pgcrypto;
            
            -- Create product_upload_errors table if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.tables 
                           WHERE table_name='product_upload_errors') THEN
                CREATE TABLE product_upload_errors (
                    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    upload_id VARCHAR(36) NOT NULL,
                    line_number INTEGER NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    raw_data JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT fk_product_upload_errors_upload_id 
                        FOREIGN KEY (upload_id) REFERENCES product_uploads(id) ON DELETE CASCADE
                );
            END IF;
        END $$;
    """)
    
    # 3. Conditionally add performance indexes using SQL for safety
    op.execute("""
        -- Core table indexes with conditional creation
        
        -- product_uploads indexes (always exists)
        CREATE INDEX IF NOT EXISTS ix_product_uploads_brand_id ON product_uploads (brand_id);
        CREATE INDEX IF NOT EXISTS ix_product_uploads_status ON product_uploads (status);
        CREATE INDEX IF NOT EXISTS ix_product_uploads_created_at ON product_uploads (created_at);
        CREATE INDEX IF NOT EXISTS ix_product_uploads_processed_at ON product_uploads (processed_at);
        
        -- products indexes (always exists)
        CREATE INDEX IF NOT EXISTS ix_products_sku ON products (sku);
        CREATE INDEX IF NOT EXISTS ix_products_created_at ON products (created_at);
        CREATE INDEX IF NOT EXISTS ix_products_updated_at ON products (updated_at);
        
        -- brands indexes (always exists) 
        CREATE INDEX IF NOT EXISTS ix_brands_name ON brands (name);
        CREATE INDEX IF NOT EXISTS ix_brands_slug ON brands (slug);
        CREATE INDEX IF NOT EXISTS ix_brands_created_at ON brands (created_at);
        
        -- Composite indexes for common query patterns
        CREATE INDEX IF NOT EXISTS ix_products_active_family ON products (active, family);
        CREATE INDEX IF NOT EXISTS ix_products_brand_active ON products (brand_id, active);
        CREATE INDEX IF NOT EXISTS ix_products_family_price ON products (family, price);
        CREATE INDEX IF NOT EXISTS ix_products_active_accessory ON products (active, is_accessory);
        
        -- High-value feature indexes (selective columns)
        CREATE INDEX IF NOT EXISTS ix_products_ir_range_m ON products (ir_range_m) WHERE ir_range_m IS NOT NULL;
        CREATE INDEX IF NOT EXISTS ix_products_resolution_mp ON products (resolution_mp) WHERE resolution_mp IS NOT NULL;
        CREATE INDEX IF NOT EXISTS ix_products_form_factor ON products (form_factor) WHERE form_factor IS NOT NULL;
    """)
    
    # 4. Conditionally create indexes for optional tables
    op.execute("""
        DO $$ 
        BEGIN 
            -- product_upload_errors indexes (if table exists)
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='product_upload_errors') THEN
                CREATE INDEX IF NOT EXISTS ix_product_upload_errors_upload_id ON product_upload_errors (upload_id);
                CREATE INDEX IF NOT EXISTS ix_product_upload_errors_line_number ON product_upload_errors (line_number);
            END IF;
            
            -- quotes table indexes (if exists)
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='quotes') THEN
                CREATE INDEX IF NOT EXISTS ix_quotes_status ON quotes (status);
                CREATE INDEX IF NOT EXISTS ix_quotes_created_at ON quotes (created_at);
                CREATE INDEX IF NOT EXISTS ix_quotes_updated_at ON quotes (updated_at);
            END IF;
            
            -- quote_items table indexes (if exists)
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='quote_items') THEN
                CREATE INDEX IF NOT EXISTS ix_quote_items_product_id ON quote_items (product_id);
                CREATE INDEX IF NOT EXISTS ix_quote_items_sku ON quote_items (sku);
            END IF;
            
            -- rule_sets and rules indexes (if exist)
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='rule_sets') THEN
                CREATE INDEX IF NOT EXISTS ix_rule_sets_is_active ON rule_sets (is_active);
                CREATE INDEX IF NOT EXISTS ix_rule_sets_priority ON rule_sets (priority);
            END IF;
            
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='rules') THEN
                CREATE INDEX IF NOT EXISTS ix_rules_active ON rules (active);
                CREATE INDEX IF NOT EXISTS ix_rules_scope ON rules (scope);
                CREATE INDEX IF NOT EXISTS ix_rules_priority ON rules (priority);
            END IF;
            
            -- prompt_runs indexes (if exists)
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='prompt_runs') THEN
                CREATE INDEX IF NOT EXISTS ix_prompt_runs_created_at ON prompt_runs (created_at);
                CREATE INDEX IF NOT EXISTS ix_prompt_runs_result_quote_id ON prompt_runs (result_quote_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Safe downgrade with conditional drops matching the upgrade
    op.execute("""
        DO $$ 
        BEGIN 
            -- Drop indexes for optional tables (if they exist)
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_prompt_runs_result_quote_id') THEN
                DROP INDEX ix_prompt_runs_result_quote_id;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_prompt_runs_created_at') THEN
                DROP INDEX ix_prompt_runs_created_at;
            END IF;
            
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_rules_priority') THEN
                DROP INDEX ix_rules_priority;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_rules_scope') THEN
                DROP INDEX ix_rules_scope;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_rules_active') THEN
                DROP INDEX ix_rules_active;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_rule_sets_priority') THEN
                DROP INDEX ix_rule_sets_priority;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_rule_sets_is_active') THEN
                DROP INDEX ix_rule_sets_is_active;
            END IF;
            
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_quote_items_sku') THEN
                DROP INDEX ix_quote_items_sku;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_quote_items_product_id') THEN
                DROP INDEX ix_quote_items_product_id;
            END IF;
            
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_quotes_updated_at') THEN
                DROP INDEX ix_quotes_updated_at;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_quotes_created_at') THEN
                DROP INDEX ix_quotes_created_at;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_quotes_status') THEN
                DROP INDEX ix_quotes_status;
            END IF;
            
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_product_upload_errors_line_number') THEN
                DROP INDEX ix_product_upload_errors_line_number;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_product_upload_errors_upload_id') THEN
                DROP INDEX ix_product_upload_errors_upload_id;
            END IF;
        END $$;
    """)
    
    # Drop core table indexes (always safe to try)
    op.execute("""
        -- Drop indexes that were actually created in upgrade
        DROP INDEX IF EXISTS ix_products_form_factor;
        DROP INDEX IF EXISTS ix_products_resolution_mp;
        DROP INDEX IF EXISTS ix_products_ir_range_m;
        DROP INDEX IF EXISTS ix_products_family_price;
        DROP INDEX IF EXISTS ix_products_brand_active;
        DROP INDEX IF EXISTS ix_products_active_family;
        DROP INDEX IF EXISTS ix_products_active_accessory;
        DROP INDEX IF EXISTS ix_brands_created_at;
        DROP INDEX IF EXISTS ix_brands_slug;
        DROP INDEX IF EXISTS ix_brands_name;
        DROP INDEX IF EXISTS ix_products_updated_at;
        DROP INDEX IF EXISTS ix_products_created_at;
        DROP INDEX IF EXISTS ix_products_sku;
        DROP INDEX IF EXISTS ix_product_uploads_processed_at;
        DROP INDEX IF EXISTS ix_product_uploads_created_at;
        DROP INDEX IF EXISTS ix_product_uploads_status;
        DROP INDEX IF EXISTS ix_product_uploads_brand_id;
    """)
    
    # Drop table and columns conditionally
    op.execute("""
        DO $$ 
        BEGIN 
            -- Drop product_upload_errors table if it exists
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='product_upload_errors') THEN
                DROP TABLE product_upload_errors;
            END IF;
            
            -- NOTE: We do NOT drop columns from product_uploads as they may have existed 
            -- before this migration. This makes the downgrade safe and non-destructive.
            -- Only drop the table and indexes we definitively added.
            RAISE NOTICE 'Columns started_at, processed_rows, error_count left intact for safety';
        END $$;
    """)