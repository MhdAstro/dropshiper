from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.database import get_db
from app.crud.variant import variant
from app.schemas.variant import Variant, VariantCreate, VariantUpdate, VariantResponse

router = APIRouter()


@router.get("/", response_model=List[VariantResponse])
async def get_variants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    variant_type: Optional[str] = Query(None, description="Filter by variant type"),
    db: AsyncSession = Depends(get_db)
):
    """Get all variants with filtering options"""
    if product_id and variant_type:
        variants = await variant.get_by_type(db, product_id=product_id, variant_type=variant_type)
    elif product_id:
        variants = await variant.get_by_product(db, product_id=product_id)
    else:
        variants = await variant.get_variants_with_products(db, skip=skip, limit=limit)
    
    return variants


@router.post("/", response_model=VariantResponse)
async def create_variant(
    variant_in: VariantCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new variant"""
    try:
        new_variant = await variant.create_if_not_exists(db, obj_in=variant_in)
        return new_variant
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{variant_id}", response_model=VariantResponse)
async def get_variant(
    variant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific variant by ID"""
    db_variant = await variant.get_with_product(db, variant_id=variant_id)
    if not db_variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    return db_variant


@router.put("/{variant_id}", response_model=VariantResponse)
async def update_variant(
    variant_id: str,
    variant_update: VariantUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a variant"""
    db_variant = await variant.get(db, id=variant_id)
    if not db_variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    updated_variant = await variant.update(db, db_obj=db_variant, obj_in=variant_update)
    return updated_variant


@router.delete("/{variant_id}")
async def delete_variant(
    variant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a variant"""
    db_variant = await variant.remove(db, id=variant_id)
    if not db_variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    return {"message": "Variant deleted successfully"}


@router.get("/product/{product_id}/types", response_model=List[str])
async def get_variant_types_for_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all variant types for a specific product"""
    variant_types = await variant.get_variant_types_for_product(db, product_id=product_id)
    return variant_types


@router.get("/product/{product_id}", response_model=List[VariantResponse])
async def get_variants_by_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all variants for a specific product"""
    variants = await variant.get_by_product(db, product_id=product_id)
    if not variants:
        raise HTTPException(status_code=404, detail="No variants found for this product")
    return variants


@router.get("/product/{product_id}/type/{variant_type}", response_model=List[VariantResponse])
async def get_variants_by_product_and_type(
    product_id: str,
    variant_type: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all variants of a specific type for a product"""
    variants = await variant.get_by_type(db, product_id=product_id, variant_type=variant_type)
    if not variants:
        raise HTTPException(
            status_code=404, 
            detail=f"No variants of type '{variant_type}' found for this product"
        )
    return variants


@router.delete("/product/{product_id}")
async def delete_variants_by_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete all variants for a specific product"""
    deleted_count = await variant.delete_by_product(db, product_id=product_id)
    return {
        "message": f"Deleted {deleted_count} variants for product",
        "deleted_count": deleted_count
    }