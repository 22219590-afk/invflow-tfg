"""
sync_odoo.py — Odoo → InvFlow DB synchronization
Strategy: derive the product catalog from actual demand moves, not from product.product list.
This guarantees only products WITH real history are synced (ID alignment guaranteed).
"""
import os
import sys
sys.path.append(os.getcwd())

from datetime import datetime, timedelta
from sqlmodel import Session, create_engine, text
from app.models.models import Product, StockMove

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
engine = create_engine(DATABASE_URL)

HISTORY_DAYS = 730  # 2 years


def sync_from_odoo():
    import xmlrpc.client
    import time

    url = os.getenv("ODOO_URL", "")
    db  = os.getenv("ODOO_DB", "")
    u   = os.getenv("ODOO_USER", "")
    p   = os.getenv("ODOO_PASSWORD", "")

    print(f"Connecting to Odoo at {url}...")
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, u, p, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print(f"Authenticated. UID: {uid}")

    def call(model, method, args, kwargs=None):
        for attempt in range(6):
            try:
                return models.execute_kw(db, uid, p, model, method, args, kwargs or {})
            except Exception as e:
                if '429' in str(e):
                    wait = (attempt + 1) * 5
                    print(f"Rate limit. Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        return None

    since = (datetime.utcnow() - timedelta(days=HISTORY_DAYS)).strftime('%Y-%m-%d %H:%M:%S')

    # ── STEP 1: Get all demand moves ───────────────────────────────────────
    print(f"Fetching outgoing stock moves (last {HISTORY_DAYS} days)...")
    moves_raw = call('stock.move', 'search_read',
        [[('state', '=', 'done'),
          ('date', '>=', since),
          ('location_dest_id.usage', '=', 'customer')]],
        {'fields': ['id', 'product_id', 'date', 'product_uom_qty',
                    'location_id', 'location_dest_id'], 'limit': 20000})
    print(f"  → {len(moves_raw)} demand moves fetched")

    # ── STEP 2: Derive product IDs from moves ──────────────────────────────
    product_id_set = set(m['product_id'][0] for m in moves_raw)
    product_id_list = list(product_id_set)
    print(f"  → {len(product_id_list)} unique products with demand history")

    if not product_id_list:
        print("ERROR: No demand moves found. Check Odoo data and date range.")
        return

    # ── STEP 3: Read product details for those IDs ─────────────────────────
    print("Fetching product details...")
    odoo_products = call('product.product', 'read',
        [product_id_list],
        {'fields': ['id', 'name', 'default_code', 'list_price', 'standard_price',
                    'categ_id', 'seller_ids']})
    print(f"  → {len(odoo_products)} products fetched")

    # ── STEP 4: Write to DB ────────────────────────────────────────────────
    print("Writing to local database...")
    with Session(engine) as session:
        # Clear in FK-safe order
        session.exec(text("DELETE FROM forecastresult"))
        session.exec(text("DELETE FROM forecastmetric"))
        session.exec(text("DELETE FROM saleshistory"))
        session.exec(text("DELETE FROM stockquant"))
        session.exec(text("DELETE FROM stockmove"))
        session.exec(text("DELETE FROM product"))
        session.commit()
        print("  → Cleared old data")

        # Insert products
        valid_ids = set()
        for p_data in odoo_products:
            if not p_data or not p_data.get('id'):
                continue
            name = p_data.get('name') or 'Producto sin nombre'
            std = float(p_data.get('standard_price') or 0)
            if std <= 0:
                std = float(p_data.get('list_price') or 0) * 0.7
            if std <= 0:
                std = 15.0

            categ = p_data.get('categ_id')
            categ_name = categ[1] if (categ and isinstance(categ, list)) else 'General'

            session.add(Product(
                odoo_id=p_data['id'],
                name=name,
                default_code=p_data.get('default_code') or '',
                list_price=float(p_data.get('list_price') or 0),
                standard_price=std,
                category_name=categ_name,
                location_name='WH/Stock',
            ))
            valid_ids.add(p_data['id'])

        session.flush()
        print(f"  → {len(valid_ids)} products inserted")

        # Insert moves
        inserted = 0
        skipped = 0
        for m in moves_raw:
            pid = m['product_id'][0] if isinstance(m['product_id'], list) else m['product_id']
            if pid not in valid_ids:
                skipped += 1
                continue
            try:
                move_date = datetime.strptime(str(m['date']).replace('T', ' ')[:19], '%Y-%m-%d %H:%M:%S')
            except Exception:
                move_date = datetime.utcnow()

            loc_id = m['location_id'][0] if isinstance(m['location_id'], list) else m.get('location_id', 0)
            loc_dest = m['location_dest_id'][0] if isinstance(m['location_dest_id'], list) else m.get('location_dest_id', 0)

            session.add(StockMove(
                odoo_id=m['id'],
                product_id=pid,
                date=move_date,
                product_uom_qty=float(m.get('product_uom_qty') or 0),
                state='done',
                move_type='out',
                location_id=loc_id if isinstance(loc_id, int) else 0,
                location_dest_id=loc_dest if isinstance(loc_dest, int) else 0,
                picking_type_id=0,
            ))
            inserted += 1

        session.commit()
        print(f"  → {inserted} stock moves inserted ({skipped} skipped)")

    print(f"\nSync complete: {len(valid_ids)} products, {inserted} demand moves")

    # ── STEP 5: Forecast Engine ────────────────────────────────────────────
    print("\nRunning Forecast Engine...")
    with Session(engine) as session:
        from app.modules.forecast.services import ForecastEngine
        result = ForecastEngine(session).run_all_products()
        print(f"  → {result}")

    # ── STEP 6: ABC/XYZ Classification ────────────────────────────────────
    print("Running ABC/XYZ classification...")
    with Session(engine) as session:
        from app.services.analytics import AnalyticsService
        try:
            AnalyticsService(session).calculate_abc_xyz()
            print("  → ABC/XYZ done")
        except Exception as e:
            print(f"  → ABC/XYZ warning: {e}")

    print("\n✓ Pipeline completed!")


if __name__ == "__main__":
    sync_from_odoo()
