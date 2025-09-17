# Quote System Documentation

This document describes the updated quote generation system that works with the new database schema.

## 🏗️ Architecture

The quote system consists of several components:

### Database Schema
- **`quotes`** - Main quote records with metadata
- **`quote_items`** - Individual products in each quote
- **`quote_feedback`** - User feedback on quotes
- **`products`** - Product catalog (3,591 products from 3 brands)
- **`brands`** - Product brands (Axis, Hanwha, I-Pro)

### Services
- **`QuoteService`** - Core business logic for quote management
- **`ProductRetrieval`** - Product search and matching
- **`IntentExtractor`** - Natural language processing

### API Endpoints
- **`POST /api/v1/quote`** - Create new quote
- **`GET /api/v1/quote/{id}`** - Get quote by ID
- **`GET /api/v1/quotes`** - List quotes with pagination
- **`PATCH /api/v1/quote/{id}/status`** - Update quote status
- **`POST /api/v1/quote/{id}/feedback`** - Add feedback

## 🚀 Usage

### Creating a Quote

```bash
curl -X POST "http://localhost:8000/api/v1/quote" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "I need 2 outdoor dome cameras with night vision for a small office",
    "title": "Small Office Security Setup"
  }'
```

**Response:**
```json
{
  "id": "33cd0caf-1e07-49ba-b7d6-ac4758c42397",
  "title": "Small Office Security Setup",
  "prompt": "I need 2 outdoor dome cameras with night vision for a small office",
  "extracted_intent": {
    "items": [
      {
        "family": "camera",
        "quantity": 2,
        "features": ["outdoor", "night vision", "dome"]
      }
    ]
  },
  "currency": "CAD",
  "total_amount": 524.0,
  "notes": null,
  "status": "draft",
  "created_at": "2024-12-20T12:00:00Z",
  "updated_at": "2024-12-20T12:00:00Z",
  "items": [
    {
      "sku": "WV-X15500-V3L",
      "description": "5MP OUTDOOR VANDAL RESISTANT BULLET CAMERA...",
      "quantity": 2,
      "unit_price": 262.0,
      "currency": "CAD",
      "subtotal": 524.0,
      "product_id": "abc123...",
      "metadata": {
        "is_fallback": false,
        "search_method": "deterministic"
      },
      "position": 0
    }
  ]
}
```

### Getting a Quote

```bash
curl "http://localhost:8000/api/v1/quote/33cd0caf-1e07-49ba-b7d6-ac4758c42397"
```

### Listing Quotes

```bash
curl "http://localhost:8000/api/v1/quotes?limit=10&offset=0"
```

### Updating Quote Status

```bash
curl -X PATCH "http://localhost:8000/api/v1/quote/33cd0caf-1e07-49ba-b7d6-ac4758c42397/status" \
  -H "Content-Type: application/json" \
  -d '"sent"'
```

### Adding Feedback

```bash
curl -X POST "http://localhost:8000/api/v1/quote/33cd0caf-1e07-49ba-b7d6-ac4758c42397/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 5,
    "comment": "Great quote, exactly what I needed!",
    "labels": {"helpful": true, "accurate": true}
  }'
```

## 📊 Data Flow

### 1. Quote Creation Process

1. **Intent Extraction**: Parse natural language prompt to extract requirements
2. **Product Search**: Find matching products using hybrid search (deterministic + vector)
3. **Accessory Addition**: Add NVR/Switch based on global preferences
4. **Database Storage**: Save quote and items to database
5. **Response**: Return structured quote data

### 2. Product Matching

The system uses a sophisticated product matching algorithm:

- **Exact SKU Match**: Direct product lookup by SKU
- **Deterministic Search**: Rule-based matching with family constraints
- **Vector Fallback**: AI-powered semantic search for complex queries
- **Brand Preferences**: Respect user brand preferences and avoidances
- **Budget Constraints**: Filter products by price limits

### 3. Data Storage

All quote data is stored in the database with proper relationships:

- **Quote**: Main record with metadata and totals
- **Quote Items**: Individual products with pricing and metadata
- **Feedback**: User ratings and comments
- **Audit Trail**: Complete history of quote changes

## 🔧 Configuration

### Environment Variables

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/database
OPENAI_API_KEY=your_openai_api_key
```

### Database Setup

1. **Create Schema**: Run the database recreation script
2. **Load Products**: Load product data from CSV files
3. **Start Server**: Launch the FastAPI application

```bash
# 1. Recreate database
python3 recreate_database_safe.py

# 2. Load product data
python3 load_products_simple.py

# 3. Start server
python3 main.py
```

## 📈 Features

### Quote Management
- ✅ Create quotes from natural language
- ✅ Retrieve quotes by ID
- ✅ List quotes with pagination
- ✅ Update quote status (draft, sent, accepted, rejected, expired)
- ✅ Add user feedback and ratings

### Product Search
- ✅ Hybrid search (deterministic + vector)
- ✅ Brand preference handling
- ✅ Budget constraint filtering
- ✅ Accessory auto-addition (NVR/Switch)
- ✅ Fallback product suggestions

### Data Integrity
- ✅ Proper foreign key relationships
- ✅ JSONB metadata storage
- ✅ Audit trail with timestamps
- ✅ Transaction safety

## 🧪 Testing

Run the test suite to verify the system:

```bash
python3 test_quote_system.py
```

This will test:
- Database table existence
- Product data availability
- Quote creation and retrieval
- Status updates
- Feedback system
- Data integrity

## 📝 API Reference

### QuoteRequest
```python
{
  "prompt": str,           # Required: Natural language description
  "title": str             # Optional: Quote title
}
```

### QuoteResponse
```python
{
  "id": str,               # Quote UUID
  "title": str,            # Quote title
  "prompt": str,           # Original prompt
  "extracted_intent": dict, # Parsed requirements
  "currency": str,         # Currency code
  "total_amount": float,   # Total price
  "notes": str,            # Additional notes
  "status": str,           # Quote status
  "created_at": str,       # ISO timestamp
  "updated_at": str,       # ISO timestamp
  "items": [QuoteItem]     # Quote items
}
```

### QuoteItem
```python
{
  "sku": str,              # Product SKU
  "description": str,      # Product description
  "quantity": int,         # Quantity
  "unit_price": float,     # Price per unit
  "currency": str,         # Currency code
  "subtotal": float,       # Line total
  "product_id": str,       # Product UUID
  "metadata": dict,        # Additional metadata
  "position": int          # Item position
}
```

## 🚨 Error Handling

The system includes comprehensive error handling:

- **Validation Errors**: 400 Bad Request for invalid input
- **Not Found**: 404 for missing quotes
- **Server Errors**: 500 for internal issues
- **Database Errors**: Proper transaction rollback
- **Intent Extraction**: Graceful fallback for parsing errors

## 🔄 Status Workflow

Quotes follow a defined status workflow:

1. **draft** - Initial creation
2. **sent** - Sent to customer
3. **accepted** - Customer accepted
4. **rejected** - Customer rejected
5. **expired** - Quote expired

## 📊 Analytics

The system tracks:

- Quote creation and completion rates
- Product selection patterns
- User feedback and ratings
- Search method effectiveness
- Fallback usage statistics

## 🛠️ Development

### Adding New Features

1. **Database**: Add new tables/columns as needed
2. **Models**: Update SQLAlchemy models
3. **Services**: Add business logic to QuoteService
4. **API**: Create new endpoints
5. **Tests**: Add test coverage

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check database queries:

```sql
-- View recent quotes
SELECT id, title, status, total_amount, created_at 
FROM quotes 
ORDER BY created_at DESC 
LIMIT 10;

-- View quote items
SELECT qi.sku, qi.description, qi.quantity, qi.unit_price, qi.subtotal
FROM quote_items qi
JOIN quotes q ON qi.quote_id = q.id
WHERE q.id = 'your-quote-id';
```

## 🎯 Best Practices

1. **Always validate input** before processing
2. **Use transactions** for multi-table operations
3. **Handle errors gracefully** with proper HTTP status codes
4. **Log important events** for debugging
5. **Test thoroughly** before deploying changes
6. **Monitor performance** and optimize queries
7. **Keep data consistent** with proper constraints
