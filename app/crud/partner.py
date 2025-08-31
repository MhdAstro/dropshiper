from app.crud.base import CRUDBase
from app.models.partner import Partner
from app.schemas.partner import PartnerCreate, PartnerUpdate

class PartnerCRUD(CRUDBase[Partner, PartnerCreate, PartnerUpdate]):
    pass

partner = PartnerCRUD(Partner)