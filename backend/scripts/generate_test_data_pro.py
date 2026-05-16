
import xmlrpc.client
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def generate_pro_history():
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    print("Cleaning up previous low-level moves...")
    old_moves = models.execute_kw(db, uid, password, 'stock.move', 'search', [[('reference', 'like', 'HIST_')]])
    if old_moves:
        models.execute_kw(db, uid, password, 'stock.move', 'unlink', [old_moves])
    
    # 1. Create Employees (Total 15)
    existing_emps = models.execute_kw(db, uid, password, 'hr.employee', 'search_count', [[]])
    to_create = 15 - existing_emps
    if to_create > 0:
        print(f"Creating {to_create} employees...")
        for i in range(to_create):
            models.execute_kw(db, uid, password, 'hr.employee', 'create', [{
                'name': f'Operario MPS {i+1}',
                'job_id': False,
                'work_email': f'operario{i+1}@empresa.com'
            }])

    # 2. Get products
    product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[('type', 'in', ['product', 'consu'])]])
    partner_id = 53 # Found earlier
    
    print(f"Generating MOs and SOs for {len(product_ids)} products...")
    
    for p_id in product_ids:
        # 2025 Sales (Sale Orders)
        for m in range(1, 13):
            qty = random.randint(100, 300)
            date = datetime(2025, m, random.randint(1, 28)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Create Sale Order
            so_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [{
                'partner_id': partner_id,
                'date_order': date,
                'origin': 'HIST_DATA_2025'
            }])
            # Create Line
            models.execute_kw(db, uid, password, 'sale.order.line', 'create', [{
                'order_id': so_id,
                'product_id': p_id,
                'product_uom_qty': qty,
                'price_unit': 50.0
            }])
            # Confirm SO (this creates stock moves)
            try:
                models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [[so_id]])
            except: pass # Ignore if fails
            
        # 2026 Sales & Manufacturing
        for m in range(1, 5):
            # Sale Order
            date_s = datetime(2026, m, random.randint(1, 28)).strftime('%Y-%m-%d %H:%M:%S')
            so_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [{
                'partner_id': partner_id,
                'date_order': date_s,
                'origin': 'HIST_DATA_2026'
            }])
            models.execute_kw(db, uid, password, 'sale.order.line', 'create', [{
                'order_id': so_id,
                'product_id': p_id,
                'product_uom_qty': random.randint(100, 300)
            }])
            try: models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [[so_id]]) 
            except: pass
            
            # Manufacturing Order
            date_p = datetime(2026, m, random.randint(1, 28)).strftime('%Y-%m-%d %H:%M:%S')
            mo_id = models.execute_kw(db, uid, password, 'mrp.production', 'create', [{
                'product_id': p_id,
                'product_qty': random.randint(100, 300),
                'product_uom_id': 1,
                'date_start': date_p,
                'origin': 'HIST_PROD_2026'
            }])
            # Confirm MO
            try:
                models.execute_kw(db, uid, password, 'mrp.production', 'action_confirm', [[mo_id]])
            except: pass

    print("Success! Odoo Pro history generated. Orders are now visible in Fabricación/Ventas.")

if __name__ == "__main__":
    generate_pro_history()
