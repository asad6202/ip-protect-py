#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def check_schema():
    dsn = os.getenv('DATABASE_URL')
    print(dsn)
    conn = await asyncpg.connect(dsn)

    # Check all existing tables
    tables = await conn.fetch('''
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    ''')

    print('Existing tables:')
    for row in tables:
        print(f'  - {row["table_name"]}')

    # Check if products table exists and show its structure
    products_exists = await conn.fetch('''
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'products' AND table_schema = 'public'
        )
    ''')

    if products_exists[0]['exists']:
        result = await conn.fetch('''
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'products'
            ORDER BY ordinal_position
        ''')

        print('\nProducts table columns:')
        for row in result:
            print(f'  {row["column_name"]}: {row["data_type"]}')

    # Check if vector extension is available
    extensions = await conn.fetch('''
        SELECT * FROM pg_available_extensions WHERE name = 'vector'
    ''')

    print(f'\nVector extension available: {len(extensions) > 0}')

    # Check enabled extensions
    enabled = await conn.fetch('''
        SELECT extname FROM pg_extension
    ''')

    print(f'Enabled extensions: {[row["extname"] for row in enabled]}')

    await conn.close()


if __name__ == "__main__":
    asyncio.run(check_schema())
