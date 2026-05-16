from celery import shared_task
from app.core.database import engine
from sqlmodel import Session
from app.services.analytics import AnalyticsService
import logging

logger = logging.getLogger(__name__)

@shared_task(name="forecast.calculate_all_forecasts")
def calculate_forecasts_task():
    """
    Background task to calculate demand forecasts for all products.
    """
    logger.info("Starting global forecasting task...")
    try:
        with Session(engine) as session:
            service = AnalyticsService(session)
            # Assuming there's a method to calculate all forecasts
            # For now, we simulate it or call the specific logic
            products = service.get_products_enriched()
            for p in products:
                service.forecast_product(p['id'])
            
            logger.info("Forecasting task completed.")
            return {"status": "success"}
    except Exception as e:
        logger.error(f"Forecasting task failed: {e}")
        return {"status": "error", "message": str(e)}
