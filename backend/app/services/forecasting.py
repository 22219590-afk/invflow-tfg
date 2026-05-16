import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, delete
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from app.models.models import Product, StockMove, SalesHistory, ForecastResult, ForecastMetric

class ForecastingService:
    def __init__(self, session: Session):
        self.session = session

    def run_all_forecasts(self):
        """Main engine: process all products and store results."""
        products = self.session.exec(select(Product)).all()
        if not products: return

        # Wipe old forecasts to ensure consistency
        self.session.exec(delete(ForecastResult))
        self.session.exec(delete(ForecastMetric))
        
        for p in products:
            self._process_product_forecast(p)
            
        self.session.commit()

    def _process_product_forecast(self, product: Product):
        """Analyzes history, runs multiple models, selects best, and stores metrics."""
        # 1. Gather History (Real + Synthetic)
        real_moves = [m for m in product.moves if m.move_type == 'out' and m.state == 'done']
        synth_history = product.sales_history
        
        if not real_moves and not synth_history:
            return

        # Prepare Time Series (Weekly granularity as requested)
        data = []
        for m in real_moves:
            data.append({"date": m.date, "qty": m.product_uom_qty})
        for s in synth_history:
            data.append({"date": s.date, "qty": s.quantity})
            
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").resample("W").sum().fillna(0)
        
        if len(df) < 4: # Minimal history for any model
            return

        series = df["qty"]
        
        # 2. Backtesting & Model Selection
        # Split: last 4 weeks for testing if we have enough data, else last 2
        test_size = min(len(df) // 4, 8) if len(df) > 12 else 2
        train = series[:-test_size]
        test = series[-test_size:]
        
        models = {}
        
        # Model 1: Holt-Winters (Triple Exponential Smoothing)
        try:
            # We try seasonal if we have enough data (at least 2 seasons)
            seasonal_periods = 52 # Weekly seasonality
            if len(train) > seasonal_periods * 2:
                hw_model = ExponentialSmoothing(train, seasonal_periods=seasonal_periods, trend='add', seasonal='add').fit()
            else:
                hw_model = ExponentialSmoothing(train, trend='add').fit()
            models["Holt-Winters"] = hw_model.forecast(test_size)
        except: pass

        # Model 2: ARIMA (Simplified (1,1,1))
        try:
            arima_model = ARIMA(train, order=(1,1,1)).fit()
            models["ARIMA"] = arima_model.forecast(test_size)
        except: pass

        # Model 3: Naive Seasonal (Fallback)
        try:
            # Just take the average of last few weeks
            val = train.tail(4).mean()
            models["Naive"] = pd.Series([val] * test_size, index=test.index)
        except: pass

        # 3. Evaluate and Select Best
        best_model_name = "Naive"
        min_mape = float('inf')
        best_metrics = {"mae": 0, "mape": 0, "rmse": 0}
        
        for name, pred in models.items():
            mae = np.mean(np.abs(test - pred))
            mape = np.mean(np.abs((test - pred) / np.maximum(test, 1))) * 100
            rmse = np.sqrt(np.mean((test - pred)**2))
            
            if mape < min_mape:
                min_mape = mape
                best_model_name = name
                best_metrics = {"mae": mae, "mape": mape, "rmse": rmse}

        # 4. Final Forecast (Next 52 weeks for MPS/MRP)
        # Re-fit best model on full series
        forecast_len = 52
        if best_model_name == "Holt-Winters":
            try:
                final_model = ExponentialSmoothing(series, trend='add').fit()
                future = final_model.forecast(forecast_len)
            except: future = [series.mean()] * forecast_len
        elif best_model_name == "ARIMA":
            try:
                final_model = ARIMA(series, order=(1,1,1)).fit()
                future = final_model.forecast(forecast_len)
            except: future = [series.mean()] * forecast_len
        else:
            future = [series.tail(4).mean()] * forecast_len

        # 5. Statistical Analysis
        std = series.std()
        mean = series.mean()
        cv = (std / mean) if mean > 0 else 0
        
        # Classification
        pattern = "Stable"
        if cv > 0.5: pattern = "Volatile"
        # Simple seasonal check: autocorrelation at lag 52 (weekly) or 4 (monthly approx)
        if len(series) > 52:
            autocorr = series.autocorr(lag=52)
            if autocorr > 0.6: pattern = "Seasonal"
        
        # 6. Store Results
        product.forecast_model = best_model_name
        product.forecast_mape = best_metrics["mape"]
        product.demand_pattern = pattern
        product.volatility_index = cv
        
        # Store future forecast results
        last_date = series.index[-1]
        
        # Ensure future is a Series with a proper date index
        if isinstance(future, list) or not isinstance(future.index, pd.DatetimeIndex):
            future_dates = pd.date_range(start=last_date + timedelta(weeks=1), periods=len(future), freq='W')
            future = pd.Series(future.values if hasattr(future, 'values') else future, index=future_dates)

        product.trend_type = "Increasing" if future.iloc[-1] > series.iloc[-1] else "Decreasing" if future.iloc[-1] < series.iloc[-1] else "Stable"

        for date, qty in future.items():
            self.session.add(ForecastResult(
                product_id=product.odoo_id,
                date=date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date,
                quantity=max(0, float(qty)),
                is_real=False
            ))
            
        # Store metrics
        metric = ForecastMetric(
            product_id=product.odoo_id,
            mae=best_metrics["mae"],
            mape=best_metrics["mape"],
            rmse=best_metrics["rmse"],
            mean=mean,
            median=series.median(),
            std_dev=std,
            p25=series.quantile(0.25),
            p75=series.quantile(0.75),
            outliers_count=0 # Simple outlier detection could be added here
        )
        self.session.add(metric)
        
        # 7. Update Daily Demand in Product (Centralized)
        # Weekly Forecast / 7
        product.daily_demand = float(future.mean() / 7.0)
        product.demand_std_dev = float(std / np.sqrt(7.0)) if std > 0 else 0.1
        
        # If product was using manual demand, we respect it but store the calculated one in metrics
