import random
import math
from datetime import datetime, timedelta
from typing import List
from sqlmodel import Session, select, delete
from app.models.models import Product, SalesHistory, StockMove

class DemandSimulator:
    def __init__(self, session: Session):
        self.session = session

    def generate_synthetic_history(self, start_year=2025, end_year=2026):
        """
        Generates controlled synthetic sales history for all products.
        Follows a monthly granularity from Jan start_year to Dec end_year.
        """
        products = self.session.exec(select(Product)).all()
        if not products:
            return 0

        # Clear existing synthetic history to avoid duplicates
        self.session.exec(delete(SalesHistory).where(SalesHistory.is_synthetic == True))
        
        count = 0
        current_date = datetime.now()
        
        # Seasonality factors (generic 12 months)
        # Peak in Summer (Jul/Aug) and End of Year (Dec)
        seasonality = [0.9, 0.85, 1.0, 1.1, 1.15, 1.2, 1.3, 1.25, 1.1, 1.0, 0.95, 1.4]
        
        for p in products:
            # Determine profile based on existing data or a pseudo-random stable assignment
            # We use odoo_id as seed to keep it consistent between runs for the same product
            random.seed(p.odoo_id)
            
            # Check if there's any real demand already to estimate base
            real_moves = self.session.exec(select(StockMove).where(StockMove.product_id == p.odoo_id, StockMove.move_type == 'out')).all()
            if real_moves:
                avg_real = sum(m.product_uom_qty for m in real_moves) / max(1, len(real_moves))
                base_demand = avg_real * 20 # Convert to monthly approx
                volatility = 0.15 # Conservative default for real data stability
            else:
                # Assign profile based on price or just random distribution
                # A: 10%, B: 20%, C: 70%
                r = random.random()
                if r < 0.1: # Profile A
                    base_demand = random.uniform(500, 1500)
                    volatility = 0.10 # 10%
                elif r < 0.3: # Profile B
                    base_demand = random.uniform(100, 499)
                    volatility = 0.25 # 25%
                else: # Profile C
                    base_demand = random.uniform(5, 99)
                    volatility = 0.50 # 50%

            # Generate monthly data
            for year in range(start_year, end_year + 1):
                for month in range(1, 13):
                    # Seasonality
                    s_factor = seasonality[month-1]
                    
                    # Noise
                    noise = 1 + random.uniform(-volatility, volatility)
                    
                    # Monthly Demand calculation
                    qty = base_demand * s_factor * noise
                    qty = max(0, round(qty, 2))
                    
                    hist_date = datetime(year, month, 15) # Middle of month
                    
                    # Skip if date is in the future relative to current app context 
                    # (Unless we want to project, but user asked for "histórico")
                    # The user mentioned Jan 2025 to Dec 2026. 
                    # If current date is May 2026, we generate up to now?
                    # The user said "Jan 2025 to Dec 2026". I'll generate the whole range.
                    
                    self.session.add(SalesHistory(
                        product_id=p.odoo_id,
                        date=hist_date,
                        quantity=qty,
                        is_synthetic=True
                    ))
                    count += 1
            
            # Batch commit every 50 products to keep memory low
            if count % 1000 == 0:
                self.session.commit()

        self.session.commit()
        return count
