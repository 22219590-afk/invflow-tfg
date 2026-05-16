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
    except: pass
    return os.getenv(key)

def call_odoo(models, db, uid, password, model, method, args, kwargs=None):
    if kwargs is None: kwargs = {}
    for attempt in range(5):
        try: return models.execute_kw(db, uid, password, model, method, args, kwargs)
        except Exception as e:
            if "429" in str(e): time.sleep((attempt + 1) * 5)
            else: raise e
    return None

def run():
    url, db, u, p = get_env_var("ODOO_URL"), get_env_var("ODOO_DB"), get_env_var("ODOO_USER"), get_env_var("ODOO_PASSWORD")
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, u, p, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    print("--- 1. BORRADO TOTAL DE DATOS ANTERIORES ---")
    try:
        # Cancel and delete sales
        sales = call_odoo(models, db, uid, p, 'sale.order', 'search', [[]])
        if sales:
            call_odoo(models, db, uid, p, 'sale.order', 'action_cancel', [sales])
            call_odoo(models, db, uid, p, 'sale.order', 'unlink', [sales])
        # Cancel and delete purchases
        purchases = call_odoo(models, db, uid, p, 'purchase.order', 'search', [[]])
        if purchases:
            call_odoo(models, db, uid, p, 'purchase.order', 'button_cancel', [purchases])
            call_odoo(models, db, uid, p, 'purchase.order', 'unlink', [purchases])
        # Archive all products to clear catalog
        prods = call_odoo(models, db, uid, p, 'product.template', 'search', [[]])
        if prods: call_odoo(models, db, uid, p, 'product.template', 'write', [prods, {'active': False}])
    except Exception as e: print("Error en borrado (ignorando):", e)

    print("--- 2. CREANDO EMPRESA REAL: EMPLEADOS ---")
    for name in ["Carlos Martínez (Resp. Almacén)", "Laura Gómez (Compras)", "Javier Ruiz (Ventas)"]:
        call_odoo(models, db, uid, p, 'hr.employee', 'create', [{'name': name}])

    print("--- 3. CREANDO PROVEEDORES Y CLIENTES ---")
    supplier_names = ["Aceros del Norte SA", "ElectroComponentes Global", "Suministros Industriales Iberia", "Plásticos y Moldeados", "TechParts EU"]
    customer_names = ["Construcciones Omega", "Talleres Mecánicos del Sur", "Ensamblajes Tecnológicos S.L.", "Distribuciones Automotrices", "Ingeniería Robótica Avanzada", "Manufacturas Delta", "Sistemas Hidráulicos", "Aeroestructuras S.A."]
    
    supplier_ids = []
    for name in supplier_names:
        supplier_ids.append(call_odoo(models, db, uid, p, 'res.partner', 'create', [{'name': name, 'is_company': True}]))
    
    customer_ids = []
    for name in customer_names:
        customer_ids.append(call_odoo(models, db, uid, p, 'res.partner', 'create', [{'name': name, 'is_company': True}]))

    print("--- 4. CREANDO CATÁLOGO DE PRODUCTOS REAL ---")
    prod_defs = [
        ("Motor Eléctrico 500W", 'A', 45.0, 7), ("Placa Base Industrial", 'A', 120.0, 14), 
        ("Eje de Acero 10mm", 'A', 5.0, 3), ("Rodamiento ABEC-7", 'A', 8.0, 5),
        ("Carcasa de Aluminio", 'B', 25.0, 10), ("Sensor de Temperatura", 'B', 15.0, 12),
        ("Cableado Estructurado 5m", 'B', 12.0, 7), ("Panel LCD de Control", 'B', 85.0, 20),
        ("Tornillería Acero Inox (Pack)", 'C', 2.0, 3), ("Fusibles Industriales", 'C', 1.5, 4),
        ("Correa de Transmisión", 'C', 18.0, 10), ("Bomba Hidráulica Mini", 'C', 150.0, 30)
    ]
    
    products = []
    for name, abc, cost, lead in prod_defs:
        t_id = call_odoo(models, db, uid, p, 'product.template', 'create', [{
            'name': name, 'type': 'consu', 'is_storable': True, 
            'list_price': cost * 1.8, 'standard_price': cost
        }])
        p_id = call_odoo(models, db, uid, p, 'product.product', 'search', [[('product_tmpl_id', '=', t_id)]])[0]
        
        call_odoo(models, db, uid, p, 'product.supplierinfo', 'create', [{
            'partner_id': random.choice(supplier_ids), 'product_tmpl_id': t_id, 'delay': lead, 'price': cost
        }])
        products.append({'id': p_id, 'abc': abc, 'cost': cost, 'lead_time': lead})

    print("--- 5. GENERANDO HISTORIAL DE VENTAS Y COMPRAS REALISTA ---")
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 12, 31)
    
    current_date = start_date
    while current_date <= end_date:
        # Ventas (2-3 pedidos por semana)
        for _ in range(random.randint(2, 3)):
            order_date = current_date + timedelta(days=random.randint(0, 6))
            if order_date > end_date: break
            
            so_id = call_odoo(models, db, uid, p, 'sale.order', 'create', [{
                'partner_id': random.choice(customer_ids),
                'date_order': order_date.strftime('%Y-%m-%d %H:%M:%S')
            }])
            
            lines = []
            for prod in products:
                prob = 0.8 if prod['abc'] == 'A' else (0.4 if prod['abc'] == 'B' else 0.1)
                if random.random() < prob:
                    qty = random.randint(50, 200) if prod['abc'] == 'A' else random.randint(10, 50)
                    lines.append({'order_id': so_id, 'product_id': prod['id'], 'product_uom_qty': qty, 'price_unit': prod['cost'] * 1.8})
            if lines:
                call_odoo(models, db, uid, p, 'sale.order.line', 'create', [lines])
                call_odoo(models, db, uid, p, 'sale.order', 'action_confirm', [[so_id]])
        
        # Compras (1 vez al mes)
        if current_date.day <= 7: 
            for s_id in random.sample(supplier_ids, 2):
                po_id = call_odoo(models, db, uid, p, 'purchase.order', 'create', [{
                    'partner_id': s_id, 'date_order': current_date.strftime('%Y-%m-%d %H:%M:%S')
                }])
                po_lines = []
                for prod in products:
                    if random.random() < 0.3:
                        po_lines.append({'order_id': po_id, 'product_id': prod['id'], 'product_qty': random.randint(100, 500), 'price_unit': prod['cost']})
                if po_lines:
                    call_odoo(models, db, uid, p, 'purchase.order.line', 'create', [po_lines])
                    call_odoo(models, db, uid, p, 'purchase.order', 'button_confirm', [[po_id]])
        
        current_date += timedelta(days=7)

    print("--- 6. SIMULACIÓN COMPLETADA CON ÉXITO ---")

if __name__ == "__main__":
    run()
