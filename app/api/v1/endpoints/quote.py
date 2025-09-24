"""
Quote generation endpoint using the new database schema.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from schemas import (
    QuoteRequest, QuoteResponse, QuoteListResponse, 
    QuoteFeedbackRequest, QuoteFeedbackResponse
)
from app.services.quote_service import QuoteService
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
    request: dict,
    db: Database = Depends(get_database)
):
    """Generate quote data from prompt without saving to database."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            quote_service = QuoteService(conn)
            # Only generate quote data without saving
            prompt = request.get('prompt', '')
            if not prompt:
                raise ValueError("Prompt is required")
            return await quote_service.generate_quote_data(prompt)
    
    except ValueError as e:
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
