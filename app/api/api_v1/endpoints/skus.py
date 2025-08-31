from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
from datetime import datetime

from app.db.database import get_db
from app.models.sku import SKU
from app.models.variant import Variant
from app.models.product import Product
from app.models.partner import Partner
from app.schemas.sku import SKUCreate, SKUUpdate, SKUResponse
from app.crud.base import CRUDBase

router = APIRouter()


class CRUDSKU(CRUDBase[SKU, SKUCreate, SKUUpdate]):
    async def create_with_variants(
        self,
        db: AsyncSession,
        *,
        obj_in: SKUCreate
    ) -> SKU:
        # Generate SKU code if not provided
        if not obj_in.sku_code:
            # Get product and variants to generate SKU code
            product_result = await db.execute(
                select(Product).where(Product.id == obj_in.product_id)
            )
            product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            # Get variants
            variants_result = await db.execute(
                select(Variant).where(Variant.id.in_(obj_in.variant_ids))
            )
            variants = variants_result.scalars().all()
            
            if len(variants) != len(obj_in.variant_ids):
                raise HTTPException(status_code=404, detail="One or more variants not found")
            
            # Verify all variants belong to the same product
            for variant in variants:
                if variant.product_id != obj_in.product_id:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Variant {variant.id} does not belong to product {obj_in.product_id}"
                    )
            
            # Generate SKU code: PRODUCT-VARIANT1-VARIANT2-...
            variant_codes = [f"{v.type.upper()}-{v.value.upper()}" for v in sorted(variants, key=lambda x: x.type)]
            sku_code = f"{product.name.upper().replace(' ', '-')}-{'-'.join(variant_codes)}"
            obj_in.sku_code = sku_code
        
        # Create SKU
        obj_data = obj_in.dict(exclude={"variant_ids"})
        db_obj = SKU(**obj_data)
        db.add(db_obj)
        await db.flush()
        
        # Add variants to SKU
        variants_result = await db.execute(
            select(Variant).where(Variant.id.in_(obj_in.variant_ids))
        )
        variants = variants_result.scalars().all()
        
        for variant in variants:
            db_obj.variants.append(variant)
        
        # Calculate and set selling price and final price using pricing service
        if db_obj.base_price:
            from app.services.pricing_service import PricingService
            pricing_service = PricingService(db)
            
            # Calculate selling price for partners
            calculated_price = await pricing_service.calculate_price_for_product(
                str(db_obj.product_id),
                float(db_obj.base_price),
                quantity=1
            )
            db_obj.price = calculated_price
            
            # Calculate final price using partner's pricing formula
            final_price = await pricing_service.calculate_final_price_with_formula(
                db_obj.base_price,
                str(db_obj.product.partner_id) if db_obj.product else None
            )
            db_obj.final_price = final_price
        
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_with_details(
        self,
        db: AsyncSession,
        *,
        sku_id: uuid.UUID
    ) -> Optional[SKU]:
        result = await db.execute(
            select(SKU)
            .options(
                selectinload(SKU.product).selectinload(Product.partner),
                selectinload(SKU.variants)
            )
            .where(SKU.id == sku_id)
        )
        return result.scalar_one_or_none()

    async def get_multi_with_details(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        product_id: Optional[uuid.UUID] = None,
        low_stock_threshold: int = 10
    ) -> List[SKU]:
        query = select(SKU).options(
            selectinload(SKU.product).selectinload(Product.partner),
            selectinload(SKU.variants)
        )
        
        if product_id:
            query = query.where(SKU.product_id == product_id)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()


sku_crud = CRUDSKU(SKU)


@router.get("/", response_model=List[SKUResponse])
async def get_skus(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    product_id: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """
    Get SKUs with filtering options.
    
    - **skip**: Number of SKUs to skip (pagination)
    - **limit**: Maximum number of SKUs to return
    - **product_id**: Filter by specific product
    - **low_stock_only**: Show only SKUs with low stock
    """
    product_uuid = None
    if product_id:
        try:
            product_uuid = uuid.UUID(product_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid product_id format")
    
    skus = await sku_crud.get_multi_with_details(
        db, 
        skip=skip, 
        limit=limit, 
        product_id=product_uuid
    )
    
    # Convert to response format
    response_skus = []
    from app.services.pricing_service import PricingService
    pricing_service = PricingService(db)
    
    for sku in skus:
        # Calculate current selling price and final price
        calculated_price = None
        final_price = None
        
        if sku.base_price:
            calculated_price = await pricing_service.calculate_price_for_product(
                str(sku.product_id),
                float(sku.base_price),
                quantity=1
            )
            
            # Calculate final price using partner's pricing formula
            if sku.product and sku.product.partner_id:
                final_price = await pricing_service.calculate_final_price_with_formula(
                    sku.base_price,
                    str(sku.product.partner_id)
                )
        
        response_sku = SKUResponse(
            id=sku.id,
            product_id=sku.product_id,
            variant_ids=[v.id for v in sku.variants],
            sku_code=sku.sku_code,
            quantity=sku.quantity,
            price=sku.price,
            cost_price=sku.cost_price,
            base_price=sku.base_price,
            final_price=final_price or sku.final_price,
            inventory=sku.inventory,
            size=sku.size,
            color=sku.color,
            weight=sku.weight,
            dimensions=sku.dimensions,
            is_active=sku.is_active,
            created_at=sku.created_at,
            updated_at=sku.updated_at,
            product_name=sku.product.name if sku.product else None,
            partner_name=sku.product.partner.name if sku.product and sku.product.partner else None,
            variants=[
                {"id": v.id, "type": v.type, "value": v.value}
                for v in sku.variants
            ],
            low_stock=sku.quantity < 10,  # Consider SKUs with quantity < 10 as low stock
            calculated_selling_price=calculated_price
        )
        
        if low_stock_only:
            if response_sku.low_stock:
                response_skus.append(response_sku)
        else:
            response_skus.append(response_sku)
    
    return response_skus


@router.get("/{sku_id}", response_model=SKUResponse)
async def get_sku(
    sku_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific SKU by ID."""
    try:
        sku_uuid = uuid.UUID(sku_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid SKU ID format")
    
    sku = await sku_crud.get_with_details(db, sku_id=sku_uuid)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    return SKUResponse(
        id=sku.id,
        product_id=sku.product_id,
        sku_code=sku.sku_code,
        size=sku.size,
        color=sku.color,
        base_price=sku.base_price,
        final_price=sku.final_price,
        inventory=sku.inventory,
        quantity=sku.quantity,
        price=sku.price,
        cost_price=sku.cost_price,
        weight=sku.weight,
        dimensions=sku.dimensions,
        is_active=sku.is_active,
        created_at=sku.created_at,
        updated_at=sku.updated_at,
        product_name=sku.product.name if sku.product else None,
        partner_name=sku.product.partner.name if sku.product and sku.product.partner else None,
        variants=[],
        low_stock=(sku.inventory or sku.quantity or 0) < 10
    )


@router.post("/", response_model=SKUResponse)
async def create_sku(
    sku: SKUCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new SKU.
    
    **Request Body Example:**
    ```json
    {
        "product_id": "123e4567-e89b-12d3-a456-426614174000",
        "size": "L",
        "color": "آبی",
        "base_price": 100000,
        "final_price": 150000,
        "inventory": 10
    }
    ```
    
    The SKU code will be auto-generated if not provided.
    """
    try:
        # Get product first to validate and generate SKU code
        product_result = await db.execute(
            select(Product).where(Product.id == sku.product_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Generate SKU code if not provided
        sku_code = sku.sku_code
        if not sku_code:
            size_part = f"-{sku.size}" if sku.size else ""
            color_part = f"-{sku.color}" if sku.color else ""
            timestamp = int(datetime.now().timestamp())
            sku_code = f"{product.name.upper().replace(' ', '-')}{size_part}{color_part}-{timestamp}"
        
        # Calculate final price if not provided
        final_price = sku.final_price
        if not final_price and sku.base_price and product.partner_id:
            # Get partner pricing rules
            partner_result = await db.execute(
                select(Partner).where(Partner.id == product.partner_id)
            )
            partner = partner_result.scalar_one_or_none()
            if partner:
                # Apply profit percentage
                base = float(sku.base_price)
                profit_pct = float(partner.profit_percentage or 0)
                final_price = base * (1 + profit_pct / 100)
                # Add fixed amount
                fixed_amt = float(partner.fixed_amount or 0)
                final_price += fixed_amt
                # Apply price ending digit rounding
                ending = int(partner.price_ending_digit or 0) if partner.price_ending_digit else 0
                if ending > 0:
                    remainder = final_price % ending
                    if remainder != 0:
                        final_price = final_price - remainder + ending
                final_price = round(final_price)
        
        # Simple creation without variant support for now
        # Create SKU object directly
        db_obj = SKU(
            product_id=sku.product_id,
            sku_code=sku_code,
            size=sku.size,
            color=sku.color,
            base_price=sku.base_price,
            final_price=final_price if final_price else sku.final_price,
            inventory=sku.inventory,
            link=sku.link,
            quantity=sku.quantity or sku.inventory or 0,
            price=sku.price,
            cost_price=sku.cost_price,
            weight=sku.weight,
            dimensions=sku.dimensions,
            is_active=sku.is_active if sku.is_active is not None else True
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        return await get_sku(str(db_obj.id), db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{sku_id}", response_model=SKUResponse)
async def update_sku(
    sku_id: str,
    sku_update: SKUUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a SKU."""
    try:
        sku_uuid = uuid.UUID(sku_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid SKU ID format")
    
    db_sku = await sku_crud.get(db, id=sku_uuid)
    if not db_sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    # Skip variant handling for now (keeping code for future use)
    # Just update the SKU fields directly
    updated_sku = await sku_crud.update(db, db_obj=db_sku, obj_in=sku_update)
    return await get_sku(str(updated_sku.id), db)


@router.delete("/{sku_id}")
async def delete_sku(
    sku_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a SKU."""
    try:
        sku_uuid = uuid.UUID(sku_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid SKU ID format")
    
    db_sku = await sku_crud.get(db, id=sku_uuid)
    if not db_sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    await sku_crud.remove(db, id=sku_uuid)
    return {"detail": "SKU deleted successfully"}


@router.get("/product/{product_id}", response_model=List[SKUResponse])
async def get_skus_by_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all SKUs for a specific product."""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    skus = await sku_crud.get_multi_with_details(
        db, 
        skip=0, 
        limit=100, 
        product_id=product_uuid
    )
    
    # Convert to response format
    response_skus = []
    from app.services.pricing_service import PricingService
    pricing_service = PricingService(db)
    
    for sku in skus:
        # Calculate current selling price and final price
        calculated_price = None
        final_price = None
        
        if sku.base_price:
            calculated_price = await pricing_service.calculate_price_for_product(
                str(sku.product_id),
                float(sku.base_price),
                quantity=1
            )
            
            # Calculate final price using partner's pricing formula
            if sku.product and sku.product.partner_id:
                final_price = await pricing_service.calculate_final_price_with_formula(
                    sku.base_price,
                    str(sku.product.partner_id)
                )
        
        response_sku = SKUResponse(
            id=sku.id,
            product_id=sku.product_id,
            variant_ids=[v.id for v in sku.variants],
            sku_code=sku.sku_code,
            size=sku.size,
            color=sku.color,
            base_price=sku.base_price,
            final_price=final_price or sku.final_price,
            inventory=sku.inventory,
            quantity=sku.quantity,
            price=sku.price,
            cost_price=sku.cost_price,
            weight=sku.weight,
            dimensions=sku.dimensions,
            is_active=sku.is_active,
            created_at=sku.created_at,
            updated_at=sku.updated_at,
            product_name=sku.product.name if sku.product else None,
            partner_name=sku.product.partner.name if sku.product and sku.product.partner else None,
            variants=[
                {"id": v.id, "type": v.type, "value": v.value}
                for v in sku.variants
            ],
            low_stock=(sku.inventory or sku.quantity or 0) < 10,
            calculated_selling_price=calculated_price
        )
        response_skus.append(response_sku)
    
    return response_skus


@router.post("/calculate-price")
async def calculate_sku_price(
    base_price: float,
    partner_id: str,
    quantity: int = 1,
    db: AsyncSession = Depends(get_db)
):
    """Calculate final price for a SKU based on partner's pricing formula."""
    try:
        partner_uuid = uuid.UUID(partner_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid partner ID format")
    
    from app.services.pricing_service import PricingService
    from decimal import Decimal
    
    pricing_service = PricingService(db)
    final_price = await pricing_service.calculate_final_price_with_formula(
        Decimal(str(base_price)),
        partner_id,
        quantity
    )
    
    return {
        "base_price": base_price,
        "final_price": float(final_price),
        "profit_margin": float(((final_price - Decimal(str(base_price))) / Decimal(str(base_price))) * 100) if base_price > 0 else 0,
        "quantity": quantity
    }


@router.post("/bulk-create")
async def create_bulk_skus(
    product_id: str,
    skus_data: List[dict],
    db: AsyncSession = Depends(get_db)
):
    """Create multiple SKUs for a product at once."""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    # Verify product exists
    product_result = await db.execute(
        select(Product).where(Product.id == product_uuid)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    created_skus = []
    for i, sku_data in enumerate(skus_data):
        try:
            # Generate SKU code if not provided
            sku_code = sku_data.get('sku_code') or f"{product.name.upper().replace(' ', '-')}-{i+1}-{sku_data.get('size', '')}-{sku_data.get('color', '')}"
            
            # Create SKU with new fields
            sku = SKU(
                product_id=product_uuid,
                sku_code=sku_code,
                size=sku_data.get('size'),
                color=sku_data.get('color'),
                base_price=sku_data.get('base_price'),
                final_price=sku_data.get('final_price'),
                inventory=sku_data.get('inventory', 0),
                quantity=sku_data.get('inventory', 0),  # Keep for compatibility
                cost_price=sku_data.get('base_price'),  # Alias
                price=sku_data.get('final_price'),  # Alias
                is_active=True
            )
            
            db.add(sku)
            await db.flush()
            await db.refresh(sku)
            created_skus.append(sku)
            
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Error creating SKU {i+1}: {str(e)}")
    
    await db.commit()
    
    # Return created SKUs
    response_skus = []
    for sku in created_skus:
        response_skus.append({
            "id": str(sku.id),
            "sku_code": sku.sku_code,
            "size": sku.size,
            "color": sku.color,
            "base_price": float(sku.base_price) if sku.base_price else None,
            "final_price": float(sku.final_price) if sku.final_price else None,
            "inventory": sku.inventory,
            "is_active": sku.is_active
        })
    
    return {
        "message": f"Created {len(created_skus)} SKUs successfully",
        "skus": response_skus
    }