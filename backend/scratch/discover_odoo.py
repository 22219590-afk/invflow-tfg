
import xmlrpc.client
import os
from dotenv import load_dotenv

load_dotenv()

def discover():
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # Check product fields
    fields = models.execute_kw(db, uid, password, 'product.template', 'fields_get', [], {'attributes': ['string', 'type', 'help']})
    print("Product Template Fields found:", "type" in fields, "is_storable" in fields, "standard_price" in fields, "list_price" in fields)
    if "is_storable" in fields:
        print("is_storable is present")
    
    # Check if we can find some categories
    cats = models.execute_kw(db, uid, password, 'product.category', 'search_read', [[], ['name']], {'limit': 5})
    print("Categories:", cats)

    # Check partners
    partners = models.execute_kw(db, uid, password, 'res.partner', 'search_read', [[('is_company', '=', True)], ['name']], {'limit': 5})
    print("Partners:", partners)

if __name__ == "__main__":
    discover()
