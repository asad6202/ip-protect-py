"""
API endpoints for item-level feedback on quote items.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
import asyncpg

from schemas import QuoteItemFeedbackRequest, QuoteItemFeedbackResponse
from db import Database
from app.services.item_feedback_service import ItemFeedbackService

router = APIRouter()

# Global database instance (will be injected)
db_instance = None

def get_database() -> Database:
    """Get database instance for dependency injection."""
    global db_instance
    if db_instance is None:
        db_instance = Database()
    return db_instance


@router.post("/quote-items/{item_id}/feedback", response_model=QuoteItemFeedbackResponse)
async def create_item_feedback(
    item_id: str,
    feedback: QuoteItemFeedbackRequest,
    db: Database = Depends(get_database)
):
    """Create feedback for a specific quote item."""
    try:
        if not db._pool:
            await db.connect()
        async with db._pool.acquire() as conn:
            item_feedback_service = ItemFeedbackService(conn)
            return await item_feedback_service.create_item_feedback(item_id, feedback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create item feedback: {str(e)}")


@router.get("/quote-items/{item_id}/feedback", response_model=List[QuoteItemFeedbackResponse])
async def get_item_feedback(
    item_id: str,
    db: Database = Depends(get_database)
):
    """Get all feedback for a specific quote item."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Verify the quote item exists
            item = await conn.fetchrow(
                "SELECT id FROM quote_items WHERE id = $1", item_id
            )
            if not item:
                raise HTTPException(status_code=404, detail="Quote item not found")
            
            # Get all feedback for this item
            results = await conn.fetch("""
                SELECT id, quote_item_id, quote_id, feedback_type, rating, comment,
                       suggested_sku, suggested_quantity, suggested_price,
                       correction_data, user_context, created_at, updated_at
                FROM quote_item_feedback 
                WHERE quote_item_id = $1
                ORDER BY created_at DESC
            """, item_id)
            
            feedback_list = []
            for result in results:
                feedback_list.append(QuoteItemFeedbackResponse(
                    id=result['id'],
                    quote_item_id=result['quote_item_id'],
                    quote_id=result['quote_id'],
                    feedback_type=result['feedback_type'],
                    rating=result['rating'],
                    comment=result['comment'],
                    suggested_sku=result['suggested_sku'],
                    suggested_quantity=result['suggested_quantity'],
                    suggested_price=float(result['suggested_price']) if result['suggested_price'] else None,
                    correction_data=result['correction_data'],
                    user_context=result['user_context'],
                    created_at=result['created_at'].isoformat(),
                    updated_at=result['updated_at'].isoformat()
                ))
            
            return feedback_list
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get item feedback: {str(e)}")


@router.get("/quotes/{quote_id}/item-feedback", response_model=List[QuoteItemFeedbackResponse])
async def get_quote_item_feedback(
    quote_id: str,
    db: Database = Depends(get_database)
):
    """Get all item-level feedback for a quote."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Verify the quote exists
            quote = await conn.fetchrow(
                "SELECT id FROM quotes WHERE id = $1", quote_id
            )
            if not quote:
                raise HTTPException(status_code=404, detail="Quote not found")
            
            # Get all item feedback for this quote
            results = await conn.fetch("""
                SELECT id, quote_item_id, quote_id, feedback_type, rating, comment,
                       suggested_sku, suggested_quantity, suggested_price,
                       correction_data, user_context, created_at, updated_at
                FROM quote_item_feedback 
                WHERE quote_id = $1
                ORDER BY created_at DESC
            """, quote_id)
            
            feedback_list = []
            for result in results:
                feedback_list.append(QuoteItemFeedbackResponse(
                    id=result['id'],
                    quote_item_id=result['quote_item_id'],
                    quote_id=result['quote_id'],
                    feedback_type=result['feedback_type'],
                    rating=result['rating'],
                    comment=result['comment'],
                    suggested_sku=result['suggested_sku'],
                    suggested_quantity=result['suggested_quantity'],
                    suggested_price=float(result['suggested_price']) if result['suggested_price'] else None,
                    correction_data=result['correction_data'],
                    user_context=result['user_context'],
                    created_at=result['created_at'].isoformat(),
                    updated_at=result['updated_at'].isoformat()
                ))
            
            return feedback_list
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quote item feedback: {str(e)}")


@router.get("/item-feedback/analytics")
async def get_item_feedback_analytics(
    db: Database = Depends(get_database)
):
    """Get analytics for item-level feedback patterns."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Get feedback type distribution
            type_stats = await conn.fetch("""
                SELECT 
                    feedback_type,
                    COUNT(*) as count,
                    AVG(rating) as avg_rating
                FROM quote_item_feedback
                GROUP BY feedback_type
                ORDER BY count DESC
            """)
            
            # Get most problematic SKUs
            problematic_skus = await conn.fetch("""
                SELECT 
                    qi.sku,
                    qi.description,
                    COUNT(qif.id) as feedback_count,
                    AVG(qif.rating) as avg_rating,
                    STRING_AGG(DISTINCT qif.feedback_type, ', ') as feedback_types
                FROM quote_item_feedback qif
                JOIN quote_items qi ON qif.quote_item_id = qi.id
                WHERE qif.feedback_type != 'correct'
                GROUP BY qi.sku, qi.description
                ORDER BY feedback_count DESC
                LIMIT 10
            """)
            
            # Get common correction patterns
            correction_patterns = await conn.fetch("""
                SELECT 
                    correction_data->>'field' as field,
                    correction_data->>'reason' as reason,
                    COUNT(*) as count
                FROM quote_item_feedback
                WHERE correction_data IS NOT NULL
                GROUP BY correction_data->>'field', correction_data->>'reason'
                ORDER BY count DESC
                LIMIT 10
            """)
            
            # Get recent feedback trends
            recent_trends = await conn.fetch("""
                SELECT 
                    DATE(created_at) as date,
                    feedback_type,
                    COUNT(*) as count
                FROM quote_item_feedback
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at), feedback_type
                ORDER BY date DESC, count DESC
            """)
            
            return {
                "feedback_type_distribution": [
                    {
                        "feedback_type": row['feedback_type'],
                        "count": row['count'],
                        "avg_rating": float(row['avg_rating']) if row['avg_rating'] else None
                    }
                    for row in type_stats
                ],
                "problematic_skus": [
                    {
                        "sku": row['sku'],
                        "description": row['description'],
                        "feedback_count": row['feedback_count'],
                        "avg_rating": float(row['avg_rating']) if row['avg_rating'] else None,
                        "feedback_types": row['feedback_types'].split(', ')
                    }
                    for row in problematic_skus
                ],
                "correction_patterns": [
                    {
                        "field": row['field'],
                        "reason": row['reason'],
                        "count": row['count']
                    }
                    for row in correction_patterns
                ],
                "recent_trends": [
                    {
                        "date": row['date'].isoformat(),
                        "feedback_type": row['feedback_type'],
                        "count": row['count']
                    }
                    for row in recent_trends
                ]
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get item feedback analytics: {str(e)}")