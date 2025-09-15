"""
Quote generation endpoint using hybrid search pipeline.
"""

import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from schemas import QuoteRequest, QuoteResponse, QuoteItem
from app.ai.intent_extractor import extract_intent
from app.services.retrieval import ProductRetrieval
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


async def find_accessory_products(conn, global_prefs: Dict[str, Any], selected_skus: set) -> List[Dict[str, Any]]:
    """
    Find additional accessory products based on global preferences.
    
    Args:
        conn: Database connection
        global_prefs: Global preferences from intent
        selected_skus: SKUs already selected to avoid duplicates
        
    Returns:
        List of additional products to add to quote
    """
    additional_products = []
    
    # Find NVR if needed
    if 'nvrChannels' in global_prefs and global_prefs['nvrChannels']:
        nvr_channels = global_prefs['nvrChannels']
        
        # Look for NVR with matching or higher channel count
        query = """
        SELECT sku, description, price, currency, family, status
        FROM products 
        WHERE status = 'active' 
          AND family = 'nvr'
          AND description ILIKE $1
        ORDER BY price ASC
        LIMIT 1
        """
        
        channel_pattern = f"%{nvr_channels} channel%"
        rows = await conn.fetch(query, channel_pattern)
        
        if rows and rows[0]['sku'] not in selected_skus:
            product = dict(rows[0])
            product['quantity'] = 1
            additional_products.append(product)
    
    # Find switch if needed
    if 'switchPorts' in global_prefs and global_prefs['switchPorts']:
        switch_ports = global_prefs['switchPorts']
        
        # Look for switch with matching or higher port count
        query = """
        SELECT sku, description, price, currency, family, status
        FROM products 
        WHERE status = 'active' 
          AND family = 'switch'
          AND description ILIKE $1
        ORDER BY price ASC
        LIMIT 1
        """
        
        port_pattern = f"%{switch_ports} port%"
        rows = await conn.fetch(query, port_pattern)
        
        if rows and rows[0]['sku'] not in selected_skus:
            product = dict(rows[0])
            product['quantity'] = 1
            additional_products.append(product)
    
    return additional_products


@router.post("/quote", response_model=QuoteResponse)
async def generate_quote(
    request: QuoteRequest,
    db: Database = Depends(get_database)
) -> QuoteResponse:
    """
    Generate a quote based on natural language description of camera/accessory needs.
    
    This endpoint:
    1. Extracts structured intent from the natural language prompt
    2. Searches for products using hybrid deterministic + vector search
    3. Assembles a quote with quantities, prices, and totals
    4. Optionally adds accessory products based on global requirements
    """
    try:
        # Extract intent from natural language
        intent = extract_intent(request.prompt)
        print(intent)
        if not intent or 'items' not in intent:
            raise HTTPException(status_code=400, detail="Could not extract product requirements from prompt")
        
        # Get database connection
        if not db._pool:
            await db.connect()
        
        async with db._pool.acquire() as conn:
            retrieval = ProductRetrieval(conn)
            quote_items = []
            selected_skus = set()
            notes_parts = []
            
            # Process each requested item
            for item_want in intent['items']:
                quantity = max(1, int(item_want.get('quantity', 1)))
                
                # Search for products
                candidates = await retrieval.search_products(item_want, request.prompt)
                
                if not candidates:
                    continue
                
                # Select the best candidate
                best_product = candidates[0]
                selected_skus.add(best_product['sku'])
                
                # Create quote item
                unit_price = float(best_product.get('price', 0))
                subtotal = unit_price * quantity
                
                quote_item = QuoteItem(
                    sku=best_product['sku'],
                    description=best_product['description'],
                    quantity=quantity,
                    unit_price=unit_price,
                    currency=best_product.get('currency', 'USD'),
                    subtotal=subtotal
                )
                quote_items.append(quote_item)
                
                # Add notes about selection criteria
                if 'brandPreference' in item_want and item_want['brandPreference']:
                    notes_parts.append(f"Preferred brands: {', '.join(item_want['brandPreference'])}")
                
                if 'brandAvoid' in item_want and item_want['brandAvoid']:
                    notes_parts.append(f"Avoided brands: {', '.join(item_want['brandAvoid'])}")
            
            # Add accessory products based on global preferences
            if 'global' in intent:
                additional_products = await find_accessory_products(conn, intent['global'], selected_skus)
                
                for product in additional_products:
                    unit_price = float(product.get('price', 0))
                    quantity = product.get('quantity', 1)
                    subtotal = unit_price * quantity
                    
                    quote_item = QuoteItem(
                        sku=product['sku'],
                        description=product['description'],
                        quantity=quantity,
                        unit_price=unit_price,
                        currency=product.get('currency', 'USD'),
                        subtotal=subtotal
                    )
                    quote_items.append(quote_item)
            
            if not quote_items:
                raise HTTPException(status_code=404, detail="No matching products found for the given requirements")
            
            # Calculate totals
            total = sum(item.subtotal for item in quote_items)
            currency = quote_items[0].currency if quote_items else 'USD'
            
            # Add global notes
            if 'global' in intent and intent['global'].get('notes'):
                notes_parts.append(intent['global']['notes'])
            
            notes = "; ".join(notes_parts) if notes_parts else None
            
            return QuoteResponse(
                items=quote_items,
                total=total,
                currency=currency,
                notes=notes
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote generation failed: {str(e)}")


@router.get("/quote/health")
async def quote_health_check():
    """Health check endpoint for quote service."""
    return {"status": "healthy", "service": "quote_generation"}
