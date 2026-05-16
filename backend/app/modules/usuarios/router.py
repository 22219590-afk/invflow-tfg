from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.database import get_session
from .service import UserService
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="", tags=["Users"])

class UserCreate(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: str = None
    password: str = None
    is_active: bool = None

@router.get("/users", response_model=List[dict])
def list_users(session: Session = Depends(get_session)):
    service = UserService(session)
    users = service.get_users()
    # Don't return hashed passwords
    return [{"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active} for u in users]

@router.post("/users")
def create_user(user_data: UserCreate, session: Session = Depends(get_session)):
    service = UserService(session)
    return service.create_user(user_data.dict())

@router.put("/users/{user_id}")
def update_user(user_id: int, user_data: UserUpdate, session: Session = Depends(get_session)):
    service = UserService(session)
    user = service.update_user(user_id, user_data.dict(exclude_unset=True))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, session: Session = Depends(get_session)):
    service = UserService(session)
    if not service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}
