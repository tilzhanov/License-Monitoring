from typing import Annotated
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, DeclarativeBase
from fastapi import Depends
from app.config import DATABASE_URL, SQL_ECHO

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=SQL_ECHO,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


class Base(DeclarativeBase):
    pass


def create_db_tables():
    Base.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def bootstrap_settings():
    """Write Telegram credentials from .env to app_settings on first run only (D-09)."""
    from app.models import AppSettings
    from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    with Session(engine) as db:
        existing = db.query(AppSettings).first()
        if existing is not None:
            return

        defaults = [
            AppSettings(key="telegram_bot_token", value=TELEGRAM_BOT_TOKEN),
            AppSettings(key="telegram_chat_id", value=TELEGRAM_CHAT_ID),
            AppSettings(key="notify_days_before", value="60"),
            AppSettings(key="notifications_enabled", value="true"),
        ]
        db.add_all(defaults)
        db.commit()
