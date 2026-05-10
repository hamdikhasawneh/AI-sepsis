from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

kwargs = {}
if settings.DATABASE_URL.startswith("sqlite"):
    kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, **kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
