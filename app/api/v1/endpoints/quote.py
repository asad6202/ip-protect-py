"""
Quote generation endpoint using hybrid search pipeline.
"""

from typing import List, Dict, Any
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
    Add NVR/Switch from global preferences (strict). No loose fallbacks.
    """
    additional_products: List[Dict[str, Any]] = []

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

    # ---------- NVR (exact channel count required; match in description OR SKU) ----------
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
            f"{nvr_channels}.*ch",  # "4ch", "4 ch", "4 channels"
            f"{nvr_channels}-ch",  # "4-ch"
            f"{nvr_channels}\\s*x",  # "4x"
            f"{nvr_channels}\\s*[xX]",  # "4 x", "4X"
            f"ch.*{nvr_channels}",  # "ch 4", "channels: 4"
            f"(^|\\D){nvr_channels}(\\D|$)",  # SKU patterns
        ] + [f"%{b}%" for b in nvr_bans]
        rows = await conn.fetch(sql, *params)
        if rows:
            r = dict(rows[0])
            if r['sku'] not in selected_skus:
                r['quantity'] = 1
                additional_products.append(r)

    # ---------- PoE Switch (exact port count required; match in description OR SKU) ----------
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
            f"{switch_ports}.*port",  # "4 port", "4-port", "4 ports", "4 PoE+ ports"
            f"{switch_ports}-port",  # "4-port"
            f"{switch_ports}.*PoE",  # "4 PoE", "4 PoE+"
            f"{switch_ports}\\s*x",  # "4x"
            f"{switch_ports}\\s*[xX]",  # "4 x", "4X"
            f"ports?\\s*[:=]\\s*{switch_ports}",  # "ports: 4", "port=4"
            f"(^|\\D){switch_ports}(\\D|$)",  # SKU patterns
        ] + [f"%{b}%" for b in switch_bans]
        rows = await conn.fetch(sql, *params)
        if rows:
            r = dict(rows[0])
            if r['sku'] not in selected_skus:
                r['quantity'] = 1
                additional_products.append(r)

    return additional_products


@router.post("/quote", response_model=QuoteResponse)
async def generate_quote(
    request: QuoteRequest,
    db: Database = Depends(get_database)
) -> QuoteResponse:
    """
    Generate a quote based on natural language description of camera/accessory needs.
    - Clear prompts → normal matching
    - Vague camera prompts → cheapest *physical* camera
    - Enforces NVR channels and switch ports when given in global prefs
    """
    try:
        # 1) Extract intent
        intent = extract_intent(request.prompt)
        print(intent)
        if not intent or 'items' not in intent:
            raise HTTPException(status_code=400, detail="Could not extract product requirements from prompt")

        # 2) Connect DB
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            retrieval = ProductRetrieval(conn)
            quote_items: List[QuoteItem] = []
            selected_skus: set = set()
            notes_parts: List[str] = []

            # 3) For each requested item
            for item_want in intent['items']:
                quantity = max(1, int(item_want.get('quantity', 1)))

                # Skip switch/NVR items if we have global preferences (to avoid duplicates)
                family = item_want.get('family') or ''
                if (family.lower() == 'switch' and 
                    'global' in intent and 'switchPorts' in intent['global']):
                    continue
                if (family.lower() == 'nvr' and 
                    'global' in intent and 'nvrChannels' in intent['global']):
                    continue

                # Search (SKU → vague-cheapest → deterministic → vector)
                candidates = await retrieval.search_products(item_want, request.prompt)
                if not candidates:
                    continue

                best = candidates[0]
                
                # Check if this is a fallback (exact SKU not found or vector fallback used)
                requested_sku = item_want.get('sku', '').strip()
                is_fallback = False
                original_request = None
                
                if requested_sku and best['sku'] != requested_sku:
                    # Check if the requested SKU was found via description match
                    # Only mark as fallback if it's a completely different product
                    # (not when we found the right product but with different SKU)
                    if not best.get('description', '').upper().find(requested_sku.upper()) >= 0:
                        is_fallback = True
                        original_request = requested_sku
                elif best.get('_used_vector_fallback', False):
                    # This item came from vector fallback (no exact match found)
                    is_fallback = True
                    # Try to extract what was originally requested from the item_want
                    if requested_sku:
                        original_request = requested_sku
                    else:
                        # Extract from description or other fields
                        desc = item_want.get('description', '')
                        if desc:
                            original_request = desc
                        else:
                            original_request = f"{item_want.get('family', 'product')} (not found)"
                elif best.get('_brand_fallback', False):
                    # This item came from brand fallback (preferred brand not available)
                    is_fallback = True
                    # Extract brand preference info
                    brand_prefs = item_want.get('brandPreference', [])
                    if brand_prefs:
                        original_request = f"Preferred brand: {', '.join(brand_prefs)} (not available)"
                    else:
                        original_request = "Preferred brand not available"

                # Defensive family/bans were applied in retrieval; still ensure we don't pick obvious accessories
                # (rare path if your DB contents change over time)
                desc_l = (best.get('description') or '').lower()
                family = item_want.get('family') or ''
                if family.lower() == 'camera' and any(
                    w in desc_l for w in [
                        'license', 'software', 'mount', 'bracket', 'housing', 'cover', 'smoked dome',
                        'cap', 'weather cap', 'tamper', 'appliance', 'stand', 'joystick',
                        'microphone', 'speaker', 'encoder', 'decoder', 'relay', 'power supply'
                    ]
                ):
                    # Skip and try next candidate if available
                    if len(candidates) > 1:
                        best = candidates[1]
                        desc_l = (best.get('description') or '').lower()

                selected_skus.add(best['sku'])

                unit_price = float(best.get('price', 0))
                subtotal = unit_price * quantity

                quote_items.append(QuoteItem(
                    sku=best['sku'],
                    description=best['description'],
                    quantity=quantity,
                    unit_price=unit_price,
                    currency=best.get('currency', 'USD'),
                    subtotal=subtotal,
                    is_fallback=is_fallback,
                    original_request=original_request
                ))

                if item_want.get("brandPreference"):
                    notes_parts.append(f"Preferred brands: {', '.join(item_want['brandPreference'])}")
                if item_want.get("brandAvoid"):
                    notes_parts.append(f"Avoided brands: {', '.join(item_want['brandAvoid'])}")
                family = item_want.get("family") or ""
                if item_want.get("vague") and family.lower() == "camera":
                    notes_parts.append("Vague request detected → selected the lowest-priced physical camera.")

            # 4) Accessories from global prefs (NVR / Switch)
            if 'global' in intent:
                extras = await find_accessory_products(conn, intent['global'], selected_skus)
                for product in extras:
                    unit_price = float(product.get('price', 0))
                    qty = int(product.get('quantity', 1))
                    subtotal = unit_price * qty

                    quote_items.append(QuoteItem(
                        sku=product['sku'],
                        description=product['description'],
                        quantity=qty,
                        unit_price=unit_price,
                        currency=product.get('currency', 'USD'),
                        subtotal=subtotal
                    ))

            # Add fallback summary to notes
            fallback_items = [item for item in quote_items if item.is_fallback]
            if fallback_items:
                fallback_summary = []
                for item in fallback_items:
                    fallback_summary.append(f"{item.original_request} → {item.sku}")
                notes_parts.append(f"Fallback products used: {', '.join(fallback_summary)}")

            if not quote_items:
                raise HTTPException(status_code=404, detail="No matching products found for the given requirements")

            # 5) Totals (single-currency assumption remains; normalize externally if multi-currency needed)
            total = sum(item.subtotal for item in quote_items)
            currency = quote_items[0].currency

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
