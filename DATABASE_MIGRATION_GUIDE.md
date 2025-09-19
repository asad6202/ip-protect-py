# Database Migration Guide

This guide explains how to apply the performance indexes and progress tracking columns to your local database.

## Overview

The migration adds:
- **Progress tracking columns** to `product_uploads` table (started_at, processed_rows, error_count)
- **Critical performance indexes** for fast search and retrieval operations
- **Product upload error tracking** table
- **Composite indexes** for common query patterns

## Option 1: Using Alembic (Recommended)

### Prerequisites
```bash
pip install alembic python-dotenv
```

### Set up your environment
1. Make sure your `.env` file contains:
   ```
   DATABASE_URL=postgresql://username:password@localhost/dbname
   ```

### Run the migration
```bash
# Option A: Use the interactive migration runner
python run_migration.py

# Option B: Use alembic directly
alembic upgrade head
```

### Verify the migration
```bash
alembic current -v
```

## Option 2: Manual SQL Script (Backup Option)

If Alembic doesn't work, you can run the SQL script directly:

```bash
# Connect to your PostgreSQL database
psql -d your_database_name -f apply_indexes_manual.sql
```

Or copy and paste the contents of `apply_indexes_manual.sql` into your database client.

## What Gets Added

### New Columns
- `product_uploads.started_at` - Timestamp when processing started
- `product_uploads.processed_rows` - Number of rows processed (for progress tracking)
- `product_uploads.error_count` - Number of errors encountered

### New Table
- `product_upload_errors` - Detailed error tracking for failed upload rows
  - `ix_product_upload_errors_upload_id` - Link errors to uploads  
  - `ix_product_upload_errors_line_number` - Find errors by CSV line number

### Performance Indexes

#### Upload Management
- `ix_product_uploads_brand_id` - Filter uploads by brand
- `ix_product_uploads_status` - Filter uploads by status (processing, completed, etc.)
- `ix_product_uploads_created_at` - Order uploads by creation time
- `ix_product_uploads_processed_at` - Order uploads by completion time

#### Product Search Performance
- `ix_products_sku` - Direct SKU lookups (very fast)
- `ix_products_created_at` - Order products by creation time
- `ix_products_updated_at` - Order products by update time

#### Brand Management
- `ix_brands_name` - Search brands by name
- `ix_brands_slug` - URL-based brand lookups
- `ix_brands_created_at` - Order brands by creation time

#### Quote Operations (if quote tables exist)
- `ix_quotes_status` - Filter quotes by status
- `ix_quotes_created_at` - Order quotes chronologically
- `ix_quotes_updated_at` - Order quotes by last modification
- `ix_quote_items_product_id` - Link quote items to products
- `ix_quote_items_sku` - Search quote items by SKU

#### Composite Indexes for Complex Queries
- `ix_products_active_family` - Active products by family (camera, nvr, switch)
- `ix_products_brand_active` - Active products by brand
- `ix_products_family_price` - Products by family and price range
- `ix_products_active_accessory` - Separate accessories from main products

#### Advanced Product Search (Selective Indexes)
- `ix_products_ir_range_m` - Night vision range searches (WHERE ir_range_m IS NOT NULL)
- `ix_products_resolution_mp` - Camera resolution searches (WHERE resolution_mp IS NOT NULL)  
- `ix_products_form_factor` - Form factor searches (WHERE form_factor IS NOT NULL)

Note: These indexes use WHERE clauses to only index non-null values, making them more selective and efficient.

#### Rule Engine Performance (if rule tables exist)
- `ix_rule_sets_is_active` - Filter active rule sets
- `ix_rule_sets_priority` - Order rule sets by priority
- `ix_rules_active` - Filter active rules
- `ix_rules_scope` - Filter rules by scope (global/item)
- `ix_rules_priority` - Order rules by priority

#### Analytics and Auditing (if prompt_runs table exists)
- `ix_prompt_runs_created_at` - Order prompt runs chronologically
- `ix_prompt_runs_result_quote_id` - Link prompt runs to generated quotes

## Performance Impact

These indexes will significantly improve:
- **Product search speed** - Up to 10x faster for filtered searches
- **Upload status tracking** - Real-time progress updates
- **Brand filtering** - Instant brand-based queries
- **Quote generation** - Faster product lookups during quote creation
- **Dashboard loading** - Improved analytics and overview queries

## Troubleshooting

### Migration Fails
1. Check your `DATABASE_URL` is correct
2. Ensure you have write permissions to the database
3. Try the manual SQL script instead

### Index Creation Fails
- Some indexes may already exist - this is normal and safe
- The migration uses `IF NOT EXISTS` to prevent conflicts

### Connection Issues
- Verify your database is running
- Check firewall/network settings
- Confirm username/password in `DATABASE_URL`

## Rollback

If you need to undo the migration:
```bash
alembic downgrade -1
```

**Important**: For safety, this will:
- ✅ Remove all indexes added by this migration
- ✅ Drop the `product_upload_errors` table  
- ❌ **Keep** the progress tracking columns (started_at, processed_rows, error_count) to avoid breaking existing data

The columns are kept because they may have existed before this migration or may be in use by running processes.

## Next Steps

After migration:
1. **Restart your application** to use the new schema
2. **Test upload progress tracking** by uploading a CSV file
3. **Monitor query performance** - searches should be noticeably faster
4. **Check error logs** for any issues with the new indexes

The progress tracking will now work for all new uploads, showing real-time progress bars and error counts in the frontend.

## Verification

After running the migration, verify the indexes were created:

```sql
-- Check all new indexes
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE indexname LIKE 'ix_%' 
  AND schemaname = 'public'
ORDER BY tablename, indexname;

-- Verify progress tracking columns exist
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'product_uploads' 
  AND column_name IN ('started_at', 'processed_rows', 'error_count');
```

Both the Alembic and manual SQL paths should produce identical results.