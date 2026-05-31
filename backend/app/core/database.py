import os
from sqlmodel import Session, create_engine, SQLModel
from typing import Generator

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")

# Pool de conexiones: evita abrir una conexión nueva por cada petición
engine = create_engine(
    DATABASE_URL,
    pool_size=10,        # conexiones permanentes abiertas
    max_overflow=20,     # conexiones extra en picos de carga
    pool_timeout=30,     # segundos esperando conexión libre antes de error
    pool_recycle=1800,   # recicla conexiones cada 30min (evita conexiones muertas)
    pool_pre_ping=True,  # verifica que la conexión sigue viva antes de usarla
)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def init_db():
    SQLModel.metadata.create_all(engine)
