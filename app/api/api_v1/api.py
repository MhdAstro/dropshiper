from fastapi import APIRouter

from app.api.api_v1.endpoints import (
    products,
    variants,
    skus,
    partners,
    platforms,
    inventory,
    orders,
    reports,
    users,
    auth,
    pricing_rules,
    settlements,
    basalam_auth
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(variants.router, prefix="/variants", tags=["variants"])
api_router.include_router(skus.router, prefix="/skus", tags=["skus"])
api_router.include_router(partners.router, prefix="/partners", tags=["partners"])
api_router.include_router(platforms.router, prefix="/platforms", tags=["platforms"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(pricing_rules.router, prefix="/pricing-rules", tags=["pricing-rules"])
api_router.include_router(settlements.router, prefix="/settlements", tags=["settlements"])
api_router.include_router(basalam_auth.router, prefix="/auth/basalam", tags=["basalam-auth"])