from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    description="ICU Sepsis Early Warning System API",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/api/health", tags=["Health"])
def api_health():
    return {"status": "ok"}


# Import and include routers
from app.api.auth import router as auth_router  # noqa: E402
from app.api.users import router as users_router  # noqa: E402
from app.api.patients import router as patients_router  # noqa: E402
from app.api.vitals import router as vitals_router  # noqa: E402
from app.api.predictions import router as predictions_router  # noqa: E402
from app.api.alerts import router as alerts_router  # noqa: E402
from app.api.settings import router as settings_router  # noqa: E402

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(patients_router, prefix="/api/patients", tags=["Patients"])
app.include_router(vitals_router, prefix="/api/vitals", tags=["Vitals"])
app.include_router(predictions_router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])


# Startup event: create tables and seed data
@app.on_event("startup")
async def startup():
    from app.db.base import Base
    from app.db.session import engine
    from app.db.seed import seed_data
    import app.models  # noqa: F401 — import all models so tables are registered

    Base.metadata.create_all(bind=engine)
    seed_data()

