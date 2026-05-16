import sys
import os
from datetime import datetime, timedelta
import random

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.odoo_connector import OdooConnector

def main():
    connector = OdooConnector.from_config()
    connector.login()
    
    print("Finding locations...")
    stock_loc = connector.find_location_by_usage('internal')
    customer_loc = connector.find_location_by_usage('customer')
    
    if not stock_loc or not customer_loc:
        print(f"Error: Locations not found. Stock: {stock_loc}, Customer: {customer_loc}")
        # Fallback to common defaults if search fails
        stock_loc = stock_loc or 8
        customer_loc = customer_loc or 5
    
    print(f"Using Stock Location: {stock_loc}, Customer Location: {customer_loc}")
    
    print("Fetching products...")
    products = connector.get_products()
    print(f"Found {len(products)} products.")
    
    # Fetch moves for last 500 days to see who is missing data
    print("Checking existing moves...")
    existing_moves = connector.get_stock_moves(days=500)
    products_with_moves = {m['product_id'][0] if isinstance(m['product_id'], list) else m['product_id'] for m in existing_moves}
    
    missing_products = [p for p in products if p['id'] not in products_with_moves]
    print(f"{len(missing_products)} products have no sales history. Generating...")
    
    count = 0
    for p in missing_products:
        # Generate 10-20 moves for each
        num_moves = random.randint(10, 25)
        print(f"Generating {num_moves} moves for {p['display_name']} (ID: {p['id']})")
        
        for _ in range(num_moves):
            qty = round(random.uniform(1, 50), 2)
            days_ago = random.randint(1, 450)
            date = datetime.now() - timedelta(days=days_ago)
            
            try:
                connector.create_stock_move(p['id'], qty, stock_loc, customer_loc, date)
                count += 1
            except Exception as e:
                print(f"  Error creating move: {e}")
                break
        
        if count > 500: # Limit to avoid hitting Odoo too hard in one go
            print("Reached limit of 500 moves. Stopping for now.")
            break

    print(f"Finished. Created {count} moves in Odoo.")

if __name__ == "__main__":
    main()
