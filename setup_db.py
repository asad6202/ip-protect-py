import os
import asyncio
from dotenv import load_dotenv
import asyncpg

load_dotenv()


async def setup_database():
    """Set up the database and create the products table (live schema)."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL not set in .env file")
        return False

    try:
        # Connect to database
        conn = await asyncpg.connect(dsn)
        print("✅ Connected to database")

        # Create products table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS products (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            manufacturer_id UUID,
            sku TEXT UNIQUE,
            description TEXT,
            price NUMERIC,
            currency TEXT,
            active BOOLEAN DEFAULT TRUE,
            trained BOOLEAN DEFAULT FALSE,
            raw JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            manufacturer_slug TEXT,
            search_text TEXT,
            product_number TEXT,
            family TEXT
        );
        """

        await conn.execute(create_table_sql)
        print("✅ Products table created successfully")

        # Test the connection
        count = await conn.fetchval("SELECT COUNT(*) FROM products")
        print(f"📊 Current product count: {count}")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(setup_database())
    if success:
        print("\n🎉 Database setup complete!")
        print("Now run: python load_data.py")
    else:
        print("\n❌ Database setup failed. Check your DATABASE_URL and database connection.")
