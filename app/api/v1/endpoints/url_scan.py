"""
API endpoints for URL scanning and product ingestion.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, List, Optional

from db import Database
from app.services.url_scanner_service import URLScannerService
from app.services.product_ingestion_service import ProductIngestionService

router = APIRouter(prefix="/url-scan", tags=["url-scan"])

# Global database instance
db_instance = None


def get_database() -> Database:
    """Get database instance."""
    global db_instance
    if db_instance is None:
        db_instance = Database()
    return db_instance


class URLScanRequest(BaseModel):
    """Request to scan a supplier URL."""
    url: HttpUrl
    brand_name: Optional[str] = None
    auto_ingest: bool = False


class URLScanResponse(BaseModel):
    """Response from URL scanning."""
    success: bool
    url: str
    products: List[Dict[str, Any]]
    count: int
    ingested_count: Optional[int] = None
    error: Optional[str] = None


@router.post("/scan", response_model=URLScanResponse)
async def scan_supplier_url(
    request: URLScanRequest,
    db: Database = Depends(get_database)
):
    """
    Scan a supplier URL and extract product information.
    
    Args:
        request: URL scan request with optional brand and auto-ingest flag
        conn: Database connection
    
    Returns:
        URLScanResponse with extracted products
    """
    try:
        if not db._pool:
            await db.connect()
        
        async with db._pool.acquire() as conn:
            # Initialize services
            scanner = URLScannerService(conn)
            
            # Scan the URL
            scan_result = await scanner.scan_url(str(request.url))
            
            if not scan_result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to scan URL: {scan_result.get('error', 'Unknown error')}"
                )
            
            products = scan_result["products"]
            ingested_count = None
            ingestion_error = None
            
            # Auto-ingest products if requested
            if request.auto_ingest and products:
                ingestion_service = ProductIngestionService(conn)
                ingestion_result = await ingestion_service.ingest_products(
                    products=products,
                    brand_name=request.brand_name,
                    source_url=str(request.url)
                )
                
                # Check if ingestion failed
                if not ingestion_result.get("success", True):
                    ingestion_error = ingestion_result.get("error", "Failed to ingest products")
                    # Include individual errors if available
                    if ingestion_result.get("errors"):
                        error_details = "; ".join([
                            f"{err.get('product', 'Unknown')}: {err.get('error', 'Unknown error')}"
                            for err in ingestion_result["errors"][:3]  # Limit to first 3 errors
                        ])
                        ingestion_error = f"{ingestion_error}. Details: {error_details}"
                    
                    # If complete failure, raise HTTP exception
                    if ingestion_result.get("ingested_count", 0) == 0:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to ingest products: {ingestion_error}"
                        )
                
                ingested_count = ingestion_result.get("ingested_count")
            
            return URLScanResponse(
                success=True,
                url=str(request.url),
                products=products,
                count=len(products),
                ingested_count=ingested_count,
                error=ingestion_error  # Include partial failure errors
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error scanning URL: {str(e)}"
        )
