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
    APP_NAME: str = "ARISE"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # OCR — Gemini Vision API (for scanned lab report PDFs and images)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # CORS — read directly from env to avoid pydantic-settings field conflicts.
    # Supports comma-separated list. Includes both 5173 and 5174 so Vite port
    # fallback never breaks the connection.
    @property
    def CORS_ORIGINS(self) -> list[str]:
        raw = os.getenv(
            "CORS_ORIGINS",
            "*"
        )
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    # Simulation
    # Default path is repo-relative: backend/data/simulation/DST_Simulation_v5.xlsx
    # Override via SIMULATION_EXCEL_PATH env var for alternative locations.
    SIMULATION_EXCEL_PATH: str = os.getenv(
        "SIMULATION_EXCEL_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # backend/
            "data", "simulation", "DST_Simulation_v5.xlsx"
        )
    )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
