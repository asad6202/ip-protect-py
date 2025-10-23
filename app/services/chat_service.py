"""
Chat service for interactive quote modifications using OpenAI.
"""

import os
import json
import base64
import re
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from agents import Agent, Runner


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
        
        # Check if message contains URLs to scan
        urls = self._extract_urls(message)
        if urls:
            return await self._handle_url_scan(quote_id, urls, message)
        
        # Build system prompt with quote context
        system_prompt = self._build_system_prompt(quote)
        
        # Create chat agent
        chat_agent = Agent(
            name="Protect IP – Quoting Flow",
            instructions=system_prompt,
            model="gpt-4o"
        )
        
        # Build messages for the agent
        messages = []
        
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
        
        # Run the agent using Runner
        result = await Runner.run(chat_agent, messages)
        
        # Debug output
        print("=" * 80)
        print("DEBUG - Chat Agent result.final_output:")
        print(result.final_output)
        print("=" * 80)
        
        # Parse AI response
        ai_response = json.loads(result.final_output)
        
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
Quote ID: {quote.get('id')}
Total Items: {len(quote.get('items', []))}
Currency: {quote.get('currency', 'USD')}

Current Items:
{items_summary}

Your task is to understand user requests to modify this quote and provide structured responses.

When the user asks to modify the quote, you should:
1. Understand what changes they want (add items, remove items, change quantities, merge with another quote, scan URLs, etc.)
2. Provide a natural language response explaining what you'll do
3. Return structured modifications in JSON format

Response Format (JSON):
{{
    "response": "Natural language explanation of changes",
    "modifications": {{
        "merge_quote": {{"source_quote_id": "QUOTE-ID-HERE"}},  # Use when user wants to combine/merge quotes
        "scan_url": {{"url": "https://example.com/products"}},  # Use when user provides a URL to scan
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
If a user provides a URL, detect it and set the scan_url modification to trigger automatic product extraction from the webpage.
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
    
    def _extract_urls(self, message: str) -> List[str]:
        """
        Extract URLs from a message.
        
        Args:
            message: User message text
        
        Returns:
            List of URLs found in the message
        """
        url_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
        urls = re.findall(url_pattern, message)
        return urls
    
    async def _handle_url_scan(
        self,
        quote_id: str,
        urls: List[str],
        message: str
    ) -> Dict[str, Any]:
        """
        Handle URL scanning and merge products into quote.
        
        Args:
            quote_id: ID of the quote
            urls: List of URLs to scan
            message: Original user message
        
        Returns:
            Dict with scan results and response
        """
        from app.services.url_scanner_service import URLScannerService
        
        scanner_service = URLScannerService(self.db_conn)
        all_products = []
        successful_scans = 0
        
        for url in urls:
            try:
                scan_result = await scanner_service.scan_url(url)
                if scan_result.get("success") and scan_result.get("products"):
                    all_products.extend(scan_result["products"])
                    successful_scans += 1
            except Exception as e:
                print(f"Error scanning URL {url}: {str(e)}")
                continue
        
        if not all_products:
            return {
                "message": f"I scanned the URL(s) you provided, but couldn't find any products. Please make sure the URL contains product information.",
                "updated_items": None,
                "modifications": None
            }
        
        try:
            merge_result = await scanner_service.merge_products_into_quote(
                quote_id,
                all_products
            )
            
            product_list = "\n".join([
                f"- {p.get('name', 'Unknown')} ({p.get('quantity', 1)}x)"
                for p in all_products[:5]
            ])
            more_text = f"\n...and {len(all_products) - 5} more" if len(all_products) > 5 else ""
            
            return {
                "message": f"I've scanned {successful_scans} URL(s) and added {merge_result['added_items']} products to your quote:\n{product_list}{more_text}",
                "updated_items": merge_result.get("new_items"),
                "modifications": {"scan_url": {"urls": urls, "products_added": merge_result['added_items']}}
            }
        except Exception as e:
            raise ValueError(f"Failed to merge products from URL: {str(e)}")
    
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
        
        # Handle quote merge first (if requested)
        if modifications.get("merge_quote"):
            from app.services.quote_service import QuoteService
            source_quote_id = modifications["merge_quote"].get("source_quote_id")
            if source_quote_id:
                quote_service = QuoteService(self.db_conn)
                merged_quote = await quote_service.merge_quotes(quote_id, source_quote_id)
                # Convert Pydantic model to dict and return all items from merged quote
                if hasattr(merged_quote, 'items'):
                    return merged_quote.items
                elif hasattr(merged_quote, 'model_dump'):
                    return merged_quote.model_dump().get('items', [])
                else:
                    return []
        
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
                    quote_id, item["sku"], int(item["quantity"])
                )
                if row:
                    updated_items.append(dict(row))
        
        # Handle new items - integrate with product search
        if modifications.get("add_items"):
            from app.services.retrieval import ProductRetrieval
            retrieval = ProductRetrieval(self.db_conn)
            
            for new_item in modifications["add_items"]:
                search_criteria = new_item.get("search_criteria", {})
                candidates = await retrieval.search_products(search_criteria, "")
                
                if candidates and len(candidates) > 0:
                    best_product = candidates[0]
                    quantity = int(new_item.get("quantity", 1))
                    unit_price = float(best_product.get('price', 0) or 0)
                    
                    # Use stored procedure for clean, type-safe insert
                    row = await self.db_conn.fetchrow(
                        """SELECT * FROM add_quote_item($1, $2, $3, $4, $5, $6, $7)""",
                        quote_id,
                        best_product['sku'],
                        best_product.get('description', ''),
                        quantity,
                        unit_price,
                        quote.get('currency', 'USD'),
                        json.dumps({'added_via_chat': True})
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
        # Build chat messages as Python dict, then convert to JSON
        new_messages = [
            {
                'role': 'user',
                'content': user_message,
                'timestamp': 'NOW()'  # Will be replaced in query
            },
            {
                'role': 'assistant',
                'content': ai_response,
                'timestamp': 'NOW()'  # Will be replaced in query
            }
        ]
        
        # Simpler approach: use a single JSONB parameter
        await self.db_conn.execute(
            """UPDATE quotes 
               SET metadata = COALESCE(metadata, '{}'::jsonb) || 
                   jsonb_build_object(
                       'chat_history', 
                       COALESCE(metadata->'chat_history', '[]'::jsonb) || $2::jsonb
                   )
               WHERE id = $1""",
            quote_id,
            json.dumps(new_messages)
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
