#!/usr/bin/env python3
"""
Backfill script to populate product embeddings using OpenAI's text-embedding-3-small model.
This script processes products in batches and updates the embedding column.
"""

import os
import sys
import asyncio
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import asyncpg

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.embeddings import get_embedding_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


class EmbeddingBackfill:
    """Handles backfilling product embeddings."""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.batch_size = 10  # Smaller batch size for testing
        
    async def get_products_needing_embeddings(self, conn: asyncpg.Connection) -> List[Dict[str, Any]]:
        """Get products that need embeddings (NULL or with changed descriptions)."""
        # First check if embedding column exists
        try:
            column_check = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'products' AND column_name = 'embedding'
                )
            """)
            
            if not column_check:
                logger.warning("Embedding column does not exist. pgvector may not be installed.")
                return []
                
        except Exception as e:
            logger.error(f"Could not check for embedding column: {e}")
            return []
        
        query = """
        SELECT sku, description, family
        FROM products 
        WHERE embedding IS NULL 
           OR description IS NOT NULL
        ORDER BY sku
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    
    async def update_embeddings_batch(self, conn: asyncpg.Connection, 
                                    products: List[Dict[str, Any]], 
                                    embeddings: List[List[float]]) -> int:
        """Update embeddings for a batch of products."""
        if not products or not embeddings:
            return 0
            
        # Prepare the update query
        update_query = """
        UPDATE products 
        SET embedding = $1::vector
        WHERE sku = $2
        """
        
        updated_count = 0
        for product, embedding in zip(products, embeddings):
            try:
                # Convert embedding list to string format for pgvector
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                await conn.execute(update_query, embedding_str, product['sku'])
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update embedding for SKU {product['sku']}: {e}")
                
        return updated_count
    
    def prepare_text_for_embedding(self, product: Dict[str, Any]) -> str:
        """Prepare product text for embedding generation."""
        parts = []
        
        if product.get('sku'):
            parts.append(product['sku'])
            
        if product.get('family'):
            parts.append(product['family'])
            
        if product.get('description'):
            parts.append(product['description'])
        
        return " ".join(parts)
    
    async def backfill_embeddings(self) -> None:
        """Main backfill process."""
        conn = None
        try:
            # Connect to database
            conn = await asyncpg.connect(self.dsn)
            logger.info("Connected to database")
            
            # Get products needing embeddings
            products = await self.get_products_needing_embeddings(conn)
            total_products = len(products)
            logger.info(f"Found {total_products} products needing embeddings")
            
            if total_products == 0:
                logger.info("No products need embeddings. Exiting.")
                return
            
            # Process in batches
            processed = 0
            failed = 0
            
            for i in range(0, total_products, self.batch_size):
                batch = products[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = (total_products + self.batch_size - 1) // self.batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} products)")
                
                try:
                    # Prepare texts for embedding
                    texts = [self.prepare_text_for_embedding(product) for product in batch]
                    
                    # Generate embeddings
                    embeddings = get_embedding_batch(texts)
                    
                    if len(embeddings) != len(batch):
                        logger.error(f"Embedding count mismatch: {len(embeddings)} vs {len(batch)}")
                        failed += len(batch)
                        continue
                    
                    # Update database
                    updated = await self.update_embeddings_batch(conn, batch, embeddings)
                    processed += updated
                    failed += len(batch) - updated
                    
                    logger.info(f"Batch {batch_num} complete: {updated} updated, {len(batch) - updated} failed")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process batch {batch_num}: {e}")
                    failed += len(batch)
            
            logger.info(f"Backfill complete: {processed} processed, {failed} failed")
            
        except Exception as e:
            logger.error(f"Backfill failed: {e}")
            raise
        finally:
            if conn:
                await conn.close()
                logger.info("Database connection closed")
    
    async def verify_embeddings(self) -> None:
        """Verify that embeddings were created successfully."""
        conn = None
        try:
            conn = await asyncpg.connect(self.dsn)
            
            # Count products with embeddings
            count_with_embeddings = await conn.fetchval(
                "SELECT COUNT(*) FROM products WHERE embedding IS NOT NULL"
            )
            
            # Count total products
            total_count = await conn.fetchval("SELECT COUNT(*) FROM products")
            
            logger.info(f"Embedding verification: {count_with_embeddings}/{total_count} products have embeddings")
            
            if count_with_embeddings == 0:
                logger.warning("No products have embeddings!")
            elif count_with_embeddings < total_count:
                logger.warning(f"Only {count_with_embeddings}/{total_count} products have embeddings")
            else:
                logger.info("All products have embeddings!")
                
        except Exception as e:
            logger.error(f"Verification failed: {e}")
        finally:
            if conn:
                await conn.close()


async def main():
    """Main entry point."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL environment variable is required")
        return
    
    backfill = EmbeddingBackfill(dsn)
    
    try:
        await backfill.backfill_embeddings()
        await backfill.verify_embeddings()
    except Exception as e:
        logger.error(f"Backfill process failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
