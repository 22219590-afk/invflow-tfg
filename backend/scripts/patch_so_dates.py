
import xmlrpc.client
import os
from dotenv import load_dotenv

load_dotenv()

def patch_so_dates():
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    sos = models.execute_kw(db, uid, password, 'sale.order', 'search_read', [[('origin', 'like', 'AUDIT_S_')]], {'fields': ['origin']})
    print(f"Patching {len(sos)} SOs...")
    
    for s in sos:
        try:
            parts = s['origin'].split('_')
            # AUDIT_S_YEAR_MONTH
            y = parts[2]
            m = parts[3]
            date_str = f"{y}-{m.zfill(2)}-15 10:00:00"
            models.execute_kw(db, uid, password, 'sale.order', 'write', [[s['id']], {'date_order': date_str}])
        except Exception as e:
            pass

if __name__ == "__main__":
    patch_so_dates()
