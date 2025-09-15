-- Enable required PostgreSQL extensions for vector search and text similarity
-- Run this migration first before adding vector columns

-- Enable pg_trgm extension for trigram-based text similarity (usually available by default)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable pgvector extension for vector similarity search
-- Note: This requires pgvector to be installed on your PostgreSQL server
-- If this fails, you can still use the system with deterministic search only
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
    RAISE NOTICE 'pgvector extension enabled successfully';
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'pgvector extension not available: %. The system will work with deterministic search only.', SQLERRM;
END $$;
