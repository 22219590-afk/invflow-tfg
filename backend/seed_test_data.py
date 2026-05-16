
from sqlmodel import Session, create_engine, select
from app.models.models import Product, AppConfig, StockQuant
import os

# Data provided by user
test_data = [
    {"id": 17, "d": 20000, "c": 80, "h": 120},
    {"id": 14, "d": 50000, "c": 60, "h": 9},
    {"id": 4, "d": 8000, "c": 100, "h": 15},
    {"id": 18, "d": 4000, "c": 150, "h": 22.5},
    {"id": 26, "d": 4300, "c": 120, "h": 18},
    {"id": 30, "d": 9000, "c": 55, "h": 8.25},
    {"id": 13, "d": 500, "c": 700, "h": 105},
    {"id": 2, "d": 1750, "c": 110, "h": 16.5},
    {"id": 12, "d": 5400, "c": 15, "h": 2.25},
    {"id": 16, "d": 13200, "c": 5, "h": 0.75},
    {"id": 27, "d": 575, "c": 100, "h": 15},
    {"id": 11, "d": 3700, "c": 15, "h": 2.25},
    {"id": 23, "d": 6000, "c": 9, "h": 1.35},
    {"id": 29, "d": 675, "c": 80, "h": 12},
    {"id": 24, "d": 3800, "c": 12, "h": 1.8},
    {"id": 28, "d": 890, "c": 50, "h": 7.5},
    {"id": 25, "d": 800, "c": 50, "h": 7.5},
    {"id": 5, "d": 5000, "c": 7, "h": 1.05},
    {"id": 20, "d": 1250, "c": 25, "h": 3.75},
    {"id": 19, "d": 750, "c": 36, "h": 5.4},
    {"id": 22, "d": 4500, "c": 5, "h": 0.75},
    {"id": 6, "d": 2000, "c": 10, "h": 1.5},
    {"id": 21, "d": 3000, "c": 6, "h": 0.9},
    {"id": 7, "d": 4000, "c": 4, "h": 0.6},
    {"id": 8, "d": 750, "c": 20, "h": 3},
    {"id": 9, "d": 2800, "c": 5, "h": 0.75},
    {"id": 10, "d": 1000, "c": 10, "h": 1.5},
    {"id": 15, "d": 650, "c": 11, "h": 1.65},
    {"id": 1, "d": 400, "c": 8, "h": 1.2},
    {"id": 3, "d": 700, "c": 2, "h": 0.3},
]

# Database connection
db_url = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
engine = create_engine(db_url)

def seed_test():
    with Session(engine) as session:
        from sqlmodel import delete
        print("Cleaning old data...")
        session.exec(delete(StockQuant))
        from app.models.models import StockMove
        session.exec(delete(StockMove))
        session.exec(delete(Product))
        
        print("Setting global config (S=80, i=0.15)...")
        # Ensure config exists
        for key, val in [("ordering_cost", "80.0"), ("holding_rate", "0.15"), ("lead_time_default_days", "2")]:
            cfg = session.exec(select(AppConfig).where(AppConfig.key == key)).first()
            if cfg: cfg.value = val
            else: session.add(AppConfig(key=key, value=val))
        
        session.commit()

        print("Inserting 30 test products...")
        for item in test_data:
            # Service level 99.87 for Art 17, others 95
            sl = 99.87 if item["id"] == 17 else 95.0
            p = Product(
                odoo_id=item["id"],
                name=f"Artículo {item['id']}",
                default_code=f"ART-{item['id']:03d}",
                standard_price=float(item["c"]),
                lead_time_days=2,
                manual_daily_demand=float(item["d"] / 240.0),
                manual_demand_std_dev=9.0, # As per user requirement
                target_service_level=sl,
                abc_class="A" if item["id"] == 17 else ("B" if item["id"] <= 30 and item["id"] > 13 else "C")
            )
            session.add(p)
        
        session.commit()
        print("Data seeded. Triggering calculation...")
        
        # Recalculate everything
        from app.services.analytics import AnalyticsService
        AnalyticsService(session).calculate_abc_xyz()
        session.commit()
        print("DONE!")

if __name__ == "__main__":
    seed_test()
