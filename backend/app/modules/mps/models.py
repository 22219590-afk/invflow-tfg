from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime


class MPSSolution(SQLModel, table=True):
    """Stores a complete aggregate planning solution."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = "Plan Maestro de Producción"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Aggregate cost breakdown
    total_cost: float = 0.0
    storage_cost: float = 0.0
    production_cost: float = 0.0
    hiring_cost: float = 0.0
    firing_cost: float = 0.0

    months: List["MPSMonthDetail"] = Relationship(back_populates="solution")


class MPSMonthDetail(SQLModel, table=True):
    """Monthly detail of an MPS solution."""
    id: Optional[int] = Field(default=None, primary_key=True)
    solution_id: int = Field(foreign_key="mpssolution.id")

    month_index: int           # 1–12
    month_name: str
    year: int

    # Demand
    demand: float              # Forecast demand used by LP
    real_demand: Optional[float] = None   # Actual (past months)
    deviation_pct: Optional[float] = None # (real - forecast) / forecast * 100

    # LP solution output
    production: float
    inventory: float
    workers: float
    hires: float
    fires: float

    # Extended fields (added in service rewrite)
    capacity_utilization: float = 0.0    # % of capacity used (production / max_cap)
    shortfall: float = 0.0               # Unmet demand (should be 0 in feasible solutions)

    solution: MPSSolution = Relationship(back_populates="months")
