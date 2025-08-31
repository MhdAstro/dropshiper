from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.db.database import get_db
from app.crud.product import product
from app.schemas.product import Product, ProductCreate, ProductUpdate, ProductResponse, BatchUpdateProduct, BatchUpdateResponse
from app.services.pricing_service import PricingService
from app.core.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    partner_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all products with filtering options"""
    filters = {}
    if partner_id:
        filters["partner_id"] = partner_id
    if category:
        filters["category"] = category
    if is_active is not None:
        filters["is_active"] = is_active
    
    products = await product.get_multi(db, skip=skip, limit=limit, filters=filters)
    return products


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new product (partner_id is required)"""
    try:
        new_product = await product.create(db, obj_in=product_in)
        
        # Update SKU final prices after product creation
        if new_product and new_product.id:
            pricing_service = PricingService(db)
            await pricing_service.update_sku_final_prices(str(new_product.id))
        
        return new_product
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific product by ID"""
    db_product = await product.get(db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a product"""
    db_product = await product.get(db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated_product = await product.update(db, db_obj=db_product, obj_in=product_update)
    
    # Update SKU final prices after product update
    if updated_product and updated_product.id:
        pricing_service = PricingService(db)
        await pricing_service.update_sku_final_prices(str(updated_product.id))
    
    return updated_product


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a product"""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    db_product = await product.remove(db, id=product_uuid)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted successfully"}


@router.put("/batch", response_model=BatchUpdateResponse)
async def batch_update_products(
    batch_update: BatchUpdateProduct,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update multiple products at once"""
    updated_count = 0
    failed_ids = []
    errors = []
    
    # Validate that we have IDs to update
    if not batch_update.ids:
        return BatchUpdateResponse(
            updated_count=0,
            failed_ids=[],
            errors=["No product IDs provided"]
        )
    
    # Validate that we have data to update
    update_data_dict = batch_update.update_data.model_dump(exclude_unset=True)
    if not update_data_dict:
        return BatchUpdateResponse(
            updated_count=0,
            failed_ids=[],
            errors=["No update data provided"]
        )
    
    pricing_service = PricingService(db)
    
    for product_id in batch_update.ids:
        try:
            # Get the product and check if it belongs to the current user
            db_product = await product.get(db, id=product_id)
            if not db_product:
                failed_ids.append(product_id)
                errors.append(f"Product {product_id} not found")
                continue
            
            # Check if the product belongs to the current user (via partner)
            from sqlalchemy import select
            from app.models.partner import Partner
            partner_query = select(Partner).where(Partner.id == db_product.partner_id)
            partner_result = await db.execute(partner_query)
            partner = partner_result.scalar_one_or_none()
            
            if not partner or partner.user_id != current_user:
                failed_ids.append(product_id)
                errors.append(f"Product {product_id} not accessible")
                continue
            
            # Update the product
            updated_product = await product.update(db, db_obj=db_product, obj_in=batch_update.update_data)
            
            if updated_product:
                # Update SKU final prices if the product was successfully updated
                await pricing_service.update_sku_final_prices(str(updated_product.id))
                updated_count += 1
            else:
                failed_ids.append(product_id)
                errors.append(f"Failed to update product {product_id}")
                
        except Exception as e:
            failed_ids.append(product_id)
            errors.append(f"Error updating product {product_id}: {str(e)}")
    
    return BatchUpdateResponse(
        updated_count=updated_count,
        failed_ids=failed_ids,
        errors=errors
    )