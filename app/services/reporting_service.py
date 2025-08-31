from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.models.sku import SKU
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.inventory_update import InventoryUpdate
from app.models.sync_log import SyncLog
from app.models.partner import Partner
from app.models.platform import Platform


class ReportingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_inventory_summary(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get inventory summary report"""
        
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)

        # Total products and SKUs
        total_products_stmt = select(func.count(Product.id)).where(Product.is_active == True)
        total_skus_stmt = select(func.count(SKU.id)).where(SKU.is_active == True)
        
        total_products_result = await self.db.execute(total_products_stmt)
        total_skus_result = await self.db.execute(total_skus_stmt)
        
        total_products = total_products_result.scalar()
        total_skus = total_skus_result.scalar()

        # Total inventory value
        inventory_value_stmt = select(
            func.sum(SKU.quantity * SKU.price)
        ).where(
            and_(SKU.is_active == True, SKU.price.is_not(None))
        )
        
        inventory_value_result = await self.db.execute(inventory_value_stmt)
        total_inventory_value = inventory_value_result.scalar() or 0

        # Low stock items
        low_stock_stmt = select(func.count(SKU.id)).where(
            and_(SKU.is_active == True, SKU.quantity <= 10)
        )
        low_stock_result = await self.db.execute(low_stock_stmt)
        low_stock_count = low_stock_result.scalar()

        # Out of stock items
        out_of_stock_stmt = select(func.count(SKU.id)).where(
            and_(SKU.is_active == True, SKU.quantity <= 0)
        )
        out_of_stock_result = await self.db.execute(out_of_stock_stmt)
        out_of_stock_count = out_of_stock_result.scalar()

        # Recent inventory updates
        recent_updates_stmt = (
            select(InventoryUpdate)
            .where(
                and_(
                    InventoryUpdate.created_at >= date_from,
                    InventoryUpdate.created_at <= date_to
                )
            )
            .order_by(desc(InventoryUpdate.created_at))
            .limit(10)
        )
        
        recent_updates_result = await self.db.execute(recent_updates_stmt)
        recent_updates = recent_updates_result.scalars().all()

        return {
            "summary": {
                "total_products": total_products,
                "total_skus": total_skus,
                "total_inventory_value": float(total_inventory_value),
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count
            },
            "recent_updates": [
                {
                    "id": str(update.id),
                    "sku_id": str(update.sku_id),
                    "old_quantity": update.old_quantity,
                    "new_quantity": update.new_quantity,
                    "update_type": update.update_type,
                    "created_at": update.created_at.isoformat()
                }
                for update in recent_updates
            ],
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            }
        }

    async def get_sales_report(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        platform_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get sales report"""
        
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)

        # Base query for orders
        orders_query = select(Order).where(
            and_(
                Order.created_at >= date_from,
                Order.created_at <= date_to
            )
        )
        
        if platform_id:
            orders_query = orders_query.where(Order.platform_id == platform_id)

        # Total orders and revenue
        total_orders_result = await self.db.execute(orders_query.with_only_columns(func.count(Order.id)))
        total_orders = total_orders_result.scalar()

        total_revenue_result = await self.db.execute(
            orders_query.with_only_columns(func.sum(Order.total_amount))
        )
        total_revenue = total_revenue_result.scalar() or 0

        # Orders by status
        status_query = (
            orders_query
            .with_only_columns(Order.status, func.count(Order.id))
            .group_by(Order.status)
        )
        status_result = await self.db.execute(status_query)
        orders_by_status = {status: count for status, count in status_result.all()}

        # Top selling products
        top_products_query = (
            select(
                Product.name,
                func.sum(OrderItem.quantity).label('total_quantity'),
                func.sum(OrderItem.total_price).label('total_revenue')
            )
            .join(SKU, OrderItem.sku_id == SKU.id)
            .join(Product, SKU.product_id == Product.id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                and_(
                    Order.created_at >= date_from,
                    Order.created_at <= date_to
                )
            )
            .group_by(Product.id, Product.name)
            .order_by(desc(func.sum(OrderItem.quantity)))
            .limit(10)
        )

        if platform_id:
            top_products_query = top_products_query.where(Order.platform_id == platform_id)

        top_products_result = await self.db.execute(top_products_query)
        top_products = [
            {
                "product_name": name,
                "total_quantity": int(quantity),
                "total_revenue": float(revenue)
            }
            for name, quantity, revenue in top_products_result.all()
        ]

        # Daily sales trend
        daily_sales_query = (
            select(
                func.date(Order.created_at).label('date'),
                func.count(Order.id).label('orders'),
                func.sum(Order.total_amount).label('revenue')
            )
            .where(
                and_(
                    Order.created_at >= date_from,
                    Order.created_at <= date_to
                )
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )

        if platform_id:
            daily_sales_query = daily_sales_query.where(Order.platform_id == platform_id)

        daily_sales_result = await self.db.execute(daily_sales_query)
        daily_sales = [
            {
                "date": date.isoformat(),
                "orders": orders,
                "revenue": float(revenue or 0)
            }
            for date, orders, revenue in daily_sales_result.all()
        ]

        return {
            "summary": {
                "total_orders": total_orders,
                "total_revenue": float(total_revenue),
                "average_order_value": float(total_revenue / total_orders) if total_orders > 0 else 0,
                "orders_by_status": orders_by_status
            },
            "top_products": top_products,
            "daily_sales": daily_sales,
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            }
        }

    async def get_partner_performance_report(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get partner performance report"""
        
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)

        # Partner sales performance
        partner_sales_query = (
            select(
                Partner.name,
                Partner.type,
                func.count(Order.id).label('total_orders'),
                func.sum(Order.total_amount).label('total_revenue'),
                func.sum(OrderItem.quantity).label('total_quantity')
            )
            .join(Product, Partner.id == Product.partner_id)
            .join(SKU, Product.id == SKU.product_id)
            .join(OrderItem, SKU.id == OrderItem.sku_id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                and_(
                    Order.created_at >= date_from,
                    Order.created_at <= date_to
                )
            )
            .group_by(Partner.id, Partner.name, Partner.type)
            .order_by(desc(func.sum(Order.total_amount)))
        )
        
        partner_sales_result = await self.db.execute(partner_sales_query)
        partner_performance = [
            {
                "partner_name": name,
                "partner_type": partner_type,
                "total_orders": orders,
                "total_revenue": float(revenue or 0),
                "total_quantity": int(quantity or 0)
            }
            for name, partner_type, orders, revenue, quantity in partner_sales_result.all()
        ]

        # Partner inventory status
        partner_inventory_query = (
            select(
                Partner.name,
                func.count(SKU.id).label('total_skus'),
                func.sum(SKU.quantity).label('total_stock'),
                func.sum(SKU.quantity * SKU.price).label('inventory_value')
            )
            .join(Product, Partner.id == Product.partner_id)
            .join(SKU, Product.id == SKU.product_id)
            .where(SKU.is_active == True)
            .group_by(Partner.id, Partner.name)
            .order_by(desc(func.sum(SKU.quantity * SKU.price)))
        )
        
        partner_inventory_result = await self.db.execute(partner_inventory_query)
        partner_inventory = [
            {
                "partner_name": name,
                "total_skus": skus,
                "total_stock": int(stock or 0),
                "inventory_value": float(value or 0)
            }
            for name, skus, stock, value in partner_inventory_result.all()
        ]

        return {
            "sales_performance": partner_performance,
            "inventory_status": partner_inventory,
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            }
        }

    async def get_platform_sync_report(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get platform synchronization report"""
        
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=7)  # Default to last week

        # Sync logs summary
        sync_summary_query = (
            select(
                Platform.name,
                SyncLog.sync_type,
                SyncLog.status,
                func.count(SyncLog.id).label('sync_count'),
                func.avg(SyncLog.records_processed).label('avg_records')
            )
            .join(Platform, SyncLog.platform_id == Platform.id)
            .where(
                and_(
                    SyncLog.started_at >= date_from,
                    SyncLog.started_at <= date_to
                )
            )
            .group_by(Platform.name, SyncLog.sync_type, SyncLog.status)
            .order_by(Platform.name, SyncLog.sync_type)
        )
        
        sync_summary_result = await self.db.execute(sync_summary_query)
        sync_summary = [
            {
                "platform_name": platform_name,
                "sync_type": sync_type,
                "status": status,
                "sync_count": count,
                "avg_records_processed": float(avg_records or 0)
            }
            for platform_name, sync_type, status, count, avg_records in sync_summary_result.all()
        ]

        # Recent sync errors
        error_logs_query = (
            select(SyncLog)
            .options(selectinload(SyncLog.platform))
            .where(
                and_(
                    SyncLog.status == "error",
                    SyncLog.started_at >= date_from,
                    SyncLog.started_at <= date_to
                )
            )
            .order_by(desc(SyncLog.started_at))
            .limit(20)
        )
        
        error_logs_result = await self.db.execute(error_logs_query)
        recent_errors = [
            {
                "platform_name": log.platform.name if log.platform else "Unknown",
                "sync_type": log.sync_type,
                "error_message": log.error_message,
                "started_at": log.started_at.isoformat()
            }
            for log in error_logs_result.scalars().all()
        ]

        return {
            "sync_summary": sync_summary,
            "recent_errors": recent_errors,
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            }
        }

    async def get_custom_report(
        self,
        report_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate custom report based on configuration"""
        
        report_type = report_config.get("type")
        date_from = report_config.get("date_from")
        date_to = report_config.get("date_to")
        filters = report_config.get("filters", {})

        if date_from:
            date_from = datetime.fromisoformat(date_from)
        if date_to:
            date_to = datetime.fromisoformat(date_to)

        if report_type == "inventory":
            return await self.get_inventory_summary(date_from, date_to)
        elif report_type == "sales":
            platform_id = filters.get("platform_id")
            return await self.get_sales_report(date_from, date_to, platform_id)
        elif report_type == "partners":
            return await self.get_partner_performance_report(date_from, date_to)
        elif report_type == "sync":
            return await self.get_platform_sync_report(date_from, date_to)
        else:
            raise ValueError(f"Unsupported report type: {report_type}")

    async def export_report_data(
        self,
        report_data: Dict[str, Any],
        export_format: str = "json"
    ) -> bytes:
        """Export report data in specified format"""
        
        if export_format.lower() == "json":
            import json
            return json.dumps(report_data, indent=2, default=str).encode('utf-8')
        
        elif export_format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            
            # Flatten the report data for CSV export
            flattened_data = self._flatten_report_data(report_data)
            
            if flattened_data:
                writer = csv.DictWriter(output, fieldnames=flattened_data[0].keys())
                writer.writeheader()
                writer.writerows(flattened_data)
            
            return output.getvalue().encode('utf-8')
        
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

    def _flatten_report_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten nested report data for CSV export"""
        
        flattened = []
        
        def flatten_dict(d, parent_key=''):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key).items())
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            items.extend(flatten_dict(item, f"{new_key}.{i}").items())
                        else:
                            items.append((f"{new_key}.{i}", item))
                else:
                    items.append((new_key, v))
            
            return dict(items)
        
        # For now, just return the main data as is
        # More sophisticated flattening can be implemented based on specific needs
        if isinstance(data, dict) and any(isinstance(v, list) for v in data.values()):
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    return value
        
        return [flatten_dict(data)]