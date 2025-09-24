"""
Service for managing item-level feedback on quote items.
"""
import asyncpg
from typing import List, Dict, Any
from datetime import datetime
import json
from uuid import uuid4
from schemas import QuoteItemFeedbackRequest, QuoteItemFeedbackResponse


class ItemFeedbackService:
    """Service for managing item-level feedback."""
    
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
    
    async def create_item_feedback(self, item_id: str, feedback: QuoteItemFeedbackRequest) -> QuoteItemFeedbackResponse:
        """Create feedback for a specific quote item."""
        # First, verify the quote item exists and get the quote_id
        item = await self.conn.fetchrow(
            "SELECT id, quote_id FROM quote_items WHERE id = $1", item_id
        )
        
        if not item:
            raise ValueError(f"Quote item with ID {item_id} not found")
        
        # Create the feedback record
        feedback_id = str(uuid4())
        quote_id = item['quote_id']
        
        await self.conn.execute('''
            INSERT INTO quote_item_feedback (
                id, quote_item_id, quote_id, feedback_type, rating, comment,
                suggested_sku, suggested_quantity, suggested_price,
                correction_data, user_context, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ''', 
            feedback_id, item_id, quote_id, feedback.feedback_type,
            getattr(feedback, 'rating', None), feedback.comment, feedback.suggested_sku, 
            feedback.suggested_quantity, feedback.suggested_price, 
            json.dumps(feedback.correction_data) if feedback.correction_data else None,
            json.dumps(feedback.user_context) if feedback.user_context else None,
            datetime.now(), datetime.now()
        )
        
        # Return the created feedback
        return QuoteItemFeedbackResponse(
            id=feedback_id,
            quote_item_id=item_id,
            quote_id=quote_id,
            feedback_type=feedback.feedback_type,
            rating=getattr(feedback, 'rating', None),
            comment=feedback.comment,
            suggested_sku=feedback.suggested_sku,
            suggested_quantity=feedback.suggested_quantity,
            suggested_price=feedback.suggested_price,
            correction_data=feedback.correction_data,
            user_context=feedback.user_context,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
    
    async def get_item_feedback(self, item_id: str) -> List[QuoteItemFeedbackResponse]:
        """Get all feedback for a specific quote item."""
        # Verify the quote item exists
        item = await self.conn.fetchrow(
            "SELECT id FROM quote_items WHERE id = $1", item_id
        )
        
        if not item:
            raise ValueError(f"Quote item with ID {item_id} not found")
        
        # Get all feedback for this item
        rows = await self.conn.fetch('''
            SELECT id, quote_item_id, quote_id, feedback_type, rating, comment,
                   suggested_sku, suggested_quantity, suggested_price,
                   correction_data, user_context, created_at, updated_at
            FROM quote_item_feedback
            WHERE quote_item_id = $1
            ORDER BY created_at DESC
        ''', item_id)
        
        feedback_list = []
        for row in rows:
            feedback_list.append(QuoteItemFeedbackResponse(
                id=row['id'],
                quote_item_id=row['quote_item_id'],
                quote_id=row['quote_id'],
                feedback_type=row['feedback_type'],
                rating=row['rating'],
                comment=row['comment'],
                suggested_sku=row['suggested_sku'],
                suggested_quantity=row['suggested_quantity'],
                suggested_price=float(row['suggested_price']) if row['suggested_price'] else None,
                correction_data=json.loads(row['correction_data']) if row['correction_data'] else None,
                user_context=json.loads(row['user_context']) if row['user_context'] else None,
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat()
            ))
        
        return feedback_list
    
    async def get_feedback_for_quote(self, quote_id: str) -> List[QuoteItemFeedbackResponse]:
        """Get all item feedback for a specific quote."""
        # Verify the quote exists
        quote = await self.conn.fetchrow(
            "SELECT id FROM quotes WHERE id = $1", quote_id
        )
        
        if not quote:
            raise ValueError(f"Quote with ID {quote_id} not found")
        
        # Get all feedback for this quote
        rows = await self.conn.fetch('''
            SELECT id, quote_item_id, quote_id, feedback_type, rating, comment,
                   suggested_sku, suggested_quantity, suggested_price,
                   correction_data, user_context, created_at, updated_at
            FROM quote_item_feedback
            WHERE quote_id = $1
            ORDER BY created_at DESC
        ''', quote_id)
        
        feedback_list = []
        for row in rows:
            feedback_list.append(QuoteItemFeedbackResponse(
                id=row['id'],
                quote_item_id=row['quote_item_id'],
                quote_id=row['quote_id'],
                feedback_type=row['feedback_type'],
                rating=row['rating'],
                comment=row['comment'],
                suggested_sku=row['suggested_sku'],
                suggested_quantity=row['suggested_quantity'],
                suggested_price=float(row['suggested_price']) if row['suggested_price'] else None,
                correction_data=json.loads(row['correction_data']) if row['correction_data'] else None,
                user_context=json.loads(row['user_context']) if row['user_context'] else None,
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat()
            ))
        
        return feedback_list
    
    async def get_item_feedback_analytics(self) -> Dict[str, Any]:
        """Get analytics for item-level feedback."""
        # Total feedback count
        total_feedback = await self.conn.fetchval("SELECT COUNT(*) FROM quote_item_feedback")
        
        # Feedback type distribution
        feedback_types = await self.conn.fetch('''
            SELECT feedback_type, COUNT(*) as count
            FROM quote_item_feedback
            GROUP BY feedback_type
            ORDER BY count DESC
        ''')
        
        # Most commented items
        most_commented = await self.conn.fetch('''
            SELECT qi.sku, qi.description, COUNT(qif.id) as feedback_count
            FROM quote_item_feedback qif
            JOIN quote_items qi ON qif.quote_item_id = qi.id
            WHERE qif.comment IS NOT NULL AND qif.comment != ''
            GROUP BY qi.sku, qi.description
            ORDER BY feedback_count DESC
            LIMIT 10
        ''')
        
        # Most suggested SKUs
        most_suggested_skus = await self.conn.fetch('''
            SELECT suggested_sku, COUNT(*) as count
            FROM quote_item_feedback
            WHERE suggested_sku IS NOT NULL AND suggested_sku != ''
            GROUP BY suggested_sku
            ORDER BY count DESC
            LIMIT 10
        ''')
        
        return {
            "total_item_feedback": total_feedback,
            "feedback_type_distribution": [dict(row) for row in feedback_types],
            "most_commented_items": [dict(row) for row in most_commented],
            "most_suggested_skus": [dict(row) for row in most_suggested_skus]
        }
