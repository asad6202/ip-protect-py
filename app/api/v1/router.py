"""
API v1 router configuration.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import quote, product, upload, dashboard, rule, nlp_rules, item_feedback

api_router = APIRouter()

# Include dashboard endpoints
api_router.include_router(dashboard.router, tags=["dashboard"])

# Include quote endpoints
api_router.include_router(quote.router, tags=["quote"])

# Include product endpoints
api_router.include_router(product.router, tags=["product"])

# Include upload endpoints
api_router.include_router(upload.router, tags=["upload"])

# Include rule endpoints
api_router.include_router(rule.router, tags=["rule"])

# Include NLP rule endpoints
api_router.include_router(nlp_rules.router, tags=["nlp-rules"])

# Include item feedback endpoints
api_router.include_router(item_feedback.router, tags=["item-feedback"])