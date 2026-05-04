import os

DB_PATH = os.getenv("DB_PATH", "/data/licenses.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NOTIFY_DAYS_BEFORE = int(os.getenv("NOTIFY_DAYS_BEFORE", "60"))
TZ = os.getenv("TZ", "Asia/Almaty")
