from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    slug: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # Relationships
    products = relationship("Product", back_populates="brand")
    uploads = relationship("ProductUpload", back_populates="brand")
    import_batches = relationship("ProductImportBatch", back_populates="brand")

    def __repr__(self) -> str:
        return f"<Brand(id={self.id}, name={self.name})>"
