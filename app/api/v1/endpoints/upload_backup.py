"""
Upload management endpoints for the IP Protect system.
"""

import os
import uuid
import csv
import pandas as pd
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from db import Database

router = APIRouter()

# Global database instance
db_instance = None

def get_database() -> Database:
    """Get database instance."""
    global db_instance
    if db_instance is None:
        db_instance = Database()
    return db_instance

class ProductUpload(BaseModel):
    id: str
    brand_id: Optional[str] = None
    original_name: str
    stored_path: str
    row_count: Optional[int] = None
    status: str
    message: Optional[str] = None
    created_at: str
    processed_at: Optional[str] = None

class UploadResponse(BaseModel):
    id: str
    brand_id: Optional[str] = None
    original_name: str
    row_count: Optional[int] = None
    status: str
    message: Optional[str] = None
    created_at: str
    processed_at: Optional[str] = None

@router.get("/uploads")
async def list_uploads(
    db: Database = Depends(get_database)
) -> List[ProductUpload]:
    """List all uploads."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if product_uploads table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'product_uploads'
                )
            """)
            
            if not table_exists:
                return []
            
            sql = """
                SELECT 
                    id, 
                    brand_id, 
                    original_name, 
                    stored_path, 
                    row_count, 
                    status, 
                    message, 
                    created_at, 
                    processed_at
                FROM product_uploads 
                ORDER BY created_at DESC
            """
            rows = await conn.fetch(sql)
            
            return [
                ProductUpload(
                    id=str(row['id']),
                    brand_id=row.get('brand_id'),
                    original_name=row['original_name'],
                    stored_path=row['stored_path'],
                    row_count=row.get('row_count'),
                    status=row['status'],
                    message=row.get('message'),
                    created_at=row['created_at'].isoformat(),
                    processed_at=row['processed_at'].isoformat() if row.get('processed_at') else None
                ) for row in rows
            ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list uploads: {str(e)}")

@router.get("/uploads/{upload_id}")
async def get_upload(
    upload_id: str,
    db: Database = Depends(get_database)
) -> ProductUpload:
    """Get a single upload by ID."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            sql = """
                SELECT 
                    id, 
                    brand_id, 
                    original_name, 
                    stored_path, 
                    row_count, 
                    status, 
                    message, 
                    created_at, 
                    processed_at
                FROM product_uploads 
                WHERE id = $1
            """
            row = await conn.fetchrow(sql, upload_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Upload not found")
            
            return ProductUpload(
                id=str(row['id']),
                brand_id=row.get('brand_id'),
                original_name=row['original_name'],
                stored_path=row['stored_path'],
                row_count=row.get('row_count'),
                status=row['status'],
                message=row.get('message'),
                created_at=row['created_at'].isoformat(),
                processed_at=row['processed_at'].isoformat() if row.get('processed_at') else None
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get upload: {str(e)}")

@router.post("/uploads")
async def upload_file(
    file: UploadFile = File(...),
    brand_id: Optional[str] = Form(None),
    db: Database = Depends(get_database)
) -> UploadResponse:
    """Upload a CSV file and process it."""
    try:
        if not db._pool:
            await db.connect()

        # Validate file type
        if not file.filename.lower().endswith(('.csv', '.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail="Only CSV, XLS, and XLSX files are supported")

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        stored_filename = f"{file_id}{file_extension}"
        
        # Create uploads directory if it doesn't exist
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        stored_path = os.path.join(uploads_dir, stored_filename)

        # Save file
        with open(stored_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Read and validate CSV
        try:
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(stored_path)
            else:
                df = pd.read_excel(stored_path)
            
            row_count = len(df)
            
            # Validate required columns
            required_columns = ['sku', 'description', 'price', 'currency', 'family']
            missing_columns = [col for col in required_columns if col.lower() not in [c.lower() for c in df.columns]]
            
            if missing_columns:
                # Clean up file
                os.remove(stored_path)
                raise HTTPException(
                    status_code=400, 
                    detail=f"Missing required columns: {', '.join(missing_columns)}. Required columns are: {', '.join(required_columns)}"
                )
            
            # Normalize column names to lowercase
            df.columns = df.columns.str.lower()
            
        except Exception as e:
            # Clean up file
            os.remove(stored_path)
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

        async with db._pool.acquire() as conn:
            # Create product_uploads table if it doesn't exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS product_uploads (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    brand_id UUID REFERENCES brands(id) ON DELETE SET NULL,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    row_count INTEGER,
                    status TEXT NOT NULL DEFAULT 'uploaded',
                    message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    processed_at TIMESTAMP WITH TIME ZONE
                )
            """)
            
            # Insert upload record
            upload_id = str(uuid.uuid4())
            sql = """
                INSERT INTO product_uploads (id, brand_id, original_name, stored_path, row_count, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, brand_id, original_name, stored_path, row_count, status, message, created_at, processed_at
            """
            row = await conn.fetchrow(
                sql, 
                upload_id, 
                brand_id, 
                file.filename, 
                stored_path, 
                row_count, 
                'uploaded'
            )
            
            # Process the file in the background
            await process_upload_file(conn, upload_id, stored_path, brand_id, df)
            
            return UploadResponse(
                id=str(row['id']),
                brand_id=row.get('brand_id'),
                original_name=row['original_name'],
                row_count=row.get('row_count'),
                status=row['status'],
                message=row.get('message'),
                created_at=row['created_at'].isoformat(),
                processed_at=row['processed_at'].isoformat() if row.get('processed_at') else None
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

async def process_upload_file(conn, upload_id: str, file_path: str, brand_id: Optional[str], df: pd.DataFrame):
    """Process the uploaded file and import products."""
    try:
        # Update status to processing
        await conn.execute(
            "UPDATE product_uploads SET status = 'processing' WHERE id = $1",
            upload_id
        )
        
        # Ensure brand exists
        if not brand_id:
            raise Exception("Brand ID is required for product upload")
        
        # Verify brand exists
        brand_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM brands WHERE id = $1)", brand_id
        )
        if not brand_exists:
            raise Exception(f"Brand with ID {brand_id} does not exist")
        
        # Add required columns to products table if they don't exist
        await conn.execute("""
            ALTER TABLE products 
            ADD COLUMN IF NOT EXISTS search_text TEXT,
            ADD COLUMN IF NOT EXISTS raw_json JSONB,
            ADD COLUMN IF NOT EXISTS ts TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT true
        """)
        
        # Process each row following the pattern from load_products_simple.py
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Extract basic fields following the load_products_simple.py pattern
                sku = str(row.get('sku', '')).strip()
                description = str(row.get('description', '')).strip()
                price_str = str(row.get('price', '0'))
                currency = str(row.get('currency', 'USD')).strip().upper()
                family = str(row.get('family', '')).strip()
                status = str(row.get('status', 'active')).strip().lower()
                
                if not sku or not description:
                    errors.append(f"Row {index + 1}: Missing required fields (SKU or description)")
                    continue
                
                # Parse price following the load_products_simple.py pattern
                import re
                try:
                    price = float(re.sub(r'[^\d.]', '', price_str))
                except ValueError:
                    price = 0.0
                
                # Convert status to boolean following load_products_simple.py pattern
                active = status == 'active'
                
                # Create search text following load_products_simple.py pattern
                search_text = f"{sku} {description} {family}".strip()
                
                # Create raw_json following load_products_simple.py pattern
                import json
                raw_json = json.dumps(dict(row))
                
                # Insert product with the updated table structure
                sql = """
                    INSERT INTO products (
                        brand_id, sku, description, price, currency, family, status,
                        form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp,
                        vandal_ik10, nvr_channels, switch_ports, is_accessory, accessory_type,
                        search_text, raw_json, active
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
                    )
                """
                
                # Map optional fields with proper null handling
                form_factor = str(row.get('form_factor', '')).strip() if pd.notna(row.get('form_factor')) and str(row.get('form_factor', '')).strip() else None
                outdoor = bool(row.get('outdoor')) if pd.notna(row.get('outdoor')) else None
                poe = bool(row.get('poe')) if pd.notna(row.get('poe')) else None
                poe_plus = bool(row.get('poe_plus')) if pd.notna(row.get('poe_plus')) else None
                ir_range_m = int(row['ir_range_m']) if pd.notna(row.get('ir_range_m')) else None
                resolution_mp = float(row['resolution_mp']) if pd.notna(row.get('resolution_mp')) else None
                vandal_ik10 = bool(row.get('vandal_ik10')) if pd.notna(row.get('vandal_ik10')) else None
                nvr_channels = int(row['nvr_channels']) if pd.notna(row.get('nvr_channels')) else None
                switch_ports = int(row['switch_ports']) if pd.notna(row.get('switch_ports')) else None
                is_accessory = bool(row.get('is_accessory', False))
                accessory_type = str(row.get('accessory_type', '')).strip() if pd.notna(row.get('accessory_type')) and str(row.get('accessory_type', '')).strip() else None
                
                await conn.execute(sql, 
                    brand_id, sku, description, price, currency, family, 'active',
                    form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp,
                    vandal_ik10, nvr_channels, switch_ports, is_accessory, accessory_type,
                    search_text, raw_json, active
                )
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
        
        # Update upload status
        if errors:
            message = f"Imported {imported_count} products. Errors: {'; '.join(errors[:5])}"
            if len(errors) > 5:
                message += f" and {len(errors) - 5} more errors"
            await conn.execute(
                "UPDATE product_uploads SET status = 'failed', message = $1, processed_at = NOW() WHERE id = $2",
                message, upload_id
            )
        else:
            await conn.execute(
                "UPDATE product_uploads SET status = 'processed', message = $1, processed_at = NOW() WHERE id = $2",
                f"Successfully imported {imported_count} products", upload_id
            )
    
    except Exception as e:
        # Update status to failed
        await conn.execute(
            "UPDATE product_uploads SET status = 'failed', message = $1, processed_at = NOW() WHERE id = $2",
            f"Processing failed: {str(e)}", upload_id
        )

@router.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: str,
    db: Database = Depends(get_database)
) -> dict:
    """Delete an upload and its associated file."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Get file path
            row = await conn.fetchrow(
                "SELECT stored_path FROM product_uploads WHERE id = $1",
                upload_id
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Upload not found")
            
            # Delete from database
            await conn.execute(
                "DELETE FROM product_uploads WHERE id = $1",
                upload_id
            )
            
            # Delete file
            file_path = row['stored_path']
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return {"message": "Upload deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete upload: {str(e)}")
