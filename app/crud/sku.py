from app.crud.base import CRUDBase
from app.models.sku import SKU
from app.schemas.sku import SKUCreate, SKUUpdate

class SKUCRUD(CRUDBase[SKU, SKUCreate, SKUUpdate]):
    pass

sku = SKUCRUD(SKU)