from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.database import get_session
from .service import ConfigService
from .schemas import OdooConfigSchema, ConfigUpdateSchema
from typing import List

router = APIRouter(prefix="/configuracion", tags=["configuracion"])

@router.get("/")
def get_config(session: Session = Depends(get_session)):
    service = ConfigService(session)
    return service.get_all_config()

@router.post("/")
def update_config(data: ConfigUpdateSchema, session: Session = Depends(get_session)):
    service = ConfigService(session)
    service.update_config(data.items)
    return {"status": "success"}

@router.post("/test-odoo")
def test_odoo(config: OdooConfigSchema, session: Session = Depends(get_session)):
    service = ConfigService(session)
    try:
        result = service.test_odoo_connection(config)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
