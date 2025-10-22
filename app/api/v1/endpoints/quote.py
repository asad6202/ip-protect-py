"""
Quote generation endpoint using the new database schema.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Form, File, UploadFile, Body
from pydantic import BaseModel
from schemas import (
    QuoteRequest, QuoteResponse, QuoteListResponse, 
    QuoteFeedbackRequest, QuoteFeedbackResponse
)
from app.services.quote_service import QuoteService
from app.services.url_scanner_service import URLScannerService
from db import Database

router = APIRouter()

# Global database instance (will be injected)
db_instance = None


def get_database() -> Database:
    """Get database instance."""
    global db_instance
    if db_instance is None:
        db_instance = Database()
    return db_instance


@router.post("/quote/generate")
async def generate_quote(
    request: Optional[Dict] = Body(default=None),
    prompt: Optional[str] = Form(default=None),
    attachments: List[UploadFile] = File(default=[]),
    db: Database = Depends(get_database)
):
    """Generate quote data from prompt and/or attachments without saving to database.
    Accepts both JSON (for prompt-only) and multipart/form-data (for attachments)."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            
            # Handle both JSON and FormData inputs
            if request:
                # JSON request (prompt-only, backward compatibility)
                prompt_text = request.get('prompt', '')
                if not prompt_text:
                    raise ValueError("Prompt is required (Empty)")
                return await quote_service.generate_quote_data(prompt_text)
            else:
                # FormData request (with potential attachments)
                if not prompt:
                    raise ValueError("Prompt is required (Missing)")
                
                # Check if attachments are provided
                if attachments and len(attachments) > 0:
                    # Use attachment-based generation (skip database lookup)
                    return await quote_service.generate_quote_from_attachments(prompt, attachments)
                else:
                    # Use traditional database product lookup
                    return await quote_service.generate_quote_data(prompt)
    
    except ValueError as e:
        print(request)
        print(prompt)
        print(attachments)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote generation failed: {str(e)}")


@router.post("/quote", response_model=QuoteResponse)
async def create_quote(
    request: QuoteRequest,
    db: Database = Depends(get_database)
) -> QuoteResponse:
    """Create a new quote and save it to the database."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            return await quote_service.create_quote(request)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote creation failed: {str(e)}")


@router.get("/quote/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: str,
    db: Database = Depends(get_database)
) -> QuoteResponse:
    """Get a quote by ID."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            return await quote_service.get_quote(quote_id)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quote: {str(e)}")


@router.get("/quotes")
async def list_quotes(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_database)
):
    """List quotes with pagination."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            quotes = await quote_service.list_quotes(limit, offset)
            
            # Get total count
            total = await conn.fetchval('SELECT COUNT(*) FROM quotes')
            
            # Calculate pagination info
            page = (offset // limit) + 1
            pages = (total + limit - 1) // limit  # Ceiling division
            
            return {
                "items": quotes,
                "total": total,
                "page": page,
                "page_size": limit,
                "pages": pages
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list quotes: {str(e)}")


@router.patch("/quote/{quote_id}/status", response_model=QuoteResponse)
async def update_quote_status(
    quote_id: str,
    status: str,
    db: Database = Depends(get_database)
) -> QuoteResponse:
    """Update quote status."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            return await quote_service.update_quote_status(quote_id, status)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update quote status: {str(e)}")


@router.patch("/quote/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: str,
    updates: dict,
    db: Database = Depends(get_database)
) -> QuoteResponse:
    """Update quote with provided fields."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            return await quote_service.update_quote(quote_id, updates)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update quote: {str(e)}")


@router.delete("/quote/{quote_id}")
async def delete_quote(
    quote_id: str,
    db: Database = Depends(get_database)
):
    """Delete a quote and all its related data."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            await quote_service.delete_quote(quote_id)
            return {"message": "Quote deleted successfully"}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete quote: {str(e)}")


@router.post("/quote/{target_quote_id}/merge/{source_quote_id}", response_model=QuoteResponse)
async def merge_quotes(
    target_quote_id: str,
    source_quote_id: str,
    db: Database = Depends(get_database)
) -> QuoteResponse:
    """
    Merge items from source quote into target quote.
    All items from the source quote are copied to the target quote.
    """
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            return await quote_service.merge_quotes(target_quote_id, source_quote_id)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to merge quotes: {str(e)}")


@router.get("/quote/{quote_id}/feedback", response_model=List[QuoteFeedbackResponse])
async def get_quote_feedback(
    quote_id: str,
    db: Database = Depends(get_database)
) -> List[QuoteFeedbackResponse]:
    """Get feedback for a quote."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            return await quote_service.get_feedback(quote_id)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feedback: {str(e)}")


@router.post("/quote/{quote_id}/feedback", response_model=QuoteFeedbackResponse)
async def add_quote_feedback(
    quote_id: str,
    feedback: QuoteFeedbackRequest,
    db: Database = Depends(get_database)
) -> QuoteFeedbackResponse:
    """Add feedback to a quote."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            return await quote_service.add_feedback(quote_id, feedback)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add feedback: {str(e)}")


@router.get("/quote/feedback/analytics")
async def get_feedback_analytics(
    db: Database = Depends(get_database)
) -> dict:
    """Get feedback analytics for GPT improvement."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            return await quote_service.get_feedback_analytics()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feedback analytics: {str(e)}")


@router.get("/quote/health")
async def quote_health_check():
    """Health check endpoint for quote service."""
    return {"status": "healthy", "service": "quote_generation"}


class URLScanRequest(BaseModel):
    """Request model for URL scanning."""
    url: str
    quote_id: str


@router.post("/quote/scan-url")
async def scan_url(
    request: URLScanRequest,
    db: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Scan a URL to extract product information and merge with existing quote.
    
    Args:
        request: URLScanRequest with url and quote_id
    
    Returns:
        Dict with scan results and updated quote information
    """
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            scanner_service = URLScannerService(conn)
            
            scan_result = await scanner_service.scan_url(request.url)
            
            if not scan_result.get("success"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to scan URL: {scan_result.get('error', 'Unknown error')}"
                )
            
            if not scan_result.get("products"):
                return {
                    "success": True,
                    "url": request.url,
                    "message": "No products found on this page",
                    "products": [],
                    "added_items": 0
                }
            
            merge_result = await scanner_service.merge_products_into_quote(
                request.quote_id,
                scan_result["products"]
            )
            
            return {
                "success": True,
                "url": request.url,
                "message": f"Successfully added {merge_result['added_items']} items from URL",
                "products": scan_result["products"],
                "added_items": merge_result["added_items"],
                "total_items": merge_result["total_items"]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"URL scanning failed: {str(e)}"
        )
