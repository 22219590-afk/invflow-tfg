
import xmlrpc.client
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def generate_history():
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # 1. Get products
    product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[('type', 'in', ['product', 'consu'])]])
    if not product_ids:
        print("No storable products found.")
        return
    
    # Locations from Odoo
    loc_src = 5 # WH/Stock
    loc_dest_customer = 2 # Customers
    loc_dest_prod = 5 # WH/Stock (for finished products)
    loc_src_prod = 12 # Production Virtual
    
    print(f"Generating history for {len(product_ids)} products...")
    
    current_year = 2026
    current_month = 5
    
    moves_to_create = []
    
    for p_id in product_ids:
        # 2025 Sales
        for m in range(1, 13):
            qty = random.randint(80, 250)
            # Spread sales across the month
            for _ in range(random.randint(2, 4)):
                d_qty = qty // 3
                date = datetime(2025, m, random.randint(1, 28)).strftime('%Y-%m-%d %H:%M:%S')
                moves_to_create.append({
                    'reference': f'HIST_SALES_2025_{m}',
                    'product_id': p_id,
                    'product_uom_qty': d_qty,
                    'product_uom': 1,
                    'location_id': loc_src,
                    'location_dest_id': loc_dest_customer,
                    'date': date,
                    'state': 'done'
                })
            
        # 2026 Sales & Production (Jan to April)
        for m in range(1, current_month):
            # Sales
            qty_s = random.randint(100, 300)
            for _ in range(random.randint(2, 4)):
                d_qty_s = qty_s // 3
                date_s = datetime(2026, m, random.randint(1, 28)).strftime('%Y-%m-%d %H:%M:%S')
                moves_to_create.append({
                    'reference': f'HIST_SALES_2026_{m}',
                    'product_id': p_id,
                    'product_uom_qty': d_qty_s,
                    'product_uom': 1,
                    'location_id': loc_src,
                    'location_dest_id': loc_dest_customer,
                    'date': date_s,
                    'state': 'done'
                })
            
            # Production
            qty_p = qty_s + random.randint(-10, 40)
            date_p = datetime(2026, m, random.randint(1, 28)).strftime('%Y-%m-%d %H:%M:%S')
            moves_to_create.append({
                'reference': f'HIST_PROD_2026_{m}',
                'product_id': p_id,
                'product_uom_qty': qty_p,
                'product_uom': 1,
                'location_id': loc_src_prod,
                'location_dest_id': loc_dest_prod,
                'date': date_p,
                'state': 'done'
            })

    print(f"Total moves to push: {len(moves_to_create)}")
    
    # Push to Odoo in batches
    batch_size = 40
    for i in range(0, len(moves_to_create), batch_size):
        batch = moves_to_create[i:i+batch_size]
        try:
            models.execute_kw(db, uid, password, 'stock.move', 'create', [batch])
            print(f"Pushed {i + len(batch)} / {len(moves_to_create)} moves...")
        except Exception as e:
            print(f"Error in batch {i}: {e}")

    print("Success! Odoo history generated.")

if __name__ == "__main__":
    generate_history()
