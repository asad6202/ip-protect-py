#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_schema():
    dsn = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(dsn)
    
    # Check if embedding column exists
    result = await conn.fetch('''
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'products'
        ORDER BY ordinal_position
    ''')
    
    print('Products table columns:')
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
