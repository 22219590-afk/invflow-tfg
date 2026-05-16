"""
Forecast API Router — Isolated FastAPI router for the forecasting module.
Only imports from app.modules.forecast.*
Does NOT import from other modules.
"""
import logging
import math
import numpy as np
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.models import User, Product
from app.modules.forecast.services import ForecastEngine

logger = logging.getLogger(__name__)

def clean_json_data(obj: Any) -> Any:
    """Recursively clean objects of NaN and Inf values for JSON compliance."""
    if isinstance(obj, dict):
        return {k: clean_json_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json_data(x) for x in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj

router = APIRouter(prefix="/v1/forecast", tags=["Forecast"])


@router.post("/run")
def run_forecast(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger full forecast recalculation for all products.
    Runs synchronously (acceptable for ≤200 products).
    """
    try:
        engine = ForecastEngine(session)
        result = engine.run_all_products()
        return {
            "message": "Forecasting engine completed successfully",
            "summary": result,
        }
    except Exception as e:
        logger.error(f"Forecast run error: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast engine error: {str(e)}")


@router.post("/run/{product_id}")
def run_forecast_product(
    product_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Recalculate forecast for a single product by Odoo product ID."""
    try:
        engine = ForecastEngine(session)
        result = engine.run_single_product(product_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forecast error for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products")
def get_forecast_products(
    search: Optional[str] = None,
    abc_class: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all products with their forecast metadata.
    Used by the frontend sidebar list.
    """
    from sqlmodel import select
    query = select(Product).where(Product.active == True)
    products = session.exec(query).all()

    result = []
    for p in products:
        # Apply filters
        if abc_class and (p.abc_class or "C") != abc_class.upper():
            continue
        if search:
            s = search.lower()
            if s not in (p.name or "").lower() and s not in (p.default_code or "").lower():
                continue

        has_data = p.forecast_model and p.forecast_model != "Insuficiente"
        result.append({
            "odoo_id": p.odoo_id,
            "name": p.name or "Producto sin nombre",
            "default_code": p.default_code or "",
            "abc_class": p.abc_class or "C",
            "forecast_model": p.forecast_model or "—",
            "forecast_mape": round(float(p.forecast_mape or 0), 2),
            "demand_pattern": p.demand_pattern or "Estable",
            "trend_type": p.trend_type or "Stable",
            "daily_demand": round(float(p.daily_demand or 0), 4),
            "seasonality_strength": round(float(p.seasonality_strength or 0), 4),
            "volatility_index": round(float(p.volatility_index or 0), 4),
            "has_forecast": has_data,
        })

    # Sort: A products first, then by name
    abc_order = {"A": 0, "B": 1, "C": 2}
    result.sort(key=lambda x: (abc_order.get(x["abc_class"], 3), x["name"]))

    return clean_json_data(result)


@router.get("/{product_id}")
def get_forecast_detail(
    product_id: int,
    granularity: str = "weekly",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get full forecast data for a product: historical, future projection, metrics.
    granularity: 'weekly' | 'monthly'
    """
    try:
        engine = ForecastEngine(session)
        data = engine.get_product_forecast_data(product_id)

        if data is None:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

        if not data.get("has_sufficient_data"):
            return {
                **data,
                "message": "Datos insuficientes para forecasting fiable. Se necesitan al menos 4 semanas de historial."
            }

        # Apply aggregation based on granularity
        if data.get("chart_data"):
            import pandas as pd
            chart_df = pd.DataFrame(data["chart_data"])
            chart_df["date"] = pd.to_datetime(chart_df["date"])
            chart_df = chart_df.set_index("date")

            # Default to weekly if not specified or for weekly view
            rule = "W"
            if granularity == "monthly":
                rule = "MS"
            elif granularity == "yearly":
                rule = "YS"
            
            # Resample numeric columns (real and forecast)
            # Use min_count=1 to keep NaNs if all values in period are NaN (important for chart gaps)
            resampled = chart_df.resample(rule).sum(min_count=1)
            resampled = resampled.reset_index()
            
            # Format labels based on granularity
            if granularity == "weekly":
                resampled["date_label"] = resampled["date"].dt.strftime("W%W-%Y")
            elif granularity == "monthly":
                resampled["date_label"] = resampled["date"].dt.strftime("%b %Y")
            elif granularity == "yearly":
                resampled["date_label"] = resampled["date"].dt.strftime("%Y")
            else:
                resampled["date_label"] = resampled["date"].dt.strftime("%d %b")
            
            # Keep date as YYYY-MM-DD for consistency
            resampled["date"] = resampled["date"].dt.strftime("%Y-%m-%d")
            
            data["chart_data"] = resampled.to_dict(orient="records")

        return clean_json_data(data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forecast detail error for {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}/comparison")
def get_model_comparison(
    product_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Returns model comparison data: runs backtest for all models and shows metrics table.
    """
    from sqlmodel import select
    from app.modules.forecast.analytics import compute_demand_stats, build_weekly_series, compute_error_metrics
    from app.modules.forecast.models import ALL_MODELS
    from app.models.models import StockMove, SalesHistory

    product = session.exec(select(Product).where(Product.odoo_id == product_id)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Build series
    data_points = [(m.date, m.product_uom_qty) for m in product.moves if m.move_type == "out" and m.state == "done"]
    data_points += [(s.date, s.quantity) for s in product.sales_history]
    series = build_weekly_series(data_points)

    if len(series) < 4:
        return {"message": "Insufficient data for model comparison", "models": []}

    n = len(series)
    test_size = max(2, min(8, int(n * 0.2)))
    train = series[:-test_size]
    test = series[-test_size:]

    comparison = []
    for model_name, model_fn in ALL_MODELS.items():
        try:
            res = model_fn(train, test_size)
            if res is None or "forecast" not in res:
                raise ValueError("Model returned None or invalid format")
            pred = res["forecast"]
            pred_aligned = pd.Series(pred.values[:test_size], index=test.index)
            metrics = compute_error_metrics(test, pred_aligned)
            comparison.append({
                "model": model_name,
                "mae": metrics["mae"],
                "mape": metrics["mape"],
                "rmse": metrics["rmse"],
                "is_winner": model_name == product.forecast_model,
            })
        except Exception as e:
            comparison.append({
                "model": model_name, "mae": None, "mape": None, "rmse": None,
                "is_winner": False, "error": str(e)
            })

    comparison.sort(key=lambda x: x.get("mape") or 9999)
    return clean_json_data({
        "product_id": product_id,
        "product_name": product.name,
        "selected_model": product.forecast_model,
        "test_weeks": test_size,
        "train_weeks": len(train),
        "models": comparison,
    })

# Need to import pandas for the granularity endpoint
import pandas as pd
