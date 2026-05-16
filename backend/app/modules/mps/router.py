from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.models import User
from app.modules.mps.models import MPSSolution, MPSMonthDetail
from app.modules.mps.services import MPSEngine

router = APIRouter(prefix="/v1/mps", tags=["MPS"])

@router.get("/latest")
def get_latest_mps(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get the most recently calculated MPS solution."""
    solution = session.exec(select(MPSSolution).order_by(MPSSolution.created_at.desc())).first()
    if not solution:
        # Auto-solve if none exists
        engine = MPSEngine(session)
        solution = engine.solve_aggregate_plan()
    
    # Load details
    details = session.exec(
        select(MPSMonthDetail)
        .where(MPSMonthDetail.solution_id == solution.id)
        .order_by(MPSMonthDetail.month_index)
    ).all()
    
    return {
        "id": solution.id,
        "name": solution.name,
        "created_at": solution.created_at,
        "total_cost": solution.total_cost,
        "breakdown": {
            "production": solution.production_cost,
            "storage": solution.storage_cost,
            "hiring": solution.hiring_cost,
            "firing": solution.firing_cost,
        },
        "months": details
    }

@router.post("/solve")
def solve_mps(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Trigger a new LP calculation for the MPS."""
    try:
        engine = MPSEngine(session)
        solution = engine.solve_aggregate_plan()
        return {"message": "MPS recalculado con éxito", "solution_id": solution.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el motor MPS: {str(e)}")
