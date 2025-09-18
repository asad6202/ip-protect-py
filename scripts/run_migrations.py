#!/usr/bin/env python3
"""
Run database migrations for the quote generation system.
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def run_migration_file(conn: asyncpg.Connection, file_path: str) -> bool:
    """Run a single migration file."""
    try:
        with open(file_path, 'r') as f:
            sql = f.read()
        
        await conn.execute(sql)
        print(f"✅ Migrated: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to migrate {file_path}: {e}")
        return False


async def main():
    """Run all migrations in order."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL environment variable is required")
        return 1
    
    # Migration files in order
    migrations = [
        "migrations/001_enable_extensions.sql",
        "migrations/002_add_embedding_column.sql"
    ]
    
    try:
        conn = await asyncpg.connect(dsn)
        print("✅ Connected to database")
        
        for migration_file in migrations:
            if os.path.exists(migration_file):
                success = await run_migration_file(conn, migration_file)
                if not success:
                    print(f"❌ Migration failed: {migration_file}")
                    await conn.close()
                    return 1
            else:
                print(f"⚠️  Migration file not found: {migration_file}")
        
        await conn.close()
        print("\n🎉 All migrations completed successfully!")
        print("\nNext steps:")
        print("1. Run: python scripts/backfill_embeddings.py")
        print("2. Test: python scripts/test_quote_api.py")
        print("3. Start server: python main.py")
        
        return 0
        
    except Exception as e:
        print(f"❌ Migration process failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
