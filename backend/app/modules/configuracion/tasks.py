from celery import shared_task
from app.core.database import engine
from sqlmodel import Session
from app.services.odoo_connector import OdooConnector
from app.services.analytics import AnalyticsService
import logging

logger = logging.getLogger(__name__)

@shared_task(name="configuracion.sync_odoo_data")
def sync_odoo_task():
    """
    Background task to sync data from Odoo to the internal database.
    This implementation follows the incremental sync requirement.
    """
    logger.info("Starting Odoo synchronization task...")
    try:
        with Session(engine) as session:
            from .service import ConfigService
            service = ConfigService(session)
            result = service.run_incremental_sync()
            
            logger.info(f"Odoo synchronization completed: {result}")
            
            # Trigger forecasting in background
            from app.modules.forecast.tasks import calculate_forecasts_task
            calculate_forecasts_task.delay()
            
            return result
    except Exception as e:
        logger.error(f"Odoo synchronization failed: {e}")
        return {"status": "error", "message": str(e)}
