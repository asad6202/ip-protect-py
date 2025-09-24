from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_intent: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="'draft'"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # Relationships
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")
    feedback = relationship("QuoteFeedback", back_populates="quote", cascade="all, delete-orphan")
    rule_executions = relationship("RuleExecution", back_populates="quote", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Quote(id={self.id}, status={self.status}, total_amount={self.total_amount})>"


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, server_default=text("gen_random_uuid()")
    )
    quote_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    sku: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    item_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # Relationships
    quote = relationship("Quote", back_populates="items")
    product = relationship("Product", back_populates="quote_items")

    def __repr__(self) -> str:
        return f"<QuoteItem(id={self.id}, sku={self.sku}, quantity={self.quantity})>"
