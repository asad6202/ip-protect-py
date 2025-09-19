from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UploadStatus(Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued" 
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'uploaded'")
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    brand = relationship("Brand", back_populates="uploads")
    import_batches = relationship("ProductImportBatch", back_populates="upload")
    errors = relationship("ProductUploadError", back_populates="upload", cascade="all, delete-orphan")

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


class ProductUploadError(Base):
    __tablename__ = "product_upload_errors"
    __table_args__ = (
        Index("ix_product_upload_errors_upload_id", "upload_id"),
        Index("ix_product_upload_errors_upload_id_line", "upload_id", "line_number"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, server_default=text("gen_random_uuid()")
    )
    upload_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("product_uploads.id", ondelete="CASCADE"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    column_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # Relationships
    upload = relationship("ProductUpload", back_populates="errors")

    def __repr__(self) -> str:
        return f"<ProductUploadError(id={self.id}, upload_id={self.upload_id}, line_number={self.line_number})>"
