from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import create_db_tables, bootstrap_settings, engine
from app.models import License, AppSettings  # noqa: F401 -- ensure models registered before create_all
from app.routers.pages import router as pages_router
from app.routers.licenses import router as licenses_router
from app.routers.settings import router as settings_router
from app.services.scheduler import init_scheduler, shutdown_scheduler
from sqlalchemy.orm import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_tables()
    bootstrap_settings()
    # Read notify_time from AppSettings; fall back to "09:00"
    with Session(engine) as db:
        row = db.query(AppSettings).filter_by(key="notify_time").first()
        time_str = row.value if row and row.value else "09:00"
    hour, minute = int(time_str.split(":")[0]), int(time_str.split(":")[1])
    init_scheduler(hour=hour, minute=minute)
    yield
    shutdown_scheduler()


app = FastAPI(title="License Monitor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(pages_router)
app.include_router(licenses_router)
app.include_router(settings_router)
