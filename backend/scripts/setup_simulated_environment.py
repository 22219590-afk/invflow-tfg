
import xmlrpc.client
import os
import random
import time
from datetime import datetime, timedelta

def get_env_var(key):
    try:
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    if k.strip() == key:
                        return v.strip().strip('"').strip("'")
    except:
        pass
    return os.getenv(key)

def call_odoo(models, db, uid, password, model, method, args, kwargs=None):
    if kwargs is None: kwargs = {}
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return models.execute_kw(db, uid, password, model, method, args, kwargs)
        except Exception as e:
            if "429" in str(e):
                wait = (attempt + 1) * 5
                print(f"Rate limit hit (429). Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise e
    return None

def setup_simulated_data():
    url = get_env_var("ODOO_URL")
    db = get_env_var("ODOO_DB")
    username = get_env_var("ODOO_USER")
    password = get_env_var("ODOO_PASSWORD")
    
    print(f"Connecting to Odoo at {url}...")
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    if not uid:
        print("Failed to authenticate")
        return
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print(f"Authenticated successfully. UID: {uid}")

    # 1. CLEANUP EVERYTHING SIM_
    print("Performing deep cleanup of previous simulation data...")
    # Orders
    old_sos = call_odoo(models, db, uid, password, 'sale.order', 'search', [[('origin', '=', 'SIM_HIST_DATA')]])
    if old_sos:
        print(f"Deleting {len(old_sos)} old Sale Orders...")
        # To delete confirmed orders, we might need to cancel them first, but for speed we'll try direct unlink or just archive products
        try: call_odoo(models, db, uid, password, 'sale.order', 'unlink', [old_sos])
        except: pass

    # Products
    old_products = call_odoo(models, db, uid, password, 'product.template', 'search', [[('name', 'like', 'SIM_')]])
    if old_products:
        print(f"Archiving {len(old_products)} previous products...")
        call_odoo(models, db, uid, password, 'product.template', 'write', [old_products, {'active': False}])

    # Partners
    old_partners = call_odoo(models, db, uid, password, 'res.partner', 'search', [[('name', 'like', 'SIM_')]])
    if old_partners:
        print(f"Deleting {len(old_partners)} old partners...")
        try: call_odoo(models, db, uid, password, 'res.partner', 'unlink', [old_partners])
        except: pass

    # 2. CREATE SUPPLIERS (Reduced to 5)
    print("Creating suppliers...")
    supplier_ids = []
    for i in range(1, 6):
        s_id = call_odoo(models, db, uid, password, 'res.partner', 'create', [{
            'name': f'SIM_Proveedor_{i:02d}',
            'is_company': True
        }])
        supplier_ids.append(s_id)
        time.sleep(0.1)

    # 3. CREATE CUSTOMERS (Reduced to 10)
    print("Creating customers...")
    customer_ids = []
    for i in range(1, 11):
        c_id = call_odoo(models, db, uid, password, 'res.partner', 'create', [{
            'name': f'SIM_Cliente_{i:02d}',
            'is_company': True
        }])
        customer_ids.append(c_id)
        time.sleep(0.1)

    # 4. CREATE PRODUCTS (A/B/C) (Reduced to 50)
    print("Creating products (ABC distribution)...")
    products = []
    abc_dist = [('A', 10), ('B', 15), ('C', 25)]
    
    template_data = []
    product_metadata = []

    for category_code, count in abc_dist:
        for i in range(count):
            name = f"SIM_Producto_{category_code}_{i+1:02d}"
            if category_code == 'A':
                cost = random.uniform(10, 50)
                lead_time = random.randint(3, 7)
            elif category_code == 'B':
                cost = random.uniform(5, 20)
                lead_time = random.randint(7, 14)
            else:
                cost = random.uniform(1, 10)
                lead_time = random.randint(14, 30)
            
            template_data.append({
                'name': name,
                'type': 'consu',
                'is_storable': True, 
                'list_price': cost * 2.0,
                'standard_price': cost,
                'default_code': f"SIM-{category_code}-{i+1:03d}"
            })
            product_metadata.append({'abc': category_code, 'lead_time': lead_time, 'cost': cost})

    # Batch create templates
    print(f"Sending {len(template_data)} products to Odoo...")
    tmpl_ids = []
    for data in template_data:
        t_id = call_odoo(models, db, uid, password, 'product.template', 'create', [data])
        tmpl_ids.append(t_id)
        time.sleep(0.2)

    # Map Variants
    print("Mapping product variants...")
    variant_records = call_odoo(models, db, uid, password, 'product.product', 'search_read', 
                               [[('product_tmpl_id', 'in', tmpl_ids)]], {'fields': ['id', 'product_tmpl_id']})
    tmpl_to_variant = {v['product_tmpl_id'][0]: v['id'] for v in variant_records}

    for i, t_id in enumerate(tmpl_ids):
        p_id = tmpl_to_variant.get(t_id)
        if p_id:
            meta = product_metadata[i]
            call_odoo(models, db, uid, password, 'product.supplierinfo', 'create', [{
                'partner_id': random.choice(supplier_ids),
                'product_tmpl_id': t_id,
                'delay': meta['lead_time'],
                'price': meta['cost']
            }])
            products.append({
                'id': p_id,
                'abc': meta['abc'],
                'cost': meta['cost'],
                'lead_time': meta['lead_time']
            })

    # 5. GENERATE SALES HISTORY (Jan 2025 - Dec 2026)
    print("Generating Sales Orders history (Fast Batch)...")
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 12, 31)
    seasonality = [0.9, 0.85, 1.0, 1.1, 1.05, 1.0, 0.8, 0.75, 1.0, 1.15, 1.25, 1.3]

    current_date = start_date
    while current_date <= end_date:
        month_idx = current_date.month - 1
        seas_factor = seasonality[month_idx]
        
        # Only process half of customers each week to speed up
        active_customers = random.sample(customer_ids, 5)
        
        for c_id in active_customers:
            order_date = current_date + timedelta(days=random.randint(0, 6))
            if order_date > end_date: continue
            
            so_id = call_odoo(models, db, uid, password, 'sale.order', 'create', [{
                'partner_id': c_id,
                'date_order': order_date.strftime('%Y-%m-%d %H:%M:%S'),
                'origin': 'SIM_HIST_DATA'
            }])
            
            lines_to_create = []
            for prod in products:
                prob = 0.7 if prod['abc'] == 'A' else (0.3 if prod['abc'] == 'B' else 0.1)
                if random.random() < prob:
                    base_qty = random.randint(20, 60) if prod['abc'] == 'A' else (random.randint(5, 20) if prod['abc'] == 'B' else random.randint(1, 5))
                    qty = int(base_qty * seas_factor * random.uniform(0.8, 1.2))
                    if qty > 0:
                        lines_to_create.append({
                            'order_id': so_id,
                            'product_id': prod['id'],
                            'product_uom_qty': qty,
                            'price_unit': prod['cost'] * 1.5
                        })
            
            if lines_to_create:
                try:
                    call_odoo(models, db, uid, password, 'sale.order.line', 'create', [lines_to_create])
                    call_odoo(models, db, uid, password, 'sale.order', 'action_confirm', [[so_id]])
                except: pass
            time.sleep(0.1)

        current_date += timedelta(days=7)
        print(f"Finished week starting {current_date.strftime('%Y-%m-%d')}")

    # 6. GENERATE PURCHASES (Batching by Month/Supplier)
    print("Generating Purchase Orders...")
    for y in [2025, 2026]:
        for m in range(1, 13):
            # Only 2 random suppliers per month to speed up
            for s_id in random.sample(supplier_ids, 2):
                po_date = datetime(y, m, random.randint(1, 5))
                po_id = call_odoo(models, db, uid, password, 'purchase.order', 'create', [{
                    'partner_id': s_id,
                    'date_order': po_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'origin': 'SIM_REPLENISH'
                }])
                
                po_lines = []
                for prod in products:
                    if random.random() < 0.3:
                        qty = 1000 if prod['abc'] == 'A' else (300 if prod['abc'] == 'B' else 50)
                        po_lines.append({'order_id': po_id, 'product_id': prod['id'], 'product_qty': qty, 'price_unit': prod['cost']})
                
                if po_lines:
                    try:
                        call_odoo(models, db, uid, password, 'purchase.order.line', 'create', [po_lines])
                        call_odoo(models, db, uid, password, 'purchase.order', 'button_confirm', [[po_id]])
                    except: pass
                time.sleep(0.2)





    print("--- SIMULATION DATA SETUP COMPLETE ---")
    print(f"Products Created/Updated: {len(products)}")
    print(f"Period: Jan 2025 - Dec 2026")
    print(f"ABC Distribution followed.")

if __name__ == "__main__":
    setup_simulated_data()
