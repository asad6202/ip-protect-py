# Database Recreation Scripts

This directory contains scripts to completely recreate the database schema from scratch.

## ⚠️ WARNING

These scripts will **PERMANENTLY DELETE** all existing data in your database. Make sure you have backups if you need to preserve any data.

## Scripts

### 1. `recreate_database_safe.py` (RECOMMENDED)
- **Safe version** that asks for confirmation before dropping tables
- Shows you exactly what data will be lost
- Requires typing 'YES' to confirm the operation
- Use this for production or when you have important data

```bash
python3 recreate_database_safe.py
```

### 2. `recreate_database.py`
- **Direct version** that drops and recreates without confirmation
- Use only when you're absolutely sure you want to delete everything
- Good for development or when you know the database is empty

```bash
python3 recreate_database.py
```

### 3. `verify_schema.py`
- Verifies that the new schema was created correctly
- Checks all tables, indexes, and extensions
- Run this after recreation to ensure everything is working

```bash
python3 verify_schema.py
```

### 4. `check_db.py`
- Shows current database state
- Lists existing tables and their structure
- Useful for checking what's currently in the database

```bash
python3 check_db.py
```

## What Gets Created

The scripts will create a complete single-user quote generator schema with:

### Tables
- **brands** - Product brands/manufacturers
- **product_uploads** - CSV upload tracking
- **product_import_batches** - Import batch tracking
- **products** - Main product catalog with full-text search
- **product_embeddings** - Vector embeddings for AI search
- **quotes** - Generated quotes
- **quote_items** - Individual items in quotes
- **quote_feedback** - User feedback on quotes
- **rule_sets** - Named rule collections
- **rules** - Business rules for quote generation
- **rule_executions** - Audit trail of rule applications
- **prompt_runs** - Audit trail of quote generation requests

### Extensions
- **pgcrypto** - For UUID generation
- **pg_trgm** - For trigram text search
- **unaccent** - For accent-insensitive search
- **vector** - For AI embeddings (optional, graceful fallback)

### Features
- Full-text search with PostgreSQL TSVECTOR
- Trigram search for fuzzy matching
- JSONB for flexible metadata storage
- Comprehensive indexing for performance
- Proper foreign key relationships
- Check constraints for data validation

## Usage Example

```bash
# 1. Check current state
python3 check_db.py

# 2. Recreate database (safe version)
python3 recreate_database_safe.py

# 3. Verify the new schema
python3 verify_schema.py
```

## Environment Requirements

Make sure your `.env` file contains:
```
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```
