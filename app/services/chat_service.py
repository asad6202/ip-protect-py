"""
Chat service for interactive quote modifications using OpenAI.
"""

import os
import json
import base64
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI


class ChatService:
    """Service for processing chat messages to modify quotes."""
    
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    async def process_chat_message(
        self,
        quote_id: str,
        message: str,
        chat_history: List[Dict[str, Any]] = None,
        attachments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message to modify a quote.
        
        Args:
            quote_id: ID of the quote to modify
            message: User's chat message
            chat_history: Previous chat messages
            attachments: List of file attachments with metadata
        
        Returns:
            Dict with response message, updated items, and modifications
        """
        # Get current quote data
        quote = await self._get_quote(quote_id)
        if not quote:
            raise ValueError(f"Quote {quote_id} not found")
        
        # Build system prompt with quote context
        system_prompt = self._build_system_prompt(quote)
        
        # Build messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history
        if chat_history:
            for msg in chat_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Process attachments and add to user message
        user_content = self._build_user_message(message, attachments)
        messages.append({"role": "user", "content": user_content})
        
        # Call OpenAI to process the request
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Parse AI response
        ai_response = json.loads(response.choices[0].message.content)
        
        # Apply modifications to quote
        updated_items = None
        if ai_response.get("modifications"):
            updated_items = await self._apply_modifications(
                quote_id,
                quote,
                ai_response["modifications"]
            )
        
        # Save chat message to database
        await self._save_chat_message(quote_id, message, ai_response.get("response", ""))
        
        return {
            "message": ai_response.get("response", "I've updated the quote based on your request."),
            "updated_items": updated_items,
            "modifications": ai_response.get("modifications")
        }
    
    def _build_system_prompt(self, quote: Dict[str, Any]) -> str:
        """Build system prompt with quote context."""
        items_summary = "\n".join([
            f"- {item['quantity']}x {item['description']} ({item['sku']}) @ {item['unit_price']} each"
            for item in quote.get('items', []) if item
        ])
        
        return f"""You are a helpful assistant for modifying CCTV product quotes.

Current Quote Information:
Title: {quote.get('title', 'Untitled Quote')}
Total Items: {len(quote.get('items', []))}
Currency: {quote.get('currency', 'USD')}

Current Items:
{items_summary}

Your task is to understand user requests to modify this quote and provide structured responses.

When the user asks to modify the quote, you should:
1. Understand what changes they want (add items, remove items, change quantities, etc.)
2. Provide a natural language response explaining what you'll do
3. Return structured modifications in JSON format

Response Format (JSON):
{{
    "response": "Natural language explanation of changes",
    "modifications": {{
        "add_items": [
            {{"name": "Product Name", "quantity": 2, "search_criteria": {{"features": ["outdoor", "5mp"]}}}}
        ],
        "remove_items": [
            {{"sku": "SKU-123"}}
        ],
        "update_items": [
            {{"sku": "SKU-456", "quantity": 5}}
        ],
        "replace_items": [
            {{"old_sku": "SKU-789", "search_criteria": {{"features": ["indoor", "4k"]}}}}
        ]
    }}
}}

If a user uploads an image, analyze it for relevant information (e.g., floor plans, site photos) to better understand their requirements.
"""
    
    def _build_user_message(
        self,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Any:
        """Build user message with text and optional image/document attachments."""
        if not attachments or len(attachments) == 0:
            return message
        
        # Build multi-modal message with images and document context
        content = [{"type": "text", "text": message}]
        
        for attachment in attachments:
            if attachment['content_type'].startswith('image/'):
                # Encode image as base64
                image_data = base64.b64encode(attachment['data']).decode('utf-8')
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{attachment['content_type']};base64,{image_data}"
                    }
                })
            elif attachment['content_type'] in ['application/pdf', 'text/plain', 
                                                'application/msword', 
                                                'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                # For PDFs and documents, add a note that they're attached
                # In future, could extract text or use vision for PDFs
                content.append({
                    "type": "text",
                    "text": f"\n[Attached document: {attachment['filename']}]\nNote: Document content analysis not yet implemented. Please describe the relevant information from the document in your message."
                })
        
        return content
    
    async def _get_quote(self, quote_id: str) -> Optional[Dict[str, Any]]:
        """Fetch quote from database."""
        query = """
            SELECT 
                q.id, q.title, q.prompt, q.currency, q.status,
                q.total_amount, q.notes, q.created_at,
                json_agg(
                    json_build_object(
                        'id', qi.id,
                        'sku', qi.sku,
                        'description', qi.description,
                        'quantity', qi.quantity,
                        'unit_price', qi.unit_price,
                        'subtotal', qi.subtotal,
                        'item_metadata', qi.item_metadata
                    ) ORDER BY qi.position
                ) FILTER (WHERE qi.id IS NOT NULL) as items
            FROM quotes q
            LEFT JOIN quote_items qi ON q.id = qi.quote_id
            WHERE q.id = $1
            GROUP BY q.id
        """
        row = await self.db_conn.fetchrow(query, quote_id)
        if not row:
            return None
        
        # Convert row to dict and parse JSON items
        result = dict(row)
        if result.get('items') and isinstance(result['items'], str):
            result['items'] = json.loads(result['items'])
        
        return result
    
    async def _apply_modifications(
        self,
        quote_id: str,
        quote: Dict[str, Any],
        modifications: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply modifications to the quote."""
        updated_items = []
        
        # Handle item removals
        if modifications.get("remove_items"):
            for item in modifications["remove_items"]:
                await self.db_conn.execute(
                    "DELETE FROM quote_items WHERE quote_id = $1 AND sku = $2",
                    quote_id, item["sku"]
                )
        
        # Handle quantity updates
        if modifications.get("update_items"):
            for item in modifications["update_items"]:
                row = await self.db_conn.fetchrow(
                    """UPDATE quote_items 
                       SET quantity = $3, 
                           subtotal = unit_price * $3
                       WHERE quote_id = $1 AND sku = $2
                       RETURNING *""",
                    quote_id, item["sku"], item["quantity"]
                )
                if row:
                    updated_items.append(dict(row))
        
        # Handle new items - integrate with product search
        if modifications.get("add_items"):
            from app.services.retrieval import ProductRetrieval
            from decimal import Decimal
            retrieval = ProductRetrieval(self.db_conn)
            
            for new_item in modifications["add_items"]:
                search_criteria = new_item.get("search_criteria", {})
                candidates = await retrieval.search_products(search_criteria, "")
                
                if candidates and len(candidates) > 0:
                    best_product = candidates[0]
                    quantity = int(new_item.get("quantity", 1))
                    
                    # Get next position
                    next_pos_row = await self.db_conn.fetchrow(
                        "SELECT COALESCE(MAX(position), 0) + 1 as next_pos FROM quote_items WHERE quote_id = $1",
                        quote_id
                    )
                    next_position = int(next_pos_row['next_pos']) if next_pos_row else 1
                    
                    # Ensure price is a Decimal
                    price = best_product.get('price', 0)
                    if price is None:
                        price = 0
                    unit_price = Decimal(str(price))
                    subtotal = unit_price * quantity
                    
                    # Prepare metadata
                    metadata_json = json.dumps({'added_via_chat': True})
                    
                    row = await self.db_conn.fetchrow(
                        """INSERT INTO quote_items 
                           (quote_id, sku, description, quantity, unit_price, subtotal, currency, position, item_metadata)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                           RETURNING *""",
                        str(quote_id),
                        str(best_product['sku']),
                        str(best_product.get('description', '')),
                        quantity,
                        unit_price,
                        subtotal,
                        str(quote.get('currency', 'USD')),
                        next_position,
                        metadata_json
                    )
                    if row:
                        updated_items.append(dict(row))
        
        # Handle replacements - integrate with product search
        if modifications.get("replace_items"):
            from app.services.retrieval import ProductRetrieval
            retrieval = ProductRetrieval(self.db_conn)
            
            for replacement in modifications["replace_items"]:
                old_sku = replacement.get("old_sku")
                search_criteria = replacement.get("search_criteria", {})
                
                candidates = await retrieval.search_products(search_criteria, "")
                
                if candidates and len(candidates) > 0:
                    best_product = candidates[0]
                    
                    row = await self.db_conn.fetchrow(
                        """UPDATE quote_items 
                           SET sku = $3,
                               description = $4,
                               unit_price = $5,
                               subtotal = quantity * $5,
                               item_metadata = COALESCE(item_metadata, '{}'::jsonb) || 
                                         jsonb_build_object('replaced_via_chat', true, 'original_sku', $2)
                           WHERE quote_id = $1 AND sku = $2
                           RETURNING *""",
                        quote_id,
                        old_sku,
                        best_product['sku'],
                        best_product.get('description', ''),
                        float(best_product.get('price', 0))
                    )
                    if row:
                        updated_items.append(dict(row))
        
        # Update quote total
        await self._update_quote_total(quote_id)
        
        return updated_items
    
    async def _update_quote_total(self, quote_id: str):
        """Recalculate and update quote total."""
        await self.db_conn.execute(
            """UPDATE quotes 
               SET total_amount = (
                   SELECT COALESCE(SUM(subtotal), 0) 
                   FROM quote_items 
                   WHERE quote_id = $1
               )
               WHERE id = $1""",
            quote_id
        )
    
    async def _save_chat_message(
        self,
        quote_id: str,
        user_message: str,
        ai_response: str
    ):
        """Save chat message to quote metadata."""
        # Store in quote metadata for now
        # Could create a separate chat_messages table in future
        await self.db_conn.execute(
            """UPDATE quotes 
               SET metadata = COALESCE(metadata, '{}'::jsonb) || 
                   jsonb_build_object(
                       'chat_history', 
                       COALESCE(metadata->'chat_history', '[]'::jsonb) || 
                       jsonb_build_array(
                           jsonb_build_object(
                               'role', 'user',
                               'content', $2,
                               'timestamp', NOW()
                           ),
                           jsonb_build_object(
                               'role', 'assistant',
                               'content', $3,
                               'timestamp', NOW()
                           )
                       )
                   )
               WHERE id = $1""",
            quote_id, user_message, ai_response
        )
    
    async def get_chat_history(self, quote_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a quote."""
        row = await self.db_conn.fetchrow(
            "SELECT metadata->'chat_history' as history FROM quotes WHERE id = $1",
            quote_id
        )
        
        if row and row['history']:
            # PostgreSQL JSONB is already parsed, no need for json.loads()
            return row['history'] if isinstance(row['history'], list) else []
        return []
