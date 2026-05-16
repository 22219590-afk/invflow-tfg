"""
Forecast Service — Orchestrator for the forecasting pipeline.
Reads from DB, runs models, stores results back to DB.
This is the single entry point for forecast calculations.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import pandas as pd
import numpy as np
from sqlmodel import Session, select, delete

from app.models.models import Product, StockMove, SalesHistory, ForecastResult, ForecastMetric
from app.modules.forecast.analytics import (
    compute_demand_stats, compute_error_metrics, build_weekly_series, build_monthly_series
)
from app.modules.forecast.models import ALL_MODELS

logger = logging.getLogger(__name__)

HORIZON_WEEKS = 52        # Forecast 52 weeks into the future
MIN_DATAPOINTS = 4        # Minimum weeks needed to attempt any forecast
TEST_SET_RATIO = 0.2      # Hold out 20% for backtesting


class ForecastEngine:
    def __init__(self, session: Session):
        self.session = session

    def run_all_products(self) -> Dict[str, Any]:
        """Process all products. Returns summary stats."""
        products = self.session.exec(select(Product)).all()
        if not products:
            return {"processed": 0, "skipped": 0, "errors": 0}

        self.session.exec(delete(ForecastResult))
        self.session.exec(delete(ForecastMetric))

        processed, skipped, errors = 0, 0, 0
        for product in products:
            try:
                result = self._process_product(product)
                if result == "skipped":
                    skipped += 1
                else:
                    processed += 1
            except Exception as e:
                logger.error(f"Forecast failed for product {product.odoo_id}: {e}")
                errors += 1

        self.session.commit()
        return {"processed": processed, "skipped": skipped, "errors": errors}

    def run_single_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        product = self.session.exec(select(Product).where(Product.odoo_id == product_id)).first()
        if not product: return None
        self.session.exec(delete(ForecastResult).where(ForecastResult.product_id == product_id))
        self.session.exec(delete(ForecastMetric).where(ForecastMetric.product_id == product_id))
        self._process_product(product)
        self.session.commit()
        return self.get_product_forecast_data(product_id)

    def get_product_forecast_data(self, product_id: int) -> Optional[Dict[str, Any]]:
        product = self.session.exec(select(Product).where(Product.odoo_id == product_id)).first()
        if not product: return None

        future_results = self.session.exec(
            select(ForecastResult).where(ForecastResult.product_id == product_id).order_by(ForecastResult.date)
        ).all()
        metrics = self.session.exec(select(ForecastMetric).where(ForecastMetric.product_id == product_id)).first()

        cutoff = datetime.utcnow() - timedelta(weeks=104) # Show up to 2 years
        real_moves = self.session.exec(
            select(StockMove).where(StockMove.product_id == product_id, StockMove.move_type == "out", StockMove.state == "done", StockMove.date >= cutoff)
        ).all()
        synth = self.session.exec(select(SalesHistory).where(SalesHistory.product_id == product_id, SalesHistory.date >= cutoff)).all()

        data_points = [(m.date, m.product_uom_qty) for m in real_moves]
        data_points += [(s.date, s.quantity) for s in synth]
        real_series = build_weekly_series(data_points)

        # Get fitted values for historical comparison
        fitted_series = pd.Series([], dtype=float)
        if product.forecast_model in ALL_MODELS and len(real_series) >= MIN_DATAPOINTS:
            try:
                model_fn = ALL_MODELS[product.forecast_model]
                res = model_fn(real_series, 0)
                if res and "fitted" in res:
                    fitted_series = res["fitted"]
            except: pass

        # 2. Build unified dataframe for alignment
        df_real = pd.DataFrame({"real": real_series})
        df_fit = pd.DataFrame({"forecast": fitted_series})
        df_hist = df_real.join(df_fit, how="left")
        
        merged = {}
        for date, row in df_hist.iterrows():
            d = date.strftime("%Y-%m-%d")
            merged[d] = {
                "date": d,
                "real": round(float(row["real"]), 2) if not pd.isna(row["real"]) else None,
                "forecast": round(float(row["forecast"]), 2) if not pd.isna(row["forecast"]) else None
            }
        
        # 3. Add future forecast results
        for r in future_results:
            d = r.date.strftime("%Y-%m-%d") if isinstance(r.date, datetime) else str(r.date)
            qty = round(float(r.quantity), 2)
            if d in merged:
                merged[d]["forecast"] = qty
            else:
                merged[d] = {"date": d, "real": None, "forecast": qty}
        
        chart_data = sorted(merged.values(), key=lambda x: x["date"])

        metrics_dict = None
        if metrics:
            metrics_dict = {
                "mae": round(float(metrics.mae), 4), "mape": round(float(metrics.mape), 4), "rmse": round(float(metrics.rmse), 4),
                "mean": round(float(metrics.mean), 4), "median": round(float(metrics.median), 4), "std_dev": round(float(metrics.std_dev), 4),
                "p25": round(float(metrics.p25), 4), "p75": round(float(metrics.p75), 4), "outliers_count": int(metrics.outliers_count),
            }

        return {
            "product_id": product_id, "product_name": product.name, "product_code": product.default_code or "",
            "abc_class": product.abc_class or "C", "forecast_model": product.forecast_model or "Naive",
            "forecast_mape": round(float(product.forecast_mape or 0), 2),
            "bias": round(float(metrics.bias if metrics else 0), 2),
            "wmape": round(float(metrics.wmape if metrics else 0), 2),
            "demand_pattern": product.demand_pattern or "Estable",
            "trend_type": product.trend_type or "Stable", "seasonality_strength": round(float(product.seasonality_strength or 0), 4),
            "volatility_index": round(float(product.volatility_index or 0), 4), "daily_demand": round(float(product.daily_demand or 0), 4),
            "chart_data": chart_data, 
            "forecast_results": [
                {"date": r.date.strftime("%Y-%m-%d"), "quantity": round(float(r.quantity), 2)} 
                for r in future_results
            ],
            "metrics": metrics_dict, "has_sufficient_data": len(real_series) >= MIN_DATAPOINTS,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _process_product(self, product: Product) -> str:
        data_points = []
        for m in product.moves:
            if m.move_type == "out" and m.state == "done": data_points.append((m.date, m.product_uom_qty))
        for s in product.sales_history: data_points.append((s.date, s.quantity))
        series = build_weekly_series(data_points)

        if len(series) < MIN_DATAPOINTS:
            product.forecast_model = "Insuficiente"; self.session.add(product); return "skipped"

        stats = compute_demand_stats(series)
        
        # Professional Backtesting: Time Series Cross Validation (Rolling Windows)
        n = len(series)
        horizon = 4 # Use 4 weeks as the test horizon for backtesting
        num_folds = 3 # Use 3 rolling windows if possible
        
        best_model_name = "Naive"
        best_mape = float("inf")
        best_metrics = {"mae": 0.0, "mape": 0.0, "rmse": 0.0, "bias": 0.0, "wmape": 0.0}

        for model_name, model_fn in ALL_MODELS.items():
            try:
                fold_errors = []
                for i in range(num_folds):
                    cutoff = n - (horizon * (i + 1))
                    if cutoff < MIN_DATAPOINTS: break
                    
                    train_fold = series.iloc[:cutoff]
                    test_fold = series.iloc[cutoff : cutoff + horizon]
                    
                    res = model_fn(train_fold, horizon)
                    if not res: continue
                    
                    m = compute_error_metrics(test_fold, res["forecast"])
                    fold_errors.append(m)
                
                if not fold_errors: continue
                
                # Average MAPE across folds
                avg_mape = np.mean([f["mape"] for f in fold_errors])
                if avg_mape < best_mape:
                    best_mape = avg_mape
                    best_model_name = model_name
                    # Take the metrics from the most recent fold as the representative ones
                    best_metrics = fold_errors[0]
            except Exception as e:
                logger.debug(f"Backtest failed for {model_name}: {e}")
                continue

        # Final forecast
        final_res = ALL_MODELS[best_model_name](series, HORIZON_WEEKS)
        future = final_res["forecast"]

        for date, qty in future.items():
            self.session.add(ForecastResult(product_id=product.odoo_id, date=date, quantity=float(max(0, qty)), is_real=False))

        self.session.add(ForecastMetric(
            product_id=product.odoo_id, 
            mae=best_metrics["mae"], mape=best_metrics["mape"], rmse=best_metrics["rmse"],
            bias=best_metrics["bias"], wmape=best_metrics["wmape"],
            mean=stats["mean"], median=stats["median"], std_dev=stats["std_dev"], p25=stats["p25"], p75=stats["p75"], outliers_count=stats["outliers_count"],
        ))

        product.forecast_model = best_model_name; product.forecast_mape = best_metrics["mape"]
        product.demand_pattern = stats["demand_pattern"]; product.trend_type = stats["trend_type"]
        product.seasonality_strength = stats["seasonality_strength"]; product.volatility_index = stats["volatility_index"]
        product.daily_demand = round(float(future.mean()) / 7.0, 4)
        product.cv = stats["cv"]
        self.session.add(product)
        return "processed"
