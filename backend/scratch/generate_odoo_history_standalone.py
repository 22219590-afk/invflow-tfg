import xmlrpc.client
import os
import random
from datetime import datetime, timedelta

def get_env():
    env = {}
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    env[k] = v.strip('"').strip("'")
    return env

def main():
    env = get_env()
    url = env.get('ODOO_URL')
    db = env.get('ODOO_DB')
    user = env.get('ODOO_USER')
    password = env.get('ODOO_PASSWORD')
    
    if not all([url, db, user, password]):
        print("Error: Missing Odoo credentials in .env")
        return

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    
    print(f"Logged in as {user} (UID: {uid})")
    
    stock_loc = 5    # WH/Stock (Internal)
    customer_loc = 2 # Customers
    
    products = models.execute_kw(db, uid, password, 'product.product', 'search_read', [[('type', 'in', ['product', 'consu'])]], {'fields': ['id', 'display_name', 'uom_id']})
    print(f"Found {len(products)} products.")
    
    count = 0
    for i, p in enumerate(products):
        idx_pct = i / len(products)
        if idx_pct < 0.2:
            num_moves = random.randint(30, 50)
            qty_range = (500, 2000) # Increased to ensure "A" status
        elif idx_pct < 0.5:
            num_moves = random.randint(15, 25)
            qty_range = (100, 300)
        else:
            num_moves = random.randint(2, 6)
            qty_range = (5, 20)

        uom_id = p.get('uom_id', [1])[0] if isinstance(p.get('uom_id'), list) else p.get('uom_id', 1)
        
        print(f"Generating {num_moves} moves for {p['display_name']}")
        
        for _ in range(num_moves):
            qty = round(random.uniform(*qty_range), 2)
            days_ago = random.randint(1, 400)
            date = datetime.now() - timedelta(days=days_ago)
            
            vals = {
                'product_id': p['id'],
                'product_uom_qty': qty,
                'product_uom': uom_id,
                'location_id': stock_loc,
                'location_dest_id': customer_loc,
                'date': date.strftime('%Y-%m-%d %H:%M:%S'),
                'state': 'done'
            }
            try:
                models.execute_kw(db, uid, password, 'stock.move', 'create', [vals])
                count += 1
            except Exception as e:
                print(f" Error: {e}")
                break
        if count > 1000: break

    print(f"Finished. Created {count} moves.")

if __name__ == "__main__":
    main()
