import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, delete
import pandas as pd

from app.models.models import (
    Product, BOM, ProductionPlan, MRPRequirement, StockQuant, StockMove, ForecastResult
)

logger = logging.getLogger(__name__)

class MRPService:
    def __init__(self, session: Session):
        self.session = session

    def run_mrp(self) -> Dict[str, Any]:
        """
        Executes the full MRP loop with absolute robustness.
        """
        logger.info("Starting MRP Calculation...")
        
        try:
            # 1. Clear previous results
            self.session.exec(delete(MRPRequirement))
            self.session.commit()

            # 2. Get all active products
            all_prods = self.session.exec(select(Product)).all()
            if not all_prods:
                logger.warning("No products found for MRP calculation")
                return {"status": "skipped", "reason": "no_products"}

            products_map = {p.odoo_id: p for p in all_prods}
            
            # Build BOM map: parent_id -> [(child_id, qty), ...]
            boms = self.session.exec(select(BOM)).all()
            bom_map = {}
            for b in boms:
                if b.parent_id not in bom_map: bom_map[b.parent_id] = []
                bom_map[b.parent_id].append((b.child_id, b.quantity))

            # 2.1 Pre-load stock for performance (Avoid N+1)
            quants = self.session.exec(select(StockQuant)).all()
            stock_map = {}
            for q in quants:
                stock_map[q.product_id] = stock_map.get(q.product_id, 0.0) + q.quantity

            # 3. Load Inputs (MPS and Forecast)
            mps_plans = self.session.exec(select(ProductionPlan)).all()
            forecasts = self.session.exec(select(ForecastResult).where(ForecastResult.is_real == False)).all()
            
            mps_lookup = {}
            for p in mps_plans:
                if p.product_id == 0: continue
                d_str = p.period_start.strftime("%Y-%m-%d")
                if p.product_id not in mps_lookup: mps_lookup[p.product_id] = {}
                mps_lookup[p.product_id][d_str] = p.planned_qty

            forecast_lookup = {}
            for f in forecasts:
                d_str = f.date.strftime("%Y-%m-%d")
                if f.product_id not in forecast_lookup: forecast_lookup[f.product_id] = {}
                forecast_lookup[f.product_id][d_str] = f.quantity

            # 4. Initialize Requirements Map
            reqs = {}
            # Use fixed 12-week horizon from the start of the current week (Monday)
            now = datetime.now()
            start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            horizon_dates = []
            for i in range(12):
                horizon_dates.append(start_of_week + timedelta(weeks=i))

            for pid, product in products_map.items():
                reqs[pid] = {}
                for dt in horizon_dates:
                    d_str = dt.strftime("%Y-%m-%d")
                    qty = 0.0
                    
                    # Priority: 1. MPS | 2. Forecast | 3. Fallback
                    # For weekly, we divide monthly forecast/mps by 4 if needed, 
                    # but ForecastResult is already weekly!
                    if pid in mps_lookup and d_str in mps_lookup[pid]:
                        qty = mps_lookup[pid][d_str]
                    elif pid in forecast_lookup and d_str in forecast_lookup[pid]:
                        qty = forecast_lookup[pid][d_str]
                    else:
                        # Fallback to daily demand * 7
                        qty = (product.daily_demand or 0.0) * 7.0
                    
                    # 4.1 Industrial Validations
                    if product.lead_time_days < 0:
                        logger.warning(f"Invalid lead time ({product.lead_time_days}) for product {pid}. Using 0.")
                        lt = 0
                    
                    if qty < 0:
                        logger.warning(f"Negative requirement ({qty}) detected for product {pid}. Clipping to 0.")
                        qty = 0.0
                    
                    reqs[pid][d_str] = self._empty_req(d_str)
                    reqs[pid][d_str]["gross"] = qty
                    
                    # Add scheduled receipts to the first period (current week)
                    if dt == horizon_dates[0]:
                        reqs[pid][d_str]["scheduled"] = product.incoming_qty or 0.0

            # 5. Recursive Netting and Explosion
            # LLC (Low Level Code) calculation for correct hierarchical processing
            llc_map = self.calculate_llc(all_prods, boms)
            
            # Sort products by LLC (0 = top level, 1 = components, etc.)
            queue = sorted(all_prods, key=lambda x: llc_map.get(x.odoo_id, 0))
            
            for product in queue:
                pid = product.odoo_id
                p_reqs = reqs[pid]
                
                # Inventory logic
                current_inv = stock_map.get(pid, 0.0)
                safety = product.safety_stock or 0.0
                lt = product.lead_time_days or 7
                
                sorted_keys = sorted(p_reqs.keys())
                for d_str in sorted_keys:
                    r = p_reqs[d_str]
                    current_inv = current_inv + r["scheduled"] - r["gross"]
                    
                    if current_inv < safety:
                        needed = safety - current_inv
                        r["net"] = needed
                        r["planned_receipt"] = needed
                        
                        # Time Phase
                        receipt_dt = datetime.strptime(d_str, "%Y-%m-%d")
                        release_dt = receipt_dt - timedelta(days=lt)
                        rel_str = release_dt.strftime("%Y-%m-%d")
                        r["release_date"] = rel_str
                        r["release_qty"] = needed
                        
                        # Explode to children
                        if pid in bom_map:
                            for child_id, b_qty in bom_map[pid]:
                                if child_id in reqs:
                                    # Find best period for child (start of the week)
                                    target_dt = release_dt - timedelta(days=release_dt.weekday())
                                    target_dt = target_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                                    target_str = target_dt.strftime("%Y-%m-%d")
                                    if target_str not in reqs[child_id]:
                                        # If outside horizon, we could extend or ignore. 
                                        # For now, let's at least try to find the closest in-horizon date if it's earlier.
                                        if target_dt < horizon_dates[0]:
                                            target_str = horizon_dates[0].strftime("%Y-%m-%d")
                                        else:
                                            # Outside future horizon, ignore or log
                                            continue
                                            
                                    reqs[child_id][target_str]["gross"] += needed * b_qty
                        
                        current_inv = safety
                    r["projected"] = current_inv

            # 6. Save results
            for pid, dates in reqs.items():
                for d_str, data in dates.items():
                    # Only save if within horizon or has content
                    self.session.add(MRPRequirement(
                        product_id=pid,
                        date=datetime.strptime(d_str, "%Y-%m-%d"),
                        gross_requirement=data["gross"],
                        scheduled_receipt=data["scheduled"],
                        projected_available=data["projected"],
                        net_requirement=data["net"],
                        planned_order_release=data["release_qty"]
                    ))
            
            self.session.commit()
            logger.info(f"MRP Complete. Products: {len(all_prods)}")
            return {"status": "success", "count": len(all_prods)}
        except Exception as e:
            logger.error(f"MRP Logic Error: {e}")
            self.session.rollback()
            raise

    def get_full_mrp_view(self) -> List[Dict[str, Any]]:
        """Returns aggregated MRP data for frontend view."""
        products = self.session.exec(select(Product)).all()
        reqs = self.session.exec(select(MRPRequirement).order_by(MRPRequirement.date)).all()
        
        view_data = []
        for p in products:
            p_reqs = [r for r in reqs if r.product_id == p.odoo_id]
            if not p_reqs: continue
            
            view_data.append({
                "product_id": p.odoo_id,
                "name": p.name,
                "sku": p.default_code,
                "lead_time": p.lead_time_days,
                "safety_stock": p.safety_stock,
                "periods": [
                    {
                        "date": r.date.strftime("%Y-%m-%d"),
                        "gross": r.gross_requirement,
                        "scheduled": r.scheduled_receipt,
                        "projected": r.projected_available,
                        "net": r.net_requirement,
                        "release": r.planned_order_release
                    } for r in p_reqs
                ]
            })
        # Sort to show those with requirements first
        view_data.sort(key=lambda x: sum(p["gross"] for p in x["periods"]), reverse=True)
        return view_data

    def _empty_req(self, date_str):
        return {
            "date": date_str,
            "gross": 0.0,
            "scheduled": 0.0,
            "net": 0.0,
            "planned_receipt": 0.0,
            "release_qty": 0.0,
            "release_date": None,
            "projected": 0.0
        }

    def _get_current_stock(self, product_id: int) -> float:
        quants = self.session.exec(select(StockQuant).where(StockQuant.product_id == product_id)).all()
        return sum(q.quantity for q in quants)

    def calculate_llc(self, products: List[Product], boms: List[BOM]) -> Dict[int, int]:
        """
        Calculates Low Level Code (LLC) for each product to ensure correct MRP processing order.
        LLC = 0 for top-level products, max(LLC(parent) + 1) for components.
        Also detects BOM cycles.
        """
        llc_map = {p.odoo_id: 0 for p in products}
        
        # Build child -> parents map
        parents_map = {}
        for b in boms:
            if b.child_id not in parents_map: parents_map[b.child_id] = []
            parents_map[b.child_id].append(b.parent_id)
            
        # Memoization map
        memo = {}

        # Recursive function to get LLC with cycle detection
        def get_llc(pid, path=None):
            if pid in memo: return memo[pid]
            if path is None: path = set()
            if pid in path:
                logger.error(f"BOM Cycle detected for product {pid}. Path: {path}")
                raise ValueError(f"Ciclo detectado en la estructura BOM del producto {pid}")
            
            if pid not in parents_map:
                memo[pid] = 0
                return 0
            
            path.add(pid)
            max_p_llc = 0
            for parent_id in parents_map[pid]:
                max_p_llc = max(max_p_llc, get_llc(parent_id, path.copy()) + 1)
            
            memo[pid] = max_p_llc
            return max_p_llc

        try:
            for p in products:
                llc_map[p.odoo_id] = get_llc(p.odoo_id)
        except ValueError as e:
            logger.error(f"LLC Calculation failed: {e}")
            # Fallback to 0 if error occurs, though usually we want to stop MRP
            raise

        return llc_map
