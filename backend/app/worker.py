from celery import Celery
import os
from app.services.odoo_connector import OdooConnector
from app.services.analytics import AnalyticsService
from app.models.models import Product, StockMove, StockQuant, Partner
from sqlmodel import Session, create_engine, select, text

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")

celery_app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)
engine = create_engine(DATABASE_URL)

@celery_app.task
def sync_odoo_data():
    connector = OdooConnector.from_config()
    connector.login()

    with Session(engine) as session:
        # Sync Products
        odoo_products = connector.get_products()
        for p in odoo_products:
            obj = session.exec(select(Product).where(Product.odoo_id == p['id'])).first()
            if not obj:
                obj = Product(odoo_id=p['id'], name=p['name'], default_code=p['default_code'])
                session.add(obj)
            else:
                obj.name = p['name']
                obj.default_code = p['default_code']
            
            import random
            random.seed(p['id'])
            if not obj.manual_daily_demand or obj.manual_daily_demand <= 0:
                obj.manual_daily_demand = round(random.uniform(1.0, 50.0), 2)
                obj.manual_demand_std_dev = round(obj.manual_daily_demand * 0.2, 2)
            
            # Ensure standard price is strictly positive for EOQ calculation
            obj.standard_price = float(p.get('standard_price', 0.0) or 0.0)
            if obj.standard_price <= 0:
                obj.standard_price = round(random.uniform(5.0, 100.0), 2)
        session.commit()
        
        # Get valid product odoo_ids
        valid_product_ids = {p.odoo_id for p in session.exec(select(Product)).all()}

        # Sync Stock
        odoo_quants = connector.get_stock_quants()
        # Clear old quants and reload
        session.exec(text("DELETE FROM stockquant"))
        for q in odoo_quants:
            if q['product_id'][0] in valid_product_ids:
                sq = StockQuant(
                    odoo_id=q['id'],
                    product_id=q['product_id'][0],
                    location_id=q['location_id'][0],
                    quantity=q['quantity']
                )
                session.add(sq)

        # Sync Moves
        odoo_moves = connector.get_stock_moves()
        session.exec(text("DELETE FROM stockmove"))
        for m in odoo_moves:
            if m['product_id'][0] in valid_product_ids:
                sm = StockMove(
                    odoo_id=m['id'],
                    product_id=m['product_id'][0],
                    date=m['date'],
                    product_uom_qty=m['product_uom_qty'],
                    state=m['state'],
                    location_id=m['location_id'][0],
                    location_dest_id=m['location_dest_id'][0],
                    picking_type_id=0 # Placeholder
                )
                session.add(sm)

        # Sync partners (suppliers)
        session.exec(text("DELETE FROM partner"))
        for p in connector.get_partners():
            session.add(Partner(
                odoo_id=p["id"],
                name=p["name"],
                email=p.get("email") or "",
                is_supplier=True,
                lead_time_days=7
            ))

        session.commit()
        
        # After sync, run analytics
        analytics = AnalyticsService(session)
        analytics.calculate_abc_xyz()

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Sync every day at midnight (example)
    sender.add_periodic_task(86400.0, sync_odoo_data.s(), name='daily sync')
