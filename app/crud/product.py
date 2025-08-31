from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.product import Product
from app.models.partner import Partner
from app.models.variant import Variant
from app.models.sku import SKU
from app.schemas.product import ProductCreate, ProductUpdate


class ProductCRUD(CRUDBase[Product, ProductCreate, ProductUpdate]):
    async def get_with_details(
        self, 
        db: AsyncSession, 
        product_id: str
    ) -> Optional[Product]:
        """Get product with partner, variants, and SKUs"""
        stmt = (
            select(Product)
            .options(
                selectinload(Product.partner),
                selectinload(Product.variants),
                selectinload(Product.skus)
            )
            .where(Product.id == product_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_partner(
        self, 
        db: AsyncSession, 
        partner_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Get all products from a specific partner"""
        stmt = (
            select(Product)
            .options(selectinload(Product.partner))
            .where(Product.partner_id == partner_id)
            .order_by(Product.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_category(
        self, 
        db: AsyncSession, 
        category: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Get all products in a specific category"""
        stmt = (
            select(Product)
            .options(selectinload(Product.partner))
            .where(Product.category == category)
            .order_by(Product.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def search_products(
        self, 
        db: AsyncSession, 
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Search products by name or description"""
        stmt = (
            select(Product)
            .options(selectinload(Product.partner))
            .where(
                Product.name.ilike(f"%{search_term}%") |
                Product.description.ilike(f"%{search_term}%")
            )
            .order_by(Product.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_products_with_low_stock(
        self, 
        db: AsyncSession, 
        threshold: int = 10
    ) -> List[Product]:
        """Get products that have SKUs with low stock"""
        stmt = (
            select(Product)
            .join(SKU, Product.id == SKU.product_id)
            .options(selectinload(Product.partner))
            .where(SKU.quantity <= threshold)
            .distinct()
            .order_by(Product.name)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def count_by_partner(
        self, 
        db: AsyncSession, 
        partner_id: str
    ) -> int:
        """Count products from a specific partner"""
        stmt = select(func.count(Product.id)).where(Product.partner_id == partner_id)
        result = await db.execute(stmt)
        return result.scalar()

    async def get_categories(self, db: AsyncSession) -> List[str]:
        """Get all unique product categories"""
        stmt = (
            select(Product.category)
            .where(Product.category.is_not(None))
            .distinct()
            .order_by(Product.category)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


product = ProductCRUD(Product)