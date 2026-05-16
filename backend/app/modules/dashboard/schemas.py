from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class KPIOverviewSchema(BaseModel):
    total_inventory_value: float
    total_products: int
    out_of_stock_count: int
    overstock_count: int
    service_level_avg: float
    inventory_turns: float
    pending_orders: int

class DashboardWidgetSchema(BaseModel):
    id: str
    title: str
    type: str
    data: Any
