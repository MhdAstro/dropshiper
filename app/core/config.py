from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    PROJECT_NAME: str = "Inventory Management System"
    DEBUG: bool = True
    
    # URLs
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Database
    DATABASE_URL: str = "postgresql://imp-psql-postgresql-ha.stage-monajjem.svc.cluster.local:5432/dropshiper_db"
    TEST_DATABASE_URL: str = "postgresql://user:pass@localhost:5432/inventory_test_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Platform API Keys
    TELEGRAM_BOT_TOKEN: str = ""
    BASALAM_API_KEY: str = ""
    BASALAM_API_SECRET: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()