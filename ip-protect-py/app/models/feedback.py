from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class QuoteFeedback(Base):
    __tablename__ = "quote_feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, server_default=text("gen_random_uuid()")
    )
    quote_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    labels: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    corrections: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # Relationships
    quote = relationship("Quote", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<QuoteFeedback(id={self.id}, quote_id={self.quote_id}, rating={self.rating})>"
