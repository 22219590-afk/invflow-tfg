import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.models import User
from app.modules.mrp.services import MRPService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/mrp", tags=["MRP"])

@router.post("/solve")
def solve_mrp(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Triggers the MRP calculation loop."""
    try:
        service = MRPService(session)
        result = service.run_mrp()
        return result
    except Exception as e:
        logger.error(f"MRP Solve Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/view")
def get_mrp_view(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Returns the complete MRP grid data for the frontend."""
    try:
        service = MRPService(session)
        return service.get_full_mrp_view()
    except Exception as e:
        logger.error(f"MRP View Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bom/{product_id}")
def get_product_bom(
    product_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Returns the BOM tree for a specific product."""
    from app.models.models import BOM, Product
    from sqlmodel import select

    def build_tree(pid, qty=1.0):
        product = session.exec(select(Product).where(Product.odoo_id == pid)).first()
        if not product: return None
        
        children = session.exec(select(BOM).where(BOM.parent_id == pid)).all()
        return {
            "id": pid,
            "name": product.name,
            "sku": product.default_code,
            "qty": qty,
            "lead_time": product.lead_time_days,
            "children": [build_tree(c.child_id, c.quantity) for c in children]
        }

    return build_tree(product_id)
