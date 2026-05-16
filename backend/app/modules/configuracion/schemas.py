from pydantic import BaseModel
from typing import Optional, List

class OdooConfigSchema(BaseModel):
    odoo_url: str
    odoo_db: str
    odoo_user: str
    odoo_password: str
    odoo_port: Optional[str] = "443"

class ConfigItemSchema(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class ConfigUpdateSchema(BaseModel):
    items: List[ConfigItemSchema]
