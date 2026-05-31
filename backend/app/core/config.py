import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "InvFlow"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://admin:admin@db/inventory_db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    ODOO_URL: str = os.getenv("ODOO_URL", "")
    ODOO_DB: str = os.getenv("ODOO_DB", "")
    ODOO_USER: str = os.getenv("ODOO_USER", "")
    ODOO_PASSWORD: str = os.getenv("ODOO_PASSWORD", "")

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "super-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # Comma-separated allowed origins, e.g. "https://app.empresa.com,https://empresa.com"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost,http://localhost:5173")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

settings = Settings()
