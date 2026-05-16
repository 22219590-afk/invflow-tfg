import os
from sqlmodel import Session, create_engine, SQLModel
from typing import Generator

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
engine = create_engine(DATABASE_URL)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def init_db():
    SQLModel.metadata.create_all(engine)
