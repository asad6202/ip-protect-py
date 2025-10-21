"""
Service for ingesting products from external sources into the database.
"""
import asyncpg
import json
from typing import Dict, List, Any, Optional
from uuid import uuid4
from datetime import datetime


class ProductIngestionService:
    """Service for ingesting products from URL scans and other sources."""
    
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
    
    async def ingest_products(
        self,
        products: List[Dict[str, Any]],
        brand_name: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest products into the database.
        
        Args:
            products: List of product dicts from URL scanner
            brand_name: Optional brand name to associate products with
            source_url: Optional source URL for tracking
        
        Returns:
            Dict with ingestion results
        """
        try:
            ingested_count = 0
            skipped_count = 0
            errors = []
            
            # Get or create brand if specified
            brand_id = None
            if brand_name:
                brand_id = await self._get_or_create_brand(brand_name)
            
            for product_data in products:
                try:
                    # Extract product details
                    sku = product_data.get('sku') or f"AUTO-{uuid4().hex[:8].upper()}"
                    name = product_data.get('name', '')
                    description = product_data.get('description', name)
                    price = product_data.get('price', 0.0) or 0.0
                    currency = product_data.get('currency', 'USD')
                    specs = product_data.get('specifications', {})
                    
                    # Determine product family
                    family = self._determine_family(name, description, specs)
                    
                    # Try to get brand from product data if not specified
                    if not brand_id and product_data.get('brand'):
                        brand_id = await self._get_or_create_brand(product_data['brand'])
                    
                    # Check if product already exists
                    existing = await self.conn.fetchrow(
                        "SELECT id FROM products WHERE sku = $1",
                        sku
                    )
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Insert product
                    await self._insert_product(
                        sku=sku,
                        description=description,
                        price=price,
                        currency=currency,
                        family=family,
                        brand_id=brand_id,
                        specifications=specs,
                        source_url=source_url
                    )
                    
                    ingested_count += 1
                    
                except Exception as e:
                    errors.append({
                        'product': product_data.get('name', 'Unknown'),
                        'error': str(e)
                    })
                    skipped_count += 1
            
            return {
                'success': True,
                'ingested_count': ingested_count,
                'skipped_count': skipped_count,
                'total': len(products),
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'ingested_count': 0,
                'skipped_count': 0,
                'total': len(products),
                'error': str(e),
                'errors': []
            }
    
    async def _get_or_create_brand(self, brand_name: str) -> str:
        """Get existing brand or create a new one."""
        # Check if brand exists
        existing = await self.conn.fetchrow(
            "SELECT id FROM brands WHERE LOWER(name) = LOWER($1)",
            brand_name
        )
        
        if existing:
            return existing['id']
        
        # Create new brand
        brand_id = str(uuid4())
        await self.conn.execute(
            """
            INSERT INTO brands (id, name, active, created_at, updated_at)
            VALUES ($1, $2, true, now(), now())
            """,
            brand_id,
            brand_name
        )
        
        return brand_id
    
    def _determine_family(self, name: str, description: str, specs: Dict) -> str:
        """Determine product family from name, description, and specs."""
        text = f"{name} {description}".lower()
        
        # NVR patterns
        nvr_keywords = ['nvr', 'recorder', 'network video recorder']
        if any(kw in text for kw in nvr_keywords) or specs.get('nvr_channels'):
            return 'nvr'
        
        # Switch patterns
        switch_keywords = ['switch', 'poe switch', 'network switch']
        if any(kw in text for kw in switch_keywords) or specs.get('switch_ports'):
            return 'switch'
        
        # Accessory patterns
        accessory_keywords = ['mount', 'bracket', 'housing', 'cable', 'power supply', 'adapter']
        if any(kw in text for kw in accessory_keywords):
            return 'accessory'
        
        # Default to camera
        return 'camera'
    
    async def _insert_product(
        self,
        sku: str,
        description: str,
        price: float,
        currency: str,
        family: str,
        brand_id: Optional[str],
        specifications: Dict,
        source_url: Optional[str]
    ):
        """Insert a product into the database."""
        product_id = str(uuid4())
        
        # Extract normalized attributes from specifications
        form_factor = specifications.get('form_factor')
        outdoor = specifications.get('outdoor')
        poe = specifications.get('poe')
        poe_plus = specifications.get('poe_plus')
        vandal_ik10 = specifications.get('vandal_ik10')
        
        # Parse numeric values
        ir_range_m = self._parse_int(specifications.get('ir_range'))
        resolution_mp = self._parse_float(specifications.get('resolution'))
        nvr_channels = self._parse_int(specifications.get('nvr_channels'))
        switch_ports = self._parse_int(specifications.get('switch_ports'))
        
        # Determine if accessory
        is_accessory = family == 'accessory'
        accessory_type = specifications.get('accessory_type') if is_accessory else None
        
        # Create search text
        search_text = f"{sku} {description}".lower()
        
        # Store raw data
        raw_json = {
            'specifications': specifications,
            'source': 'url_scan',
            'source_url': source_url,
            'imported_at': datetime.now().isoformat()
        }
        
        # Insert product
        await self.conn.execute(
            """
            INSERT INTO products (
                id, brand_id, sku, description, price, currency, family, active,
                form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp,
                vandal_ik10, nvr_channels, switch_ports, is_accessory, accessory_type,
                search_text, raw_json, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8,
                $9, $10, $11, $12, $13, $14,
                $15, $16, $17, $18, $19,
                $20, $21, now(), now()
            )
            """,
            product_id, brand_id, sku, description, price, currency, family, True,
            form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp,
            vandal_ik10, nvr_channels, switch_ports, is_accessory, accessory_type,
            search_text, json.dumps(raw_json)
        )
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Safely parse integer from various formats."""
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, str):
            # Extract numbers from strings like "30m" or "16 channels"
            import re
            numbers = re.findall(r'\d+', value)
            if numbers:
                return int(numbers[0])
        
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_float(self, value: Any) -> Optional[float]:
        """Safely parse float from various formats."""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Extract numbers from strings like "5MP" or "4K"
            import re
            numbers = re.findall(r'[\d.]+', value)
            if numbers:
                try:
                    return float(numbers[0])
                except ValueError:
                    pass
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
