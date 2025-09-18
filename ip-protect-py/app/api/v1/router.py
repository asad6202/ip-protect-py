"""
API v1 router configuration.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import quote, product

api_router = APIRouter()

# Include quote endpoints
api_router.include_router(quote.router, tags=["quote"])

# Include product endpoints
api_router.include_router(product.router, tags=["product"])