from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, create_engine, SQLModel, select, Field, delete
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os

from app.core.config import settings
from app.models.models import (
    Product, StockQuant, StockMove, SaleOrderLine, Partner, AppConfig, User, WidgetQuery,
    BOM
)
from app.core.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, require_role
)

from app.modules.dashboard.router import router as dashboard_router
from app.modules.configuracion.router import router as config_router
from app.modules.usuarios.service import UserService

app = FastAPI(
    title="InvFlow — Inventory Optimization API",
    description="Inventory planning DSS integrated with Odoo ERP",
    version="2.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    redirect_slashes=False,
)

app.include_router(dashboard_router, prefix="/v1")
app.include_router(config_router, prefix="/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.core.database import engine, get_session


# ─── STARTUP ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    _ensure_schema_updates()
    _seed_defaults()


def _ensure_schema_updates():
    """Manual migration handle for SQLModel (which doesn't handle ALTRES)."""
    from sqlmodel import text
    with Session(engine) as session:
        try:
            # Add new columns if missing
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS target_service_level FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS manual_daily_demand FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS manual_demand_std_dev FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS safety_stock_continuous FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS safety_stock_periodic FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS target_stock_level FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS num_orders_year FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS stock_policy_override VARCHAR'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS cost_order FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS cost_holding FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS cost_total FLOAT'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS incoming_qty FLOAT DEFAULT 0.0'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS reserved_quantity FLOAT DEFAULT 0.0'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS location_name VARCHAR'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS category_name VARCHAR'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS image_url VARCHAR'))
            session.exec(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS description VARCHAR'))
            session.exec(text('ALTER TABLE stockmove ADD COLUMN IF NOT EXISTS expected_date TIMESTAMP'))
            # User table migrations
            session.exec(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE'))
            session.exec(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT \'viewer\''))
            session.commit()
        except Exception as e:
            print(f"Migration warning: {e}")
            session.rollback()


def _seed_defaults():
    with Session(engine) as session:
        # Create default admin user
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            session.add(User(
                username="admin",
                hashed_password=get_password_hash("admin"),
                role="admin",
            ))

        # Seed inventory planning config
        inventory_defaults = {
            "service_level_a": ("95", "Service level for A products (%)"),
            "service_level_b": ("90", "Service level for B products (%)"),
            "service_level_c": ("85", "Service level for C products (%)"),
            "review_period_b_days": ("14", "Periodic review interval for B products (days)"),
            "abc_threshold_a": ("0.80", "ABC cutoff A (cumulative value %)"),
            "abc_threshold_b": ("0.95", "ABC cutoff B (cumulative value %)"),
            "lead_time_default_days": ("7", "Default supplier lead time (days)"),
            "ordering_cost": ("50.0", "Cost of placing one order (S)"),
            "holding_rate": ("0.20", "Annual holding rate (i) - e.g. 0.20 for 20%"),
        }
        # Seed Odoo connection config — pre-filled from env vars
        odoo_defaults = {
            "odoo_url":     (os.getenv("ODOO_URL", ""), "Odoo instance URL"),
            "odoo_db":      (os.getenv("ODOO_DB", ""), "Odoo database name"),
            "odoo_user":    (os.getenv("ODOO_USER", ""), "Odoo login (email)"),
            "odoo_api_key": (os.getenv("ODOO_PASSWORD", ""), "Odoo API key or password"),
        }

        all_defaults = {**inventory_defaults, **odoo_defaults}
        for key, (val, desc) in all_defaults.items():
            existing = session.exec(select(AppConfig).where(AppConfig.key == key)).first()
            if not existing:
                session.add(AppConfig(key=key, value=val, description=desc))
            # DO NOT overwrite existing values with .env anymore to allow UI persistence

        session.commit()

        # Manual schema migration for new fields
        from sqlalchemy import text
        try:
            session.exec(text("ALTER TABLE product ADD COLUMN eoq FLOAT DEFAULT 0.0"))
            session.commit()
        except: session.rollback()
        try:
            session.exec(text("ALTER TABLE product ADD COLUMN review_period INTEGER DEFAULT 14"))
            session.commit()
        except: session.rollback()
        try:
            session.exec(text("ALTER TABLE product ADD COLUMN last_order_date TIMESTAMP"))
            session.commit()
        except: session.rollback()
        
        try:
            session.exec(text("ALTER TABLE product ADD COLUMN stock_policy_override VARCHAR(10)"))
            session.commit()
        except: session.rollback()

        # Seed default widget queries
        widget_defaults = [
            WidgetQuery(
                widget_id="global_kpis",
                title="KPI Global Dashboard",
                endpoint="/api/kpis",
                query_sql="SELECT SUM(qty * price) as val FROM stock_quant; SELECT COUNT(*) FROM stock_move WHERE expected_date < now()",
                odoo_domain="['|', ('type', '=', 'product'), ('type', '=', 'storable')]"
            ),
            WidgetQuery(
                widget_id="inventory_table",
                title="Inventory Master Data",
                endpoint="/api/products",
                query_sql="SELECT * FROM product ORDER BY abc_class ASC, name ASC",
                odoo_domain="[]"
            )
        ]
        for w in widget_defaults:
            if not session.exec(select(WidgetQuery).where(WidgetQuery.widget_id == w.widget_id)).first():
                session.add(w)

        session.commit()
    try:
        from app.seed import seed
        seed()
    except Exception as e:
        print(f"Seed failed: {e}")


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.post("/v1/auth/login", tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form.username)).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role, "username": user.username}


@app.get("/v1/auth/me", tags=["Auth"])
def me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}


# ─── USER MANAGEMENT ─────────────────────────────────────────────────────────

# ─── USER MANAGEMENT (Consolidated below) ─────────────────────────────────────


# ─── WIDGET QUERIES ───────────────────────────────────────────────────────────

@app.get("/v1/widgets", tags=["Admin"])
def get_widgets(session: Session = Depends(get_session)):
    return session.exec(select(WidgetQuery)).all()

@app.put("/v1/widgets/{widget_id}", tags=["Admin"])
def update_widget(widget_id: str, data: dict, session: Session = Depends(get_session)):
    widget = session.exec(select(WidgetQuery).where(WidgetQuery.widget_id == widget_id)).first()
    if not widget: raise HTTPException(404)
    widget.query_sql = data.get("query_sql", widget.query_sql)
    widget.odoo_domain = data.get("odoo_domain", widget.odoo_domain)
    session.add(widget)
    session.commit()
    return widget

# ─── USERS (Admin only) ───────────────────────────────────────────────────────


class UserCreate(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: str = None
    password: str = None
    is_active: bool = None

@app.get("/v1/users", tags=["Users"])
def list_users(session: Session = Depends(get_session)):
    service = UserService(session)
    users = service.get_users()
    return [{"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active} for u in users]

@app.post("/v1/users", tags=["Users"])
def create_user(user_data: UserCreate, session: Session = Depends(get_session)):
    service = UserService(session)
    return service.create_user(user_data.dict())

@app.put("/v1/users/{user_id}", tags=["Users"])
def update_user(user_id: int, user_data: UserUpdate, session: Session = Depends(get_session)):
    service = UserService(session)
    user = service.update_user(user_id, user_data.dict(exclude_unset=True))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}

@app.delete("/v1/users/{user_id}", tags=["Users"])
def delete_user(user_id: int, session: Session = Depends(get_session)):
    service = UserService(session)
    if not service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}

# Legacy user management moved to modular router (Cleaned up)


# ─── PRODUCTS ─────────────────────────────────────────────────────────────────

@app.get("/v1/products", tags=["Inventory"])
def get_products(
    abc: Optional[str] = None,
    search: Optional[str] = None,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    from app.services.analytics import AnalyticsService
    products = AnalyticsService(session).get_products_enriched()
    if abc:
        products = [p for p in products if p["abc_class"] == abc.upper()]
    if search:
        s = search.lower()
        products = [p for p in products if s in p["name"].lower() or s in (p["default_code"] or "").lower()]
    return products


class ProductUpdate(BaseModel):
    target_service_level: Optional[float] = None
    lead_time_days: Optional[int] = None
    manual_daily_demand: Optional[float] = None
    manual_demand_std_dev: Optional[float] = None
    stock_policy_override: Optional[str] = None


@app.put("/v1/products/{product_id}", tags=["Inventory"])
def update_product(
    product_id: int,
    body: ProductUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if body.target_service_level is not None:
        product.target_service_level = body.target_service_level
    if body.lead_time_days is not None:
        product.lead_time_days = body.lead_time_days
    if body.manual_daily_demand is not None:
        product.manual_daily_demand = body.manual_daily_demand
    if body.manual_demand_std_dev is not None:
        product.manual_demand_std_dev = body.manual_demand_std_dev
    if body.stock_policy_override is not None:
        product.stock_policy_override = body.stock_policy_override
    
    session.add(product)
    session.commit()
    
    # Fast re-calculate only for this product
    from app.services.analytics import AnalyticsService
    service = AnalyticsService(session)
    # Sync fresh stock from Odoo before recalculating
    service.sync_product_stock_from_odoo(product)
    service.calculate_product_policy(product)
    session.commit()
    session.refresh(product)
    
    return product


# ─── KPIS ─────────────────────────────────────────────────────────────────────

@app.get("/v1/kpis", tags=["Inventory"])
def get_kpis(
    period: str = "month",
    period_days: Optional[int] = None,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    from app.services.analytics import AnalyticsService
    # Accept either semantic period name or explicit period_days (frontend sends period_days)
    if period_days is not None:
        days = max(1, period_days)
    else:
        period_map = {
            "week": 7,
            "month": 30,
            "quarter": 90,
            "trimester": 120,
            "semester": 180,
            "year": 365,
        }
        days = period_map.get(period, 30)
    return AnalyticsService(session).get_kpis(period_days=days)


@app.post("/v1/products/{product_id}/update-policy", tags=["Inventory"])
def update_product_policy(
    product_id: int,
    policy_override: str,
    name: Optional[str] = None,
    daily_demand: Optional[float] = None,
    target_service_level: float = 95.0,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    from app.services.analytics import AnalyticsService
    from app.models.models import Product
    product = session.exec(select(Product).where(Product.id == product_id)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.stock_policy_override = policy_override
    product.target_service_level = target_service_level
    if name:
        product.name = name
    if daily_demand is not None:
        product.manual_daily_demand = daily_demand
    
    # Recalculate
    service = AnalyticsService(session)
    # Sync fresh stock from Odoo before recalculating
    service.sync_product_stock_from_odoo(product)
    service.calculate_product_policy(product)
    
    session.add(product)
    session.commit()
    session.refresh(product)
    
    # Return enriched format as expected by frontend
    return service.get_products_enriched_single(product_id)



# ─── COMPONENTS (BOM EXPLOSION — READ ONLY) ───────────────────────────────────

@app.get("/v1/products/{product_id}/components", tags=["Inventory"])
def get_product_components(
    product_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Returns BOM components for a finished product with demand propagation.
    RESTRICTION: Does NOT recalculate demand. Reads existing daily_demand from the
    parent product and propagates it proportionally via BOM quantities.
    
    Example: If BOM says 1 parent = 3 units of component A, and parent daily_demand = 10,
    then component A daily_need = 30.
    """
    from app.models.models import BOM, StockQuant

    parent = session.get(Product, product_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Product not found")

    # Fetch all BOM lines where this product is the parent (by odoo_id FK)
    bom_lines = session.exec(
        select(BOM).where(BOM.parent_id == parent.odoo_id)
    ).all()

    if not bom_lines:
        return {"has_components": False, "components": []}

    # Build stock map for children
    child_ids = [b.child_id for b in bom_lines]
    quants = session.exec(
        select(StockQuant).where(StockQuant.product_id.in_(child_ids))
    ).all()
    stock_map: dict = {}
    for q in quants:
        stock_map[q.product_id] = stock_map.get(q.product_id, 0.0) + q.quantity

    # Use the EXISTING demand of the parent — no recalculation
    parent_daily_demand = parent.daily_demand or 0.0

    components = []
    for bom in bom_lines:
        child = session.exec(
            select(Product).where(Product.odoo_id == bom.child_id)
        ).first()
        if not child:
            continue

        child_stock = stock_map.get(bom.child_id, 0.0)
        # Derived demand: parent demand × BOM quantity
        daily_need = parent_daily_demand * bom.quantity
        # Units needed to cover lead time of the parent
        lead_time_need = daily_need * max(parent.lead_time_days or 7, 1)
        # Replenishment needed: how many units of the component are short
        repl_needed = max(0.0, lead_time_need - child_stock)

        components.append({
            "child_id": child.id,
            "child_odoo_id": child.odoo_id,
            "name": child.name,
            "default_code": child.default_code,
            "bom_qty": bom.quantity,          # units of child per 1 parent
            "current_stock": round(child_stock, 2),
            "daily_need": round(daily_need, 4),         # propagated from parent demand
            "parent_daily_demand": round(parent_daily_demand, 4),
            "lead_time_need": round(lead_time_need, 2), # need to cover parent LT
            "repl_needed": round(repl_needed, 2),       # gap to cover
            "abc_class": child.abc_class or "—",
            "status": "OK" if child_stock >= lead_time_need else ("Stockout" if child_stock <= 0 else "Reorder"),
        })

    return {
        "has_components": True,
        "parent_id": parent.id,
        "parent_name": parent.name,
        "parent_daily_demand": round(parent_daily_demand, 4),
        "components": components,
    }


# ─── ODOO CONNECTION ──────────────────────────────────────────────────────────

class OdooConfigUpdate(BaseModel):
    url: str
    db: str
    user: str
    password: Optional[str] = None
    api_key: Optional[str] = None
    port: Optional[int] = 443

@app.post("/v1/odoo/config", tags=["Odoo"])
def update_odoo_config(
    body: OdooConfigUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role("admin", "planner")),
):
    updates = {
        "odoo_url": body.url,
        "odoo_db": body.db,
        "odoo_user": body.user,
    }
    if body.password:
        updates["odoo_api_key"] = body.password
    if body.api_key:
        updates["odoo_api_key"] = body.api_key
    if body.port:
        updates["odoo_port"] = str(body.port)
        
    for k, v in updates.items():
        row = session.exec(select(AppConfig).where(AppConfig.key == k)).first()
        if not row:
            session.add(AppConfig(key=k, value=v))
        else:
            row.value = v
            session.add(row)
    
    session.commit()
    return {"message": "Odoo configuration updated successfully"}

@app.get("/v1/odoo/config", tags=["Odoo"])
def get_odoo_config(
    session: Session = Depends(get_session),
    _: User = Depends(require_role("admin", "planner")),
):
    keys = ["odoo_url", "odoo_db", "odoo_user", "odoo_api_key", "odoo_port"]
    rows = session.exec(select(AppConfig).where(AppConfig.key.in_(keys))).all()
    config = {r.key: r.value for r in rows}
    return {
        "url": config.get("odoo_url", ""),
        "db": config.get("odoo_db", ""),
        "user": config.get("odoo_user", ""),
        "api_key": config.get("odoo_api_key", ""),
        "port": int(config.get("odoo_port", 443)) if config.get("odoo_port") else 443
    }

@app.get("/v1/odoo/test", tags=["Odoo"])
def test_odoo(
    url: Optional[str] = None,
    db: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    port: Optional[int] = None,
    session: Session = Depends(get_session),
    _: User = Depends(require_role("admin", "planner")),
):
    try:
        from app.services.odoo_connector import OdooConnector
        if url and db and user and password:
            # Test with provided params
            c = OdooConnector(url, db, user, password, port)
        else:
            # Fallback to saved config
            c = OdooConnector.from_config(session)
        
        c.login()
        return c.test_connection()
    except Exception as e:
        detail = str(e)
        status_code = 503
        if "Access Denied" in detail:
            status_code = 401
            detail = "Odoo Access Denied: Verifica tu usuario (email) y API Key."
        elif "404" in detail:
            detail = f"Odoo Error 404: Instancia no encontrada. host={c.host if 'c' in locals() else 'unknown'}"
        raise HTTPException(status_code=status_code, detail=detail)


@app.get("/v1/odoo/partners", tags=["Odoo"])
def get_odoo_partners(
    session: Session = Depends(get_session),
    _: User = Depends(require_role("admin", "planner")),
):
    from app.services.odoo_connector import OdooConnector
    try:
        c = OdooConnector.from_config(session)
        return c.get_partners()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/odoo/purchase-order", tags=["Odoo"])
def create_odoo_po(
    partner_id: int,
    product_id_odoo: int,
    quantity: float,
    session: Session = Depends(get_session),
    _: User = Depends(require_role("admin", "planner")),
):
    from app.services.odoo_connector import OdooConnector
    try:
        c = OdooConnector.from_config(session)
        # Create a PO with a single line
        lines = [{
            'product_id': product_id_odoo,
            'product_qty': quantity,
            'price_unit': 0.0 # Odoo will usually fill this from vendor pricelists
        }]
        po_id = c.create_purchase_order(partner_id, lines)
        return {"status": "success", "po_id": po_id, "message": f"Purchase Order #{po_id} created in Odoo"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── SYNC ─────────────────────────────────────────────────────────────────────

@app.post("/v1/sync", tags=["Sync"])
def sync_data(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.services.odoo_connector import OdooConnector
    from sqlmodel import text
    try:
        # TFG Fix: Before clearing, capture manual overrides to restore them
        existing_overrides = {
            p.odoo_id: {
                "demand": p.manual_daily_demand,
                "std_dev": p.manual_demand_std_dev,
                "service_level": p.target_service_level,
                "policy": p.stock_policy_override,
                "lead_time": p.lead_time_days
            } 
            for p in session.exec(select(Product)).all()
            if p.manual_daily_demand is not None or p.stock_policy_override is not None
        }

        # Clear old data to ensure a fresh start
        # Order matters: delete child tables before parent (product)
        session.exec(text("DELETE FROM forecastresult"))
        session.exec(text("DELETE FROM forecastmetric"))
        session.exec(text("DELETE FROM saleshistory"))
        session.exec(text("DELETE FROM bom"))
        session.exec(text("DELETE FROM stockquant"))
        session.exec(text("DELETE FROM stockmove"))
        session.exec(text("DELETE FROM saleorderline"))
        session.exec(text("DELETE FROM product"))
        session.exec(text("DELETE FROM partner"))
        session.commit()

        connector = OdooConnector.from_config(session)
        connector.login()

        # Sync products
        odoo_products = connector.get_products()
        
        # Fetch all seller info in one go to get lead times
        all_seller_ids = []
        for p in odoo_products:
            all_seller_ids.extend(p.get("seller_ids", []))
        
        seller_info_map = {}
        if all_seller_ids:
            s_infos = connector.models.execute_kw(connector.db, connector.uid, connector.password, 'product.supplierinfo', 'read', [all_seller_ids, ['product_id', 'delay', 'min_qty']])
            for si in s_infos:
                pid = si['product_id'][0] if isinstance(si['product_id'], list) else si['product_id']
                if pid not in seller_info_map:
                    seller_info_map[pid] = si
        
        # Fetch pending purchases (RFQs + POs) — fuente canónica para stock en tránsito
        # qty = product_qty - qty_received por línea, por lo que refleja recepciones parciales
        pending_map = connector.get_pending_purchases()
        
        product_odoo_ids = set()
        for p in odoo_products:
            odoo_name = p.get("display_name") or p.get("name") or "Unnamed Product"
            ref = p.get("default_code") or ""
            categ = p.get("categ_id")
            categ_name = categ[1] if (categ and isinstance(categ, list) and len(categ) > 1) else "General"
            
            # Get lead time from seller info
            s_info = seller_info_map.get(p["id"], {})
            odoo_lead_time = int(s_info.get("delay", 7))
            
            # ── TRÁNSITO: Fuente canónica = purchase.order.line ───────────────────────
            # Se usa SOLO purchase.order.line con qty_received porque:
            #   - Refleja exactamente lo recibido (incluyendo recepciones parciales)
            #   - qty = product_qty - qty_received = pendiente real
            #   - Cuando el pedido se valida completamente, qty_received == product_qty → pending = 0
            # NO se usa max(po, shipments) porque puede duplicar si ambas fuentes tienen el mismo producto.
            # NO se usa virt-hand fallback porque puede dar valores residuales incorrectos post-recepción.
            pending_qty = pending_map.get(p["id"], 0.0)

            # Audit log (solo si hay movimiento de stock)
            real_qty = float(p.get("qty_available", 0.0) or 0.0)
            if pending_qty > 0 or real_qty > 0:
                print(f"[SYNC] {p.get('default_code') or p['id']}: stock_real={real_qty:.0f}, transito={pending_qty:.0f}")

            std_price = float(p.get("standard_price", 0) or 0)
            if std_price <= 0:
                std_price = float(p.get("list_price", 0) or 0) * 0.7
            
            # Restore overrides if they existed
            ov = existing_overrides.get(p["id"], {})
            
            new_p = Product(
                odoo_id=p["id"],
                name=odoo_name,
                default_code=ref,
                list_price=float(p.get("list_price", 0) or 0),
                standard_price=std_price,
                manual_daily_demand=ov.get("demand"),
                manual_demand_std_dev=ov.get("std_dev"),
                target_service_level=ov.get("service_level"),
                stock_policy_override=ov.get("policy"),
                lead_time_days=ov.get("lead_time", odoo_lead_time),
                incoming_qty=pending_qty,
                reserved_quantity=max(0.0, float(p.get("qty_available", 0.0) or 0.0) - float(p.get("virtual_available", 0.0) or 0.0)),
                location_name="WH/Stock",
                category_name=categ_name,
                description=p.get("description_sale") or p.get("name"),
            )
            session.add(new_p)
            product_odoo_ids.add(p["id"])

        # Flush to make products available for FK checks in quants/moves
        session.flush()

        # Sync stock quants
        for q in connector.get_stock_quants():
            pid = q["product_id"][0] if isinstance(q["product_id"], list) else q["product_id"]
            if pid in product_odoo_ids:
                session.add(StockQuant(
                    odoo_id=q["id"],
                    product_id=pid,
                    location_id=q["location_id"][0] if isinstance(q["location_id"], list) else q["location_id"],
                    quantity=q.get("quantity", 0),
                ))

        # Sync stock moves (last 365 days)
        for m in connector.get_stock_moves(days=500):
            pid = m["product_id"][0] if isinstance(m["product_id"], list) else m["product_id"]
            if pid in product_odoo_ids:
                try:
                    move_date = datetime.strptime(m["date"], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    move_date = datetime.utcnow()
                session.add(StockMove(
                    odoo_id=m["id"],
                    product_id=pid,
                    date=move_date,
                    product_uom_qty=float(m.get("product_uom_qty", 0) or 0),
                    state=m.get("state", "done"),
                    move_type=m.get("move_type", "out"),
                    location_id=m["location_id"][0] if isinstance(m["location_id"], list) else 0,
                    location_dest_id=m["location_dest_id"][0] if isinstance(m["location_dest_id"], list) else 0,
                    picking_type_id=0,
                    expected_date=datetime.strptime(m["date_deadline"], "%Y-%m-%d %H:%M:%S") if m.get("date_deadline") else None,
                ))

        # Sync partners (suppliers)
        for p in connector.get_partners():
            session.add(Partner(
                odoo_id=p["id"],
                name=p["name"],
                email=p.get("email") or "",
                is_supplier=True, # For demo simplicity
                lead_time_days=7 # Default
            ))

        # Sync BOMs
        for b in connector.get_boms():
            # Only add if parent and child exist in our synced products
            if b['parent_id'] in product_odoo_ids and b['child_id'] in product_odoo_ids:
                session.add(BOM(
                    parent_id=b['parent_id'],
                    child_id=b['child_id'],
                    quantity=b['quantity']
                ))

        # Sync Sale Order Lines (Real Sales) - Last 2 years to be safe
        for sl in connector.get_sale_order_lines(days=730):
            pid = sl["product_id"][0] if isinstance(sl["product_id"], (list, tuple)) else sl["product_id"]
            if pid in product_odoo_ids:
                try:
                    sl_date = datetime.strptime(sl["create_date"], "%Y-%m-%d %H:%M:%S")
                except:
                    sl_date = datetime.utcnow()
                
                session.add(SaleOrderLine(
                    odoo_id=sl["id"],
                    product_id=pid,
                    order_id=sl["order_id"][0] if isinstance(sl["order_id"], (list, tuple)) else sl["order_id"],
                    date=sl_date,
                    product_uom_qty=float(sl.get("product_uom_qty", 0) or 0),
                    price_unit=float(sl.get("price_unit", 0) or 0),
                    price_subtotal=float(sl.get("price_subtotal", 0) or 0),
                    state=sl.get("state", "sale")
                ))

        # Finalize sync
        session.commit()

        # Industrial Cold-Start Automation (DEACTIVATED: User wants real data only)
        # real_moves_count = session.exec(select(StockMove).where(StockMove.move_type == 'out')).all()
        # if len(real_moves_count) < 50:
        #    from app.services.demand_simulator import DemandSimulator
        #    DemandSimulator(session).generate_synthetic_history()

        # Then run Analytics (ABC classification and policy calculation)
        from app.services.analytics import AnalyticsService
        AnalyticsService(session).calculate_abc_xyz()

        return {"message": "Sync complete and ABC/XYZ classification recalculated", "products": len(odoo_products)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo sync failed: {str(e)}")


# NOTE: /v1/forecast/* routes are now handled by app.modules.forecast.router
# The legacy endpoints below are kept for backwards compatibility with /v1/sync


@app.post("/v1/cold-start", tags=["Sync"])
def cold_start(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Initializes the system with synthetic sales history to stabilize ABC classification.
    Use this when real Odoo history is insufficient (< 12 months).
    """
    from app.services.demand_simulator import DemandSimulator
    from app.services.analytics import AnalyticsService
    
    simulator = DemandSimulator(session)
    count = simulator.generate_synthetic_history(start_year=2025, end_year=2026)
    
    # Recalculate ABC with the new synthetic data
    AnalyticsService(session).calculate_abc_xyz()
    
    return {"message": "Cold start complete", "synthetic_records": count}


@app.post("/v1/recalculate", tags=["Inventory"])
def recalculate_all(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Recalculate ABC + policy parameters. Also refreshes stock levels and transit from Odoo.
    Lightweight: does NOT delete products, sales history, or moves. Only updates quants + incoming.
    """
    from app.services.analytics import AnalyticsService
    from sqlmodel import text
    try:
        # ── PASO 1: Refresh stock real + tránsito desde Odoo ─────────────────────
        try:
            from app.services.odoo_connector import OdooConnector
            connector = OdooConnector.from_config(session)
            connector.login()

            products_db = session.exec(select(Product)).all()
            product_odoo_ids = {p.odoo_id for p in products_db}

            # 1a. Refresh incoming_qty desde purchase.order.line (fuente canónica)
            # qty = product_qty - qty_received → pendiente real tras recepciones parciales/totales
            pending_map = connector.get_pending_purchases()
            for p in products_db:
                old_incoming = p.incoming_qty or 0.0
                new_incoming = pending_map.get(p.odoo_id, 0.0)
                if old_incoming != new_incoming:
                    if old_incoming > 0 and new_incoming == 0:
                        print(f"[RECALC] ✓ Recepción completa: {p.name} | {old_incoming:.0f} uds → stock real")
                    elif old_incoming > new_incoming:
                        print(f"[RECALC] Recepción parcial: {p.name} | tránsito {old_incoming:.0f} → {new_incoming:.0f}")
                    else:
                        print(f"[RECALC] Nuevo pedido: {p.name} | tránsito {old_incoming:.0f} → {new_incoming:.0f}")
                p.incoming_qty = new_incoming
                session.add(p)
            session.commit()

            # 1b. Refresh stock real (stock.quant) — solo borra y recarga quants, NO productos
            session.exec(text("DELETE FROM stockquant"))
            session.commit()
            quant_count = 0
            for q in connector.get_stock_quants():
                pid = q["product_id"][0] if isinstance(q["product_id"], list) else q["product_id"]
                if pid in product_odoo_ids:
                    loc = q["location_id"][0] if isinstance(q["location_id"], list) else q["location_id"]
                    session.add(StockQuant(
                        odoo_id=q["id"],
                        product_id=pid,
                        location_id=loc,
                        quantity=float(q.get("quantity", 0)),
                    ))
                    quant_count += 1
            session.commit()
            print(f"[RECALC] Stock real: {quant_count} quants actualizados desde Odoo")

        except Exception as odoo_err:
            # Odoo no disponible — continúa solo con recálculo local
            print(f"[RECALC] Odoo no disponible para refresh stock: {odoo_err}")

        # ── PASO 2: Recalcular ABC + parámetros de política ──────────────────────
        AnalyticsService(session).calculate_abc_xyz()
        products_enriched = AnalyticsService(session).get_products_enriched()
        return {"message": "Recalculation complete", "products": len(products_enriched)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recalculation failed: {str(e)}")


# /v1/forecast/{product_id} is now handled by the isolated forecast router


# ─── SIMULATE ─────────────────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    product_ids: List[int]
    demand_delta_pct: float = 0.0
    lead_time_override: Optional[int] = None


@app.post("/v1/simulate", tags=["Simulation"])
def simulate(
    body: SimulateRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    from app.services.analytics import AnalyticsService
    return AnalyticsService(session).simulate_scenario(
        product_ids=body.product_ids,
        demand_delta_pct=body.demand_delta_pct,
        lead_time_override=body.lead_time_override,
    )


# ─── CONFIG ───────────────────────────────────────────────────────────────────

@app.get("/v1/config", tags=["Config"])
def get_config(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    rows = session.exec(select(AppConfig)).all()
    return [{"key": r.key, "value": r.value, "description": r.description} for r in rows]


class ConfigUpdate(BaseModel):
    key: str
    value: str


@app.put("/v1/config", tags=["Config"])
def update_config(
    body: ConfigUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role("admin", "planner")),
):
    row = session.exec(select(AppConfig).where(AppConfig.key == body.key)).first()
    if not row:
        # Allow creating new config keys on-the-fly
        row = AppConfig(key=body.key, value=body.value)
        session.add(row)
    else:
        row.value = body.value
        session.add(row)
    session.commit()
    return {"key": row.key, "value": row.value}


# ─── PURCHASE ORDERS ──────────────────────────────────────────────────────────

class PurchaseOrderRequest(BaseModel):
    product_odoo_id: int
    partner_odoo_id: int
    quantity: float
    price_unit: Optional[float] = None


@app.post("/v1/purchase-orders", tags=["Purchase"])
def create_purchase_order(
    body: PurchaseOrderRequest,
    session: Session = Depends(get_session),
    _: User = Depends(require_role("admin", "planner")),
):
    product = session.exec(select(Product).where(Product.odoo_id == body.product_odoo_id)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    partner = session.exec(select(Partner).where(Partner.odoo_id == body.partner_odoo_id)).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Supplier not found")

    try:
        from app.services.odoo_connector import OdooConnector
        connector = OdooConnector.from_config(session)
        connector.login()
        order_lines = [{
            "product_id": body.product_odoo_id,
            "product_qty": body.quantity,
            "price_unit": body.price_unit or product.standard_price,
            "name": product.name,
            "date_planned": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }]
        po_id = connector.create_purchase_order(body.partner_odoo_id, order_lines)
        return {
            "success": True,
            "odoo_po_id": po_id,
            "message": f"Purchase order created in Odoo (ID: {po_id})",
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Odoo error: {str(e)}",
        )


# ─── SUPPLIERS ────────────────────────────────────────────────────────────────

@app.get("/suppliers", tags=["Purchase"])
def get_suppliers(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    partners = session.exec(select(Partner).where(Partner.is_supplier == True)).all()
    return [{"odoo_id": p.odoo_id, "name": p.name, "lead_time_days": p.lead_time_days, "moq": p.moq} for p in partners]


# ─── SYSTEM SEED ──────────────────────────────────────────────────────────────

@app.post("/system/seed", tags=["System"])
def seed_sample_data(session: Session = Depends(get_session), _: User = Depends(require_role("admin"))):
    # 1. Check if products exist
    existing = session.exec(select(Product)).first()
    if existing:
        return {"message": "Data already exists. Seed skipped."}

    # 2. Create sample finished product
    p1 = Product(odoo_id=1001, name="Bicicleta Pro X1", default_code="BIKE-01", standard_price=450.0, daily_demand=2.5, safety_stock=10, lead_time_days=5)
    p2 = Product(odoo_id=2001, name="Cuadro Aluminio", default_code="FRAME-01", standard_price=120.0, daily_demand=0.0, safety_stock=5, lead_time_days=10)
    p3 = Product(odoo_id=3001, name="Rueda 29\"", default_code="WHEEL-29", standard_price=45.0, daily_demand=0.0, safety_stock=20, lead_time_days=3)
    
    session.add_all([p1, p2, p3])
    session.commit()

    # 3. Create BOM
    bom1 = BOM(parent_id=1001, child_id=2001, quantity=1.0)
    bom2 = BOM(parent_id=1001, child_id=3001, quantity=2.0)
    session.add_all([bom1, bom2])
    
    session.commit()
    return {"message": "Sample data seeded successfully. Explore Daily Plan."}


# ─── HEALTH ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "InvFlow API v2"}
