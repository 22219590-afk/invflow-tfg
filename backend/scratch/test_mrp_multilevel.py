
import sys
import os
from datetime import datetime, timedelta
from sqlmodel import Session, create_engine, select, delete

# Add backend to path
sys.path.append(os.getcwd())

from app.models.models import Product, BOM, MRPRequirement, StockQuant
from app.modules.mrp.services import MRPService

# Use a local test DB
DATABASE_URL = "sqlite:///test_mrp.db"
engine = create_engine(DATABASE_URL)

def setup_data():
    with Session(engine) as session:
        # Clear old data
        session.exec(delete(BOM))
        session.exec(delete(Product))
        session.exec(delete(MRPRequirement))
        session.exec(delete(StockQuant))
        session.commit()

        # Create Products
        # P1 (Parent) -> C1, C2
        # C1 -> GC1 (Grandchild)
        p1 = Product(odoo_id=400, name="Final Product P1", daily_demand=1.0)
        c1 = Product(odoo_id=300, name="Component C1", daily_demand=0.0)
        c2 = Product(odoo_id=200, name="Component C2", daily_demand=0.0)
        gc1 = Product(odoo_id=100, name="Grandchild GC1", daily_demand=0.0)
        
        session.add_all([p1, c1, c2, gc1])
        session.commit()

        # Create BOMs
        session.add(BOM(parent_id=400, child_id=300, quantity=2.0)) # 1 P1 needs 2 C1
        session.add(BOM(parent_id=400, child_id=200, quantity=1.0)) # 1 P1 needs 1 C2
        session.add(BOM(parent_id=300, child_id=100, quantity=3.0)) # 1 C1 needs 3 GC1
        session.commit()

        # Create Stock (Empty)
        session.add(StockQuant(odoo_id=1, product_id=400, location_id=1, quantity=0))
        session.add(StockQuant(odoo_id=2, product_id=300, location_id=1, quantity=0))
        session.add(StockQuant(odoo_id=3, product_id=200, location_id=1, quantity=0))
        session.add(StockQuant(odoo_id=4, product_id=100, location_id=1, quantity=0))
        session.commit()

def test_mrp():
    with Session(engine) as session:
        service = MRPService(session)
        print("Running MRP...")
        service.run_mrp()
        
        # Check requirements for GC1 (odoo_id=4)
        # P1 demand = 1.0 * 30 = 30
        # C1 needs = 30 * 2 = 60
        # GC1 needs = 60 * 3 = 180
        
        reqs = session.exec(select(MRPRequirement).where(MRPRequirement.product_id == 100)).all()
        total_gross = sum(r.gross_requirement for r in reqs)
        print(f"Total Gross Requirement for GC1: {total_gross}")
        
        if total_gross == 180:
            print("SUCCESS: Multilevel explosion worked (by chance or logic).")
        else:
            print(f"FAILURE: Expected 180, got {total_gross}")

if __name__ == "__main__":
    # Initialize DB
    from app.models.models import SQLModel
    SQLModel.metadata.create_all(engine)
    
    setup_data()
    test_mrp()
