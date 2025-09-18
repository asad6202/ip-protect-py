from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class PromptRun(Base):
    __tablename__ = "prompt_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, server_default=text("gen_random_uuid()")
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_intent: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    rules_applied: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    result_quote_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("quotes.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # Relationships
    result_quote = relationship("Quote")

    def __repr__(self) -> str:
        return f"<PromptRun(id={self.id}, result_quote_id={self.result_quote_id})>"
