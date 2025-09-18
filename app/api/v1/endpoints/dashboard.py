from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
import asyncpg

from db import Database, get_database

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Get aggregated dashboard statistics."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Get brand count
            brands_count = await conn.fetchval("""
                SELECT COUNT(DISTINCT b.id) 
                FROM brands b
            """)
            
            # Get products count
            products_count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM products 
                WHERE active = true
            """)
            
            # Get quotes count
            quotes_count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM quotes
            """)
            
            # Get uploads count
            uploads_count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM product_uploads
            """)
            
            return {
                "brands": brands_count or 0,
                "products": products_count or 0, 
                "quotes": quotes_count or 0,
                "uploads": uploads_count or 0
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")


@router.get("/dashboard/recent-quotes")
async def get_recent_quotes(
    limit: int = 5,
    db: Database = Depends(get_database)
) -> List[Dict[str, Any]]:
    """Get recent quotes for dashboard."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            sql = """
                SELECT 
                    id,
                    title,
                    total_amount,
                    currency,
                    status,
                    created_at,
                    updated_at
                FROM quotes
                ORDER BY created_at DESC
                LIMIT $1
            """
            
            rows = await conn.fetch(sql, limit)
            
            return [
                {
                    "id": str(row['id']),
                    "title": row['title'] or 'Untitled Quote',
                    "total_amount": float(row['total_amount']) if row['total_amount'] else 0.0,
                    "currency": row['currency'] or 'USD',
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat(),
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else row['created_at'].isoformat()
                } for row in rows
            ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent quotes: {str(e)}")


@router.get("/dashboard/recent-uploads")  
async def get_recent_uploads(
    limit: int = 5,
    db: Database = Depends(get_database)
) -> List[Dict[str, Any]]:
    """Get recent uploads for dashboard."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            sql = """
                SELECT 
                    id,
                    brand_id,
                    original_name,
                    row_count,
                    status,
                    created_at
                FROM product_uploads
                ORDER BY created_at DESC
                LIMIT $1
            """
            
            rows = await conn.fetch(sql, limit)
            
            return [
                {
                    "id": str(row['id']),
                    "brand_id": row['brand_id'],
                    "original_name": row['original_name'],
                    "row_count": row['row_count'],
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat()
                } for row in rows
            ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent uploads: {str(e)}")