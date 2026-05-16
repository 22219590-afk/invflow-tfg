from sqlmodel import Session, create_engine, select
from app.models.models import Product, StockQuant, StockMove, Partner, BOM, ProductionPlan
from datetime import datetime, timedelta
import random
import os
import numpy as np

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
engine = create_engine(DATABASE_URL)

PRODUCT_NAMES = [
    ("Válvula de bola DN50", "VB-050"),
    ("Filtro de aceite industrial", "FI-201"),
    ("Rodamiento SKF 6205", "RD-6205"),
    ("Junta tórica EPDM 30mm", "JT-030"),
    ("Correa trapezoidal B50", "CT-B50"),
    ("Compresor de tornillo 5.5kW", "CP-055"),
    ("Aceite hidráulico HV46", "AH-046"),
    ("Sensor de presión 4-20mA", "SP-420"),
    ("Cojinete de agujas NKI 35", "CA-035"),
    ("Bomba centrífuga 1HP", "BC-001"),
    ("Cable apantallado 2x0.5mm", "CA-205"),
    ("Relé térmico 18-25A", "RT-025"),
    ("Contactor LC1D25", "CO-D25"),
    ("PLC Siemens S7-1200", "PL-S71"),
    ("Electroválvula 5/2 1/4\"", "EV-524"),
    ("Manómetro 0-10 bar", "MN-010"),
    ("Filtro de aire G4 500x500", "FA-500"),
    ("Grasa SKF LGMT2", "GR-MT2"),
    ("Flexible metálico DN25", "FM-025"),
    ("Termostato bimetálico 60°C", "TB-060"),
]

SUPPLIERS = [
    ("Suministros Industriales Pérez", "proveedor1@example.com", 5, 10.0),
    ("TechParts Iberia SL", "ventas@techparts.es", 7, 1.0),
    ("HydroFluid Distribuciones", "pedidos@hydrofluid.com", 10, 5.0),
]


def seed():
    with Session(engine) as session:
        if session.exec(select(Product)).first():
            return

        print("Seeding mock data...")

        # Seed suppliers
        supplier_ids = []
        for i, (name, email, lt, moq) in enumerate(SUPPLIERS, start=1):
            p = Partner(
                odoo_id=900 + i,
                name=name,
                email=email,
                is_supplier=True,
                lead_time_days=lt,
                moq=moq,
            )
            session.add(p)
            supplier_ids.append(900 + i)

        products = []
        for i, (pname, code) in enumerate(PRODUCT_NAMES, start=1):
            abc = random.choices(["A", "B", "C"], weights=[0.2, 0.3, 0.5])[0]
            lead = random.choice([5, 7, 10, 14, 21])
            p = Product(
                odoo_id=1000 + i,
                name=pname,
                default_code=code,
                list_price=round(random.uniform(10, 2000), 2),
                standard_price=round(random.uniform(5, 1500), 2),
                abc_class=abc,
                xyz_class=random.choice(["X", "Y", "Z"]),
                daily_demand=round(random.uniform(0.5, 15), 2),
                demand_std_dev=round(random.uniform(0.1, 5), 2),
                lead_time_days=lead,
                supplier_id=random.choice(supplier_ids),
            )
            session.add(p)
            products.append(p)

        session.commit()

        for p in products:
            stock_level = random.uniform(0, 80)
            q = StockQuant(
                odoo_id=2000 + p.odoo_id,
                product_id=p.odoo_id,
                location_id=8,
                quantity=round(stock_level, 2),
            )
            session.add(q)

            # 365 days of realistic demand moves
            for d in range(365):
                # Some days have no demand (30% chance)
                if random.random() < 0.3:
                    continue
                # Add trend and seasonality to mock demand
                seasonality = 1.0 + 0.3 * np.sin(2 * np.pi * d / 365.0)
                trend = 1.0 + 0.002 * (365 - d) # growth towards present
                p_base = float(p.daily_demand)
                qty = round(random.uniform(p_base * 0.5, p_base * 1.5) * seasonality * trend, 2)
                m = StockMove(
                    odoo_id=30000 + p.odoo_id * 1000 + d,
                    product_id=p.odoo_id,
                    date=datetime.now() - timedelta(days=d),
                    product_uom_qty=qty,
                    state="done",
                    location_id=8,
                    location_dest_id=9,
                    picking_type_id=1,
                )
                session.add(m)

        session.commit()
        print("Mock data seeded successfully.")

        # Seed historical production plans (planned values) for past months of current year
        current_year = datetime.now().year
        for m in range(1, datetime.now().month):
            dt = datetime(current_year, m, 1)
            p_val = 4000 + random.uniform(-500, 500)
            plan = ProductionPlan(
                product_id=0,
                period_start=dt,
                planned_qty=round(p_val, 2),
                projected_inventory=1000 + random.uniform(-200, 200),
                planned_workers=20,
                cost_production=p_val * 10,
                cost_labor=20 * 2500
            )
            session.add(plan)
            
            # Also seed REAL production moves for these months
            # Move from Production (7) to Stock (8)
            real_p = p_val * random.uniform(0.85, 1.15) # 15% deviation
            move = StockMove(
                odoo_id=40000 + m,
                product_id=1001, # Just assign to one for aggregate
                date=dt + timedelta(days=15),
                product_uom_qty=round(real_p, 2),
                state="done",
                location_id=7, # Production
                location_dest_id=8 # Stock
            )
            session.add(move)

        session.commit()
        print("Historical plans and production seeded.")

        # Seed BOMs for MRP demonstration
        print("Seeding BOM structures...")
        # Valve (1001) requires 2x O-Ring (1004) and 1x Bearing (1009)
        session.add(BOM(parent_id=1001, child_id=1004, quantity=2.0))
        session.add(BOM(parent_id=1001, child_id=1009, quantity=1.0))
        
        # Compressor (1006) requires 4x Pressure Sensor (1008) and 2x Air Filter (1028)
        session.add(BOM(parent_id=1006, child_id=1008, quantity=4.0))
        session.add(BOM(parent_id=1006, child_id=1028, quantity=2.0))
        
        # S7-1200 (1025) requires 1x Contactor (1024)
        session.add(BOM(parent_id=1025, child_id=1024, quantity=1.0))
        
        session.commit()
        print("BOMs seeded.")


if __name__ == "__main__":
    seed()
