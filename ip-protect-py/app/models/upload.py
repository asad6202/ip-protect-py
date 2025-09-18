from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ProductUpload(Base):
    __tablename__ = "product_uploads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, server_default=text("gen_random_uuid()")
    )
    brand_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True
    )
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="'uploaded'"
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    brand = relationship("Brand", back_populates="uploads")
    import_batches = relationship("ProductImportBatch", back_populates="upload")

    def __repr__(self) -> str:
        return f"<ProductUpload(id={self.id}, original_name={self.original_name}, status={self.status})>"


class ProductImportBatch(Base):
    __tablename__ = "product_import_batches"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, server_default=text("gen_random_uuid()")
    )
    brand_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True
    )
    upload_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("product_uploads.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # Relationships
    brand = relationship("Brand", back_populates="import_batches")
    upload = relationship("ProductUpload", back_populates="import_batches")

    def __repr__(self) -> str:
        return f"<ProductImportBatch(id={self.id}, brand_id={self.brand_id})>"
