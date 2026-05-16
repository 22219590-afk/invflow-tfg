from sqlmodel import Session, select
from app.models.models import User
from typing import List, Optional
from app.core.auth import get_password_hash

class UserService:
    def __init__(self, session: Session):
        self.session = session

    def get_users(self) -> List[User]:
        return self.session.exec(select(User)).all()

    def create_user(self, data: dict) -> User:
        # TFG Fix: Use bcrypt hash from auth core
        hashed = get_password_hash(data['password'])
        user = User(
            username=data['username'],
            hashed_password=hashed,
            role='admin', # All users are admins now
            is_active=True
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_user(self, user_id: int, data: dict) -> Optional[User]:
        user = self.session.get(User, user_id)
        if not user:
            return None
        
        if 'username' in data:
            user.username = data['username']
        if 'password' in data and data['password']:
            user.hashed_password = get_password_hash(data['password'])
        # Role is always admin
        user.role = 'admin'
        if 'is_active' in data:
            user.is_active = data['is_active']
            
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        user = self.session.get(User, user_id)
        if not user:
            return False
        self.session.delete(user)
        self.session.commit()
        return True
