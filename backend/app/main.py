from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.websocket import manager


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


# WebSocket endpoint for real-time alerts
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Import and include routers
from app.api.auth import router as auth_router  # noqa: E402
from app.api.users import router as users_router  # noqa: E402
from app.api.patients import router as patients_router  # noqa: E402
from app.api.vitals import router as vitals_router  # noqa: E402
from app.api.predictions import router as predictions_router  # noqa: E402
from app.api.alerts import router as alerts_router  # noqa: E402
from app.api.settings import router as settings_router  # noqa: E402
from app.api.tasks import router as tasks_router  # noqa: E402
from app.api.labs import router as labs_router  # noqa: E402
from app.api.documents import router as documents_router  # noqa: E402

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(patients_router, prefix="/api/patients", tags=["Patients"])
app.include_router(vitals_router, prefix="/api/vitals", tags=["Vitals"])
app.include_router(predictions_router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(labs_router, prefix="/api/labs", tags=["Lab Results"])
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])


# Startup event: create tables and seed data
@app.on_event("startup")
async def startup():
    from app.db.base import Base
    from app.db.session import engine
    from app.db.seed import seed_data
    import app.models  # noqa: F401 — import all models so tables are registered

    Base.metadata.create_all(bind=engine)
    seed_data()

