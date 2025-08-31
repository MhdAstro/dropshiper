import pytest
from uuid import uuid4

from app.services.inventory_update_service import InventoryUpdateService
from app.models.partner import Partner
from app.models.product import Product
from app.models.sku import SKU
from app.models.platform import Platform
from app.models.source_platform import SourcePlatform


@pytest.mark.asyncio
async def test_manual_inventory_update(db_session):
    """Test manual inventory update"""
    
    # Create test data
    partner = Partner(
        name="Test Supplier",
        type="supplier",
        contact_email="test@supplier.com"
    )
    db_session.add(partner)
    await db_session.flush()

    product = Product(
        name="Test Product",
        partner_id=partner.id,
        base_price=100.00
    )
    db_session.add(product)
    await db_session.flush()

    sku = SKU(
        product_id=product.id,
        sku_code="TEST-SKU-001",
        quantity=50,
        price=120.00
    )
    db_session.add(sku)
    await db_session.commit()

    # Test manual inventory update
    service = InventoryUpdateService(db_session)
    
    result = await service.manual_inventory_update(
        str(sku.id),
        75,
        "Restocked from warehouse",
        str(uuid4())
    )

    assert result["new_quantity"] == 75
    assert result["old_quantity"] == 50
    
    # Verify SKU was updated
    await db_session.refresh(sku)
    assert sku.quantity == 75


@pytest.mark.asyncio
async def test_get_low_stock_items(db_session):
    """Test getting low stock items"""
    
    # Create test data
    partner = Partner(
        name="Test Supplier",
        type="supplier"
    )
    db_session.add(partner)
    await db_session.flush()

    product = Product(
        name="Test Product",
        partner_id=partner.id
    )
    db_session.add(product)
    await db_session.flush()

    # Create SKUs with different stock levels
    low_stock_sku = SKU(
        product_id=product.id,
        sku_code="LOW-STOCK-001",
        quantity=5,
        price=100.00
    )
    
    high_stock_sku = SKU(
        product_id=product.id,
        sku_code="HIGH-STOCK-001",
        quantity=50,
        price=100.00
    )
    
    db_session.add_all([low_stock_sku, high_stock_sku])
    await db_session.commit()

    # Test low stock detection
    service = InventoryUpdateService(db_session)
    
    low_stock_items = await service.get_low_stock_items(threshold=10)
    
    assert len(low_stock_items) == 1
    assert low_stock_items[0]["sku_code"] == "LOW-STOCK-001"
    assert low_stock_items[0]["current_quantity"] == 5


@pytest.mark.asyncio
async def test_process_order_inventory_update(db_session):
    """Test inventory update when order is placed"""
    
    # Create test data
    partner = Partner(name="Test Supplier", type="supplier")
    db_session.add(partner)
    await db_session.flush()

    product = Product(name="Test Product", partner_id=partner.id)
    db_session.add(product)
    await db_session.flush()

    sku = SKU(
        product_id=product.id,
        sku_code="ORDER-TEST-001",
        quantity=100,
        price=50.00
    )
    db_session.add(sku)
    await db_session.commit()

    # Test order inventory update
    service = InventoryUpdateService(db_session)
    
    order_items = [
        {
            "sku_id": str(sku.id),
            "quantity": 25
        }
    ]
    
    result = await service.process_order_inventory_update(order_items)
    
    assert result["updated"] == 1
    assert len(result["errors"]) == 0
    assert len(result["insufficient_stock"]) == 0
    
    # Verify inventory was reduced
    await db_session.refresh(sku)
    assert sku.quantity == 75


@pytest.mark.asyncio
async def test_insufficient_stock_order(db_session):
    """Test order with insufficient stock"""
    
    # Create test data
    partner = Partner(name="Test Supplier", type="supplier")
    db_session.add(partner)
    await db_session.flush()

    product = Product(name="Test Product", partner_id=partner.id)
    db_session.add(product)
    await db_session.flush()

    sku = SKU(
        product_id=product.id,
        sku_code="INSUFFICIENT-001",
        quantity=10,
        price=50.00
    )
    db_session.add(sku)
    await db_session.commit()

    # Test order with insufficient stock
    service = InventoryUpdateService(db_session)
    
    order_items = [
        {
            "sku_id": str(sku.id),
            "quantity": 15  # More than available
        }
    ]
    
    result = await service.process_order_inventory_update(order_items)
    
    assert result["updated"] == 0
    assert len(result["insufficient_stock"]) == 1
    assert result["insufficient_stock"][0]["available"] == 10
    assert result["insufficient_stock"][0]["requested"] == 15
    
    # Verify inventory was not changed
    await db_session.refresh(sku)
    assert sku.quantity == 10