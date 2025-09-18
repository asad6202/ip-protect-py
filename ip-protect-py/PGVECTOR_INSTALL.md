# Installing pgvector for Vector Search

The quote generation system can work with or without pgvector, but vector search provides better semantic matching when deterministic search yields weak results.

## Option 1: Install pgvector (Recommended)

### For macOS (using Homebrew)
```bash
# Install PostgreSQL with pgvector
brew install pgvector

# Or if you already have PostgreSQL installed
brew install pgvector
```

### For Ubuntu/Debian
```bash
# Add the pgvector repository
curl -fsSL https://apt.postgresql.org/pub/repos/apt/signkey | sudo gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

# Install pgvector
sudo apt update
sudo apt install postgresql-14-pgvector
```

### For Docker
```bash
# Use the pgvector Docker image
docker run --name postgres-pgvector -e POSTGRES_PASSWORD=password -p 5432:5432 -d pgvector/pgvector:pg14
```

### For Docker Compose
```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg14
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ip_protect
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Option 2: Use Without pgvector

The system will work with deterministic search only. You can:

1. **Skip the migration step** that adds the embedding column
2. **Run the setup** - it will gracefully handle the missing extension
3. **Use the system** - it will fall back to SQL-based search only

## Verification

After installing pgvector, verify it's working:

```sql
-- Connect to your database
psql -d your_database_name

-- Check if the extension is available
SELECT * FROM pg_available_extensions WHERE name = 'vector';

-- Enable the extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify it's enabled
SELECT * FROM pg_extension WHERE extname = 'vector';
```

## Troubleshooting

### "could not open extension control file"
This means pgvector is not installed. Install it using one of the methods above.

### "permission denied"
Make sure you're connecting as a superuser or a user with CREATE privileges:
```sql
-- Check your role
SELECT current_user, usesuper FROM pg_user WHERE usename = current_user;

-- If not superuser, grant privileges
GRANT CREATE ON DATABASE your_database_name TO your_username;
```

### "extension already exists"
This is normal - the extension is already installed and enabled.

## Performance Notes

- pgvector works best with PostgreSQL 14+
- The IVFFlat index is optimized for L2 distance (cosine similarity)
- Adjust the `lists` parameter based on your data size:
  - Small datasets (< 10K rows): lists = 100
  - Medium datasets (10K-100K rows): lists = 1000
  - Large datasets (> 100K rows): lists = 10000

## Next Steps

Once pgvector is installed:

1. Run the migrations: `python scripts/run_migrations.py`
2. Backfill embeddings: `python scripts/backfill_embeddings.py`
3. Test the system: `python scripts/test_quote_api.py`
4. Start the server: `python main.py`
