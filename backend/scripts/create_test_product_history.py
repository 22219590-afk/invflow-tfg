"""
create_test_product_history.py — Creates a test product in Odoo with a controlled history.
Used to verify forecasting accuracy.
"""
import os
import xmlrpc.client
import math
import random
from datetime import datetime, timedelta

def get_env_var(key):
    try:
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if not os.path.exists(env_path):
            env_path = '.env'
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    if k.strip() == key:
                        return v.strip().strip('"').strip("'")
    except Exception:
        pass
    return os.getenv(key, '')

def create_test_data():
    url = get_env_var("ODOO_URL")
    db = get_env_var("ODOO_DB")
    username = get_env_var("ODOO_USER")
    password = get_env_var("ODOO_PASSWORD")

    print(f"Connecting to Odoo: {url}...")
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print(f"Authenticated as UID {uid}")

    # 1. Create Product
    product_name = "Producto Prueba"
    print(f"Creating product: {product_name}...")
    
    # Check if exists
    existing = models.execute_kw(db, uid, password, 'product.product', 'search', [[('name', '=', product_name)]])
    if existing:
        product_id = existing[0]
        print(f"Product already exists (ID: {product_id}), reusing.")
    else:
        product_id = models.execute_kw(db, uid, password, 'product.product', 'create', [{
            'name': product_name,
            'default_code': 'TEST-PROD-01',
            'list_price': 100.0,
            'standard_price': 60.0,
            'type': 'consu',
            'sale_ok': True,
            'purchase_ok': True,
        }])
        print(f"Created product ID: {product_id}")

    # 2. Get Locations
    # We need a customer location (usage='customer') and a warehouse location (usage='internal')
    customer_loc = models.execute_kw(db, uid, password, 'stock.location', 'search', [[('usage', '=', 'customer')]])[0]
    stock_loc = models.execute_kw(db, uid, password, 'stock.location', 'search', [[('usage', '=', 'internal')]])[0]

    # 3. Generate History (2025-01-01 to today)
    print("Generating sales history...")
    start_date = datetime(2025, 1, 1)
    end_date = datetime.now()
    
    current_date = start_date
    total_moves = 0
    
    # We'll create one sale every 3-4 days to create a dense history
    while current_date < end_date:
        # Business logic for the pattern:
        # weeks = days / 7
        days_passed = (current_date - start_date).days
        weeks_passed = days_passed / 7.0
        
        # Base demand + Trend + Seasonality (peak in summer/July)
        # 52 weeks in a year. Sine peak at week 26 (July)
        seasonality = 20 * math.sin(2 * math.pi * (weeks_passed - 13) / 52.0)
        trend = weeks_passed * 0.4
        base = 40
        noise = random.uniform(-5, 5)
        
        qty = max(1, int(base + trend + seasonality + noise))
        
        date_str = current_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Create stock move
        models.execute_kw(db, uid, password, 'stock.move', 'create', [{
            'description_picking': f'Venta Test {current_date.strftime("%Y-%m-%d")}',
            'product_id': product_id,
            'product_uom_qty': qty,
            'quantity': qty,
            'product_uom': 1, # Unit
            'location_id': stock_loc,
            'location_dest_id': customer_loc,
            'date': date_str,
            'state': 'done',
        }])
        
        # Advance 3-5 days
        current_date += timedelta(days=random.randint(3, 5))
        total_moves += 1
        if total_moves % 20 == 0:
            print(f" Created {total_moves} moves...")

    print(f"Finished! Created {total_moves} historical sales for '{product_name}'.")

if __name__ == "__main__":
    create_test_data()
