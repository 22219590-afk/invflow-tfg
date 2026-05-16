"""
Forecast Analytics — Pure statistical analysis layer.
No DB access, no API calls. Only numpy/pandas computations.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any


def compute_demand_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute full statistical profile for a demand time series."""
    if series.empty or len(series) < 2:
        return {
            "mean": 0.0, "median": 0.0, "std_dev": 0.0, "cv": 0.0,
            "p25": 0.0, "p75": 0.0, "outliers_count": 0,
            "intermittency": 0.0, "demand_pattern": "Insuficiente",
            "trend_type": "Stable", "seasonality_strength": 0.0,
            "volatility_index": 0.0,
        }

    mean = float(series.mean())
    std = float(series.std()) if len(series) > 1 else 0.0
    cv = (std / mean) if mean > 0 else 0.0

    # Outlier detection via IQR
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    outliers = int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())

    # Intermittency: % weeks with zero demand
    zero_ratio = float((series == 0).sum() / len(series))

    # Trend: compare first half vs second half mean
    mid = len(series) // 2
    first_half_mean = series.iloc[:mid].mean()
    second_half_mean = series.iloc[mid:].mean()
    if second_half_mean > first_half_mean * 1.1:
        trend = "Increasing"
    elif second_half_mean < first_half_mean * 0.9:
        trend = "Decreasing"
    else:
        trend = "Stable"

    # Seasonality strength via autocorrelation at lag 13 (quarterly) and 52 (annual)
    seasonality_strength = 0.0
    if len(series) >= 26:
        try:
            ac13 = abs(float(series.autocorr(lag=13)))
            ac26 = abs(float(series.autocorr(lag=26))) if len(series) >= 52 else 0.0
            seasonality_strength = float(max(ac13, ac26))
        except Exception:
            seasonality_strength = 0.0

    # Demand pattern classification
    if zero_ratio > 0.5:
        pattern = "Intermitente"
    elif cv > 0.7:
        pattern = "Volátil"
    elif seasonality_strength > 0.45:
        pattern = "Estacional"
    else:
        pattern = "Estable"

    return {
        "mean": round(mean, 4),
        "median": round(float(series.median()), 4),
        "std_dev": round(std, 4),
        "cv": round(cv, 4),
        "p25": round(q1, 4),
        "p75": round(q3, 4),
        "outliers_count": outliers,
        "intermittency": round(zero_ratio, 4),
        "demand_pattern": pattern,
        "trend_type": trend,
        "seasonality_strength": round(seasonality_strength, 4),
        "volatility_index": round(cv, 4),
    }


def compute_error_metrics(actual: pd.Series, predicted: pd.Series) -> Dict[str, float]:
    """MAE, MAPE, RMSE, BIAS, WMAPE between actual and predicted values."""
    if len(actual) == 0 or len(predicted) == 0:
        return {"mae": 0.0, "mape": 0.0, "rmse": 0.0, "bias": 0.0, "wmape": 0.0}
    
    actual = actual.fillna(0)
    predicted = predicted.fillna(0)
    
    diff = actual.values - predicted.values
    abs_diff = np.abs(diff)
    
    mae = float(np.mean(abs_diff))
    mape = float(np.mean(abs_diff / np.maximum(actual.values, 1.0))) * 100
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    
    # Bias: average error (not absolute)
    bias = float(np.mean(diff))
    
    # WMAPE: Weighted Mean Absolute Percentage Error (Total Abs Error / Total Demand)
    total_actual = np.sum(actual.values)
    wmape = (np.sum(abs_diff) / total_actual * 100) if total_actual > 0 else 0.0
    
    return {
        "mae": round(mae, 4), 
        "mape": round(mape, 4), 
        "rmse": round(rmse, 4),
        "bias": round(bias, 4),
        "wmape": round(wmape, 4)
    }


def build_weekly_series(data_points: list) -> pd.Series:
    """Convert list of (date, qty) tuples into a clean weekly aggregated Series."""
    if not data_points:
        return pd.Series([], dtype=float)
    df = pd.DataFrame(data_points, columns=["date", "qty"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").resample("W").sum().fillna(0)
    return df["qty"]


def build_monthly_series(series: pd.Series) -> pd.Series:
    """Resample weekly series to monthly."""
    if series.empty:
        return series
    return series.resample("MS").sum()
