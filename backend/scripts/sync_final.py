
import os
import sys
from datetime import datetime
from sqlmodel import Session, create_engine, select, delete
from dotenv import load_dotenv

load_dotenv()
sys.path.append('/app')

from app.services.odoo_connector import OdooConnector
from app.models.models import StockMove, Product

def sync_final():
    connector = OdooConnector.from_config()
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    
    with Session(engine) as session:
        print("Cleaning table...")
        session.exec(delete(StockMove))
        session.commit()
        
        print("Fetching moves...")
        moves = connector.get_stock_moves(days=500)
        print(f"Moves from Odoo: {len(moves)}")
        
        products = session.exec(select(Product)).all()
        p_ids = {p.odoo_id for p in products}
        
        added_count = 0
        synced = set()
        
        for m in moves:
            p_field = m['product_id']
            pid = p_field[0] if isinstance(p_field, (list, tuple)) else p_field
            
            if pid in p_ids:
                mid = m['id']
                if mid in synced: continue
                try:
                    d = datetime.strptime(m['date'], '%Y-%m-%d %H:%M:%S')
                    sm = StockMove(
                        odoo_id=mid, product_id=pid, date=d, product_uom_qty=m['product_uom_qty'],
                        state=m.get('state', 'done'), move_type=m.get('move_type', 'out'),
                        location_id=m['location_id'][0] if isinstance(m['location_id'], (list, tuple)) else (m['location_id'] or 0),
                        location_dest_id=m['location_dest_id'][0] if isinstance(m['location_dest_id'], (list, tuple)) else (m['location_dest_id'] or 0),
                        picking_type_id=0, expected_date=None
                    )
                    session.add(sm)
                    session.commit()
                    synced.add(mid)
                    added_count += 1
                except Exception as e:
                    print(f"FAILED mid {mid}: {e}")
                    session.rollback()
                
        print(f"Final count: {added_count}")

if __name__ == "__main__":
    sync_final()
