
import os
import sys
import pandas as pd
from sqlmodel import Session, create_engine, select
from dotenv import load_dotenv

load_dotenv()
sys.path.append('/app')

from app.models.models import StockMove

def check_data():
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    with Session(engine) as session:
        moves = session.exec(select(StockMove).where(StockMove.move_type == 'out')).all()
        print(f"Total moves found: {len(moves)}")
        if not moves: return
        
        df = pd.DataFrame([{'date': m.date, 'qty': m.product_uom_qty} for m in moves])
        df['date'] = pd.to_datetime(df['date'])
        if df['date'].dt.tz:
            df['date'] = df['date'].dt.tz_localize(None)
            
        series = df.set_index('date').resample('MS')['qty'].sum().fillna(0)
        print("Monthly Demand Series:")
        print(series)

if __name__ == "__main__":
    check_data()
