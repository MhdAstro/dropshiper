from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.db.database import get_db
from app.models.partner import Partner
from app.models.product import Product
from app.schemas.partner import PartnerCreate, PartnerUpdate, PartnerResponse, PartnerDetailResponse
from app.crud.base import CRUDBase
from app.crud.settlement import settlement_crud
from app.core.security import get_current_user

router = APIRouter()

# CRUD instance
partner_crud = CRUDBase[Partner, PartnerCreate, PartnerUpdate](Partner)


async def calculate_partner_statistics(db: AsyncSession, partner_id: uuid.UUID):
    """Calculate comprehensive statistics for a partner"""
    
    # Products count
    products_count_query = select(func.count(Product.id)).where(Product.partner_id == partner_id)
    products_count_result = await db.execute(products_count_query)
    products_count = products_count_result.scalar() or 0
    
    # Orders statistics (assuming Order model exists)
    try:
        # Total orders
        total_orders_query = select(func.count(Order.id)).where(Order.partner_id == partner_id)
        total_orders_result = await db.execute(total_orders_query)
        total_orders = total_orders_result.scalar() or 0
        
        # Pending orders (assuming status field exists)
        pending_orders_query = select(func.count(Order.id)).where(
            and_(Order.partner_id == partner_id, Order.status == 'pending')
        )
        pending_orders_result = await db.execute(pending_orders_query)
        pending_orders = pending_orders_result.scalar() or 0
        
        # Completed orders
        completed_orders_query = select(func.count(Order.id)).where(
            and_(Order.partner_id == partner_id, Order.status == 'completed')
        )
        completed_orders_result = await db.execute(completed_orders_query)
        completed_orders = completed_orders_result.scalar() or 0
        
        # Total order value
        total_value_query = select(func.sum(Order.total_amount)).where(Order.partner_id == partner_id)
        total_value_result = await db.execute(total_value_query)
        total_order_value = total_value_result.scalar() or Decimal('0')
        
        # Average order value
        average_order_value = total_order_value / total_orders if total_orders > 0 else Decimal('0')
        
        # Last order date
        last_order_query = select(func.max(Order.created_at)).where(Order.partner_id == partner_id)
        last_order_result = await db.execute(last_order_query)
        last_order_date = last_order_result.scalar()
        
    except Exception:
        # Order model might not exist yet, set defaults
        total_orders = pending_orders = completed_orders = 0
        total_order_value = average_order_value = Decimal('0')
        last_order_date = None
    
    return {
        'products_count': products_count,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_order_value': total_order_value,
        'average_order_value': average_order_value,
        'last_order_date': last_order_date
    }


@router.get("/", response_model=List[PartnerResponse])
async def get_partners(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    partner_type: Optional[str] = Query(None, description="Filter by partner type"),
    search: Optional[str] = Query(None, description="Search by partner name"),
    active_only: bool = Query(True, description="Show only active partners"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get partners with comprehensive filtering options.
    
    - **skip**: Number of partners to skip (pagination)
    - **limit**: Maximum number of partners to return
    - **partner_type**: Filter by partner type (supplier, distributor, retailer, manufacturer, wholesaler)
    - **search**: Search by partner name (case-insensitive)
    - **active_only**: Show only active partners
    
    Returns list of partners with basic statistics including:
    - Products count
    - Total orders and pending orders
    - Current debt and total order value
    """
    query = select(Partner)
    
    # Filter by current user
    query = query.where(Partner.user_id == current_user)
    
    # Apply filters
    if partner_type:
        query = query.where(Partner.type == partner_type.lower())
    
    if search:
        query = query.where(Partner.name.ilike(f"%{search}%"))
    
    if active_only:
        query = query.where(Partner.is_active == True)
    
    query = query.offset(skip).limit(limit).order_by(Partner.created_at.desc())
    result = await db.execute(query)
    partners = result.scalars().all()
    
    # Calculate statistics for each partner
    response_partners = []
    for partner in partners:
        stats = await calculate_partner_statistics(db, partner.id)
        
        response_partners.append(
            PartnerResponse(
                id=partner.id,
                name=partner.name,
                type=partner.type,
                contact_email=partner.contact_email,
                contact_phone=partner.contact_phone,
                address=partner.address,
                description=partner.description,
                platform=partner.platform,
                platform_address=partner.platform_address,
                credit_limit=partner.credit_limit,
                payment_terms=partner.payment_terms,
                settlement_period_days=partner.settlement_period_days,
                profit_percentage=partner.profit_percentage,
                fixed_amount=partner.fixed_amount,
                price_ending_digit=partner.price_ending_digit,
                api_endpoint=partner.api_endpoint,
                api_key=partner.api_key,
                is_active=partner.is_active,
                created_at=partner.created_at,
                updated_at=partner.updated_at,
                products_count=stats['products_count'],
                total_orders=stats['total_orders'],
                pending_orders=stats['pending_orders'],
                completed_orders=stats['completed_orders'],
                total_order_value=stats['total_order_value'],
                current_debt=partner.current_debt or Decimal('0')
            )
        )
    
    return response_partners


@router.get("/{partner_id}", response_model=PartnerDetailResponse)
async def get_partner_detail(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get detailed information about a specific partner.
    
    Returns comprehensive partner information including:
    - Basic partner details
    - Financial information (credit limit, current debt, payment terms)
    - Statistics (orders, products, values)
    - Recent activity data
    """
    try:
        partner_uuid = uuid.UUID(partner_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid partner ID format")
    
    partner = await partner_crud.get(db, id=partner_uuid)
    if not partner or partner.user_id != current_user:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Calculate comprehensive statistics
    stats = await calculate_partner_statistics(db, partner_uuid)
    
    return PartnerDetailResponse(
        id=partner.id,
        name=partner.name,
        type=partner.type,
        contact_email=partner.contact_email,
        contact_phone=partner.contact_phone,
        address=partner.address,
        description=partner.description,
        platform=partner.platform,
        platform_address=partner.platform_address,
        credit_limit=partner.credit_limit or Decimal('0'),
        current_debt=partner.current_debt or Decimal('0'),
        payment_terms=partner.payment_terms,
        settlement_period_days=partner.settlement_period_days or 30,
        profit_percentage=partner.profit_percentage or Decimal('0'),
        fixed_amount=partner.fixed_amount or Decimal('0'),
        price_ending_digit=partner.price_ending_digit or 0,
        api_endpoint=partner.api_endpoint,
        api_key=partner.api_key,
        is_active=partner.is_active,
        created_at=partner.created_at,
        updated_at=partner.updated_at,
        products_count=stats['products_count'],
        total_orders=stats['total_orders'],
        pending_orders=stats['pending_orders'],
        completed_orders=stats['completed_orders'],
        total_order_value=stats['total_order_value'],
        average_order_value=stats['average_order_value'],
        last_order_date=stats['last_order_date']
    )


@router.get("/{partner_id}/summary", response_model=PartnerResponse)
async def get_partner_summary(
    partner_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get basic partner information with summary statistics."""
    try:
        partner_uuid = uuid.UUID(partner_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid partner ID format")
    
    partner = await partner_crud.get(db, id=partner_uuid)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Calculate basic statistics
    stats = await calculate_partner_statistics(db, partner_uuid)
    
    return PartnerResponse(
        id=partner.id,
        name=partner.name,
        type=partner.type,
        contact_email=partner.contact_email,
        contact_phone=partner.contact_phone,
        address=partner.address,
        description=partner.description,
        credit_limit=partner.credit_limit,
        payment_terms=partner.payment_terms,
        api_endpoint=partner.api_endpoint,
        api_key=partner.api_key,
        is_active=partner.is_active,
        created_at=partner.created_at,
        updated_at=partner.updated_at,
        products_count=stats['products_count'],
        total_orders=stats['total_orders'],
        pending_orders=stats['pending_orders'],
        completed_orders=stats['completed_orders'],
        total_order_value=stats['total_order_value'],
        current_debt=partner.current_debt or Decimal('0')
    )


@router.post("/", response_model=PartnerResponse)
async def create_partner(
    partner: PartnerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Create a new partner.
    
    **Request Body Example:**
    ```json
    {
        "name": "تامین‌کننده اصلی",
        "type": "supplier",
        "contact_email": "info@supplier.com",
        "contact_phone": "021-12345678",
        "address": "تهران، خیابان ولیعصر",
        "description": "تامین‌کننده اصلی محصولات پوشاک"
    }
    ```
    """
    # Add user_id to partner data
    partner_data = partner.dict()
    partner_data['user_id'] = current_user
    partner_obj = PartnerCreate(**partner_data)
    
    db_partner = await partner_crud.create(db, obj_in=partner_obj)
    return PartnerResponse(
        id=db_partner.id,
        name=db_partner.name,
        type=db_partner.type,
        contact_email=db_partner.contact_email,
        contact_phone=db_partner.contact_phone,
        address=db_partner.address,
        description=db_partner.description,
        platform=db_partner.platform,
        platform_address=db_partner.platform_address,
        credit_limit=db_partner.credit_limit,
        current_debt=db_partner.current_debt,
        payment_terms=db_partner.payment_terms,
        settlement_period_days=db_partner.settlement_period_days,
        profit_percentage=db_partner.profit_percentage,
        fixed_amount=db_partner.fixed_amount,
        price_ending_digit=db_partner.price_ending_digit,
        api_endpoint=db_partner.api_endpoint,
        api_key=db_partner.api_key,
        is_active=db_partner.is_active,
        created_at=db_partner.created_at,
        updated_at=db_partner.updated_at,
        products_count=0,
        total_orders=0,
        pending_orders=0,
        completed_orders=0,
        total_order_value=0
    )


@router.put("/{partner_id}", response_model=PartnerResponse)
async def update_partner(
    partner_id: str,
    partner_update: PartnerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a partner."""
    try:
        partner_uuid = uuid.UUID(partner_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid partner ID format")
    
    db_partner = await partner_crud.get(db, id=partner_uuid)
    if not db_partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    updated_partner = await partner_crud.update(db, db_obj=db_partner, obj_in=partner_update)
    
    # Count products for this partner
    count_query = select(func.count(Product.id)).where(Product.partner_id == partner_uuid)
    count_result = await db.execute(count_query)
    products_count = count_result.scalar() or 0
    
    return PartnerResponse(
        id=updated_partner.id,
        name=updated_partner.name,
        type=updated_partner.type,
        contact_email=updated_partner.contact_email,
        contact_phone=updated_partner.contact_phone,
        address=updated_partner.address,
        description=updated_partner.description,
        platform=updated_partner.platform,
        platform_address=updated_partner.platform_address,
        credit_limit=updated_partner.credit_limit,
        current_debt=updated_partner.current_debt,
        payment_terms=updated_partner.payment_terms,
        settlement_period_days=updated_partner.settlement_period_days,
        profit_percentage=updated_partner.profit_percentage,
        fixed_amount=updated_partner.fixed_amount,
        price_ending_digit=updated_partner.price_ending_digit,
        api_endpoint=updated_partner.api_endpoint,
        api_key=updated_partner.api_key,
        is_active=updated_partner.is_active,
        created_at=updated_partner.created_at,
        updated_at=updated_partner.updated_at,
        products_count=products_count,
        total_orders=0,
        pending_orders=0,
        completed_orders=0,
        total_order_value=0
    )


@router.delete("/{partner_id}")
async def delete_partner(
    partner_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a partner."""
    try:
        partner_uuid = uuid.UUID(partner_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid partner ID format")
    
    db_partner = await partner_crud.get(db, id=partner_uuid)
    if not db_partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Check if partner has products
    count_query = select(func.count(Product.id)).where(Product.partner_id == partner_uuid)
    count_result = await db.execute(count_query)
    products_count = count_result.scalar() or 0
    
    if products_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete partner with {products_count} associated products"
        )
    
    await partner_crud.remove(db, id=partner_uuid)
    return {"detail": "Partner deleted successfully"}


@router.patch("/{partner_id}/debt", response_model=PartnerResponse)
async def update_partner_debt(
    partner_id: str,
    debt_update: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Update partner's current debt.
    
    **Request Body Example:**
    ```json
    {
        "amount": 1500000,
        "operation": "add",
        "reason": "New purchase order"
    }
    ```
    
    - **amount**: Amount in Toman
    - **operation**: "add", "subtract", or "set"
    - **reason**: Reason for debt update (optional)
    """
    try:
        partner_uuid = uuid.UUID(partner_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid partner ID format")
    
    partner = await partner_crud.get(db, id=partner_uuid)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    amount = Decimal(str(debt_update.get('amount', 0)))
    operation = debt_update.get('operation', 'set').lower()
    
    if operation not in ['add', 'subtract', 'set']:
        raise HTTPException(status_code=400, detail="Operation must be 'add', 'subtract', or 'set'")
    
    current_debt = partner.current_debt or Decimal('0')
    
    if operation == 'add':
        new_debt = current_debt + amount
    elif operation == 'subtract':
        new_debt = current_debt - amount
    else:  # set
        new_debt = amount
    
    # Ensure debt doesn't go negative
    new_debt = max(new_debt, Decimal('0'))
    
    # Check credit limit
    credit_limit = partner.credit_limit or Decimal('0')
    if credit_limit > 0 and new_debt > credit_limit:
        raise HTTPException(
            status_code=400, 
            detail=f"Debt amount ({new_debt:,.0f} تومان) exceeds credit limit ({credit_limit:,.0f} تومان)"
        )
    
    # Update debt
    updated_partner = await partner_crud.update(
        db, 
        db_obj=partner, 
        obj_in={"current_debt": new_debt}
    )
    
    # Create settlement record if debt was reduced (settlement made)
    if operation == 'subtract' and amount > 0:
        try:
            await settlement_crud.create_settlement_record(
                db=db,
                partner_id=partner_uuid,
                amount=float(amount),
                previous_debt=float(current_debt),
                remaining_debt=float(new_debt),
                reason=debt_update.get('reason', 'تسویه بدهی'),
                settled_by="system"
            )
            await db.commit()  # Ensure the settlement is committed
        except Exception as e:
            print(f"Error creating settlement record: {e}")
            # Don't fail the debt update if settlement record creation fails
    
    # Calculate statistics for response
    stats = await calculate_partner_statistics(db, partner_uuid)
    
    return PartnerResponse(
        id=updated_partner.id,
        name=updated_partner.name,
        type=updated_partner.type,
        contact_email=updated_partner.contact_email,
        contact_phone=updated_partner.contact_phone,
        address=updated_partner.address,
        description=updated_partner.description,
        credit_limit=updated_partner.credit_limit,
        payment_terms=updated_partner.payment_terms,
        api_endpoint=updated_partner.api_endpoint,
        api_key=updated_partner.api_key,
        is_active=updated_partner.is_active,
        created_at=updated_partner.created_at,
        updated_at=updated_partner.updated_at,
        products_count=stats['products_count'],
        total_orders=stats['total_orders'],
        pending_orders=stats['pending_orders'],
        completed_orders=stats['completed_orders'],
        total_order_value=stats['total_order_value'],
        current_debt=updated_partner.current_debt
    )


@router.get("/statistics/overview", tags=["partners-statistics"])
async def get_partners_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    Get overview statistics for all partners.
    
    Returns:
    - Total partners count
    - Active/inactive partners
    - Partners by type
    - Total debt across all partners
    - Partners with high debt (near credit limit)
    """
    # Total partners
    total_query = select(func.count(Partner.id))
    total_result = await db.execute(total_query)
    total_partners = total_result.scalar() or 0
    
    # Active partners
    active_query = select(func.count(Partner.id)).where(Partner.is_active == True)
    active_result = await db.execute(active_query)
    active_partners = active_result.scalar() or 0
    
    # Partners by type
    type_query = select(Partner.type, func.count(Partner.id)).group_by(Partner.type)
    type_result = await db.execute(type_query)
    partners_by_type = {row[0]: row[1] for row in type_result.fetchall()}
    
    # Total debt
    debt_query = select(func.sum(Partner.current_debt)).where(Partner.current_debt.isnot(None))
    debt_result = await db.execute(debt_query)
    total_debt = debt_result.scalar() or Decimal('0')
    
    # High debt partners (debt > 80% of credit limit)
    high_debt_query = select(func.count(Partner.id)).where(
        and_(
            Partner.current_debt > (Partner.credit_limit * Decimal('0.8')),
            Partner.credit_limit > 0
        )
    )
    high_debt_result = await db.execute(high_debt_query)
    high_debt_partners = high_debt_result.scalar() or 0
    
    return {
        "total_partners": total_partners,
        "active_partners": active_partners,
        "inactive_partners": total_partners - active_partners,
        "partners_by_type": partners_by_type,
        "total_debt": total_debt,
        "high_debt_partners": high_debt_partners
    }