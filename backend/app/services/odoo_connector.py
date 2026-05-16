import xmlrpc.client
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlmodel import Session
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _get_odoo_settings(session: Optional[Session] = None) -> Dict[str, str]:
    """Load Odoo connection settings — prefer AppConfig (DB), fall back to env vars."""
    import os
    from sqlmodel import select
    from app.models.models import AppConfig

    defaults = {
        "odoo_url":      os.getenv("ODOO_URL", ""),
        "odoo_db":       os.getenv("ODOO_DB", ""),
        "odoo_user":     os.getenv("ODOO_USER", ""),
        "odoo_api_key":  os.getenv("ODOO_PASSWORD", ""),
        "odoo_port":     os.getenv("ODOO_PORT", "443"),
    }

    # If no session provided, we must create a temporary one
    # But ideally, we should pass the session from the endpoint
    if not session:
        from sqlmodel import create_engine
        db_url = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
        engine = create_engine(db_url, pool_pre_ping=True)
        with Session(engine) as temp_session:
            rows = temp_session.exec(select(AppConfig)).all()
            for r in rows:
                if r.key in defaults: defaults[r.key] = r.value
                if r.key == "odoo_api_key": defaults["odoo_api_key"] = r.value
    else:
        rows = session.exec(select(AppConfig)).all()
        for r in rows:
            if r.key in defaults: defaults[r.key] = r.value
            if r.key == "odoo_api_key": defaults["odoo_api_key"] = r.value

    if defaults.get("odoo_url"):
        defaults["odoo_url"] = defaults["odoo_url"].strip().rstrip('/')
            
    return defaults


class OdooConnector:
    """Odoo XML-RPC connector. Reliable for Odoo Online and API Keys."""

    def __init__(
        self,
        url: str,
        db: str,
        user: str,
        password: str,      # can be password or API key
        port: int = 443
    ):
        parsed = urlparse(url)
        self.host = parsed.hostname or parsed.path.split('/')[0]
        self.db = db.strip()
        self.user = user.strip()
        self.password = password.strip()
        
        if port:
            self.port = int(port)
        elif parsed.port:
            self.port = parsed.port
        else:
            self.port = 443 if parsed.scheme == 'https' else 80
            
        base_url = f"{parsed.scheme}://{self.host}"
        if self.port not in [80, 443]:
            base_url += f":{self.port}"
            
        logger.info(f"Connecting to Odoo via XML-RPC at {base_url}")
        
        try:
            self.common = xmlrpc.client.ServerProxy(f"{base_url}/xmlrpc/2/common")
            self.models = xmlrpc.client.ServerProxy(f"{base_url}/xmlrpc/2/object")
        except Exception as e:
            logger.error(f"Failed to initialize XML-RPC proxies: {e}")
            raise
            
        self.uid = None
        self.logged_in = False

    @classmethod
    def from_config(cls, session: Optional[Session] = None):
        """Factory method to create a connector using DB/Env settings."""
        s = _get_odoo_settings(session)
        p = int(s["odoo_port"]) if s.get("odoo_port") and str(s["odoo_port"]).isdigit() else 443
        return cls(
            url=s["odoo_url"],
            db=s["odoo_db"],
            user=s["odoo_user"],
            password=s["odoo_api_key"],
            port=p
        )

    def login(self):
        try:
            self.uid = self.common.authenticate(self.db, self.user, self.password, {})
            if not self.uid:
                raise Exception("Access Denied")
            self.logged_in = True
            logger.info(f"Odoo login successful (UID: {self.uid})")
        except Exception as e:
            logger.error(f"Odoo login failed: {e}")
            raise

    def test_connection(self) -> Dict[str, Any]:
        """Returns version info if connected."""
        if not self.logged_in:
            self.login()
        info = self.common.version()
        return {"status": "connected", "odoo_version": info.get('server_version', 'Unknown')}

    # ── Data readers ─────────────────────────────────────────────────────────

    def get_products(self, updated_since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if not self.logged_in: self.login()
        domain = [['type', 'in', ['product', 'storable', 'consu']]]
        if updated_since:
            domain.append(['write_date', '>=', updated_since.strftime('%Y-%m-%d %H:%M:%S')])
        
        fields = ['id', 'name', 'display_name', 'default_code', 'qty_available', 'virtual_available', 'incoming_qty', 'list_price', 'standard_price', 'categ_id', 'description_sale', 'seller_ids']
        ids = self.models.execute_kw(self.db, self.uid, self.password, 'product.product', 'search', [domain])
        if not ids: return []
        return self.models.execute_kw(self.db, self.uid, self.password, 'product.product', 'read', [ids, fields])

    def get_stock_moves(self, days=500, updated_since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if not self.logged_in: self.login()
        date_limit = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        domain = [
            ['state', '=', 'done'],
            ['date', '>=', date_limit],
            ['product_id.type', 'in', ['product', 'storable', 'consu']],
            '|',
            ['location_id.usage', '=', 'internal'],
            ['location_dest_id.usage', '=', 'internal']
        ]
        if updated_since:
            domain.append(['write_date', '>=', updated_since.strftime('%Y-%m-%d %H:%M:%S')])
        
        fields = ['product_id', 'product_uom_qty', 'date', 'location_id', 'location_dest_id', 'date_deadline', 'state', 'write_date']
        all_moves = self.models.execute_kw(self.db, self.uid, self.password, 'stock.move', 'search_read', [domain, fields])
        
        # Deduplicate by ID (Odoo can return duplicates if it's a multi-step move)
        seen_ids = set()
        moves = []
        for m in all_moves:
            if m['id'] not in seen_ids:
                moves.append(m)
                seen_ids.add(m['id'])
        
        # Optimize: get unique location IDs and fetch their usages in one call
        loc_ids = set()
        for m in moves:
            src = m['location_id']
            dst = m['location_dest_id']
            if src: loc_ids.add(src[0] if isinstance(src, (list, tuple)) else src)
            if dst: loc_ids.add(dst[0] if isinstance(dst, (list, tuple)) else dst)
        
        loc_data = {}
        if loc_ids:
            try:
                locs = self.models.execute_kw(self.db, self.uid, self.password, 'stock.location', 'read', [list(loc_ids), ['usage']])
                loc_data = {l['id']: l['usage'] for l in locs}
            except Exception as e:
                print(f"Error fetching locations: {e}")
            
        # Tag moves as 'in' or 'out'
        for m in moves:
            src = m['location_id']
            dst = m['location_dest_id']
            src_id = src[0] if isinstance(src, (list, tuple)) else src
            dst_id = dst[0] if isinstance(dst, (list, tuple)) else dst
            
            src_usage = loc_data.get(src_id) if src_id else 'other'
            dest_usage = loc_data.get(dst_id) if dst_id else 'other'
            
            if src_usage == 'internal' and dest_usage != 'internal':
                m['move_type'] = 'out' # Demand
            elif src_usage != 'internal' and dest_usage == 'internal':
                m['move_type'] = 'in'  # Production / Purchase
            else:
                m['move_type'] = 'other' # Internal transfer (ignored for demand)
                
        return [m for m in moves if m['move_type'] != 'other']

    def get_stock_quants(self) -> List[Dict[str, Any]]:
        if not self.logged_in: self.login()
        # Fetch actual inventory levels (stock.quant) for INTERNAL locations only.
        #
        # CRITICAL: Must filter by location_id.usage = 'internal'.
        # Without this, Odoo returns quants for ALL location types:
        #   - internal  → warehouse stock (CORRECT, should count)
        #   - customer  → goods delivered to customer (WRONG, would inflate stock)
        #   - supplier  → goods at supplier (WRONG)
        #   - transit   → goods in virtual transit (WRONG)
        #
        # When a delivery (stock.picking) is validated:
        #   - WH/Stock quant decreases (e.g., 10 → 6)
        #   - Customers location quant is created (qty = 4)
        # If both are summed, stock appears unchanged: 6 + 4 = 10 (BUG).
        # Filtering to 'internal' only gives the correct value: 6.
        fields = ['id', 'product_id', 'location_id', 'quantity', 'reserved_quantity']
        domain = [('location_id.usage', '=', 'internal'), ('quantity', '>', 0)]
        try:
            quants = self.models.execute_kw(self.db, self.uid, self.password, 'stock.quant', 'search_read', [domain, fields])
            logger.info(f"[QUANTS] Fetched {len(quants)} internal quants from Odoo")
            return quants
        except Exception as e:
            logger.error(f"[QUANTS] Error fetching stock quants: {e}")
            return []


    def get_partners(self) -> List[Dict[str, Any]]:
        if not self.logged_in: self.login()
        domain = [['supplier_rank', '>', 0]]
        fields = ['id', 'name', 'email', 'phone']
        return self.models.execute_kw(self.db, self.uid, self.password, 'res.partner', 'search_read', [domain, fields])

    def get_sale_order_lines(self, days=365) -> List[Dict[str, Any]]:
        if not self.logged_in: self.login()
        date_limit = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        # Filter for confirmed/done sales
        domain = [
            ['state', 'in', ['sale', 'done']],
            ['create_date', '>=', date_limit]
        ]
        fields = ['id', 'product_id', 'order_id', 'product_uom_qty', 'price_unit', 'price_subtotal', 'create_date', 'state']
        return self.models.execute_kw(self.db, self.uid, self.password, 'sale.order.line', 'search_read', [domain, fields])

    def get_pending_purchases(self) -> Dict[int, float]:
        """Fetch pending quantities from RFQs and Purchase Orders."""
        if not self.logged_in: self.login()
        
        # Odoo states: 'draft', 'sent', 'to approve' (pending confirmation)
        # 'purchase' (confirmed, potentially partially received)
        domain = [('state', 'in', ['draft', 'sent', 'to approve', 'purchase'])]
        fields = ['product_id', 'product_qty', 'qty_received']
        
        try:
            lines = self.models.execute_kw(self.db, self.uid, self.password, 'purchase.order.line', 'search_read', [domain, fields])
            pending = {}
            for l in lines:
                if not l.get('product_id'): continue
                pid = l['product_id'][0] if isinstance(l['product_id'], list) else l['product_id']
                # Crucial: Only count what's NOT yet received
                qty = float(l.get('product_qty', 0.0)) - float(l.get('qty_received', 0.0))
                if qty > 0:
                    pending[pid] = pending.get(pid, 0.0) + qty
            return pending
        except Exception as e:
            logger.error(f"Error fetching pending purchases: {e}")
            return {}

    def get_open_manufacturing_orders(self) -> Dict[int, float]:
        """Fetch pending quantities from open Manufacturing Orders (mrp.production)."""
        if not self.logged_in: self.login()
        
        domain = [('state', 'in', ['draft', 'confirmed', 'progress', 'to_close'])]
        fields = ['product_id', 'product_qty', 'qty_producing']
        
        try:
            mos = self.models.execute_kw(self.db, self.uid, self.password, 'mrp.production', 'search_read', [domain, fields])
            pending = {}
            for mo in mos:
                if not mo.get('product_id'): continue
                pid = mo['product_id'][0] if isinstance(mo['product_id'], list) else mo['product_id']
                qty = float(mo.get('product_qty', 0.0)) - float(mo.get('qty_producing', 0.0))
                if qty > 0:
                    pending[pid] = pending.get(pid, 0.0) + qty
            return pending
        except Exception as e:
            logger.error(f"Error fetching open MOs: {e}")
            return {}

    def get_incoming_shipments(self) -> Dict[int, float]:
        """Fetch truly PENDING quantities from Incoming Shipments (not yet received).
        
        Uses stock.move with:
        - state IN [assigned, confirmed, partially_available]  (not done, not cancelled)
        - pending = product_uom_qty - qty_done   (subtracts already received)
        
        This correctly handles partial receipts:
          ordered=10, received=6 → pending=4 (not 10)
        """
        if not self.logged_in: self.login()
        
        domain = [
            ('picking_id.picking_type_id.code', '=', 'incoming'),
            ('state', 'in', ['assigned', 'confirmed', 'partially_available'])
        ]
        # CRITICAL: include qty_done to correctly compute pending for partial receipts
        fields = ['product_id', 'product_uom_qty', 'quantity_done']
        
        try:
            moves = self.models.execute_kw(self.db, self.uid, self.password, 'stock.move', 'search_read', [domain, fields])
            pending = {}
            for m in moves:
                if not m.get('product_id'): continue
                pid = m['product_id'][0] if isinstance(m['product_id'], list) else m['product_id']
                ordered = float(m.get('product_uom_qty', 0.0))
                done    = float(m.get('quantity_done', 0.0))
                # True pending = ordered - already done in this move
                qty = max(0.0, ordered - done)
                if qty > 0:
                    pending[pid] = pending.get(pid, 0.0) + qty
                    logger.debug(f"[TRANSIT] product={pid} ordered={ordered} done={done} pending={qty}")
            return pending
        except Exception as e:
            logger.error(f"Error fetching incoming shipments: {e}")
            return {}

    def create_purchase_order(self, partner_id: int, lines: List[Dict[str, Any]]) -> int:
        """
        lines: [{'product_id': int, 'product_qty': float, 'price_unit': float}]
        """
        if not self.logged_in: self.login()
        
        po_vals = {
            'partner_id': partner_id,
            'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'order_line': []
        }
        
        for line in lines:
            line_vals = (0, 0, {
                'product_id': line['product_id'],
                'product_qty': line['product_qty'],
                'price_unit': line.get('price_unit', 0.0),
                'name': f"Auto-generated purchase for product {line['product_id']}",
                'date_planned': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),
            })
            po_vals['order_line'].append(line_vals)
            
        return self.models.execute_kw(self.db, self.uid, self.password, 'purchase.order', 'create', [po_vals])

    def find_location_by_usage(self, usage: str) -> Optional[int]:
        if not self.logged_in: self.login()
        domain = [('usage', '=', usage)]
        ids = self.models.execute_kw(self.db, self.uid, self.password, 'stock.location', 'search', [domain], {'limit': 1})
        return ids[0] if ids else None

    def create_stock_move(self, product_id: int, qty: float, src_loc: int, dst_loc: int, date: datetime) -> int:
        if not self.logged_in: self.login()
        vals = {
            'product_id': product_id,
            'product_uom_qty': qty,
            'product_uom': 1, # Assuming Unit
            'location_id': src_loc,
            'location_dest_id': dst_loc,
            'date': date.strftime('%Y-%m-%d %H:%M:%S'),
            'state': 'done'
        }
        return self.models.execute_kw(self.db, self.uid, self.password, 'stock.move', 'create', [vals])

    def get_boms(self) -> List[Dict[str, Any]]:
        if not self.logged_in: self.login()
        # Odoo model for BOMs is mrp.bom
        fields = ['id', 'product_tmpl_id', 'product_id', 'bom_line_ids']
        # We also need mrp.bom.line for children
        boms = self.models.execute_kw(self.db, self.uid, self.password, 'mrp.bom', 'search_read', [[], fields])
        
        result = []
        for b in boms:
            # product_id in mrp.bom can be null if it's for a template
            # For simplicity in InvFlow, we'll try to find a variant or use template's first variant
            parent_id = b['product_id'][0] if (b['product_id'] and isinstance(b['product_id'], list)) else None
            if not parent_id:
                # Try to find variants for this template
                tmpl_id = b['product_tmpl_id'][0]
                variants = self.models.execute_kw(self.db, self.uid, self.password, 'product.product', 'search', [[['product_tmpl_id', '=', tmpl_id]]], {'limit': 1})
                if variants: parent_id = variants[0]
            
            if not parent_id: continue
            
            # Fetch lines
            line_ids = b['bom_line_ids']
            if not line_ids: continue
            
            lines = self.models.execute_kw(self.db, self.uid, self.password, 'mrp.bom.line', 'read', [line_ids, ['product_id', 'product_qty']])
            for l in lines:
                child_id = l['product_id'][0]
                result.append({
                    'parent_id': parent_id,
                    'child_id': child_id,
                    'quantity': float(l['product_qty'])
                })
        return result

