# NL2SQL API - Natural Language to SQL Query System

A production-ready FastAPI application that converts natural language queries into safe SQL statements and executes them against a PostgreSQL database containing camera product data.

## 🚀 Features

- **Natural Language Processing**: Uses GPT-4o to convert plain English queries into SQL
- **Safe Query Execution**: Multi-layer validation ensures only SELECT queries are executed
- **PostgreSQL Integration**: Async database operations with connection pooling
- **REST API**: Clean FastAPI endpoints with automatic OpenAPI documentation
- **Data Loading**: Automated CSV data import from multiple camera manufacturers
- **Error Handling**: Comprehensive error handling with appropriate HTTP status codes
- **Development Ready**: Includes setup scripts, Docker support, and testing examples

## 🏗️ Architecture

```
User Query → GPT-4o → SQL Validation → PostgreSQL → JSON Response
```

### Components

- **FastAPI Server** (`main.py`): REST API endpoints and lifecycle management
- **GPT Integration** (`gpt.py`): OpenAI API calls with prompt engineering
- **SQL Validation** (`utils.py`): Safety checks and SQL normalization
- **Database Layer** (`db.py`): Async PostgreSQL operations with connection pooling
- **Data Models** (`schemas.py`): Pydantic request/response schemas
- **Data Loading** (`load_data.py`): CSV import and database population
- **Database Setup** (`setup_db.py`): Database initialization script

## 📋 Prerequisites

- Python 3.10+
- PostgreSQL database (local or remote)
- OpenAI API key
- Git

### Optional
- Docker (for easy PostgreSQL setup)
- Docker Desktop (for Windows users)

## 🛠️ Installation

1. **Clone the repository** (if applicable) or ensure you're in the project directory

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux/Mac:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🗄️ Database Setup

### Option 1: Docker (Recommended for Development)

1. **Install Docker Desktop** (if not already installed)
   - Download from [docker.com](https://www.docker.com/products/docker-desktop)

2. **Start PostgreSQL container**
   ```bash
   docker run --name postgres-nl2sql \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=nl2sql \
     -p 5432:5432 \
     -d postgres:15
   ```

3. **Verify container is running**
   ```bash
   docker ps
   ```

### Option 2: Direct PostgreSQL Installation

1. **Install PostgreSQL** from [postgresql.org](https://www.postgresql.org/download/)

2. **Create database**
   ```sql
   CREATE DATABASE nl2sql;
   ```

3. **Update connection string** in `.env` file (see Configuration section)

### Option 3: Cloud Database

Use services like:
- [Supabase](https://supabase.com) (free tier available)
- [Neon](https://neon.tech) (free tier available)
- [ElephantSQL](https://www.elephantsql.com) (free tier available)

## ⚙️ Configuration

1. **Create `.env` file** in the project root:
   ```bash
   # OpenAI API Key (get from https://platform.openai.com)
   OPENAI_API_KEY=sk-your-openai-api-key-here

   # PostgreSQL connection string
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nl2sql
   ```

2. **Get OpenAI API Key**:
   - Visit [platform.openai.com](https://platform.openai.com)
   - Create an account or log in
   - Navigate to API Keys section
   - Create a new API key
   - Copy it to your `.env` file

## 📊 Data Loading

The project includes camera product data from three manufacturers:

- **Axis**: Security cameras and access control systems
- **Hanwha**: Network cameras with AI capabilities
- **i-Pro**: Professional surveillance cameras

### Load the data:

1. **Set up the database**
   ```bash
   python setup_db.py
   ```

2. **Load CSV data**
   ```bash
   python load_data.py
   ```

This will:
- Create the `products` table if it doesn't exist
- Load all CSV files from the `data/` directory
- Handle duplicates and data validation
- Provide loading statistics

### Database Schema

```sql
CREATE TABLE products (
    sku TEXT PRIMARY KEY,
    description TEXT,
    price FLOAT,
    currency TEXT,
    family TEXT,
    status TEXT
);
```

## 🚀 Running the Application

1. **Start the server**
   ```bash
   uvicorn main:app --reload
   ```

2. **Access the API**
   - **API Documentation**: http://localhost:8000/docs
   - **Alternative Docs**: http://localhost:8000/redoc
   - **OpenAPI Schema**: http://localhost:8000/openapi.json

## 📡 API Usage

### Endpoint: `POST /query`

Convert natural language to SQL and execute the query.

**Request Body:**
```json
{
  "query": "Show me vandal resistant cameras under $1500"
}
```

**Response:**
```json
{
  "results": [
    {
      "sku": "CAM-001",
      "description": "5MP outdoor vandal resistant bullet camera",
      "price": 1299.0,
      "currency": "CAD",
      "family": "camera",
      "status": "active"
    }
  ],
  "sql": "SELECT * FROM products WHERE description ILIKE '%vandal%' AND description ILIKE '%resistant%' AND price < 1500.0 LIMIT 10;"
}
```

### Example Queries

```bash
# Basic search
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me 5MP cameras"}'

# Price filtering
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "List cameras under 1300 CAD"}'

# Feature-based search
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What vandal resistant bullet cameras do you have?"}'

# Status filtering
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show all active products with AI engine"}'

# Manufacturer specific
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "List all Hanwha products"}'
```

## 🔒 Security Features

- **SQL Injection Prevention**: GPT output is validated against a strict allowlist
- **Read-Only Operations**: Only SELECT queries are permitted
- **Table Restriction**: Queries limited to the `products` table only
- **Result Limiting**: Maximum 10 results per query (configurable)
- **Input Validation**: Pydantic models ensure proper request structure

## 🧪 Testing

### Manual Testing
- Use the Swagger UI at http://localhost:8000/docs
- Test various natural language queries
- Verify SQL generation and results

### Sample Test Queries
```bash
# Test with different manufacturers
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"query": "What Axis products are available?"}'
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"query": "Show i-Pro cameras with AI"}'
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"query": "List Hanwha outdoor cameras"}'
```

## 📁 Project Structure

```
nl2sql-api/
├── main.py                 # FastAPI application and endpoints
├── gpt.py                  # GPT-4o integration and SQL generation
├── db.py                   # PostgreSQL async operations
├── utils.py                # SQL validation and safety utilities
├── schemas.py              # Pydantic request/response models
├── setup_db.py             # Database initialization script
├── load_data.py            # CSV data loading utility
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── README.md              # This file
└── data/                  # CSV data files
    ├── Axis_price_list_formatted_with_families.csv
    ├── hanwha_price_list_formatted_with_families_fixed.csv
    └── i-pro_price_list_formatted_with_families_clean.csv
```

## 🔧 Development

### Adding New Manufacturers

1. Format CSV with columns: `sku,description,price,currency,family,status`
2. Place in `data/` directory
3. The loader will automatically include it

### Modifying SQL Generation

Edit the system prompt in `gpt.py` to change how queries are generated.

### Extending the API

Add new endpoints in `main.py` following FastAPI patterns.

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Ensure PostgreSQL is running
   - Check `DATABASE_URL` in `.env`
   - Verify port 5432 is not blocked

2. **OpenAI API Errors**
   - Check API key is valid
   - Ensure sufficient credits
   - Verify internet connection

3. **Import Errors**
   - Run `pip install -r requirements.txt`
   - Ensure you're in the virtual environment

4. **Port Already in Use**
   - Change port: `uvicorn main:app --port 8001`
   - Or kill existing process

### Logs and Debugging

- Server logs appear in terminal when running
- Use `--reload` flag for development
- Check database directly with psql or pgAdmin

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**: Use production-grade secret management
2. **Database**: Use managed PostgreSQL (RDS, Cloud SQL, etc.)
3. **Scaling**: Add Redis for caching if needed
4. **Monitoring**: Add logging and metrics
5. **Security**: Use HTTPS, API authentication, rate limiting

### Docker Deployment

```dockerfile
# Dockerfile example
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋 Support

For questions or issues:
- Check the troubleshooting section above
- Review the API documentation at `/docs`
- Open an issue on GitHub

---

**Happy querying! 🔍**
