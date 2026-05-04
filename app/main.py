from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import bootstrap_settings, create_db_tables, engine
from app.models import AppSettings, License  # noqa: F401 -- ensure models registered before create_all
from app.routers.licenses import router as licenses_router
from app.routers.pages import router as pages_router
from app.routers.settings import router as settings_router
from app.services.scheduler import init_scheduler, shutdown_scheduler


def _read_notify_time() -> tuple[int, int]:
    """Read notify_time from AppSettings; fall back to 09:00 on missing/malformed."""
    with Session(engine) as db:
        row = db.query(AppSettings).filter_by(key="notify_time").first()
        raw = row.value if row and row.value else "09:00"
    try:
        h_str, m_str = raw.split(":")
        return int(h_str), int(m_str)
    except (ValueError, AttributeError):
        return 9, 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_tables()
    bootstrap_settings()
    hour, minute = _read_notify_time()
    init_scheduler(hour=hour, minute=minute)
    yield
    shutdown_scheduler()


app = FastAPI(title="License Monitor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(pages_router)
app.include_router(licenses_router)
app.include_router(settings_router)
