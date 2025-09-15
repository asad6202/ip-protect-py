-- Add embedding column and indexes for vector similarity search
-- Run this after enabling extensions

-- Create basic indexes first (these will always work)
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_family ON products(family);
CREATE INDEX IF NOT EXISTS idx_products_desc_trgm ON products USING gin (description gin_trgm_ops);

-- Add embedding column for text-embedding-3-small (1536 dimensions)
-- This will only work if pgvector extension is available
DO $$
BEGIN
    ALTER TABLE products ADD COLUMN IF NOT EXISTS embedding vector(1536);
    RAISE NOTICE 'Embedding column added successfully';
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Could not add embedding column: %. Vector search will not be available.', SQLERRM;
END $$;

-- Create vector similarity index using IVFFlat (only if pgvector is available)
DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_products_embedding ON products 
    USING ivfflat (embedding vector_l2_ops) 
    WITH (lists = 100);
    RAISE NOTICE 'Vector similarity index created successfully';
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Could not create vector index: %. Vector search will not be available.', SQLERRM;
END $$;

-- Add composite index for filtered vector search (only if pgvector is available)
DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_products_family_status_embedding ON products (family, status) 
    WHERE embedding IS NOT NULL;
    RAISE NOTICE 'Composite vector index created successfully';
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Could not create composite vector index: %.', SQLERRM;
END $$;
