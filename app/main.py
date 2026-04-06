from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import create_db_tables, bootstrap_settings
from app.models import License, AppSettings  # noqa: F401 -- ensure models registered before create_all
from app.routers.pages import router as pages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_tables()
    bootstrap_settings()
    yield


app = FastAPI(title="License Monitor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(pages_router)
