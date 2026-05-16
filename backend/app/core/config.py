import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Odoo Inventory Optimizer"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    ODOO_URL: str = os.getenv("ODOO_URL", "")
    ODOO_DB: str = os.getenv("ODOO_DB", "")
    ODOO_USER: str = os.getenv("ODOO_USER", "")
    ODOO_PASSWORD: str = os.getenv("ODOO_PASSWORD", "")

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "super-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 1 week

settings = Settings()
