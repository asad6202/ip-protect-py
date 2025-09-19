-- Manual SQL script to apply performance indexes and progress tracking columns
-- Use this as a backup if Alembic migrations don't work
-- Run this script on your PostgreSQL database

-- =====================================================
-- 1. Add missing columns to product_uploads table
-- =====================================================
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

-- =====================================================
-- 2. Create product_upload_errors table if not exists
-- =====================================================
-- Ensure pgcrypto extension exists for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS product_upload_errors (
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

-- =====================================================
-- 3. Create performance indexes
-- =====================================================

-- Create indexes only if they don't exist (PostgreSQL 9.5+)

-- product_uploads table indexes
CREATE INDEX IF NOT EXISTS ix_product_uploads_brand_id ON product_uploads (brand_id);
CREATE INDEX IF NOT EXISTS ix_product_uploads_status ON product_uploads (status);
CREATE INDEX IF NOT EXISTS ix_product_uploads_created_at ON product_uploads (created_at);
CREATE INDEX IF NOT EXISTS ix_product_uploads_processed_at ON product_uploads (processed_at);

-- product_upload_errors indexes
CREATE INDEX IF NOT EXISTS ix_product_upload_errors_upload_id ON product_upload_errors (upload_id);
CREATE INDEX IF NOT EXISTS ix_product_upload_errors_line_number ON product_upload_errors (line_number);

-- Additional products table indexes
CREATE INDEX IF NOT EXISTS ix_products_sku ON products (sku);
CREATE INDEX IF NOT EXISTS ix_products_created_at ON products (created_at);
CREATE INDEX IF NOT EXISTS ix_products_updated_at ON products (updated_at);

-- brands table indexes
CREATE INDEX IF NOT EXISTS ix_brands_name ON brands (name);
CREATE INDEX IF NOT EXISTS ix_brands_slug ON brands (slug);
CREATE INDEX IF NOT EXISTS ix_brands_created_at ON brands (created_at);

-- quotes table indexes (if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='quotes') THEN
        CREATE INDEX IF NOT EXISTS ix_quotes_status ON quotes (status);
        CREATE INDEX IF NOT EXISTS ix_quotes_created_at ON quotes (created_at);
        CREATE INDEX IF NOT EXISTS ix_quotes_updated_at ON quotes (updated_at);
    END IF;
END $$;

-- quote_items table indexes (if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='quote_items') THEN
        CREATE INDEX IF NOT EXISTS ix_quote_items_product_id ON quote_items (product_id);
        CREATE INDEX IF NOT EXISTS ix_quote_items_sku ON quote_items (sku);
    END IF;
END $$;

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS ix_products_active_family ON products (active, family);
CREATE INDEX IF NOT EXISTS ix_products_brand_active ON products (brand_id, active);
CREATE INDEX IF NOT EXISTS ix_products_family_price ON products (family, price);
CREATE INDEX IF NOT EXISTS ix_products_active_accessory ON products (active, is_accessory);

-- Advanced search indexes for product features (selective, with WHERE clauses)
CREATE INDEX IF NOT EXISTS ix_products_ir_range_m ON products (ir_range_m) WHERE ir_range_m IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_products_resolution_mp ON products (resolution_mp) WHERE resolution_mp IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_products_form_factor ON products (form_factor) WHERE form_factor IS NOT NULL;

-- rule_sets and rules indexes (if tables exist)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='rule_sets') THEN
        CREATE INDEX IF NOT EXISTS ix_rule_sets_is_active ON rule_sets (is_active);
        CREATE INDEX IF NOT EXISTS ix_rule_sets_priority ON rule_sets (priority);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='rules') THEN
        CREATE INDEX IF NOT EXISTS ix_rules_active ON rules (active);
        CREATE INDEX IF NOT EXISTS ix_rules_scope ON rules (scope);
        CREATE INDEX IF NOT EXISTS ix_rules_priority ON rules (priority);
    END IF;
END $$;

-- prompt_runs indexes (if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='prompt_runs') THEN
        CREATE INDEX IF NOT EXISTS ix_prompt_runs_created_at ON prompt_runs (created_at);
        CREATE INDEX IF NOT EXISTS ix_prompt_runs_result_quote_id ON prompt_runs (result_quote_id);
    END IF;
END $$;

-- =====================================================
-- 4. Verification - Show created indexes
-- =====================================================
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
  AND (indexname LIKE 'ix_%' OR indexname LIKE '%_pkey' OR indexname LIKE '%_unique')
ORDER BY tablename, indexname;