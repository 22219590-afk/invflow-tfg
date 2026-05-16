import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlmodel import Session, create_engine, select, delete
import pulp
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA

# Ensure backend path is in sys.path
sys.path.append(os.getcwd())
from app.models.models import Product, StockMove, ProductionPlan, ResourceCapacity

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
engine = create_engine(DATABASE_URL)

def get_best_forecast(series, periods=12):
    if len(series) < 3:
        avg = sum(series) / len(series) if series else 100.0
        return {"forecast": [max(0.0, avg) for _ in range(periods)], "model": "Promedio", "mape": 0.0}

    df = pd.Series(series)
    def mape(y_t, y_p):
        y_t, y_p = np.array(y_t), np.array(y_p)
        mask = y_t > 0
        return float(np.mean(np.abs((y_t[mask] - y_p[mask]) / y_t[mask])) * 100) if np.any(mask) else 99.9

    # Model 1: Holt-Winters (Modelo Popper)
    hw_f, hw_m = [df.mean()] * periods, 999.0
    try:
        if len(series) >= 12:
            hw_model = ExponentialSmoothing(df, trend='add', seasonal='add', seasonal_periods=min(12, len(series)//2)).fit()
        else:
            hw_model = ExponentialSmoothing(df, trend='add').fit()
        hw_f, hw_m = hw_model.forecast(periods).tolist(), mape(df, hw_model.fittedvalues)
    except: pass

    # Model 2: ARIMA (Modelo Arriba)
    ar_f, ar_m = [df.mean()] * periods, 999.0
    try:
        ar_model = ARIMA(df, order=(1,1,1)).fit()
        ar_f, ar_m = ar_model.forecast(periods).tolist(), mape(df, ar_model.fittedvalues)
    except: pass

    if ar_m < hw_m:
        return {"forecast": [max(0.0, f) for f in ar_f], "model": "ARIMA (Modelo Arriba)", "mape": round(ar_m, 2)}
    else:
        return {"forecast": [max(0.0, f) for f in hw_f], "model": "Holt-Winters (Modelo Popper)", "mape": round(hw_m, 2)}

def run_mps_optimization(product_id=0, periods=12):
    with Session(engine) as session:
        print(f"--- Iniciando Optimización MPS para ID: {product_id} ---")
        
        # 1. Leer datos de la BD Intermedia
        if product_id == 0:
            moves = session.exec(select(StockMove)).all()
            products = session.exec(select(Product)).all()
            initial_stock = sum(sum(q.quantity for q in p.quants) for p in products)
            safety_stock = sum(float(p.safety_stock or 0.0) for p in products) or 100.0
        else:
            product = session.exec(select(Product).where(Product.odoo_id == product_id)).first()
            moves = product.moves if product else []
            initial_stock = sum(q.quantity for q in product.quants) if product else 0.0
            safety_stock = float(product.safety_stock or 0.0) if product else 0.0

        if not moves:
            print("No hay datos históricos en la BD intermedia.")
            return None

        # 2. Calcular Previsión (MAPE)
        df_m = pd.DataFrame([{"date": m.date, "qty": m.product_uom_qty} for m in moves])
        df_m["date"] = pd.to_datetime(df_m["date"])
        series = df_m.set_index("date").resample("ME")["qty"].sum().fillna(0)
        # Excluir el mes actual si está incompleto (evita caídas a 0 en la previsión)
        if len(series) > 1:
            series = series.iloc[:-1]
        series = series.tolist()
        f_res = get_best_forecast(series, periods)
        demand = f_res["forecast"]
        print(f"DEBUG: Demanda calculada: {demand}")
        print(f"DEBUG: Stock Inicial: {initial_stock}")
        
        # 3. Solver Simplex
        cap = session.exec(select(ResourceCapacity)).first()
        if not cap:
            cap = ResourceCapacity(name="Planta", initial_workers=10, units_per_worker_month=300, cost_worker_month=2500, cost_hiring=1500, cost_firing=2000, cost_per_unit=10.0)
            session.add(cap); session.commit(); session.refresh(cap)

        u, cw, ch, cf, cp, ci = cap.units_per_worker_month, cap.cost_worker_month, cap.cost_hiring, cap.cost_firing, cap.cost_per_unit, 5.0
        prob = pulp.LpProblem("MPS", pulp.LpMinimize)
        P = [pulp.LpVariable(f"P_{t}", lowBound=0) for t in range(periods)]
        I = [pulp.LpVariable(f"I_{t}", lowBound=safety_stock) for t in range(periods)]
        W = [pulp.LpVariable(f"W_{t}", lowBound=0) for t in range(periods)]
        H = [pulp.LpVariable(f"H_{t}", lowBound=0) for t in range(periods)]
        F = [pulp.LpVariable(f"F_{t}", lowBound=0) for t in range(periods)]

        prob += pulp.lpSum([cp*P[t] + ci*I[t] + cw*W[t] + ch*H[t] + cf*F[t] for t in range(periods)])
        for t in range(periods):
            prev_i = initial_stock if t == 0 else I[t-1]
            prob += prev_i + P[t] - I[t] == demand[t]
            prev_w = cap.initial_workers if t == 0 else W[t-1]
            prob += prev_w + H[t] - F[t] == W[t]
            prob += P[t] <= W[t] * u

        if prob.solve(pulp.PULP_CBC_CMD(msg=0)) == pulp.LpStatusOptimal:
            # 4. Guardar Resultados en la BD
            session.exec(delete(ProductionPlan).where(ProductionPlan.product_id == product_id))
            plan_results = []
            for t in range(periods):
                dt = datetime.now() + timedelta(days=30*t)
                entry = ProductionPlan(
                    product_id=product_id, period_start=dt,
                    planned_qty=round(pulp.value(P[t]), 2), projected_inventory=round(pulp.value(I[t]), 2),
                    planned_workers=round(pulp.value(W[t]), 2), hiring_qty=round(pulp.value(H[t]), 2), firing_qty=round(pulp.value(F[t]), 2),
                    cost_production=round(pulp.value(P[t])*cp, 2), cost_holding=round(pulp.value(I[t])*ci, 2),
                    cost_labor=round(pulp.value(W[t])*cw, 2), cost_hiring=round(pulp.value(H[t])*ch, 2), cost_firing=round(pulp.value(F[t])*cf, 2)
                )
                session.add(entry)
                plan_results.append(entry)
            session.commit()
            print(f"Optimización completada. Modelo: {f_res['model']} (MAPE: {f_res['mape']}%)")
            return {"model": f_res["model"], "mape": f_res["mape"], "total_cost": round(pulp.value(prob.objective), 2)}
        else:
            print("No se encontró solución óptima.")
            return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--product_id", type=int, default=0)
    args = parser.parse_args()
    run_mps_optimization(args.product_id)
