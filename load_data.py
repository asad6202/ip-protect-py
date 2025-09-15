import os
import csv
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

load_dotenv()


async def create_table(db_pool):
    """Create the products table if it doesn't exist."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        description TEXT,
        price FLOAT,
        currency TEXT,
        family TEXT,
        status TEXT
    );
    """
    async with db_pool.acquire() as conn:
        await conn.execute(create_sql)
        print("✓ Products table created or already exists")


async def load_csv_data(db_pool, csv_file_path: str):
    """Load data from a single CSV file into the database."""
    print(f"Loading data from {csv_file_path}...")

    # Read and parse CSV
    products = []
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Clean and validate data
            try:
                product = {
                    'sku': row['sku'].strip().strip('"'),
                    'description': row['description'].strip().strip('"'),
                    'price': float(row['price'].strip().strip('"')),
                    'currency': row['currency'].strip().strip('"'),
                    'family': row['family'].strip().strip('"'),
                    'status': row['status'].strip().strip('"')
                }
                products.append(product)
            except (ValueError, KeyError) as e:
                print(f"⚠️  Skipping row with error: {e}")
                continue

    # Insert data in batches
    batch_size = 100
    total_inserted = 0

    async with db_pool.acquire() as conn:
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]

            # Use ON CONFLICT to handle duplicates
            insert_sql = """
            INSERT INTO products (sku, description, price, currency, family, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (sku) DO UPDATE SET
                description = EXCLUDED.description,
                price = EXCLUDED.price,
                currency = EXCLUDED.currency,
                family = EXCLUDED.family,
                status = EXCLUDED.status
            """

            for product in batch:
                try:
                    await conn.execute(insert_sql,
                        product['sku'], product['description'], product['price'],
                        product['currency'], product['family'], product['status']
                    )
                    total_inserted += 1
                except Exception as e:
                    print(f"⚠️  Error inserting {product['sku']}: {e}")

    print(f"✓ Loaded {total_inserted} products from {csv_file_path}")
    return total_inserted


async def main():
    """Main function to load all CSV files."""
    # Get database connection
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL not set in .env file")
        return

    # Create connection pool
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)

    try:
        # Create table
        await create_table(pool)

        # Define CSV files to load
        data_dir = Path("data")
        csv_files = [
            data_dir / "Axis_price_list_formatted_with_families.csv",
            data_dir / "hanwha_price_list_formatted_with_families_fixed.csv",
            data_dir / "i-pro_price_list_formatted_with_families_clean.csv"
        ]

        total_loaded = 0
        for csv_file in csv_files:
            if csv_file.exists():
                loaded = await load_csv_data(pool, str(csv_file))
                total_loaded += loaded
            else:
                print(f"⚠️  CSV file not found: {csv_file}")

        print(f"\n🎉 Successfully loaded {total_loaded} products into the database!")

        # Quick verification
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM products")
            print(f"📊 Total products in database: {count}")

            # Show sample data
            sample = await conn.fetch("SELECT sku, description, price, currency, family FROM products LIMIT 3")
            print("\n📋 Sample data:")
            for row in sample:
                print(f"  {row['sku']}: {row['description'][:50]}... - ${row['price']} {row['currency']} ({row['family']})")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
