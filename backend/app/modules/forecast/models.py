"""
Forecast Models — Individual model implementations.
Each model: receives a pd.Series, returns a dict with 'forecast' and 'fitted' series.
No DB access. Stateless functions.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

MIN_SERIES_LEN_ARIMA = 10
MIN_SERIES_LEN_HW = 12

def check_stationarity(series: pd.Series) -> bool:
    """ADF Test for stationarity. Returns True if stationary (p-value < 0.05)."""
    if len(series) < 10: return True # Insufficient data, assume stationary for simple models
    try:
        from statsmodels.tsa.stattools import adfuller
        result = adfuller(series.dropna())
        return result[1] < 0.05
    except:
        return True

def model_naive(series: pd.Series, horizon: int) -> dict:
    """Naive forecast: rolling mean of last 4 observations."""
    if series.empty:
        return {"forecast": pd.Series([], dtype=float), "fitted": pd.Series([], dtype=float)}
    
    # Forecast
    val = float(series.tail(4).mean())
    last_date = series.index[-1]
    future_dates = pd.date_range(start=last_date + pd.tseries.frequencies.to_offset("W"),
                                  periods=horizon, freq="W")
    forecast = pd.Series([max(0, val)] * horizon, index=future_dates)
    
    # Fitted: simple rolling mean
    fitted = series.rolling(window=min(4, len(series))).mean().fillna(method='bfill')
    
    return {"forecast": forecast, "fitted": fitted}


def model_holt_winters(series: pd.Series, horizon: int) -> dict | None:
    """Holt-Winters Exponential Smoothing with AIC optimization."""
    if len(series) < MIN_SERIES_LEN_HW:
        return None
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        # Seasonal periods: 52 for weekly, 12 for monthly
        # Check freq of series index
        freq = series.index.inferred_freq or "W"
        sp = 52 if "W" in freq else 12
        
        # Only use seasonal if we have at least 2 full cycles
        use_seasonal = len(series) >= 2 * sp
        
        if use_seasonal:
            model = ExponentialSmoothing(series, seasonal_periods=sp, trend="add", seasonal="add",
                                         initialization_method="estimated").fit(optimized=True)
        else:
            model = ExponentialSmoothing(series, trend="add",
                                         initialization_method="estimated").fit(optimized=True)
            
        forecast = model.forecast(horizon).clip(lower=0)
        fitted = model.fittedvalues.clip(lower=0)
        return {"forecast": forecast, "fitted": fitted, "aic": model.aic}
    except Exception as e:
        logger.warning(f"Holt-Winters failed: {e}")
        return None


def model_arima(series: pd.Series, horizon: int) -> dict | None:
    """Professional Auto-ARIMA using pmdarima (AIC/BIC selection)."""
    if len(series) < MIN_SERIES_LEN_ARIMA:
        return None
    try:
        import pmdarima as pm
        
        # Check stationarity to decide on 'd'
        is_stationary = check_stationarity(series)
        d_val = 0 if is_stationary else 1
        
        model = pm.auto_arima(
            series, 
            d=d_val,
            start_p=0, start_q=0, max_p=3, max_q=3,
            seasonal=False, # Weekly seasonality (52) is too slow for auto_arima on many products
            stepwise=True,
            suppress_warnings=True, 
            error_action='ignore'
        )
        
        forecast_vals = model.predict(n_periods=horizon)
        last_date = series.index[-1]
        freq = series.index.inferred_freq or "W"
        future_dates = pd.date_range(start=last_date + pd.tseries.frequencies.to_offset(freq),
                                      periods=horizon, freq=freq)
        
        forecast = pd.Series([max(0, v) for v in forecast_vals], index=future_dates)
        fitted = pd.Series(model.predict_in_sample(), index=series.index).clip(lower=0)
        
        return {"forecast": forecast, "fitted": fitted, "aic": model.aic()}
    except Exception as e:
        logger.warning(f"Auto-ARIMA failed: {e}")
        return None


def model_exponential_smoothing(series: pd.Series, horizon: int) -> dict | None:
    """Simple exponential smoothing (SES) — good for stationary series."""
    if len(series) < 3:
        return None
    try:
        from statsmodels.tsa.holtwinters import SimpleExpSmoothing
        model = SimpleExpSmoothing(series, initialization_method="estimated").fit(optimized=True)
        forecast = model.forecast(horizon).clip(lower=0)
        fitted = model.fittedvalues.clip(lower=0)
        return {"forecast": forecast, "fitted": fitted}
    except Exception as e:
        logger.warning(f"SES failed: {e}")
        return None


ALL_MODELS = {
    "Holt-Winters": model_holt_winters,
    "ARIMA": model_arima,
    "Exponential-Smoothing": model_exponential_smoothing,
    "Naive": model_naive,
}
