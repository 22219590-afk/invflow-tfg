from sqlmodel import Session, select
from app.models.models import Product, BOM, MRPRequirement, StockQuant
from datetime import datetime, timedelta
from typing import List

class MRPService:
    def __init__(self, session: Session):
        self.session = session

    def run_mrp_explosion(self):
        """
        Material Requirements Planning (MRP) Explosion logic.
        1. Identify gross requirements (from MPS / ProductionPlan).
        2. Explode BOM for each requirement.
        3. Calculate net requirements based on current stock.
        4. Generate planned order releases.
        """
        from sqlalchemy import text
        from datetime import timedelta
        
        # 1. Clear old requirements
        self.session.exec(text("DELETE FROM mrprequirement"))
        
        # 2. Get all MPS plans (Parent requirements)
        mps_plans = self.session.exec(select(ProductionPlan)).all()
        
        for plan in mps_plans:
            # For each parent product in MPS
            product_id = plan.product_id
            if product_id == 0: continue # Skip aggregate plans
            
            # 3. Find BOM components
            bom_lines = self.session.exec(select(BOM).where(BOM.parent_id == product_id)).all()
            
            for line in bom_lines:
                child_id = line.child_id
                child_product = self.session.exec(select(Product).where(Product.odoo_id == child_id)).first()
                if not child_product: continue
                
                # Gross Requirement for child = Parent Planned Qty * BOM Qty
                gross = plan.planned_qty * line.quantity
                if gross <= 0: continue
                
                # 4. Simple Net Requirement calculation
                # (Ideally this should be cumulative across periods, but for now we do period-by-period)
                current_stock = sum(q.quantity for q in child_product.quants)
                
                net = max(0.0, gross - current_stock)
                
                # 5. Planned Order Release (Lead time offset)
                release_date = plan.period_start - timedelta(days=child_product.lead_time_days or 7)
                
                requirement = MRPRequirement(
                    product_id=child_id,
                    date=plan.period_start,
                    gross_requirement=gross,
                    projected_available=max(0.0, current_stock - gross),
                    net_requirement=net,
                    planned_order_release=net if net > 0 else 0.0
                )
                self.session.add(requirement)
        
        self.session.commit()
        return {"status": "success", "message": "MRP Explosion completed"}

    def get_requirements(self) -> List[MRPRequirement]:
        return self.session.exec(select(MRPRequirement)).all()
