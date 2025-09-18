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
        try:
            # Extract intent from the prompt
            intent = extract_intent(request.prompt)
            if not intent or 'items' not in intent:
                raise ValueError("Could not extract product requirements from prompt")
            
            # Create quote record
            quote_id = str(uuid4())
            currency = None
            total_amount = 0.0
            notes_parts = []
            
            # Insert quote
            await self.conn.execute('''
                INSERT INTO quotes (id, title, prompt, extracted_intent, currency, total_amount, notes, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', quote_id, request.title, request.prompt, json.dumps(intent), 
                currency, total_amount, None, 'draft')
            
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
                    
                    # Track totals
                    if not currency:
                        currency = best.get('currency', 'USD')
                    total_amount += subtotal
                    
                    # Add to response
                    quote_items.append(QuoteItemRequest(
                        sku=best['sku'],
                        description=best['description'],
                        quantity=quantity,
                        unit_price=unit_price,
                        currency=best.get('currency', 'USD'),
                        subtotal=subtotal,
                        product_id=product_id,
                        metadata=metadata,
                        position=i
                    ))
                else:
                    # No product found - create placeholder with extracted content
                    # Use the extracted SKU if available, otherwise generate a placeholder
                    extracted_sku = (item_want.get('sku') or '').strip()
                    family = item_want.get('family', 'product')
                    features = item_want.get('features', [])
                    
                    if extracted_sku:
                        placeholder_sku = extracted_sku
                    else:
                        placeholder_sku = f"PLACEHOLDER-{family.upper()}-{i+1}"
                    
                    # Create description from extracted content
                    description_parts = [family.title()]
                    if features:
                        description_parts.extend([f.title() for f in features[:3]])  # Limit to 3 features
                    if item_want.get('formFactor'):
                        description_parts.append(item_want['formFactor'].title())
                    if item_want.get('location'):
                        description_parts.append(item_want['location'].title())
                    
                    description = f"{' '.join(description_parts)} (Product not found in catalog)"
                    
                    # Set price and quantity to 0
                    unit_price = 0.0
                    subtotal = 0.0
                    
                    # Create metadata indicating no product found
                    metadata = {
                        'is_fallback': False,
                        'original_request': item_want.get('sku', ''),
                        'search_method': 'no_match',
                        'extracted_content': item_want,
                        'placeholder': True
                    }
                    
                    # Insert placeholder quote item
                    item_id = str(uuid4())
                    await self.conn.execute('''
                        INSERT INTO quote_items (
                            id, quote_id, product_id, sku, description, quantity, 
                            unit_price, currency, subtotal, metadata, position
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ''', item_id, quote_id, None, placeholder_sku, description,
                        quantity, unit_price, 'USD', subtotal,
                        json.dumps(metadata), i)
                    
                    # Set currency if not set
                    if not currency:
                        currency = 'USD'
                    
                    # Add to response
                    quote_items.append(QuoteItemRequest(
                        sku=placeholder_sku,
                        description=description,
                        quantity=quantity,
                        unit_price=unit_price,
                        currency=currency,
                        subtotal=subtotal,
                        product_id=None,
                        metadata=metadata,
                        position=i
                    ))
            
            # Add accessories from global preferences
            if 'global' in intent:
                extras = await self._find_accessory_products(intent['global'], selected_skus)
                for j, product in enumerate(extras):
                    unit_price = float(product.get('price', 0))
                    qty = int(product.get('quantity', 1))
                    subtotal = unit_price * qty
                    
                    # Get product_id
                    product_id = await self.conn.fetchval(
                        'SELECT id FROM products WHERE sku = $1', product['sku']
                    )
                    
                    # Insert quote item
                    item_id = str(uuid4())
                    await self.conn.execute('''
                        INSERT INTO quote_items (
                            id, quote_id, product_id, sku, description, quantity, 
                            unit_price, currency, subtotal, metadata, position
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ''', item_id, quote_id, product_id, product['sku'], product['description'],
                        qty, unit_price, product.get('currency', 'USD'), subtotal,
                        json.dumps({'is_accessory': True}), len(quote_items) + j)
                    
                    total_amount += subtotal
                    
                    quote_items.append(QuoteItemRequest(
                        sku=product['sku'],
                        description=product['description'],
                        quantity=qty,
                        unit_price=unit_price,
                        currency=product.get('currency', 'USD'),
                        subtotal=subtotal,
                        product_id=product_id,
                        metadata={'is_accessory': True},
                        position=len(quote_items) + j
                    ))
            
            # Update quote with totals
            notes = "; ".join(notes_parts) if notes_parts else None
            await self.conn.execute('''
                UPDATE quotes 
                SET currency = $1, total_amount = $2, notes = $3, updated_at = now()
                WHERE id = $4
            ''', currency, total_amount, notes, quote_id)
            
            # Return the created quote
            return await self.get_quote(quote_id)
            
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
            quote_items.append(QuoteItemRequest(
                sku=item['sku'],
                description=item['description'],
                quantity=item['quantity'],
                unit_price=float(item['unit_price']),
                currency=item['currency'],
                subtotal=float(item['subtotal']),
                product_id=item['product_id'],
                metadata=json.loads(item['metadata']) if item['metadata'] else None,
                position=item['position']
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
            # Get quote items count for efficiency
            item_count = await self.conn.fetchval(
                'SELECT COUNT(*) FROM quote_items WHERE quote_id = $1', quote['id']
            )
            
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
                items=[]  # Don't load items for list view
            ))
        
        return result
    
    async def update_quote_status(self, quote_id: str, status: str) -> QuoteResponse:
        """Update quote status."""
        valid_statuses = ['draft', 'sent', 'accepted', 'rejected', 'expired']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        await self.conn.execute('''
            UPDATE quotes 
            SET status = $1, updated_at = now()
            WHERE id = $2
        ''', status, quote_id)
        
        return await self.get_quote(quote_id)
    
    async def add_feedback(self, quote_id: str, feedback: QuoteFeedbackRequest) -> QuoteFeedbackResponse:
        """Add feedback to a quote."""
        feedback_id = str(uuid4())
        
        await self.conn.execute('''
            INSERT INTO quote_feedback (id, quote_id, rating, comment, labels, corrections)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', feedback_id, quote_id, feedback.rating, feedback.comment,
            json.dumps(feedback.labels) if feedback.labels else None,
            json.dumps(feedback.corrections) if feedback.corrections else None)
        
        # Get the created feedback
        result = await self.conn.fetchrow('''
            SELECT id, quote_id, rating, comment, labels, corrections, created_at
            FROM quote_feedback WHERE id = $1
        ''', feedback_id)
        
        return QuoteFeedbackResponse(
            id=result['id'],
            quote_id=result['quote_id'],
            rating=result['rating'],
            comment=result['comment'],
            labels=json.loads(result['labels']) if result['labels'] else None,
            corrections=json.loads(result['corrections']) if result['corrections'] else None,
            created_at=result['created_at'].isoformat()
        )
    
    async def _find_accessory_products(self, global_prefs: Dict[str, Any], selected_skus: set) -> List[Dict[str, Any]]:
        """Find accessory products (NVR/Switch) from global preferences."""
        additional_products = []
        
        nvr_bans = [
            "adapter", "charger", "license", "software", "tamper", "battery",
            "mount", "bracket", "housing", "cover", "cap", "weather cap",
            "sunshade", "sun shade", "kit", "rack", "rack mount", "recorder mount"
        ]
        switch_bans = [
            "adapter", "charger", "license", "software", "battery",
            "mount", "bracket", "housing", "cover", "cap", "weather cap",
            "sunshade", "sun shade", "tamper", "joystick", "speaker", "microphone", "mic",
            "appliance", "kit", "rack", "rack mount", "recorder mount"
        ]
        
        # NVR search
        if 'nvrChannels' in global_prefs and global_prefs['nvrChannels']:
            nvr_channels = int(global_prefs['nvrChannels'])
            not_likes = " AND ".join([f"LOWER(description) NOT LIKE ${i+7}" for i in range(len(nvr_bans))])
            sql = f"""
            SELECT sku, description, price, currency, family, active
            FROM products
            WHERE active = true
              AND (LOWER(description) LIKE '%nvr%' OR LOWER(description) LIKE '%recorder%')
              AND (
                    description ~* $1 OR  -- 4ch, 4 ch, 4 channels
                    description ~* $2 OR  -- 4-ch
                    description ~* $3 OR  -- 4x
                    description ~* $4 OR  -- 4 x, 4X
                    description ~* $5 OR  -- ch 4, channels: 4
                    sku ~* $6             -- ...-4, 4-, _4_
              )
              AND {not_likes}
            ORDER BY price ASC NULLS LAST
            LIMIT 1
            """
            params = [
                f"{nvr_channels}.*ch",
                f"{nvr_channels}-ch",
                f"{nvr_channels}\\s*x",
                f"{nvr_channels}\\s*[xX]",
                f"ch.*{nvr_channels}",
                f"(^|\\D){nvr_channels}(\\D|$)",
            ] + [f"%{b}%" for b in nvr_bans]
            rows = await self.conn.fetch(sql, *params)
            if rows:
                r = dict(rows[0])
                if r['sku'] not in selected_skus:
                    r['quantity'] = 1
                    additional_products.append(r)
        
        # Switch search
        if 'switchPorts' in global_prefs and global_prefs['switchPorts']:
            switch_ports = int(global_prefs['switchPorts'])
            not_likes = " AND ".join([f"LOWER(description) NOT LIKE ${i+8}" for i in range(len(switch_bans))])
            sql = f"""
            SELECT sku, description, price, currency, family, active
            FROM products
            WHERE active = true
              AND LOWER(description) LIKE '%switch%'
              AND LOWER(description) LIKE '%poe%'
              AND (
                    description ~* $1 OR  -- 4 port, 4-port, 4 ports, 4 PoE+ ports
                    description ~* $2 OR  -- 4-port
                    description ~* $3 OR  -- 4 PoE, 4 PoE+
                    description ~* $4 OR  -- 4x
                    description ~* $5 OR  -- 4 x, 4X
                    description ~* $6 OR  -- ports: 4, port=4
                    sku ~* $7             -- ...-4, 4-, _4_
              )
              AND {not_likes}
            ORDER BY price ASC NULLS LAST
            LIMIT 1
            """
            params = [
                f"{switch_ports}.*port",
                f"{switch_ports}-port",
                f"{switch_ports}.*PoE",
                f"{switch_ports}\\s*x",
                f"{switch_ports}\\s*[xX]",
                f"ports?\\s*[:=]\\s*{switch_ports}",
                f"(^|\\D){switch_ports}(\\D|$)",
            ] + [f"%{b}%" for b in switch_bans]
            rows = await self.conn.fetch(sql, *params)
            if rows:
                r = dict(rows[0])
                if r['sku'] not in selected_skus:
                    r['quantity'] = 1
                    additional_products.append(r)
        
        return additional_products
