
import xmlrpc.client
import os
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def export_for_audit():
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # 500 days of history
    date_limit = (datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Domain for ALL moves related to our products
    domain = [
        ['state', '=', 'done'],
        ['date', '>=', date_limit],
        ['product_id.type', 'in', ['product', 'storable', 'consu']]
    ]
    fields = ['product_id', 'product_uom_qty', 'date', 'location_id', 'location_dest_id', 'origin', 'reference']
    
    print("Fetching data from Odoo... please wait.")
    moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read', [domain, fields])
    
    output_file = "/app/auditoria_odoo.csv" # Inside container path
    # We will also try to write to a shared volume if available, 
    # but the easiest is to let the user know where it is.
    
    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Producto', 'Cantidad', 'Fecha', 'Origen (ID)', 'Destino (ID)', 'Documento Origen', 'Referencia'])
        for m in moves:
            writer.writerow([
                m['product_id'][1] if m['product_id'] else '',
                m['product_uom_qty'],
                m['date'],
                m['location_id'][1] if m['location_id'] else '',
                m['location_dest_id'][1] if m['location_dest_id'] else '',
                m['origin'] or '',
                m['reference'] or ''
            ])
            
    print(f"Export complete! {len(moves)} records saved to {output_file}")

if __name__ == "__main__":
    export_for_audit()
