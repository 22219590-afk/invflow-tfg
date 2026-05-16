
from typing import List, Dict, Any, Optional
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlmodel import Session, select, delete
import pulp
import logging

from app.models.models import Product, StockMove, StockQuant, ProductionPlan, ResourceCapacity

logger = logging.getLogger(__name__)

class ProductionService:
    def __init__(self, session: Session):
        self.session = session

    def _get_product_stock(self, odoo_id: int) -> float:
        quants = self.session.exec(select(StockQuant).where(StockQuant.product_id == odoo_id)).all()
        return float(sum(q.quantity for q in quants))

    def _get_unified_forecast(self, product_id: Optional[int], periods: int = 12) -> Dict:
        """Fetches the unified forecast from the central ForecastingService results."""
        from app.models.models import ForecastResult
        
        current_year = datetime.now().year
        query = select(ForecastResult).where(ForecastResult.is_real == False)
        
        if product_id:
            query = query.where(ForecastResult.product_id == product_id)
            
        results = self.session.exec(query).all()
        
        if not results:
            # Fallback if no forecast has been run yet
            return {"forecast": [0.0] * periods, "model": "Sin Forecast (Sync Requerida)", "mape": 0.0}
            
        df = pd.DataFrame([{"date": r.date, "qty": r.quantity} for r in results])
        df["date"] = pd.to_datetime(df["date"])
        # Aggregate to Monthly
        monthly = df.set_index("date").resample("MS")["qty"].sum().reindex(
            pd.date_range(start=f"{current_year}-01-01", periods=12, freq="MS"), fill_value=0.0
        )
        
        # Get metrics for model name/mape
        if product_id:
            from app.models.models import Product
            p = self.session.exec(select(Product).where(Product.odoo_id == product_id)).first()
            model_name = p.forecast_model or "Unified"
            mape = p.forecast_mape or 0.0
        else:
            model_name = "Agregado Unificado"
            mape = 0.0 # Could average MAPEs if needed
            
        return {"forecast": monthly.tolist(), "model": model_name, "mape": mape}

    def calculate_aggregate_mps(self, periods: int = 12) -> Dict:
        try:
            products = self.session.exec(select(Product)).all()
            if not products: return {"error": "Sin productos"}
            cap = self.session.exec(select(ResourceCapacity)).first()
            if not cap: return {"error": "Sin capacidad"}

            current_year, current_month = datetime.now().year, datetime.now().month

            all_moves = []
            for p in products:
                for m in p.moves:
                    all_moves.append({"date": m.date, "qty": m.product_uom_qty, "type": m.move_type})
            
            df_m = pd.DataFrame(all_moves)
            if df_m.empty: return {"error": "Sin movimientos"}
            
            df_m["date"] = pd.to_datetime(df_m["date"])
            if df_m["date"].dt.tz: df_m["date"] = df_m["date"].dt.tz_localize(None)

            real_demand = df_m[df_m["type"] == "out"].set_index("date").resample("MS")["qty"].sum().fillna(0)
            real_prod = df_m[df_m["type"] == "in"].set_index("date").resample("MS")["qty"].sum().fillna(0)

            # Use Unified Forecast
            f_res = self._get_unified_forecast(None, periods=12)
            forecast_2026 = f_res["forecast"]
            
            # Solver for future
            rem_p = 13 - current_month
            solve_demand = forecast_2026[current_month-1:]
            
            initial_stock = sum(self._get_product_stock(p.odoo_id) for p in products)
            safety = sum(float(p.safety_stock or 0.0) for p in products) or 100.0
            u, cw, ch, cf, cp, ci = cap.units_per_worker_month, cap.cost_worker_month, cap.cost_hiring, cap.cost_firing, cap.cost_per_unit, 5.0

            prob = pulp.LpProblem("Aggregate_MPS", pulp.LpMinimize)
            P, I, W, H, F = [[pulp.LpVariable(f"{v}_{t}", lowBound=0) for t in range(rem_p)] for v in "PIWHF"]

            prob += pulp.lpSum([cp*P[t] + ci*I[t] + cw*W[t] + ch*H[t] + cf*F[t] for t in range(rem_p)])
            for t in range(rem_p):
                prev_i = initial_stock if t == 0 else I[t-1]
                prob += prev_i + P[t] - I[t] == solve_demand[t]
                prev_w = cap.initial_workers if t == 0 else W[t-1]
                prob += prev_w + H[t] - F[t] == W[t]
                prob += P[t] <= W[t] * u

            total_cost = 0
            if prob.solve(pulp.PULP_CBC_CMD(msg=0)) == pulp.LpStatusOptimal:
                total_cost = pulp.value(prob.objective)

            year_plan = []
            for m in range(1, 13):
                month_dt = datetime(current_year, m, 1)
                rd, rp = float(real_demand.get(month_dt, 0.0)), float(real_prod.get(month_dt, 0.0))
                stored = self.session.exec(select(ProductionPlan).where(ProductionPlan.product_id == 0, ProductionPlan.period_start == month_dt)).first()
                
                item = {
                    "month_idx": m, "period_start": month_dt.isoformat(),
                    "is_past": m < current_month, "is_current": m == current_month,
                    "demand_planned": forecast_2026[m-1], "demand_real": rd, "real_qty": rp,
                    "dev_demand": round(((rd - forecast_2026[m-1]) / (forecast_2026[m-1] if forecast_2026[m-1] > 0 else 1) * 100), 1) if forecast_2026[m-1] > 0 else 0,
                }
                if m >= current_month:
                    t = m - current_month
                    item.update({
                        "planned_qty": float(pulp.value(P[t])), "projected_inventory": float(pulp.value(I[t])),
                        "planned_workers": int(pulp.value(W[t])), "hiring_qty": int(pulp.value(H[t])), "firing_qty": int(pulp.value(F[t]))
                    })
                else:
                    item.update({
                        "planned_qty": stored.planned_qty if stored else 0,
                        "projected_inventory": stored.projected_inventory if stored else 0,
                        "planned_workers": stored.planned_workers if stored else cap.initial_workers,
                        "hiring_qty": 0, "firing_qty": 0,
                        "dev_prod": round(((rp - stored.planned_qty) / (stored.planned_qty if stored and stored.planned_qty > 0 else 1) * 100), 1) if stored else 0
                    })
                year_plan.append(item)

            # Persist future
            self.session.exec(delete(ProductionPlan).where(ProductionPlan.period_start >= datetime(current_year, current_month, 1)))
            for it in year_plan:
                if not it["is_past"]:
                    self.session.add(ProductionPlan(
                        product_id=0, period_start=datetime.fromisoformat(it["period_start"]),
                        planned_qty=it["planned_qty"], planned_workers=it["planned_workers"],
                        projected_inventory=it["projected_inventory"], hired=it["hiring_qty"], fired=it["firing_qty"]
                    ))
            self.session.commit()
            return {"plan": year_plan, "total_cost": total_cost, "best_model": f_res["model"], "mape": f_res["mape"]}
        except Exception as e:
            logger.exception("MPS Error")
            return {"error": str(e)}

    def calculate_mps(self, product_id: int, periods: int = 12, manual_demand: List[float] = None) -> Dict:
        try:
            p = self.session.exec(select(Product).where(Product.odoo_id == product_id)).first()
            if not p: return {"error": "Sin producto"}
            current_year, current_month = datetime.now().year, datetime.now().month
            all_m = [{"date": m.date, "qty": m.product_uom_qty, "type": m.move_type} for m in p.moves]
            df = pd.DataFrame(all_m)
            if df.empty: return {"error": "Sin movimientos"}
            df["date"] = pd.to_datetime(df["date"])
            if df["date"].dt.tz: df["date"] = df["date"].dt.tz_localize(None)

            rd, rp = [df[df["type"] == t].set_index("date").resample("MS")["qty"].sum().fillna(0) for t in ("out", "in")]
            
            # Use Unified Forecast
            f_res = self._get_unified_forecast(product_id, periods=12)
            forecast = manual_demand if manual_demand else f_res["forecast"]
            
            year_plan, curr_stock, safety = [], self._get_product_stock(p.odoo_id), float(p.safety_stock or 0.0)
            for m in range(1, 13):
                month_dt = datetime(current_year, m, 1)
                rd_m, rp_m = float(rd.get(month_dt, 0.0)), float(rp.get(month_dt, 0.0))
                stored = self.session.exec(select(ProductionPlan).where(ProductionPlan.product_id == product_id, ProductionPlan.period_start == month_dt)).first()

                item = {
                    "month_idx": m, "period_start": month_dt.isoformat(), "is_past": m < current_month,
                    "demand_planned": forecast[m-1], "demand_real": rd_m, "real_qty": rp_m,
                    "dev_demand": round(((rd_m - forecast[m-1]) / (forecast[m-1] if forecast[m-1] > 0 else 1) * 100), 1) if forecast[m-1] > 0 else 0,
                }
                if m >= current_month:
                    demand = forecast[m-1]
                    needed = max(0.0, demand + safety - curr_stock)
                    item.update({"planned_qty": needed})
                    curr_stock = curr_stock + needed - demand
                    item.update({"projected_inventory": curr_stock})
                else:
                    item.update({
                        "planned_qty": stored.planned_qty if stored else 0, "projected_inventory": stored.projected_inventory if stored else 0,
                        "dev_prod": round(((rp_m - stored.planned_qty) / (stored.planned_qty if stored and stored.planned_qty > 0 else 1) * 100), 1) if stored else 0
                    })
                year_plan.append(item)
            return {"plan": year_plan, "best_model": f_res["model"], "mape": f_res["mape"]}
        except Exception as e:
            return {"error": str(e)}
