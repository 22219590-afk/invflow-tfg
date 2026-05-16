import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlmodel import Session, select, create_engine
from app.models.models import User
from app.core.auth import get_password_hash

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
engine = create_engine(DATABASE_URL)

def reset():
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if admin:
            print(f"Resetting existing admin user...")
            admin.hashed_password = get_password_hash("admin")
            admin.role = "admin"
            admin.is_active = True
        else:
            print(f"Creating new admin user...")
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin"),
                role="admin",
                is_active=True
            )
        session.add(admin)
        session.commit()
        print("Admin user reset to username: admin, password: admin")

if __name__ == "__main__":
    reset()
