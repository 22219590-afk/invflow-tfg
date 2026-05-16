
import xmlrpc.client
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def generate_full_audit_history():
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    supplier_id = 68
    product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[('type', 'in', ['product', 'consu'])]])
    
    print(f"Generating Purchase history for {len(product_ids)} products...")
    
    for p_id in product_ids:
        # Purchases 2025 (Monthly supply)
        for m in range(1, 13):
            qty = random.randint(150, 400)
            date = datetime(2025, m, 1).strftime('%Y-%m-%d %H:%M:%S')
            
            po_id = models.execute_kw(db, uid, password, 'purchase.order', 'create', [{
                'partner_id': supplier_id,
                'date_order': date,
                'origin': 'HIST_PURCH_2025'
            }])
            models.execute_kw(db, uid, password, 'purchase.order.line', 'create', [{
                'order_id': po_id,
                'product_id': p_id,
                'product_qty': qty,
                'price_unit': 10.0,
                'name': 'Suministro Histórico'
            }])
            try:
                # Confirm PO
                models.execute_kw(db, uid, password, 'purchase.order', 'button_confirm', [[po_id]])
                # Validate Picking
                pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[('purchase_id', '=', po_id)]])
                for p_id_pick in pickings:
                    # In Odoo 17, setting quantity_done is different, using move_ids
                    moves = models.execute_kw(db, uid, password, 'stock.move', 'search', [[('picking_id', '=', p_id_pick)]])
                    for m_id in moves:
                        models.execute_kw(db, uid, password, 'stock.move', 'write', [[m_id], {'quantity_done': qty}])
                    models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[p_id_pick]])
            except Exception as e:
                print(f"Failed to validate PO {po_id}: {e}")

        # Purchases 2026 (Jan to April)
        for m in range(1, 5):
            qty = random.randint(200, 500)
            date = datetime(2026, m, 1).strftime('%Y-%m-%d %H:%M:%S')
            po_id = models.execute_kw(db, uid, password, 'purchase.order', 'create', [{
                'partner_id': supplier_id,
                'date_order': date,
                'origin': 'HIST_PURCH_2026'
            }])
            models.execute_kw(db, uid, password, 'purchase.order.line', 'create', [{
                'order_id': po_id,
                'product_id': p_id,
                'product_qty': qty,
                'price_unit': 12.0,
                'name': 'Suministro 2026'
            }])
            try:
                models.execute_kw(db, uid, password, 'purchase.order', 'button_confirm', [[po_id]])
                pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[('purchase_id', '=', po_id)]])
                for p_id_pick in pickings:
                    moves = models.execute_kw(db, uid, password, 'stock.move', 'search', [[('picking_id', '=', p_id_pick)]])
                    for m_id in moves:
                        models.execute_kw(db, uid, password, 'stock.move', 'write', [[m_id], {'quantity_done': qty}])
                    models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[p_id_pick]])
            except: pass

    print("Purchase history generated and validated.")

if __name__ == "__main__":
    generate_full_audit_history()
