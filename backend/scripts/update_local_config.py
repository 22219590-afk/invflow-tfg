import os
import sys
sys.path.append("/app")
from sqlmodel import Session, create_engine, select
from app.models.models import ResourceCapacity, ProductionPlan
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
engine = create_engine(DATABASE_URL)

def update_costs_and_labor():
    with Session(engine) as session:
        # 1. Update ResourceCapacity
        cap = session.exec(select(ResourceCapacity)).first()
        if not cap:
            cap = ResourceCapacity(name="Planta Principal")
            session.add(cap)
        
        cap.cost_worker_month = 2800 # Updated salary
        cap.cost_hiring = 2500
        cap.cost_firing = 3000
        cap.initial_workers = 15 # Workers in 2026
        cap.cost_per_unit = 10.0 # Production cost
        # cap.cost_holding = 5.0 # This is used in solver logic but not in model yet
        
        session.add(cap)
        
        # 2. Seed past ProductionPlan for comparison (Real vs Plan)
        # We need entries for Jan-Apr 2026
        # Let's delete existing past plans to avoid duplicates
        from sqlmodel import delete
        session.exec(delete(ProductionPlan).where(ProductionPlan.product_id == 0, ProductionPlan.period_start < datetime(2026, 5, 1)))
        
        # December 2025 (Reference for hiring/firing)
        session.add(ProductionPlan(
            product_id=0,
            period_start=datetime(2025, 12, 1),
            planned_qty=3500,
            planned_workers=12,
            projected_inventory=1000
        ))
        
        # Jan to Apr 2026
        for m in range(1, 5):
            session.add(ProductionPlan(
                product_id=0,
                period_start=datetime(2026, m, 1),
                planned_qty=4000 + (m * 100),
                planned_workers=15,
                projected_inventory=800 + (m * 50)
            ))
            
        session.commit()
        print("Local costs and labor history updated.")

if __name__ == "__main__":
    update_costs_and_labor()
