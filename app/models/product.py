from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, server_default=text("gen_random_uuid()")
    )
    brand_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True
    )
    
    # Raw upload fields (required)
    sku: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    family: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    
    # Normalized attributes (nullable)
    form_factor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outdoor: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    poe: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    poe_plus: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ir_range_m: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resolution_mp: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    vandal_ik10: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    nvr_channels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    switch_ports: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_accessory: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    accessory_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Search helpers
    search_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ts: Mapped[Optional[TSVECTOR]] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', coalesce(search_text, ''))", persisted=True),
        nullable=True
    )
    raw_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # Relationships
    brand = relationship("Brand", back_populates="products")
    embeddings = relationship("ProductEmbedding", back_populates="product", uselist=False)
    quote_items = relationship("QuoteItem", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, sku={self.sku}, family={self.family})>"


class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"

    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[Optional[list]] = mapped_column(String, nullable=True)  # VECTOR(1536)

    # Relationships
    product = relationship("Product", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<ProductEmbedding(product_id={self.product_id})>"
