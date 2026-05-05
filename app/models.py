from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Asset types — keep as plain strings (SQLite-friendly, no enum migration pain).
ASSET_TYPE_LICENSE = "license"
ASSET_TYPE_SUPPORT = "support"
ASSET_TYPE_SSL = "ssl"
ASSET_TYPES = (ASSET_TYPE_LICENSE, ASSET_TYPE_SUPPORT, ASSET_TYPE_SSL)


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[date] = mapped_column(Date, default=date.today)
    updated_at: Mapped[date] = mapped_column(Date, default=date.today, onupdate=date.today)

    products: Mapped[list["Product"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("vendor_id", "name", name="uq_product_vendor_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[date] = mapped_column(Date, default=date.today)
    updated_at: Mapped[date] = mapped_column(Date, default=date.today, onupdate=date.today)

    vendor: Mapped[Vendor] = relationship(back_populates="products")
    assets: Mapped[list["Asset"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Asset(Base):
    """Polymorphic asset — license, support contract, or SSL certificate.

    Common fields cover all types. Type-specific fields stored in named columns
    (kept nullable so a single table fits all three asset types).
    """
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, default=ASSET_TYPE_LICENSE, index=True)
    # Display name. Called `product_name` for backwards compatibility with the
    # original License schema and templates; for SSL assets this is the cert
    # name, for Support it's the contract title.
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    responsible: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cost: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notify_days_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Optional external link to a contract / datasheet / order in SharePoint,
    # Confluence, Drive, etc. Stored verbatim; surfaced as a clickable link
    # on the asset detail and form pages.
    document_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # SSL-specific
    ssl_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ssl_issuer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Support-specific
    support_contract_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    support_sla: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[date] = mapped_column(Date, default=date.today)
    updated_at: Mapped[date] = mapped_column(Date, default=date.today, onupdate=date.today)

    product: Mapped[Optional[Product]] = relationship(back_populates="assets")


# ---- Backwards-compat alias ----
# Existing code (routers, services, tests) still imports `License`. Keep the
# name pointing to Asset so the legacy /licenses paths and tests keep working
# while the catalog UI is built out. New code should use Asset.
License = Asset


class AppSettings(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
