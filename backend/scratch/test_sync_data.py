import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.odoo_connector import OdooConnector

def test_pending():
    connector = OdooConnector.from_config()
    connector.login()
    
    print("Testing Pending Purchases...")
    pending = connector.get_pending_purchases()
    print(f"Total entries in pending_map: {len(pending)}")
    for pid, qty in list(pending.items())[:10]:
        print(f"  Product ID {pid}: Pending Qty {qty}")

    print("\nTesting Stock Moves...")
    moves = connector.get_stock_moves(days=500)
    print(f"Total moves found: {len(moves)}")
    
    # Check move types (source and dest locations)
    if moves:
        m = moves[0]
        print(f"Sample move: {m}")

if __name__ == "__main__":
    test_pending()
