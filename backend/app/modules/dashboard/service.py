from sqlmodel import Session, select, func
from app.models.models import Product, StockQuant, StockMove
from app.services.analytics import AnalyticsService
from .schemas import KPIOverviewSchema

class DashboardService:
    def __init__(self, session: Session):
        self.session = session

    def get_global_kpis(self, period_days: int = 30) -> KPIOverviewSchema:
        analytics = AnalyticsService(self.session)
        kpis = analytics.get_kpis(period_days=period_days)
        
        # Mapping existing analytics kpis to our new schema
        return KPIOverviewSchema(
            total_inventory_value=kpis.get("inventory_value", 0.0),
            total_products=kpis.get("total_products", 0),
            out_of_stock_count=kpis.get("stockouts", 0),
            overstock_count=kpis.get("overstock", 0),
            service_level_avg=kpis.get("service_level", 0.0),
            inventory_turns=kpis.get("inventory_turns", 0.0),
            pending_orders=kpis.get("pending_orders", 0)
        )

    def get_stock_alerts(self):
        # Implementation for stock alerts
        pass
