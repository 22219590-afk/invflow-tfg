from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.core.database import get_session
from .service import DashboardService
from .schemas import KPIOverviewSchema
from typing import Optional

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/kpis", response_model=KPIOverviewSchema)
def get_dashboard_kpis(
    period_days: Optional[int] = 30,
    session: Session = Depends(get_session)
):
    service = DashboardService(session)
    return service.get_global_kpis(period_days=period_days)
