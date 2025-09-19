"""
Upload management endpoints for the IP Protect system.
"""

import os
import uuid
import csv
import pandas as pd
import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
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
    brand_id: Optional[str] = None,
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
            
            if brand_id:
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
                    WHERE brand_id = $1
                    ORDER BY created_at DESC
                """
                rows = await conn.fetch(sql, brand_id)
            else:
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
    db: Database = Depends(get_database),
    background_tasks: BackgroundTasks = BackgroundTasks()
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
                    processed_at TIMESTAMP WITH TIME ZONE,
                    started_at TIMESTAMP WITH TIME ZONE,
                    processed_rows INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0
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
            
            # Update status to queued for background processing
            await conn.execute(
                "UPDATE product_uploads SET status = 'queued' WHERE id = $1",
                upload_id
            )
            
            # Queue the file processing in the background (non-blocking)
            background_tasks.add_task(
                process_upload_file_async, 
                upload_id, 
                stored_path, 
                brand_id, 
                df.copy()  # Pass a copy to avoid any threading issues
            )
            
            # Return immediately with queued status
            return UploadResponse(
                id=upload_id,
                brand_id=brand_id,
                original_name=file.filename,
                row_count=row_count,
                status='queued',
                message='Upload queued for processing',
                created_at=row['created_at'].isoformat(),
                processed_at=None
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
                
                # Create search text following load_products_simple.py pattern
                search_text = f"{sku} {description} {family}".strip()
                
                # Create raw_json following load_products_simple.py pattern
                import json
                raw_json = json.dumps(dict(row))
                
                # Insert product with the complete table structure including search_text and raw_json
                sql = """
                    INSERT INTO products (
                        brand_id, sku, description, price, currency, family, active,
                        form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp,
                        vandal_ik10, nvr_channels, switch_ports, is_accessory, accessory_type,
                        search_text, raw_json
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
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
                
                # Convert status to boolean for active column
                active = status == 'active'
                
                await conn.execute(sql, 
                    brand_id, sku, description, price, currency, family, active,
                    form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp,
                    vandal_ik10, nvr_channels, switch_ports, is_accessory, accessory_type,
                    search_text, raw_json
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
            
            # Delete the uploaded file after successful processing
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Successfully deleted uploaded file: {file_path}")
            except Exception as e:
                print(f"Warning: Failed to delete uploaded file {file_path}: {str(e)}")
    
    except Exception as e:
        # Update status to failed
        await conn.execute(
            "UPDATE product_uploads SET status = 'failed', message = $1, processed_at = NOW() WHERE id = $2",
            f"Processing failed: {str(e)}", upload_id
        )

async def process_upload_file_async(upload_id: str, file_path: str, brand_id: Optional[str], df: pd.DataFrame):
    """Process uploaded file asynchronously using bulk operations for optimal performance."""
    db = Database()
    
    try:
        await db.connect()
        
        async with db._pool.acquire() as conn:
            # Update status to processing with started_at timestamp
            await conn.execute(
                "UPDATE product_uploads SET status = 'processing', started_at = NOW() WHERE id = $1",
                upload_id
            )
            
            # Validate brand exists
            if not brand_id:
                raise Exception("Brand ID is required for product upload")
            
            brand_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM brands WHERE id = $1)", brand_id
            )
            if not brand_exists:
                raise Exception(f"Brand with ID {brand_id} does not exist")
            
            # Prepare bulk data for insertion
            bulk_data = []
            error_data = []
            processed_rows = 0
            
            for index, row in df.iterrows():
                try:
                    # Extract and validate basic fields
                    sku = str(row.get('sku', '')).strip()
                    description = str(row.get('description', '')).strip()
                    price_str = str(row.get('price', '0'))
                    currency = str(row.get('currency', 'USD')).strip().upper()
                    family = str(row.get('family', '')).strip()
                    status = str(row.get('status', 'active')).strip().lower()
                    
                    if not sku or not description:
                        error_data.append((
                            upload_id,
                            index + 1,
                            None,
                            f"Missing required fields (SKU: {sku}, description: {description})",
                            str(dict(row))[:500]  # Truncate to avoid huge data
                        ))
                        continue
                    
                    # Parse price
                    import re
                    try:
                        price = float(re.sub(r'[^\d.]', '', price_str))
                    except ValueError:
                        price = 0.0
                    
                    # Create search text and raw_json
                    search_text = f"{sku} {description} {family}".strip()
                    import json
                    raw_json = json.dumps(dict(row))
                    
                    # Prepare data for bulk insert (matching the database schema)
                    product_data = (
                        str(uuid.uuid4()),  # id
                        brand_id,           # brand_id
                        sku,               # sku
                        description,       # description  
                        price,             # price
                        currency,          # currency
                        family,            # family
                        status == 'active', # active
                        str(row.get('form_factor', '')).strip() if pd.notna(row.get('form_factor')) else None,
                        bool(row.get('outdoor')) if pd.notna(row.get('outdoor')) else None,
                        bool(row.get('poe')) if pd.notna(row.get('poe')) else None,
                        bool(row.get('poe_plus')) if pd.notna(row.get('poe_plus')) else None,
                        int(row.get('ir_range_m')) if pd.notna(row.get('ir_range_m')) and str(row.get('ir_range_m')).isdigit() else None,
                        float(row.get('resolution_mp')) if pd.notna(row.get('resolution_mp')) else None,
                        bool(row.get('vandal_ik10')) if pd.notna(row.get('vandal_ik10')) else None,
                        int(row.get('nvr_channels')) if pd.notna(row.get('nvr_channels')) and str(row.get('nvr_channels')).isdigit() else None,
                        int(row.get('switch_ports')) if pd.notna(row.get('switch_ports')) and str(row.get('switch_ports')).isdigit() else None,
                        bool(row.get('is_accessory', False)),
                        str(row.get('accessory_type', '')).strip() if pd.notna(row.get('accessory_type')) else None,
                        search_text,       # search_text
                        raw_json          # raw_json
                    )
                    
                    bulk_data.append(product_data)
                    processed_rows += 1
                    
                    # Process in batches of 500 for optimal performance
                    if len(bulk_data) >= 500:
                        await perform_bulk_insert(conn, bulk_data)
                        
                        # Update progress
                        await conn.execute(
                            "UPDATE product_uploads SET processed_rows = $1 WHERE id = $2",
                            processed_rows, upload_id
                        )
                        
                        bulk_data = []  # Reset for next batch
                        
                except Exception as e:
                    error_data.append((
                        upload_id,
                        index + 1,
                        None,
                        f"Processing error: {str(e)}",
                        str(dict(row))[:500]
                    ))
            
            # Insert remaining data if any
            if bulk_data:
                await perform_bulk_insert(conn, bulk_data)
            
            # Insert error records if any
            if error_data:
                await conn.executemany(
                    """INSERT INTO product_upload_errors 
                       (upload_id, line_number, column_name, error_message, raw_data) 
                       VALUES ($1, $2, $3, $4, $5)""",
                    error_data
                )
            
            # Final status update
            error_count = len(error_data)
            total_processed = processed_rows
            
            await conn.execute("""
                UPDATE product_uploads 
                SET status = $1, processed_rows = $2, error_count = $3, 
                    message = $4, processed_at = NOW() 
                WHERE id = $5
            """, 
                'completed' if error_count == 0 else 'failed',
                total_processed,
                error_count,
                f"Successfully processed {total_processed} products" + (f" with {error_count} errors" if error_count > 0 else ""),
                upload_id
            )
            
            # Clean up file after successful processing
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Successfully deleted uploaded file: {file_path}")
            except Exception as e:
                print(f"Warning: Failed to delete uploaded file {file_path}: {str(e)}")
                
    except Exception as e:
        # Update status to failed on any critical error using a fresh connection
        print(f"Upload processing failed for {upload_id}: {str(e)}")
        try:
            # Create a new database connection for error handling
            error_db = Database()
            await error_db.connect()
            async with error_db._pool.acquire() as error_conn:
                await error_conn.execute("""
                    UPDATE product_uploads 
                    SET status = 'failed', message = $1, processed_at = NOW() 
                    WHERE id = $2
                """, f"Processing failed: {str(e)}", upload_id)
            await error_db.close()
        except Exception as error_e:
            print(f"Failed to update error status for {upload_id}: {str(error_e)}")
    
    finally:
        # Ensure database connection is closed
        try:
            if db and db._pool:
                await db.close()
        except:
            pass

async def perform_bulk_insert(conn, bulk_data: list):
    """Perform bulk insert using asyncpg's executemany for optimal performance with transaction safety."""
    if not bulk_data:
        return
    
    sql = """
        INSERT INTO products (
            id, brand_id, sku, description, price, currency, family, active,
            form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp,
            vandal_ik10, nvr_channels, switch_ports, is_accessory, accessory_type,
            search_text, raw_json
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
        ON CONFLICT (sku, brand_id) DO UPDATE SET
            description = EXCLUDED.description,
            price = EXCLUDED.price,
            currency = EXCLUDED.currency,
            family = EXCLUDED.family,
            active = EXCLUDED.active,
            form_factor = EXCLUDED.form_factor,
            outdoor = EXCLUDED.outdoor,
            poe = EXCLUDED.poe,
            poe_plus = EXCLUDED.poe_plus,
            ir_range_m = EXCLUDED.ir_range_m,
            resolution_mp = EXCLUDED.resolution_mp,
            vandal_ik10 = EXCLUDED.vandal_ik10,
            nvr_channels = EXCLUDED.nvr_channels,
            switch_ports = EXCLUDED.switch_ports,
            is_accessory = EXCLUDED.is_accessory,
            accessory_type = EXCLUDED.accessory_type,
            search_text = EXCLUDED.search_text,
            raw_json = EXCLUDED.raw_json
    """
    
    # Use transaction for data integrity
    async with conn.transaction():
        await conn.executemany(sql, bulk_data)

@router.get("/uploads/{upload_id}/progress")
async def get_upload_progress(upload_id: str):
    """Get real-time progress for an upload by ID."""
    db = Database()
    
    try:
        await db.connect()
        async with db._pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT 
                    id,
                    brand_id,
                    original_name,
                    row_count,
                    status,
                    message,
                    created_at,
                    processed_at,
                    processed_rows,
                    error_count,
                    started_at
                FROM product_uploads 
                WHERE id = $1
            """, upload_id)
            
            if not result:
                raise HTTPException(status_code=404, detail="Upload not found")
            
            upload_data = dict(result)
            
            # Ensure safe integer defaults for null values
            processed_rows = upload_data['processed_rows'] or 0
            error_count = upload_data['error_count'] or 0
            total_rows = upload_data['row_count'] or 0
            
            # Calculate progress percentage safely
            progress_percent = 0
            if total_rows > 0 and processed_rows >= 0:
                progress_percent = (processed_rows / total_rows) * 100
                
            # Format response with safe defaults
            return {
                "upload_id": upload_data['id'],
                "brand_id": upload_data['brand_id'],
                "filename": upload_data['original_name'],
                "status": upload_data['status'],
                "message": upload_data['message'],
                "total_rows": total_rows,
                "processed_rows": processed_rows,
                "error_count": error_count,
                "progress_percent": round(progress_percent, 1),
                "created_at": upload_data['created_at'].isoformat() if upload_data['created_at'] else None,
                "started_at": upload_data['started_at'].isoformat() if upload_data['started_at'] else None,
                "completed_at": upload_data['processed_at'].isoformat() if upload_data['processed_at'] else None,
                "is_processing": upload_data['status'] in ['queued', 'processing'],
                "is_completed": upload_data['status'] in ['completed', 'failed']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting upload progress: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get upload progress")
    finally:
        try:
            if db._pool:
                await db.close()
        except:
            pass


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
