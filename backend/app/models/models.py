from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = "viewer"  # admin | planner | viewer
    is_active: bool = True


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    odoo_id: int = Field(index=True, unique=True)
    name: str
    default_code: Optional[str] = None
    list_price: float = 0.0
    standard_price: float = 0.0
    uom_id: Optional[int] = None
    category_id: Optional[int] = None
    active: bool = True
    supplier_id: Optional[int] = None  # FK to Partner.odoo_id

    # Demand analytics
    abc_class: Optional[str] = None   # A, B, C
    xyz_class: Optional[str] = None   # X, Y, Z
    stock_policy_override: Optional[str] = None # A=ROP, B=Periodic, C=Demand
    daily_demand: float = 0.0
    demand_std_dev: float = 0.0
    cv: float = 0.0

    # Stock policy results
    safety_stock: float = 0.0          # Current effective SS
    safety_stock_continuous: float = 0.0
    safety_stock_periodic: float = 0.0
    min_stock: float = 0.0             # Reorder Point / MIN
    max_stock: float = 0.0             # Max Stock
    target_stock_level: float = 0.0    # Target Level S (Periodic)
    eoq: float = 0.0                   # Wilson
    num_orders_year: float = 0.0       # N
    lead_time_days: int = 7
    review_period: int = 14            # T
    recommended_qty: float = 0.0
    
    # Financial results
    cost_order: float = 0.0
    cost_holding: float = 0.0
    cost_total: float = 0.0
    
    # Audit / Traceability fields
    z_value: float = 0.0
    annual_demand: float = 0.0
    
    # Manual Overrides
    target_service_level: Optional[float] = None
    manual_daily_demand: Optional[float] = None
    manual_demand_std_dev: Optional[float] = None
    
    # Periodic History
    last_order_date: Optional[datetime] = None

    moves: List["StockMove"] = Relationship(back_populates="product")
    quants: List["StockQuant"] = Relationship(back_populates="product")
    sales_history: List["SalesHistory"] = Relationship(back_populates="product")
    sale_lines: List["SaleOrderLine"] = Relationship(back_populates="product")
    
    # BOM Relationships
    bom_parents: List["BOM"] = Relationship(back_populates="parent", sa_relationship_kwargs={"primaryjoin": "Product.odoo_id==BOM.parent_id"})
    bom_children: List["BOM"] = Relationship(back_populates="child", sa_relationship_kwargs={"primaryjoin": "Product.odoo_id==BOM.child_id"})

    # New UI fields
    reserved_quantity: float = 0.0
    incoming_qty: float = 0.0
    location_name: Optional[str] = "Almacén Principal"
    category_name: Optional[str] = "General"
    image_url: Optional[str] = None
    description: Optional[str] = None

    # Forecasting analysis fields
    forecast_model: Optional[str] = None
    forecast_mape: float = 0.0
    demand_pattern: str = "Stable"
    trend_type: str = "Stable"
    seasonality_strength: float = 0.0
    volatility_index: float = 0.0

    # Relationships
    forecast_results: List["ForecastResult"] = Relationship(back_populates="product")
    forecast_metrics: Optional["ForecastMetric"] = Relationship(back_populates="product")


class StockQuant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    odoo_id: int = Field(index=True, unique=True)
    product_id: int = Field(foreign_key="product.odoo_id")
    location_id: int
    quantity: float
    reserved_quantity: float = 0.0

    product: Product = Relationship(back_populates="quants")


class StockMove(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    odoo_id: int = Field(index=True, unique=True)
    product_id: int = Field(foreign_key="product.odoo_id")
    date: datetime
    product_uom_qty: float
    state: str
    move_type: str = "out" # "out" for demand, "in" for production/purchase
    location_id: int
    location_dest_id: int
    picking_type_id: int
    expected_date: Optional[datetime] = None

    product: Product = Relationship(back_populates="moves")


class SaleOrderLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    odoo_id: int = Field(index=True, unique=True)
    product_id: int = Field(foreign_key="product.odoo_id")
    order_id: int
    date: datetime
    product_uom_qty: float
    price_unit: float
    price_subtotal: float
    state: str # sale, done, etc.

    product: Product = Relationship(back_populates="sale_lines")


class SalesHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.odoo_id")
    date: datetime
    quantity: float
    is_synthetic: bool = True
    
    product: Product = Relationship(back_populates="sales_history")


class ForecastResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.odoo_id")
    date: datetime
    quantity: float # Predicted value
    is_real: bool = False # False for future, True for backtesting
    
    # Traceability
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    
    product: Product = Relationship(back_populates="forecast_results")


class ForecastMetric(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.odoo_id", unique=True)
    
    mae: float = 0.0
    mape: float = 0.0
    rmse: float = 0.0
    bias: float = 0.0
    wmape: float = 0.0
    
    mean: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0
    p25: float = 0.0
    p75: float = 0.0
    outliers_count: int = 0
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    product: Product = Relationship(back_populates="forecast_metrics")


class Partner(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    odoo_id: int = Field(index=True, unique=True)
    name: str
    email: Optional[str] = None
    is_supplier: bool = True
    lead_time_days: int = 7
    moq: float = 1.0   # Minimum Order Quantity


class AppConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    value: str
    description: Optional[str] = None


class WidgetQuery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    widget_id: str = Field(unique=True, index=True)
    title: str
    query_sql: Optional[str] = None
    odoo_domain: Optional[str] = None
    endpoint: str


# ─── Production Module Models ──────────────────────────────────────────────────

class BOM(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    parent_id: int = Field(foreign_key="product.odoo_id")
    child_id: int = Field(foreign_key="product.odoo_id")
    quantity: float = 1.0  # Qty of child needed for 1 unit of parent

    parent: "Product" = Relationship(back_populates="bom_parents", sa_relationship_kwargs={"foreign_keys": "[BOM.parent_id]"})
    child: "Product" = Relationship(back_populates="bom_children", sa_relationship_kwargs={"foreign_keys": "[BOM.child_id]"})


class ResourceCapacity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    capacity_per_day: float = 8.0  # Hours, Units, etc.
    cost_per_unit: float = 0.0
    
    # Advanced MPS / Labor fields
    cost_worker_month: float = 2000.0
    cost_hiring: float = 1000.0
    cost_firing: float = 1500.0
    units_per_worker_month: float = 500.0
    initial_workers: int = 10


class ProductionPlan(SQLModel, table=True):
    """Stores Master Production Schedule (MPS) results."""
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(index=True)
    period_start: datetime
    planned_qty: float
    projected_inventory: float
    cost_production: float = 0.0
    cost_holding: float = 0.0
    
    # Advanced MPS / Labor results
    planned_workers: float = 0.0
    hiring_qty: float = 0.0
    firing_qty: float = 0.0
    cost_labor: float = 0.0
    cost_hiring: float = 0.0
    cost_firing: float = 0.0


class MRPRequirement(SQLModel, table=True):
    """Stores Material Requirements Planning (MRP) explosion results."""
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(index=True)
    date: datetime
    gross_requirement: float
    scheduled_receipt: float = 0.0
    projected_available: float
    net_requirement: float
    planned_order_release: float
    
    # Traceability
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
