"""
redistribute_odoo_dates.py — Modifies Odoo stock.move dates to create a realistic history.
Distributes moves over the last 14 months to enable proper forecasting.
"""
import os
import xmlrpc.client
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

def redistribute():
    url = get_env_var("ODOO_URL")
    db = get_env_var("ODOO_DB")
    username = get_env_var("ODOO_USER")
    password = get_env_var("ODOO_PASSWORD")

    print(f"Connecting to Odoo: {url}...")
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print(f"Authenticated as UID {uid}")

    # Search for all done customer moves
    print("Searching for moves to redistribute...")
    move_ids = models.execute_kw(db, uid, password, 'stock.move', 'search', [
        [('state', '=', 'done'), ('location_dest_id.usage', '=', 'customer')]
    ])
    print(f"Found {len(move_ids)} moves.")

    if not move_ids:
        print("No moves found to update.")
        return

    now = datetime.now()
    # We want to distribute them over the last 420 days
    start_date = now - timedelta(days=420)
    
    print("Updating dates in Odoo (this might take a while)...")
    batch_size = 50
    for i in range(0, len(move_ids), batch_size):
        batch = move_ids[i:i + batch_size]
        for move_id in batch:
            # Pick a random date between start_date and now
            random_days = random.randint(0, 420)
            random_seconds = random.randint(0, 86400)
            new_date = start_date + timedelta(days=random_days, seconds=random_seconds)
            
            # Format as Odoo expects: YYYY-MM-DD HH:MM:SS
            date_str = new_date.strftime('%Y-%m-%d %H:%M:%S')
            
            try:
                # We update 'date' (the execution date)
                # Note: Some Odoo versions might restrict editing done moves. 
                # If so, we might need to use sudo or direct SQL if we had access, 
                # but via XML-RPC we'll try 'write'.
                models.execute_kw(db, uid, password, 'stock.move', 'write', [[move_id], {'date': date_str}])
            except Exception as e:
                print(f"Failed to update move {move_id}: {e}")
        
        print(f"Processed {min(i + batch_size, len(move_ids))}/{len(move_ids)}...")

    print("Redistribution complete.")

if __name__ == "__main__":
    redistribute()
