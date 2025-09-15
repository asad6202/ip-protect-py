# Quote Generation API

This document describes the hybrid quote-generation pipeline that has been added to the IP Protect application.

## Overview

The quote generation system accepts natural language prompts about CCTV cameras and accessories, extracts structured intent using OpenAI function calling, and retrieves products using a hybrid approach:

1. **Deterministic Search**: Direct SKU matches and SQL filters based on family, brand, features, and budget
2. **Vector Fallback**: Semantic similarity search using pgvector when deterministic search yields weak results
3. **Quote Assembly**: Combines selected products with quantities, prices, and totals

## Architecture

```
User Prompt → Intent Extraction → Hybrid Search → Quote Assembly → Response
     ↓              ↓                ↓              ↓
  Natural        OpenAI           Deterministic   Structured
  Language       Function         + Vector        JSON
                 Calling          Search
```

## Components

### 1. Intent Extractor (`app/ai/intent_extractor.py`)
- Uses OpenAI GPT-4o-mini with function calling
- Extracts structured JSON from natural language
- Normalizes technical terms (PoE+ → poe, IR 30m → ir-30m)
- Handles brand preferences, budget constraints, and feature requirements

### 2. Embeddings Helper (`app/ai/embeddings.py`)
- Generates text embeddings using OpenAI's text-embedding-3-small
- Supports batch processing for efficiency
- Returns 1536-dimensional vectors for pgvector storage

### 3. Retrieval Service (`app/services/retrieval.py`)
- **Deterministic Search**: SQL queries with ILIKE filters
- **Vector Fallback**: pgvector similarity search
- **Scoring System**: Ranks products by feature matches, brand preferences, and budget fit
- **Hybrid Logic**: Falls back to vector search when deterministic results are weak

### 4. Quote Endpoint (`app/api/v1/endpoints/quote.py`)
- FastAPI endpoint: `POST /api/v1/quote`
- Processes intent and generates structured quotes
- Handles accessory inference (NVR, switches)
- Returns items with quantities, prices, and totals

## Database Schema

### Products Table
```sql
CREATE TABLE products (
    sku TEXT PRIMARY KEY,
    description TEXT,
    price FLOAT,
    currency TEXT,
    family TEXT,        -- camera | nvr | switch | mount | storage | cable | monitor | other
    status TEXT,        -- active | inactive
    embedding vector(1536)  -- For vector similarity search
);
```

### Required Extensions
- `vector`: For pgvector similarity search
- `pg_trgm`: For trigram-based text similarity

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
export OPENAI_API_KEY="your-openai-api-key"
export DATABASE_URL="postgresql://user:password@localhost/dbname"
```

### 3. Run Database Migrations
```bash
# Enable extensions
psql -d your_database -f migrations/001_enable_extensions.sql

# Add embedding column and indexes
psql -d your_database -f migrations/002_add_embedding_column.sql
```

### 4. Backfill Embeddings
```bash
python scripts/backfill_embeddings.py
```

### 5. Test the System
```bash
python scripts/test_quote_api.py
```

### 6. Start the Server
```bash
python main.py
```

## API Usage

### Generate Quote
```bash
POST /api/v1/quote
Content-Type: application/json

{
  "prompt": "Need 4 outdoor dome cameras with IR 30m and PoE. Add 1 NVR 16 channels and a 24-port PoE switch."
}
```

### Response Format
```json
{
  "items": [
    {
      "sku": "CAM-001",
      "description": "Outdoor Dome Camera 4MP PoE IR 30m",
      "quantity": 4,
      "unit_price": 299.99,
      "currency": "USD",
      "subtotal": 1199.96
    }
  ],
  "total": 1199.96,
  "currency": "USD",
  "notes": "Preferred brands: Axis; Avoided brands: PTZ"
}
```

## Scoring System

Products are scored based on:
- **Feature Match**: 3 points per matching feature
- **Brand Preference**: 2 points per preferred brand
- **Brand Avoid**: -2 points per avoided brand
- **Family Match**: 1 point for correct family
- **Budget Fit**: +1 if within budget, -∞ if over budget

## Configuration

### Intent Schema
The system extracts the following structured data:

```json
{
  "items": [
    {
      "quantity": 4,
      "sku": "optional-specific-sku",
      "family": "camera",
      "formFactor": "dome",
      "location": "outdoor",
      "features": ["poe", "ir-30m"],
      "brandPreference": ["Axis"],
      "brandAvoid": ["PTZ"],
      "budgetPerUnit": {"amount": 300, "currency": "USD"}
    }
  ],
  "global": {
    "nvrChannels": 16,
    "switchPorts": 24,
    "storageNeeds": "2TB",
    "avoidPtz": true,
    "notes": "Outdoor installation"
  }
}
```

### Feature Normalization
Technical terms are normalized for consistent matching:
- `PoE+` → `poe`
- `IR 30 m` → `ir-30m`
- `H.265` → `h265`
- `4K` → `4k`
- `night vision` → `night-vision`

## Testing

### HTTP Tests
Use the provided `http/quote.http` file with your HTTP client (VS Code REST Client, Postman, etc.)

### Python Tests
```bash
python scripts/test_quote_api.py
```

### Manual Testing
```bash
# Test intent extraction
python -c "from app.ai.intent_extractor import extract_intent; print(extract_intent('Need 4 outdoor cameras'))"

# Test embeddings
python -c "from app.ai.embeddings import get_embedding; print(len(get_embedding('camera')))"

# Test retrieval
python -c "from app.services.retrieval import test_retrieval; test_retrieval()"
```

## Troubleshooting

### Common Issues

1. **No embeddings found**
   - Run the backfill script: `python scripts/backfill_embeddings.py`
   - Check OpenAI API key is set correctly

2. **Database connection errors**
   - Verify DATABASE_URL is correct
   - Ensure PostgreSQL is running
   - Check pgvector extension is installed

3. **Intent extraction fails**
   - Verify OPENAI_API_KEY is set
   - Check API key has sufficient credits
   - Ensure internet connectivity

4. **No products found**
   - Verify products table has data
   - Check product status is 'active'
   - Ensure embeddings are populated

### Performance Optimization

1. **Vector Index Tuning**
   - Adjust `lists` parameter in IVFFlat index based on data size
   - Monitor query performance with `EXPLAIN ANALYZE`

2. **Batch Processing**
   - Use batch embedding generation for large datasets
   - Process products in chunks to avoid memory issues

3. **Caching**
   - Consider caching embeddings for frequently accessed products
   - Implement query result caching for common searches

## Monitoring

### Health Check
```bash
GET /api/v1/quote/health
```

### Database Monitoring
```sql
-- Check embedding coverage
SELECT COUNT(*) as total, 
       COUNT(embedding) as with_embeddings,
       COUNT(embedding)::float / COUNT(*) * 100 as coverage_pct
FROM products;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE tablename = 'products';
```

## Future Enhancements

1. **Advanced Scoring**: Machine learning-based relevance scoring
2. **Caching Layer**: Redis for query result caching
3. **Analytics**: Track query patterns and product popularity
4. **A/B Testing**: Compare deterministic vs vector search performance
5. **Multi-language**: Support for non-English queries
6. **Real-time Updates**: WebSocket for live quote updates
