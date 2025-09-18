"""
Quote service for managing quotes in the new database schema.
"""
import asyncio
import asyncpg
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from app.ai.intent_extractor import extract_intent
from app.services.retrieval import ProductRetrieval
from schemas import QuoteRequest, QuoteResponse, QuoteItemRequest, QuoteItemResponse, QuoteFeedbackRequest, QuoteFeedbackResponse


class QuoteService:
    """Service for managing quotes with the new database schema."""
    
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.retrieval = ProductRetrieval(conn)
    
    async def generate_quote_data(self, prompt: str):
        """Generate quote data from prompt without saving to database."""
        try:
            # Extract intent from the prompt
            intent = extract_intent(prompt)
            if not intent or 'items' not in intent:
                raise ValueError("Could not extract product requirements from prompt")
            
            currency = None
            total_amount = 0.0
            notes_parts = []
            quote_items = []
            selected_skus = set()
            
            for i, item_want in enumerate(intent['items']):
                quantity = max(1, int(item_want.get('quantity', 1)))
                
                # Skip switch/NVR items if we have global preferences (to avoid duplicates)
                family = item_want.get('family') or ''
                if (family.lower() == 'switch' and 
                    'global' in intent and 'switchPorts' in intent['global']):
                    continue
                if (family.lower() == 'nvr' and 
                    'global' in intent and 'nvrChannels' in intent['global']):
                    continue
                
                # Search for products
                candidates = await self.retrieval.search_products(item_want, prompt)
                
                if candidates:
                    # Product found - use it
                    best = candidates[0]
                    selected_skus.add(best['sku'])
                    
                    # Calculate pricing
                    unit_price = float(best.get('price', 0))
                    subtotal = unit_price * quantity
                    
                    quote_items.append({
                        'sku': best['sku'],
                        'description': best['description'],
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'currency': best.get('currency', 'USD'),
                        'subtotal': subtotal,
                        'product_id': None,
                        'metadata': {},
                        'position': i
                    })
                    
                    # Track totals
                    if not currency:
                        currency = best.get('currency', 'USD')
                    total_amount += subtotal
                    
                else:
                    # Product not found - create fallback
                    quote_items.append({
                        'sku': item_want.get('sku', f'ITEM-{i+1}'),
                        'description': f"Product not found: {item_want.get('sku', 'Unknown item')}",
                        'quantity': quantity,
                        'unit_price': 0.0,
                        'currency': currency or 'USD',
                        'subtotal': 0.0,
                        'product_id': None,
                        'metadata': {},
                        'position': i
                    })
                    
                    notes_parts.append(f"• Item not found: {item_want.get('sku', 'Unknown item')}")
            
            # Set default currency if none found
            if not currency:
                currency = 'USD'
                
            # Create notes
            notes = "\n".join(notes_parts) if notes_parts else None
            
            return {
                'items': quote_items,
                'currency': currency,
                'total': total_amount,
                'notes': notes
            }
            
        except Exception as e:
            print(f"Error generating quote data: {str(e)}")
            raise ValueError(f"Failed to generate quote: {str(e)}")

    async def create_quote(self, request: QuoteRequest) -> QuoteResponse:
        """Create a new quote and save it to the database."""
        # Use provided items or extract from prompt
        if request.items:
            # Use provided items (from frontend)
            return await self._create_quote_with_items(request)
        else:
            # Extract intent from the prompt (fallback)
            return await self._create_quote_from_prompt(request)
    
    async def _create_quote_with_items(self, request: QuoteRequest) -> QuoteResponse:
        """Create a quote using provided items from frontend."""
        # Create quote record
        quote_id = str(uuid4())
        currency = request.currency or 'USD'
        total_amount = 0.0
        
        # Insert quote
        await self.conn.execute('''
            INSERT INTO quotes (id, title, prompt, extracted_intent, currency, total_amount, notes, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''', quote_id, request.title, request.prompt, json.dumps(request.extracted_intent or {}), 
            currency, total_amount, request.notes, 'draft')
        
        # Process each provided item
        quote_items = []
        for i, item in enumerate(request.items):
            # Insert quote item
            item_id = str(uuid4())
            await self.conn.execute('''
                INSERT INTO quote_items (
                    id, quote_id, product_id, sku, description, quantity, 
                    unit_price, currency, subtotal, metadata, position
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ''', item_id, quote_id, item.product_id, item.sku, item.description,
                item.quantity, item.unit_price, item.currency, item.subtotal,
                json.dumps(item.metadata or {}), i)
            
            quote_items.append(QuoteItemResponse(
                id=item_id,
                sku=item.sku,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                currency=item.currency,
                subtotal=item.subtotal,
                product_id=item.product_id,
                metadata=item.metadata,
                position=i,
                created_at=datetime.now().isoformat()
            ))
            
            total_amount += item.subtotal
        
        # Update total amount
        await self.conn.execute('''
            UPDATE quotes SET total_amount = $1 WHERE id = $2
        ''', total_amount, quote_id)
        
        # Get the created quote
        quote = await self.conn.fetchrow('''
            SELECT id, title, prompt, extracted_intent, currency, total_amount, 
                   notes, status, created_at, updated_at
            FROM quotes WHERE id = $1
        ''', quote_id)
        
        return QuoteResponse(
            id=quote['id'],
            title=quote['title'],
            prompt=quote['prompt'],
            extracted_intent=json.loads(quote['extracted_intent']) if quote['extracted_intent'] else None,
            currency=quote['currency'],
            total_amount=float(quote['total_amount']) if quote['total_amount'] else None,
            notes=quote['notes'],
            status=quote['status'],
            created_at=quote['created_at'].isoformat(),
            updated_at=quote['updated_at'].isoformat(),
            items=quote_items
        )
    
    async def _create_quote_from_prompt(self, request: QuoteRequest) -> QuoteResponse:
        """Create a quote by extracting intent from prompt (original logic)."""
        try:
            # Extract intent from the prompt
            intent = extract_intent(request.prompt)
            if not intent or 'items' not in intent:
                raise ValueError("Could not extract product requirements from prompt")
            
            # Create quote record
            quote_id = str(uuid4())
            currency = request.currency or 'USD'
            total_amount = 0.0
            notes_parts = []
            
            # Insert quote
            await self.conn.execute('''
                INSERT INTO quotes (id, title, prompt, extracted_intent, currency, total_amount, notes, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', quote_id, request.title, request.prompt, json.dumps(intent), 
                currency, total_amount, request.notes, 'draft')
            
            # Process each item
            quote_items = []
            selected_skus = set()
            
            for i, item_want in enumerate(intent['items']):
                quantity = max(1, int(item_want.get('quantity', 1)))
                
                # Skip switch/NVR items if we have global preferences (to avoid duplicates)
                family = item_want.get('family') or ''
                if (family.lower() == 'switch' and 
                    'global' in intent and 'switchPorts' in intent['global']):
                    continue
                if (family.lower() == 'nvr' and 
                    'global' in intent and 'nvrChannels' in intent['global']):
                    continue
                
                # Search for products
                candidates = await self.retrieval.search_products(item_want, request.prompt)
                
                if candidates:
                    # Product found - use it
                    best = candidates[0]
                    selected_skus.add(best['sku'])
                    
                    # Calculate pricing
                    unit_price = float(best.get('price', 0))
                    subtotal = unit_price * quantity
                    
                    # Get product_id if available
                    product_id = await self.conn.fetchval(
                        'SELECT id FROM products WHERE sku = $1', best['sku']
                    )
                    
                    # Create metadata
                    metadata = {
                        'is_fallback': best.get('_used_vector_fallback', False),
                        'original_request': item_want.get('sku', ''),
                        'search_method': 'vector_fallback' if best.get('_used_vector_fallback') else 'deterministic'
                    }
                    
                    # Insert quote item
                    item_id = str(uuid4())
                    await self.conn.execute('''
                        INSERT INTO quote_items (
                            id, quote_id, product_id, sku, description, quantity, 
                            unit_price, currency, subtotal, metadata, position
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ''', item_id, quote_id, product_id, best['sku'], best['description'],
                        quantity, unit_price, best.get('currency', 'USD'), subtotal,
                        json.dumps(metadata), i)
                    
                    quote_items.append(QuoteItemResponse(
                        id=item_id,
                        sku=best['sku'],
                        description=best['description'],
                        quantity=quantity,
                        unit_price=unit_price,
                        currency=best.get('currency', 'USD'),
                        subtotal=subtotal,
                        product_id=product_id,
                        metadata=metadata,
                        position=i,
                        created_at=datetime.now().isoformat()
                    ))
                    
                    total_amount += subtotal
                    notes_parts.append(f"{quantity}x {best['sku']} - {best['description']}")
                
                else:
                    # No product found - create fallback item
                    fallback_sku = f"FALLBACK-{i+1}"
                    fallback_description = f"Product not found for: {item_want.get('description', 'Unknown')}"
                    unit_price = 0.0
                    subtotal = 0.0
                    
                    # Insert fallback quote item
                    item_id = str(uuid4())
                    await self.conn.execute('''
                        INSERT INTO quote_items (
                            id, quote_id, product_id, sku, description, quantity, 
                            unit_price, currency, subtotal, metadata, position
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ''', item_id, quote_id, None, fallback_sku, fallback_description,
                        quantity, unit_price, currency or 'USD', subtotal,
                        json.dumps({'is_fallback': True, 'original_request': item_want}), i)
                    
                    quote_items.append(QuoteItemResponse(
                        id=item_id,
                        sku=fallback_sku,
                        description=fallback_description,
                        quantity=quantity,
                        unit_price=unit_price,
                        currency=currency or 'USD',
                        subtotal=subtotal,
                        product_id=None,
                        metadata={'is_fallback': True, 'original_request': item_want},
                        position=i,
                        created_at=datetime.now().isoformat()
                    ))
                    
                    notes_parts.append(f"{quantity}x {fallback_sku} - {fallback_description}")
            
            # Update total amount
            await self.conn.execute('''
                UPDATE quotes SET total_amount = $1 WHERE id = $2
            ''', total_amount, quote_id)
            
            # Get the created quote
            quote = await self.conn.fetchrow('''
                SELECT id, title, prompt, extracted_intent, currency, total_amount, 
                       notes, status, created_at, updated_at
                FROM quotes WHERE id = $1
            ''', quote_id)
            
            # Add notes about the quote generation
            if notes_parts:
                notes_text = f"Generated from prompt: {request.prompt}\n\nItems:\n" + "\n".join(notes_parts)
                await self.conn.execute('''
                    UPDATE quotes SET notes = $1 WHERE id = $2
                ''', notes_text, quote_id)
                quote = await self.conn.fetchrow('''
                    SELECT id, title, prompt, extracted_intent, currency, total_amount, 
                           notes, status, created_at, updated_at
                    FROM quotes WHERE id = $1
                ''', quote_id)
            
            return QuoteResponse(
                id=quote['id'],
                title=quote['title'],
                prompt=quote['prompt'],
                extracted_intent=json.loads(quote['extracted_intent']) if quote['extracted_intent'] else None,
                currency=quote['currency'],
                total_amount=float(quote['total_amount']) if quote['total_amount'] else None,
                notes=quote['notes'],
                status=quote['status'],
                created_at=quote['created_at'].isoformat(),
                updated_at=quote['updated_at'].isoformat(),
                items=quote_items
            )
            
        except Exception as e:
            # If there's an error, clean up the quote
            if 'quote_id' in locals():
                await self.conn.execute('DELETE FROM quotes WHERE id = $1', quote_id)
            raise e
    
    async def get_quote(self, quote_id: str) -> QuoteResponse:
        """Get a quote by ID."""
        # Get quote
        quote = await self.conn.fetchrow('''
            SELECT id, title, prompt, extracted_intent, currency, total_amount, 
                   notes, status, created_at, updated_at
            FROM quotes WHERE id = $1
        ''', quote_id)
        
        if not quote:
            raise ValueError(f"Quote {quote_id} not found")
        
        # Get quote items
        items = await self.conn.fetch('''
            SELECT id, sku, description, quantity, unit_price, currency, subtotal,
                   product_id, metadata, position, created_at
            FROM quote_items 
            WHERE quote_id = $1 
            ORDER BY position ASC, created_at ASC
        ''', quote_id)
        
        quote_items = []
        for item in items:
            quote_items.append(QuoteItemResponse(
                id=item['id'],
                sku=item['sku'],
                description=item['description'],
                quantity=item['quantity'],
                unit_price=float(item['unit_price']),
                currency=item['currency'],
                subtotal=float(item['subtotal']),
                product_id=item['product_id'],
                metadata=json.loads(item['metadata']) if item['metadata'] else None,
                position=item['position'],
                created_at=item['created_at'].isoformat()
            ))
        
        return QuoteResponse(
            id=quote['id'],
            title=quote['title'],
            prompt=quote['prompt'],
            extracted_intent=json.loads(quote['extracted_intent']) if quote['extracted_intent'] else None,
            currency=quote['currency'],
            total_amount=float(quote['total_amount']) if quote['total_amount'] else None,
            notes=quote['notes'],
            status=quote['status'],
            created_at=quote['created_at'].isoformat(),
            updated_at=quote['updated_at'].isoformat(),
            items=quote_items
        )
    
    async def list_quotes(self, limit: int = 50, offset: int = 0) -> List[QuoteResponse]:
        """List quotes with pagination."""
        quotes = await self.conn.fetch('''
            SELECT id, title, prompt, extracted_intent, currency, total_amount, 
                   notes, status, created_at, updated_at
            FROM quotes 
            ORDER BY created_at DESC 
            LIMIT $1 OFFSET $2
        ''', limit, offset)
        
        result = []
        for quote in quotes:
            # Get quote items
            items = await self.conn.fetch('''
                SELECT id, sku, description, quantity, unit_price, currency, subtotal,
                       product_id, metadata, position, created_at
                FROM quote_items 
                WHERE quote_id = $1 
                ORDER BY position ASC, created_at ASC
            ''', quote['id'])
            
            quote_items = []
            for item in items:
                quote_items.append(QuoteItemResponse(
                    id=item['id'],
                    sku=item['sku'],
                    description=item['description'],
                    quantity=item['quantity'],
                    unit_price=float(item['unit_price']),
                    currency=item['currency'],
                    subtotal=float(item['subtotal']),
                    product_id=item['product_id'],
                    metadata=json.loads(item['metadata']) if item['metadata'] else None,
                    position=item['position'],
                    created_at=item['created_at'].isoformat()
                ))
            
            result.append(QuoteResponse(
                id=quote['id'],
                title=quote['title'],
                prompt=quote['prompt'],
                extracted_intent=json.loads(quote['extracted_intent']) if quote['extracted_intent'] else None,
                currency=quote['currency'],
                total_amount=float(quote['total_amount']) if quote['total_amount'] else None,
                notes=quote['notes'],
                status=quote['status'],
                created_at=quote['created_at'].isoformat(),
                updated_at=quote['updated_at'].isoformat(),
                items=quote_items
            ))
        
        return result
    
    async def get_feedback_analytics(self) -> dict:
        """Get feedback analytics for GPT improvement."""
        # Get overall feedback statistics
        stats = await self.conn.fetchrow("""
            SELECT 
                COUNT(*) as total_feedback,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback
            FROM quote_feedback
        """)
        
        # Get accuracy distribution
        accuracy_stats = await self.conn.fetchrow("""
            SELECT 
                COUNT(CASE WHEN labels->>'accuracy' = 'excellent' THEN 1 END) as excellent,
                COUNT(CASE WHEN labels->>'accuracy' = 'good' THEN 1 END) as good,
                COUNT(CASE WHEN labels->>'accuracy' = 'fair' THEN 1 END) as fair,
                COUNT(CASE WHEN labels->>'accuracy' = 'poor' THEN 1 END) as poor
            FROM quote_feedback
            WHERE labels->>'accuracy' IS NOT NULL
        """)
        
        # Get common issues
        common_issues = await self.conn.fetch("""
            SELECT 
                'missing_products' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'missing_products' IS NOT NULL AND labels->>'missing_products' != ''
            UNION ALL
            SELECT 
                'incorrect_products' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'incorrect_products' IS NOT NULL AND labels->>'incorrect_products' != ''
            UNION ALL
            SELECT 
                'pricing_issues' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'pricing_issues' IS NOT NULL AND labels->>'pricing_issues' != ''
            UNION ALL
            SELECT 
                'quantity_issues' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'quantity_issues' IS NOT NULL AND labels->>'quantity_issues' != ''
            UNION ALL
            SELECT 
                'technical_specs' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'technical_specs' IS NOT NULL AND labels->>'technical_specs' != ''
            ORDER BY count DESC
        """)
        
        # Get recent feedback for GPT context
        recent_feedback = await self.conn.fetch("""
            SELECT 
                rating,
                comment,
                labels,
                corrections,
                created_at
            FROM quote_feedback
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        return {
            "overall_stats": {
                "total_feedback": stats['total_feedback'] or 0,
                "average_rating": float(stats['avg_rating']) if stats['avg_rating'] else 0,
                "positive_feedback": stats['positive_feedback'] or 0,
                "negative_feedback": stats['negative_feedback'] or 0,
            },
            "accuracy_distribution": {
                "excellent": accuracy_stats['excellent'] or 0,
                "good": accuracy_stats['good'] or 0,
                "fair": accuracy_stats['fair'] or 0,
                "poor": accuracy_stats['poor'] or 0,
            },
            "common_issues": [
                {"issue_type": row['issue_type'], "count": row['count']}
                for row in common_issues
            ],
            "recent_feedback": [
                {
                    "rating": row['rating'],
                    "comment": row['comment'],
                    "labels": json.loads(row['labels']) if row['labels'] else None,
                    "corrections": json.loads(row['corrections']) if row['corrections'] else None,
                    "created_at": row['created_at'].isoformat()
                }
                for row in recent_feedback
            ]
        }
    
    async def update_quote(self, quote_id: str, updates: Dict[str, Any]) -> QuoteResponse:
        """Update quote with provided fields."""
        # Check if quote exists
        quote_exists = await self.conn.fetchval('SELECT id FROM quotes WHERE id = $1', quote_id)
        if not quote_exists:
            raise ValueError(f"Quote with id {quote_id} not found")
        
        # Build dynamic update query
        update_fields = []
        update_values = []
        param_count = 1
        
        if 'title' in updates:
            update_fields.append(f"title = ${param_count}")
            update_values.append(updates['title'])
            param_count += 1
        
        if 'notes' in updates:
            update_fields.append(f"notes = ${param_count}")
            update_values.append(updates['notes'])
            param_count += 1
        
        if 'status' in updates:
            valid_statuses = ['draft', 'sent', 'accepted', 'rejected', 'expired']
            if updates['status'] not in valid_statuses:
                raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
            update_fields.append(f"status = ${param_count}")
            update_values.append(updates['status'])
            param_count += 1
        
        if not update_fields:
            raise ValueError("No valid fields to update")
        
        # Add updated_at
        update_fields.append(f"updated_at = now()")
        
        # Add quote_id as last parameter
        update_values.append(quote_id)
        
        query = f'''
            UPDATE quotes 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
        '''
        
        await self.conn.execute(query, *update_values)
        
        return await self.get_quote(quote_id)
    
    async def delete_quote(self, quote_id: str) -> bool:
        """Delete a quote and all its related data."""
        # Check if quote exists
        quote_exists = await self.conn.fetchval('SELECT id FROM quotes WHERE id = $1', quote_id)
        if not quote_exists:
            raise ValueError(f"Quote with id {quote_id} not found")
        
        # Delete in order: quote_items, feedback, then quotes
        # This ensures foreign key constraints are respected
        await self.conn.execute('DELETE FROM quote_items WHERE quote_id = $1', quote_id)
        await self.conn.execute('DELETE FROM quote_feedback WHERE quote_id = $1', quote_id)
        await self.conn.execute('DELETE FROM quotes WHERE id = $1', quote_id)
        
        return True
    
    async def create_feedback(self, quote_id: str, feedback: QuoteFeedbackRequest) -> QuoteFeedbackResponse:
        """Create feedback for a quote."""
        # Check if quote exists
        quote_exists = await self.conn.fetchval('SELECT id FROM quotes WHERE id = $1', quote_id)
        if not quote_exists:
            raise ValueError(f"Quote with id {quote_id} not found")
        
        # Create feedback
        feedback_id = str(uuid4())
        await self.conn.execute('''
            INSERT INTO quote_feedback (id, quote_id, rating, comment, labels, corrections, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, now())
        ''', feedback_id, quote_id, feedback.rating, feedback.comment, 
            json.dumps(feedback.labels) if feedback.labels else None,
            json.dumps(feedback.corrections) if feedback.corrections else None)
        
        return QuoteFeedbackResponse(
            id=feedback_id,
            quote_id=quote_id,
            rating=feedback.rating,
            comment=feedback.comment,
            labels=feedback.labels,
            corrections=feedback.corrections,
            created_at=datetime.now().isoformat()
        )
    
    async def get_feedback(self, quote_id: str) -> List[QuoteFeedbackResponse]:
        """Get feedback for a quote."""
        feedbacks = await self.conn.fetch('''
            SELECT id, quote_id, rating, comment, labels, corrections, created_at
            FROM quote_feedback 
            WHERE quote_id = $1 
            ORDER BY created_at DESC
        ''', quote_id)
        
        result = []
        for feedback in feedbacks:
            result.append(QuoteFeedbackResponse(
                id=feedback['id'],
                quote_id=feedback['quote_id'],
                rating=feedback['rating'],
                comment=feedback['comment'],
                labels=json.loads(feedback['labels']) if feedback['labels'] else None,
                corrections=json.loads(feedback['corrections']) if feedback['corrections'] else None,
                created_at=feedback['created_at'].isoformat()
            ))
        
        return result
    
    async def get_feedback_analytics(self) -> dict:
        """Get feedback analytics for GPT improvement."""
        # Get overall feedback statistics
        stats = await self.conn.fetchrow("""
            SELECT 
                COUNT(*) as total_feedback,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback
            FROM quote_feedback
        """)
        
        # Get accuracy distribution
        accuracy_stats = await self.conn.fetchrow("""
            SELECT 
                COUNT(CASE WHEN labels->>'accuracy' = 'excellent' THEN 1 END) as excellent,
                COUNT(CASE WHEN labels->>'accuracy' = 'good' THEN 1 END) as good,
                COUNT(CASE WHEN labels->>'accuracy' = 'fair' THEN 1 END) as fair,
                COUNT(CASE WHEN labels->>'accuracy' = 'poor' THEN 1 END) as poor
            FROM quote_feedback
            WHERE labels->>'accuracy' IS NOT NULL
        """)
        
        # Get common issues
        common_issues = await self.conn.fetch("""
            SELECT 
                'missing_products' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'missing_products' IS NOT NULL AND labels->>'missing_products' != ''
            UNION ALL
            SELECT 
                'incorrect_products' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'incorrect_products' IS NOT NULL AND labels->>'incorrect_products' != ''
            UNION ALL
            SELECT 
                'pricing_issues' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'pricing_issues' IS NOT NULL AND labels->>'pricing_issues' != ''
            UNION ALL
            SELECT 
                'quantity_issues' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'quantity_issues' IS NOT NULL AND labels->>'quantity_issues' != ''
            UNION ALL
            SELECT 
                'technical_specs' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'technical_specs' IS NOT NULL AND labels->>'technical_specs' != ''
            ORDER BY count DESC
        """)
        
        # Get recent feedback for GPT context
        recent_feedback = await self.conn.fetch("""
            SELECT 
                rating,
                comment,
                labels,
                corrections,
                created_at
            FROM quote_feedback
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        return {
            "overall_stats": {
                "total_feedback": stats['total_feedback'] or 0,
                "average_rating": float(stats['avg_rating']) if stats['avg_rating'] else 0,
                "positive_feedback": stats['positive_feedback'] or 0,
                "negative_feedback": stats['negative_feedback'] or 0,
            },
            "accuracy_distribution": {
                "excellent": accuracy_stats['excellent'] or 0,
                "good": accuracy_stats['good'] or 0,
                "fair": accuracy_stats['fair'] or 0,
                "poor": accuracy_stats['poor'] or 0,
            },
            "common_issues": [
                {"issue_type": row['issue_type'], "count": row['count']}
                for row in common_issues
            ],
            "recent_feedback": [
                {
                    "rating": row['rating'],
                    "comment": row['comment'],
                    "labels": json.loads(row['labels']) if row['labels'] else None,
                    "corrections": json.loads(row['corrections']) if row['corrections'] else None,
                    "created_at": row['created_at'].isoformat()
                }
                for row in recent_feedback
            ]
        }
    
    async def add_feedback(self, quote_id: str, feedback: QuoteFeedbackRequest) -> QuoteFeedbackResponse:
        """Add feedback to a quote."""
        feedback_id = str(uuid4())
        
        # Insert feedback into database
        await self.conn.execute("""
            INSERT INTO quote_feedback (id, quote_id, rating, comment, labels, corrections)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, 
        feedback_id, 
        quote_id, 
        feedback.rating, 
        feedback.comment,
        json.dumps(feedback.labels) if feedback.labels else None,
        json.dumps(feedback.corrections) if feedback.corrections else None
        )
        
        # Return the created feedback
        return QuoteFeedbackResponse(
            id=feedback_id,
            quote_id=quote_id,
            rating=feedback.rating,
            comment=feedback.comment,
            labels=feedback.labels,
            corrections=feedback.corrections,
            created_at=datetime.now().isoformat()
        )
    
    async def get_feedback(self, quote_id: str) -> List[QuoteFeedbackResponse]:
        """Get all feedback for a quote."""
        rows = await self.conn.fetch("""
            SELECT id, quote_id, rating, comment, labels, corrections, created_at
            FROM quote_feedback
            WHERE quote_id = $1
            ORDER BY created_at DESC
        """, quote_id)
        
        result = []
        for feedback in rows:
            result.append(QuoteFeedbackResponse(
                id=feedback['id'],
                quote_id=feedback['quote_id'],
                rating=feedback['rating'],
                comment=feedback['comment'],
                labels=json.loads(feedback['labels']) if feedback['labels'] else None,
                corrections=json.loads(feedback['corrections']) if feedback['corrections'] else None,
                created_at=feedback['created_at'].isoformat()
            ))
        
        return result
    
    async def get_feedback_analytics(self) -> dict:
        """Get feedback analytics for GPT improvement."""
        # Get overall feedback statistics
        stats = await self.conn.fetchrow("""
            SELECT 
                COUNT(*) as total_feedback,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback
            FROM quote_feedback
        """)
        
        # Get accuracy distribution
        accuracy_stats = await self.conn.fetchrow("""
            SELECT 
                COUNT(CASE WHEN labels->>'accuracy' = 'excellent' THEN 1 END) as excellent,
                COUNT(CASE WHEN labels->>'accuracy' = 'good' THEN 1 END) as good,
                COUNT(CASE WHEN labels->>'accuracy' = 'fair' THEN 1 END) as fair,
                COUNT(CASE WHEN labels->>'accuracy' = 'poor' THEN 1 END) as poor
            FROM quote_feedback
            WHERE labels->>'accuracy' IS NOT NULL
        """)
        
        # Get common issues
        common_issues = await self.conn.fetch("""
            SELECT 
                'missing_products' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'missing_products' IS NOT NULL AND labels->>'missing_products' != ''
            UNION ALL
            SELECT 
                'incorrect_products' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'incorrect_products' IS NOT NULL AND labels->>'incorrect_products' != ''
            UNION ALL
            SELECT 
                'pricing_issues' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'pricing_issues' IS NOT NULL AND labels->>'pricing_issues' != ''
            UNION ALL
            SELECT 
                'quantity_issues' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'quantity_issues' IS NOT NULL AND labels->>'quantity_issues' != ''
            UNION ALL
            SELECT 
                'technical_specs' as issue_type,
                COUNT(*) as count
            FROM quote_feedback 
            WHERE labels->>'technical_specs' IS NOT NULL AND labels->>'technical_specs' != ''
            ORDER BY count DESC
        """)
        
        # Get recent feedback for GPT context
        recent_feedback = await self.conn.fetch("""
            SELECT 
                rating,
                comment,
                labels,
                corrections,
                created_at
            FROM quote_feedback
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        return {
            "overall_stats": {
                "total_feedback": stats['total_feedback'] or 0,
                "average_rating": float(stats['avg_rating']) if stats['avg_rating'] else 0,
                "positive_feedback": stats['positive_feedback'] or 0,
                "negative_feedback": stats['negative_feedback'] or 0,
            },
            "accuracy_distribution": {
                "excellent": accuracy_stats['excellent'] or 0,
                "good": accuracy_stats['good'] or 0,
                "fair": accuracy_stats['fair'] or 0,
                "poor": accuracy_stats['poor'] or 0,
            },
            "common_issues": [
                {"issue_type": row['issue_type'], "count": row['count']}
                for row in common_issues
            ],
            "recent_feedback": [
                {
                    "rating": row['rating'],
                    "comment": row['comment'],
                    "labels": json.loads(row['labels']) if row['labels'] else None,
                    "corrections": json.loads(row['corrections']) if row['corrections'] else None,
                    "created_at": row['created_at'].isoformat()
                }
                for row in recent_feedback
            ]
        }
