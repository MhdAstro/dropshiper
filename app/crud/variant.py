from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.variant import Variant
from app.models.product import Product
from app.schemas.variant import VariantCreate, VariantUpdate


class VariantCRUD(CRUDBase[Variant, VariantCreate, VariantUpdate]):
    async def get_by_product(
        self, 
        db: AsyncSession, 
        product_id: str
    ) -> List[Variant]:
        """Get all variants for a specific product"""
        stmt = (
            select(Variant)
            .where(Variant.product_id == product_id)
            .order_by(Variant.type, Variant.value)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_type(
        self, 
        db: AsyncSession, 
        product_id: str, 
        variant_type: str
    ) -> List[Variant]:
        """Get all variants of a specific type for a product"""
        stmt = (
            select(Variant)
            .where(
                Variant.product_id == product_id,
                Variant.type == variant_type.lower()
            )
            .order_by(Variant.value)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_with_product(
        self, 
        db: AsyncSession, 
        variant_id: str
    ) -> Optional[Variant]:
        """Get variant with product information"""
        stmt = (
            select(Variant)
            .options(selectinload(Variant.product))
            .where(Variant.id == variant_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_variant_types_for_product(
        self, 
        db: AsyncSession, 
        product_id: str
    ) -> List[str]:
        """Get all unique variant types for a product"""
        stmt = (
            select(Variant.type)
            .where(Variant.product_id == product_id)
            .distinct()
            .order_by(Variant.type)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def check_variant_exists(
        self, 
        db: AsyncSession, 
        product_id: str, 
        variant_type: str, 
        variant_value: str
    ) -> bool:
        """Check if a variant with the same type and value already exists for the product"""
        stmt = (
            select(Variant)
            .where(
                Variant.product_id == product_id,
                Variant.type == variant_type.lower(),
                Variant.value == variant_value
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_if_not_exists(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: VariantCreate
    ) -> Variant:
        """Create variant only if it doesn't already exist"""
        existing = await self.check_variant_exists(
            db, 
            str(obj_in.product_id), 
            obj_in.type, 
            obj_in.value
        )
        
        if existing:
            # Return existing variant
            stmt = (
                select(Variant)
                .where(
                    Variant.product_id == obj_in.product_id,
                    Variant.type == obj_in.type.lower(),
                    Variant.value == obj_in.value
                )
            )
            result = await db.execute(stmt)
            return result.scalar_one()
        
        # Create new variant
        return await self.create(db, obj_in=obj_in)

    async def get_variants_with_products(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Variant]:
        """Get variants with their product information"""
        stmt = (
            select(Variant)
            .options(selectinload(Variant.product))
            .order_by(Variant.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def delete_by_product(
        self, 
        db: AsyncSession, 
        product_id: str
    ) -> int:
        """Delete all variants for a specific product"""
        stmt = select(Variant).where(Variant.product_id == product_id)
        result = await db.execute(stmt)
        variants = result.scalars().all()
        
        count = len(variants)
        for variant in variants:
            await db.delete(variant)
        
        await db.commit()
        return count


variant = VariantCRUD(Variant)