from __future__ import annotations
import os
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://sepsis_user:sepsis_pass@db:5432/sepsis_db"
    )

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # App
    APP_NAME: str = "ICU Sepsis Detection System"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # CORS
    _CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    
    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [o.strip() for o in self._CORS_ORIGINS.split(",")]

    # Simulation
    SIMULATION_EXCEL_PATH: str = os.getenv(
        "SIMULATION_EXCEL_PATH",
        r"C:\Users\hrhkh\Downloads\icu_dst_simulation_data.xlsx"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
