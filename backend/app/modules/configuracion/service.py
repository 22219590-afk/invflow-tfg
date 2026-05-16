from sqlmodel import Session, select, delete
from app.models.models import AppConfig
from app.services.odoo_connector import OdooConnector
from .schemas import OdooConfigSchema, ConfigItemSchema
from typing import List

class ConfigService:
    def __init__(self, session: Session):
        self.session = session

    def get_all_config(self) -> List[AppConfig]:
        return self.session.exec(select(AppConfig)).all()

    def update_config(self, items: List[ConfigItemSchema]):
        for item in items:
            existing = self.session.exec(select(AppConfig).where(AppConfig.key == item.key)).first()
            if existing:
                existing.value = item.value
                if item.description:
                    existing.description = item.description
                self.session.add(existing)
            else:
                new_item = AppConfig(key=item.key, value=item.value, description=item.description)
                self.session.add(new_item)
        self.session.commit()

    def test_odoo_connection(self, config: OdooConfigSchema):
        connector = OdooConnector(
            url=config.odoo_url,
            db=config.odoo_db,
            user=config.odoo_user,
            password=config.odoo_password,
            port=int(config.odoo_port) if config.odoo_port and config.odoo_port.isdigit() else None
        )
        return connector.test_connection()

    def run_incremental_sync(self):
        """
        Main entry point for incremental sync.
        Following the production requirement:
        - Avoid overloading Odoo.
        - Store data internally.
        - Incremental updates.
        """
        import datetime
        from app.models.models import Product, StockQuant, StockMove, Partner
        from sqlalchemy import text

        # 1. Get last sync date
        last_sync_item = self.session.exec(select(AppConfig).where(AppConfig.key == "last_sync_date")).first()
        updated_since = None
        if last_sync_item and last_sync_item.value:
            try:
                updated_since = datetime.datetime.fromisoformat(last_sync_item.value)
            except ValueError:
                pass

        connector = OdooConnector.from_config()
        connector.login()

        # 2. Sync Products (Upsert)
        odoo_products = connector.get_products(updated_since=updated_since)
        for p in odoo_products:
            obj = self.session.exec(select(Product).where(Product.odoo_id == p['id'])).first()
            if not obj:
                obj = Product(
                    odoo_id=p['id'], 
                    name=p.get('display_name') or p.get('name'), 
                    default_code=p.get('default_code')
                )
            else:
                obj.name = p.get('display_name') or p.get('name')
                obj.default_code = p.get('default_code')
            
            obj.list_price = p.get('list_price', 0.0)
            obj.standard_price = p.get('standard_price', 0.0)
            # Add other fields as needed
            self.session.add(obj)
        
        self.session.commit()

        # 3. Sync Stock Moves (Incremental)
        odoo_moves = connector.get_stock_moves(days=365, updated_since=updated_since)
        for m in odoo_moves:
            # Check if move already exists
            existing_move = self.session.exec(select(StockMove).where(StockMove.odoo_id == m['id'])).first()
            if not existing_move:
                move_date = datetime.datetime.utcnow()
                try:
                    move_date = datetime.datetime.strptime(m["date"], "%Y-%m-%d %H:%M:%S")
                except: pass
                
                self.session.add(StockMove(
                    odoo_id=m['id'],
                    product_id=m['product_id'][0] if isinstance(m['product_id'], list) else m['product_id'],
                    date=move_date,
                    product_uom_qty=m.get('product_uom_qty', 0),
                    state=m.get('state', 'done'),
                    move_type=m.get('move_type', 'out'),
                    location_id=m['location_id'][0] if isinstance(m['location_id'], list) else 0,
                    location_dest_id=m['location_dest_id'][0] if isinstance(m['location_dest_id'], list) else 0,
                    picking_type_id=0
                ))
        
        # 4. Sync Stock Quants (Quants are usually full-sync since they are snapshots)
        # But we only clear and reload if anything changed or periodically
        odoo_quants = connector.get_stock_quants()
        self.session.exec(text("DELETE FROM stockquant"))
        for q in odoo_quants:
            self.session.add(StockQuant(
                odoo_id=q["id"],
                product_id=q["product_id"][0],
                location_id=q["location_id"][0],
                quantity=q.get("quantity", 0),
                reserved_quantity=q.get("reserved_quantity", 0.0)
            ))

        # 5. Update last sync date
        now_str = datetime.datetime.now().isoformat()
        if not last_sync_item:
            self.session.add(AppConfig(key="last_sync_date", value=now_str, description="Last successful Odoo sync date"))
        else:
            last_sync_item.value = now_str
            self.session.add(last_sync_item)
        
        self.session.commit()

        # 6. Run background analytics
        from app.services.analytics import AnalyticsService
        AnalyticsService(self.session).calculate_abc_xyz()
        
        return {"status": "success", "synced_at": now_str}
