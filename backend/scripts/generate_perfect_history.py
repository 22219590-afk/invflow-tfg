
import xmlrpc.client
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def generate_perfect_history():
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print("Starting data generation with AUDIT_ prefix...")
    
    product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[('type', 'in', ['product', 'consu'])]])
    partner_id = 53
    supplier_id = 68
    
    print(f"Generating high-frequency history for {len(product_ids)} products...")
    
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 4, 30)
    
    total_moves_to_patch = []

    for p_id in product_ids:
        # Generate moves for each month
        curr = start_date
        while curr <= end_date:
            m = curr.month
            y = curr.year
            
            # --- SALES (1-2 times a week) ---
            monthly_sales_target = random.randint(150, 400)
            if m in [6, 7, 12]: monthly_sales_target *= 1.5 # Seasonality
            
            sales_count = random.randint(5, 8) # Reduced frequency for stability
            for _ in range(sales_count):
                qty = monthly_sales_target // sales_count
                day = random.randint(1, 28)
                exact_date = datetime(y, m, day, random.randint(9, 18), random.randint(0, 59)).strftime('%Y-%m-%d %H:%M:%S')
                
                so_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [{
                    'partner_id': partner_id, 'date_order': exact_date, 'origin': f'AUDIT_S_{y}_{m}'
                }])
                models.execute_kw(db, uid, password, 'sale.order.line', 'create', [{
                    'order_id': so_id, 'product_id': p_id, 'product_uom_qty': qty, 'price_unit': 45.0
                }])
                try:
                    models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [[so_id]])
                    # Validate Picking
                    picks = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[('sale_id', '=', so_id)]])
                    for pk in picks:
                        moves = models.execute_kw(db, uid, password, 'stock.move', 'search', [[('picking_id', '=', pk)]])
                        for mid in moves: 
                            models.execute_kw(db, uid, password, 'stock.move', 'write', [[mid], {'quantity_done': qty, 'date': exact_date}])
                        models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[pk]])
                        # Patch date AGAIN after validation because validation overrides it
                        for mid in moves: total_moves_to_patch.append((mid, exact_date))
                except: pass

            # --- PRODUCTION (2026 only, 1 time a week) ---
            if y == 2026:
                prod_count = random.randint(4, 5)
                for _ in range(prod_count):
                    qty = random.randint(30, 60)
                    day = random.randint(1, 28)
                    exact_date = datetime(y, m, day, random.randint(7, 15), random.randint(0, 59)).strftime('%Y-%m-%d %H:%M:%S')
                    
                    mo_id = models.execute_kw(db, uid, password, 'mrp.production', 'create', [{
                        'product_id': p_id, 'product_qty': qty, 'product_uom_id': 1, 'date_start': exact_date, 'origin': f'AUDIT_P_{y}_{m}'
                    }])
                    try:
                        models.execute_kw(db, uid, password, 'mrp.production', 'action_confirm', [[mo_id]])
                        models.execute_kw(db, uid, password, 'mrp.production', 'write', [[mo_id], {'qty_producing': qty, 'date_finished': exact_date}])
                        models.execute_kw(db, uid, password, 'mrp.production', 'button_mark_done', [[mo_id]])
                        # MO moves
                        moves = models.execute_kw(db, uid, password, 'stock.move', 'search', [[('production_id', '=', mo_id)]])
                        for mid in moves: total_moves_to_patch.append((mid, exact_date))
                    except: pass

            # --- PURCHASES (Once a month) ---
            qty_pur = random.randint(200, 600)
            exact_date_pur = datetime(y, m, 1, 10, 0).strftime('%Y-%m-%d %H:%M:%S')
            po_id = models.execute_kw(db, uid, password, 'purchase.order', 'create', [{
                'partner_id': supplier_id, 'date_order': exact_date_pur, 'origin': f'AUDIT_B_{y}_{m}'
            }])
            models.execute_kw(db, uid, password, 'purchase.order.line', 'create', [{
                'order_id': po_id, 'product_id': p_id, 'product_qty': qty_pur, 'price_unit': 15.0, 'name': 'Stock'
            }])
            try:
                models.execute_kw(db, uid, password, 'purchase.order', 'button_confirm', [[po_id]])
                picks = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[('purchase_id', '=', po_id)]])
                for pk in picks:
                    moves = models.execute_kw(db, uid, password, 'stock.move', 'search', [[('picking_id', '=', pk)]])
                    for mid in moves: 
                        models.execute_kw(db, uid, password, 'stock.move', 'write', [[mid], {'quantity_done': qty_pur}])
                    models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[pk]])
                    for mid in moves: total_moves_to_patch.append((mid, exact_date_pur))
            except: pass

            curr += timedelta(days=32)
            curr = curr.replace(day=1)

    print(f"Patching {len(total_moves_to_patch)} move dates to force historical timeline...")
    # Batch patching for speed
    for mid, date in total_moves_to_patch:
        try:
            models.execute_kw(db, uid, password, 'stock.move', 'write', [[mid], {'date': date}])
        except: pass

    print("Success! Perfect logical history generated.")

if __name__ == "__main__":
    generate_perfect_history()
