"""
Product management endpoints for the IP Protect system.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from db import Database
import math

router = APIRouter()

# Global database instance
db_instance = None

def get_database() -> Database:
    """Get database instance."""
    global db_instance
    if db_instance is None:
        db_instance = Database()
    return db_instance

class Product(BaseModel):
    id: str
    brand_id: Optional[str] = None
    sku: str
    description: str
    price: float
    currency: str
    family: str
    status: str  # We'll map 'active' to 'status'
    form_factor: Optional[str] = None
    outdoor: Optional[bool] = None
    poe: Optional[bool] = None
    poe_plus: Optional[bool] = None
    ir_range_m: Optional[int] = None
    resolution_mp: Optional[float] = None
    vandal_ik10: Optional[bool] = None
    nvr_channels: Optional[int] = None
    switch_ports: Optional[int] = None
    is_accessory: bool
    accessory_type: Optional[str] = None
    created_at: str
    updated_at: str

class PaginatedProductsResponse(BaseModel):
    items: List[Product]  # Frontend expects 'items'
    total: int
    page: int
    page_size: int
    pages: int  # Frontend expects 'pages'

class Brand(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    created_at: str
    updated_at: str
    product_count: int = 0

def convert_db_product_to_api(db_row: Dict[str, Any]) -> Product:
    """Convert database row to API Product model."""
    return Product(
        id=str(db_row['id']),
        brand_id=db_row.get('brand_id'),
        sku=db_row['sku'],
        description=db_row['description'],
        price=float(db_row['price']) if db_row['price'] else 0.0,
        currency=db_row['currency'] or 'USD',
        family=db_row['family'] or '',
        status='active' if db_row.get('active', True) else 'inactive',  # Map boolean to status
        form_factor=db_row.get('form_factor'),
        outdoor=db_row.get('outdoor'),
        poe=db_row.get('poe'),
        poe_plus=db_row.get('poe_plus'),
        ir_range_m=db_row.get('ir_range_m'),
        resolution_mp=float(db_row['resolution_mp']) if db_row.get('resolution_mp') else None,
        vandal_ik10=db_row.get('vandal_ik10'),
        nvr_channels=db_row.get('nvr_channels'),
        switch_ports=db_row.get('switch_ports'),
        is_accessory=bool(db_row.get('is_accessory', False)),
        accessory_type=db_row.get('accessory_type'),
        created_at=db_row['created_at'].isoformat() if db_row.get('created_at') else '',
        updated_at=db_row['updated_at'].isoformat() if db_row.get('updated_at') else ''
    )

@router.get("/products", response_model=PaginatedProductsResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    family: Optional[str] = Query(None),
    brand_id: Optional[str] = Query(None),
    is_accessory: Optional[bool] = Query(None),
    db: Database = Depends(get_database)
) -> PaginatedProductsResponse:
    """List products with pagination and filters."""
    try:
        if not db._pool:
            await db.connect()

        # Build the WHERE clause
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append("(description ILIKE $1 OR sku ILIKE $1)")
            params.append(f"%{search}%")
        
        if family:
            where_conditions.append(f"family = ${len(params) + 1}")
            params.append(family)
            
        if brand_id:
            where_conditions.append(f"brand_id = ${len(params) + 1}")
            params.append(brand_id)
            
        if is_accessory is not None:
            where_conditions.append(f"is_accessory = ${len(params) + 1}")
            params.append(is_accessory)

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        # Get total count
        count_sql = f"SELECT COUNT(*) FROM products {where_clause}"
        
        async with db._pool.acquire() as conn:
            total = await conn.fetchval(count_sql, *params)
            
            # Get paginated results
            offset = (page - 1) * page_size
            params.extend([page_size, offset])
            
            products_sql = f"""
                SELECT id, brand_id, sku, description, price, currency, family, active,
                       form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp,
                       vandal_ik10, nvr_channels, switch_ports, is_accessory, 
                       accessory_type, created_at, updated_at
                FROM products 
                {where_clause}
                ORDER BY created_at DESC 
                LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """
            
            rows = await conn.fetch(products_sql, *params)
            products = [convert_db_product_to_api(dict(row)) for row in rows]
            
            total_pages = math.ceil(total / page_size)
            
            return PaginatedProductsResponse(
                items=products,  # Changed to 'items'
                total=total,
                page=page,
                page_size=page_size,
                pages=total_pages  # Changed to 'pages'
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")

@router.get("/products/families")
async def get_product_families(
    db: Database = Depends(get_database)
) -> List[str]:
    """Get list of unique product families."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            sql = "SELECT DISTINCT family FROM products WHERE family IS NOT NULL ORDER BY family"
            rows = await conn.fetch(sql)
            families = [row['family'] for row in rows]
            return families
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product families: {str(e)}")

@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    db: Database = Depends(get_database)
) -> Product:
    """Get a single product by ID."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            sql = """
                SELECT id, brand_id, sku, description, price, currency, family, active,
                       form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp,
                       vandal_ik10, nvr_channels, switch_ports, is_accessory, 
                       accessory_type, created_at, updated_at
                FROM products 
                WHERE id = $1
            """
            row = await conn.fetchrow(sql, product_id)
            if not row:
                raise HTTPException(status_code=404, detail="Product not found")
            
            return convert_db_product_to_api(dict(row))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product: {str(e)}")

@router.get("/brands")
async def list_brands(
    db: Database = Depends(get_database)
) -> List[Brand]:
    """List all brands."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # First check if brands table exists
            brands_exist = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'brands'
                )
            """)
            
            if brands_exist:
                sql = """
                    SELECT 
                        b.id, 
                        b.name, 
                        b.slug, 
                        b.created_at, 
                        b.updated_at,
                        COALESCE(COUNT(p.id), 0) as product_count
                    FROM brands b
                    LEFT JOIN products p ON b.id = p.brand_id
                    GROUP BY b.id, b.name, b.slug, b.created_at, b.updated_at
                    ORDER BY b.name
                """
                rows = await conn.fetch(sql)
                return [
                    Brand(
                        id=str(row['id']),
                        name=row['name'],
                        slug=row.get('slug'),
                        created_at=row['created_at'].isoformat() if row.get('created_at') else '',
                        updated_at=row['updated_at'].isoformat() if row.get('updated_at') else '',
                        product_count=int(row['product_count'])
                    ) for row in rows
                ]
            else:
                # If no brands table, extract unique brand_ids from products with counts
                sql = """
                    SELECT 
                        brand_id as id, 
                        brand_id as name,
                        COUNT(*) as product_count
                    FROM products 
                    WHERE brand_id IS NOT NULL 
                    GROUP BY brand_id
                    ORDER BY brand_id
                """
                rows = await conn.fetch(sql)
                return [
                    Brand(
                        id=row['id'],
                        name=row['name'],
                        slug=None,
                        created_at='',
                        updated_at='',
                        product_count=int(row['product_count'])
                    ) for row in rows
                ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list brands: {str(e)}")


@router.get("/brands/{brand_id}")
async def get_brand(
    brand_id: str,
    db: Database = Depends(get_database)
) -> Brand:
    """Get a single brand by ID."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if brands table exists
            brands_exist = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'brands'
                )
            """)
            
            if brands_exist:
                sql = """
                    SELECT 
                        b.id, 
                        b.name, 
                        b.slug, 
                        b.created_at, 
                        b.updated_at,
                        COALESCE(COUNT(p.id), 0) as product_count
                    FROM brands b
                    LEFT JOIN products p ON b.id = p.brand_id
                    WHERE b.id = $1
                    GROUP BY b.id, b.name, b.slug, b.created_at, b.updated_at
                """
                row = await conn.fetchrow(sql, brand_id)
                if not row:
                    raise HTTPException(status_code=404, detail="Brand not found")
                
                return Brand(
                    id=str(row['id']),
                    name=row['name'],
                    slug=row.get('slug'),
                    created_at=row['created_at'].isoformat() if row.get('created_at') else '',
                    updated_at=row['updated_at'].isoformat() if row.get('updated_at') else '',
                    product_count=int(row['product_count'])
                )
            else:
                # If no brands table, check if brand_id exists in products
                sql = """
                    SELECT 
                        brand_id as id, 
                        brand_id as name,
                        COUNT(*) as product_count
                    FROM products 
                    WHERE brand_id = $1
                    GROUP BY brand_id
                """
                row = await conn.fetchrow(sql, brand_id)
                if not row:
                    raise HTTPException(status_code=404, detail="Brand not found")
                
                return Brand(
                    id=row['id'],
                    name=row['name'],
                    slug=None,
                    created_at='',
                    updated_at='',
                    product_count=int(row['product_count'])
                )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get brand: {str(e)}")


class BrandCreate(BaseModel):
    name: str
    slug: Optional[str] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


@router.post("/brands")
async def create_brand(
    brand_data: BrandCreate,
    db: Database = Depends(get_database)
) -> Brand:
    """Create a new brand."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if brands table exists, if not create it
            brands_exist = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'brands'
                )
            """)
            
            if not brands_exist:
                # Create brands table
                await conn.execute("""
                    CREATE TABLE brands (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name TEXT NOT NULL UNIQUE,
                        slug TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
            
            # Insert new brand
            sql = """
                INSERT INTO brands (name, slug) 
                VALUES ($1, $2) 
                RETURNING id, name, slug, created_at, updated_at
            """
            row = await conn.fetchrow(sql, brand_data.name, brand_data.slug)
            
            return Brand(
                id=str(row['id']),
                name=row['name'],
                slug=row.get('slug'),
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat(),
                product_count=0
            )
    
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=400, detail="Brand with this name already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create brand: {str(e)}")


@router.patch("/brands/{brand_id}")
async def update_brand(
    brand_id: str,
    brand_data: BrandUpdate,
    db: Database = Depends(get_database)
) -> Brand:
    """Update a brand."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if brands table exists
            brands_exist = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'brands'
                )
            """)
            
            if not brands_exist:
                raise HTTPException(status_code=404, detail="Brands table does not exist")
            
            # Build update query dynamically
            update_fields = []
            values = []
            param_count = 1
            
            if brand_data.name is not None:
                update_fields.append(f"name = ${param_count}")
                values.append(brand_data.name)
                param_count += 1
            
            if brand_data.slug is not None:
                update_fields.append(f"slug = ${param_count}")
                values.append(brand_data.slug)
                param_count += 1
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            update_fields.append(f"updated_at = NOW()")
            values.append(brand_id)
            
            sql = f"""
                UPDATE brands 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, name, slug, created_at, updated_at
            """
            
            row = await conn.fetchrow(sql, *values)
            if not row:
                raise HTTPException(status_code=404, detail="Brand not found")
            
            # Get product count
            count_sql = "SELECT COUNT(*) FROM products WHERE brand_id = $1"
            product_count = await conn.fetchval(count_sql, brand_id)
            
            return Brand(
                id=str(row['id']),
                name=row['name'],
                slug=row.get('slug'),
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat(),
                product_count=int(product_count)
            )
    
    except HTTPException:
        raise
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=400, detail="Brand with this name already exists")
        raise HTTPException(status_code=500, detail=f"Failed to update brand: {str(e)}")


@router.delete("/brands/{brand_id}")
async def delete_brand(
    brand_id: str,
    db: Database = Depends(get_database)
) -> dict:
    """Delete a brand."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if brands table exists
            brands_exist = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'brands'
                )
            """)
            
            if not brands_exist:
                raise HTTPException(status_code=404, detail="Brands table does not exist")
            
            # Check if brand exists
            brand_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM brands WHERE id = $1)", 
                brand_id
            )
            
            if not brand_exists:
                raise HTTPException(status_code=404, detail="Brand not found")
            
            # Get count of products for logging
            product_count = await conn.fetchval(
                "SELECT COUNT(*) FROM products WHERE brand_id = $1", 
                brand_id
            )
            
            # Get count of uploads for logging
            upload_count = await conn.fetchval(
                "SELECT COUNT(*) FROM product_uploads WHERE brand_id = $1", 
                brand_id
            )
            
            # Delete all associated data in the correct order (respecting foreign key constraints)
            # 1. Delete products first (they reference brand_id)
            if product_count > 0:
                await conn.execute("DELETE FROM products WHERE brand_id = $1", brand_id)
            
            # 2. Delete uploads (they reference brand_id)
            if upload_count > 0:
                await conn.execute("DELETE FROM product_uploads WHERE brand_id = $1", brand_id)
            
            # 3. Finally delete the brand
            sql = "DELETE FROM brands WHERE id = $1"
            result = await conn.execute(sql, brand_id)
            
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Brand not found")
            
            # Prepare deletion summary
            deleted_items = []
            if product_count > 0:
                deleted_items.append(f"{product_count} products")
            if upload_count > 0:
                deleted_items.append(f"{upload_count} uploads")
            
            summary = f"Brand deleted successfully"
            if deleted_items:
                summary += f" along with {', '.join(deleted_items)}"
            
            return {"message": summary}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete brand: {str(e)}")