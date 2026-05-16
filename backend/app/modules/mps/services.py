"""
MPS Engine — Planificación Maestra de Producción (Aggregate Planning via Linear Programming)
==============================================================================================
Model: Chase / Level / Mixed strategy, optimized with PuLP (CBC solver).

DECISION VARIABLES (per period t ∈ {0…T-1}):
  P[t]  = units produced
  I[t]  = ending inventory
  W[t]  = workers on payroll
  H[t]  = workers hired
  F[t]  = workers fired
  S[t]  = shortfall (unmet demand, penalized heavily)

OBJECTIVE (minimize):
  Σ  cost_prod * P[t]
   + cost_hold * I[t]
   + cost_worker * W[t]
   + cost_hire * H[t]
   + cost_fire * F[t]
   + cost_shortfall * S[t]   ← large penalty ensures model prefers production over shortfall

CONSTRAINTS:
  Inventory balance:  I[t] = I[t-1] + P[t] - D[t] + S[t]   (S allows infeasible demand to be met partially)
  Workforce balance:  W[t] = W[t-1] + H[t] - F[t]
  Capacity:           P[t] <= W[t] * cap_per_worker
  Safety stock:       I[t] >= SS_aggregate
  Non-negativity:     all variables >= 0

WHY COSTS WERE CONSTANT BEFORE:
  1. Initial inventory was hardcoded to 500 (never changed → same optimal every run)
  2. Safety stock floor was hardcoded to 400 (never reflected real SS)
  3. Demand was being double-counted: StockMove OUT + SalesHistory (both represent the same sales)
  4. cost_prod was a flat €10 independent of actual product value
  5. No shortfall variable → model became infeasible when demand > capacity, solver returned degenerate solution
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

import numpy as np
import pulp
from sqlmodel import Session, select, delete

from app.models.models import (
    Product, StockQuant, SaleOrderLine, ForecastResult, ResourceCapacity
)
from app.modules.mps.models import MPSSolution, MPSMonthDetail

logger = logging.getLogger(__name__)

# ─── constants ────────────────────────────────────────────────────────────────

WORKING_DAYS_MONTH = 20          # Standard working days per month
SHORTFALL_PENALTY   = 1_000.0   # €/unit of unmet demand — very high to force production
DEFAULT_COST_HOLD   = 2.0       # €/unit/month holding cost when no price available
DEFAULT_COST_PROD   = 15.0      # €/unit production cost when no price available


class MPSEngine:
    def __init__(self, session: Session):
        self.session = session

    # ── 1. DEMAND AGGREGATION ─────────────────────────────────────────────────

    def _get_aggregate_demand(self) -> List[Dict[str, Any]]:
        """
        Build monthly demand series for the planning horizon (12 months, current year).

        Data sources (in priority order):
          • Past months  → real confirmed sales (SaleOrderLine state=sale/done)
          • Future months → ForecastResult (engine output), fallback to daily_demand*20
        
        NOTE: We do NOT sum StockMove + SalesHistory because they represent the
        same physical events and would double-count.
        """
        now = datetime.now()
        current_year = now.year
        months_data = []

        # Pre-load all sale lines for the year (single query, O(1) vs N months)
        year_start = datetime(current_year, 1, 1)
        year_end   = datetime(current_year + 1, 1, 1)

        sale_lines = self.session.exec(
            select(SaleOrderLine)
            .where(SaleOrderLine.state.in_(["sale", "done"]))
            .where(SaleOrderLine.date >= year_start)
            .where(SaleOrderLine.date < year_end)
        ).all()

        # Pre-load forecast results for future months
        forecasts = self.session.exec(
            select(ForecastResult)
            .where(ForecastResult.date >= year_start)
            .where(ForecastResult.date < year_end)
            .where(ForecastResult.is_real == False)
        ).all()

        # Fallback: product daily demand
        products = self.session.exec(select(Product)).all()
        total_daily_fallback = sum((p.daily_demand or 0.0) for p in products)

        for m in range(1, 13):
            month_start = datetime(current_year, m, 1)
            month_end   = datetime(current_year, m + 1, 1) if m < 12 else datetime(current_year + 1, 1, 1)
            is_past     = month_end <= now

            # ── Real demand (past months only) ────────────────────────────────
            real_q = None
            if is_past or month_start <= now < month_end:
                real_q = sum(
                    sl.product_uom_qty for sl in sale_lines
                    if month_start <= sl.date < month_end
                )

            # ── Forecast demand ───────────────────────────────────────────────
            forecast_q = sum(
                f.quantity for f in forecasts
                if month_start <= f.date < month_end
            )

            # If no forecast available fall back to daily_demand * working days
            if forecast_q == 0:
                forecast_q = total_daily_fallback * WORKING_DAYS_MONTH

            # ── Effective demand: real for past, forecast for future ───────────
            effective = (real_q or forecast_q) if is_past else forecast_q

            months_data.append({
                "month_index":     m,
                "month_name":      month_start.strftime("%B"),
                "year":            current_year,
                "real_demand":     real_q,
                "forecast_demand": round(forecast_q, 2),
                "effective_demand": round(max(effective or 0.0, 0.0), 2),
                "is_past":         is_past,
            })

        return months_data

    # ── 2. INITIAL STATE ──────────────────────────────────────────────────────

    def _get_real_initial_inventory(self) -> float:
        """Sum all StockQuant quantities — same source as Plan Diario and KPIs."""
        quants = self.session.exec(select(StockQuant)).all()
        return max(0.0, sum(q.quantity for q in quants))

    def _get_aggregate_safety_stock(self) -> float:
        """Sum of all product safety stocks — real aggregate floor for the LP."""
        products = self.session.exec(select(Product)).all()
        return sum(max(p.safety_stock or 0.0, 0.0) for p in products)

    def _get_unit_costs(self) -> Dict[str, float]:
        """
        Average cost per unit across all products weighted by daily demand.
        Used to derive a meaningful production cost coefficient.
        """
        products = self.session.exec(select(Product)).all()
        total_demand = sum(p.daily_demand or 0.0 for p in products)
        if total_demand == 0 or not products:
            return {"cost_prod": DEFAULT_COST_PROD, "cost_hold": DEFAULT_COST_HOLD}

        weighted_price = sum(
            (p.standard_price or 0.0) * (p.daily_demand or 0.0)
            for p in products
        ) / total_demand

        # Production cost ≈ 40% of standard price (material + labor ratio)
        cost_prod = max(weighted_price * 0.40, DEFAULT_COST_PROD)
        # Holding cost ≈ 20% annual rate / 12 months * unit price
        cost_hold = max(weighted_price * 0.20 / 12.0, DEFAULT_COST_HOLD)

        return {"cost_prod": round(cost_prod, 4), "cost_hold": round(cost_hold, 4)}

    # ── 3. LP SOLVER ──────────────────────────────────────────────────────────

    def solve_aggregate_plan(self) -> MPSSolution:
        """
        Solve the Aggregate Planning LP with PuLP/CBC.
        Always feasible thanks to shortfall variable S[t].
        Results change when demand, stock, capacity or costs change.
        """
        months_data = self._get_aggregate_demand()
        T = len(months_data)

        # ── Parameters ───────────────────────────────────────────────────────
        res = self.session.exec(select(ResourceCapacity)).first()
        if not res:
            res = ResourceCapacity(
                name="Planta Principal",
                cost_worker_month=2_500.0,
                cost_hiring=1_200.0,
                cost_firing=1_800.0,
                units_per_worker_month=450.0,
                initial_workers=15,
            )

        unit_costs   = self._get_unit_costs()
        COST_PROD    = unit_costs["cost_prod"]
        COST_HOLD    = unit_costs["cost_hold"]
        COST_WORKER  = res.cost_worker_month
        COST_HIRE    = res.cost_hiring
        COST_FIRE    = res.cost_firing
        CAP_WORKER   = max(res.units_per_worker_month, 1.0)  # units per worker per month

        # ── Real initial state (from DB, not hardcoded) ───────────────────────
        I_init = self._get_real_initial_inventory()
        W_init = max(res.initial_workers, 1)
        SS     = self._get_aggregate_safety_stock()

        logger.info(
            f"[MPS] Starting LP | T={T} months | I_init={I_init:.0f} | "
            f"SS={SS:.0f} | W_init={W_init} | CAP/worker={CAP_WORKER:.0f} | "
            f"cost_prod={COST_PROD:.2f} | cost_hold={COST_HOLD:.2f}"
        )

        # ── Problem ───────────────────────────────────────────────────────────
        prob = pulp.LpProblem("Aggregate_Planning_MPS", pulp.LpMinimize)

        P = [pulp.LpVariable(f"Prod_{t}",     lowBound=0) for t in range(T)]
        I = [pulp.LpVariable(f"Inv_{t}",      lowBound=0) for t in range(T)]
        W = [pulp.LpVariable(f"Workers_{t}",  lowBound=0) for t in range(T)]
        H = [pulp.LpVariable(f"Hire_{t}",     lowBound=0) for t in range(T)]
        F = [pulp.LpVariable(f"Fire_{t}",     lowBound=0) for t in range(T)]
        S = [pulp.LpVariable(f"Shortfall_{t}", lowBound=0) for t in range(T)]  # unmet demand

        # ── Objective ─────────────────────────────────────────────────────────
        prob += pulp.lpSum([
            COST_PROD   * P[t]
            + COST_HOLD   * I[t]
            + COST_WORKER * W[t]
            + COST_HIRE   * H[t]
            + COST_FIRE   * F[t]
            + SHORTFALL_PENALTY * S[t]
            for t in range(T)
        ])

        # ── Constraints ───────────────────────────────────────────────────────
        for t in range(T):
            D_t = months_data[t]["effective_demand"]

            # [C1] Inventory balance  — S[t] absorbs demand that can't be met
            if t == 0:
                prob += I[t] == I_init + P[t] - D_t + S[t]
            else:
                prob += I[t] == I[t - 1] + P[t] - D_t + S[t]

            # [C2] Production capacity bound
            prob += P[t] <= W[t] * CAP_WORKER

            # [C3] Workforce continuity
            if t == 0:
                prob += W[t] == W_init + H[t] - F[t]
            else:
                prob += W[t] == W[t - 1] + H[t] - F[t]

            # [C4] Safety stock floor (real aggregate SS, not hardcoded)
            prob += I[t] >= SS

            # [C5] Cannot fire more than current workforce
            if t == 0:
                prob += F[t] <= W_init
            else:
                prob += F[t] <= W[t - 1]

        # ── Solve ─────────────────────────────────────────────────────────────
        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=30)
        prob.solve(solver)

        status = pulp.LpStatus[prob.status]
        logger.info(f"[MPS] Solver status: {status} | Objective: {pulp.value(prob.objective):.2f}")

        if status not in ("Optimal", "Feasible"):
            logger.error(f"[MPS] Solver failed: {status}")

        # ── Persist ───────────────────────────────────────────────────────────
        self.session.exec(delete(MPSSolution))
        self.session.exec(delete(MPSMonthDetail))

        def v(var):
            """Safe value extraction — returns 0 if variable has no solution."""
            val = pulp.value(var)
            return round(float(val), 4) if val is not None else 0.0

        total_cost       = v(prob.objective)
        production_cost  = sum(v(P[t]) * COST_PROD  for t in range(T))
        storage_cost     = sum(v(I[t]) * COST_HOLD   for t in range(T))
        hiring_cost      = sum(v(H[t]) * COST_HIRE   for t in range(T))
        firing_cost      = sum(v(F[t]) * COST_FIRE   for t in range(T))
        shortfall_total  = sum(v(S[t])               for t in range(T))
        worker_cost      = sum(v(W[t]) * COST_WORKER for t in range(T))

        solution = MPSSolution(
            name=f"Plan Maestro {datetime.now().year}",
            total_cost=total_cost,
            production_cost=production_cost,
            storage_cost=storage_cost,
            hiring_cost=hiring_cost,
            firing_cost=firing_cost,
        )
        self.session.add(solution)
        self.session.flush()

        for t in range(T):
            m      = months_data[t]
            prod_t = v(P[t])
            inv_t  = v(I[t])
            wrk_t  = v(W[t])

            # Capacity utilization: production / (workers * cap)
            max_cap = max(wrk_t * CAP_WORKER, 1.0)
            cap_util = min(round(prod_t / max_cap * 100, 1), 100.0)

            # Shortfall = unmet demand this month
            shortfall_t = v(S[t])

            real_d = m["real_demand"]
            dev    = None
            if real_d is not None and m["forecast_demand"] > 0:
                dev = round((real_d - m["forecast_demand"]) / m["forecast_demand"] * 100, 2)

            detail = MPSMonthDetail(
                solution_id=solution.id,
                month_index=m["month_index"],
                month_name=m["month_name"],
                year=m["year"],
                demand=m["forecast_demand"],
                real_demand=real_d,
                deviation_pct=dev,
                production=prod_t,
                inventory=inv_t,
                workers=wrk_t,
                hires=v(H[t]),
                fires=v(F[t]),
                capacity_utilization=cap_util,
                shortfall=shortfall_t,
            )
            self.session.add(detail)

            logger.info(
                f"[MPS] {m['month_name']:>12} | D={m['effective_demand']:8.0f} | "
                f"P={prod_t:8.0f} | I={inv_t:8.0f} | W={wrk_t:5.1f} | "
                f"Cap={cap_util:5.1f}% | Short={shortfall_t:.0f}"
            )

        self.session.commit()
        self.session.refresh(solution)
        return solution
