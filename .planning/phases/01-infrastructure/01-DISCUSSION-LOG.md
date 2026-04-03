# Phase 1: Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 01-infrastructure
**Areas discussed:** Port & deployment, DB schema, Settings model

---

## Port & Deployment

| Option | Description | Selected |
|--------|-------------|----------|
| 8080 | Стандартный выбор для внутренних веб-сервисов | ✓ |
| 8000 | Дефолт FastAPI/uvicorn | |
| Задать через .env | APP_PORT в .env | |

**User's choice:** 8080 (через .env с дефолтом 8080)
**Notes:** unless-stopped политика перезапуска

---

## DB Schema

### Cost field

| Option | Description | Selected |
|--------|-------------|----------|
| Decimal + валюта | NUMERIC(15,2) + currency | |
| Текст | VARCHAR — произвольный формат | ✓ |
| Два поля | amount + currency | |

**User's choice:** Текст (VARCHAR)
**Notes:** Пользователи пишут "1 500 000 тенге" или "$5000/год" — агрегация не нужна

### Обязательные поля

**User's choice:** product_name, purchase_date, expiry_date — обязательные. Остальные опциональные.

### Дефолтный порог уведомления

| Option | Selected |
|--------|----------|
| 30 дней | |
| 60 дней | ✓ |
| 90 дней | |

**User's choice:** 60 дней

---

## Settings Model

### Что в app_settings

**User's choice:** Все 4 поля: telegram_bot_token, telegram_chat_id, notify_days_before, notifications_enabled

### Bootstrap из .env

| Option | Selected |
|--------|----------|
| Только Telegram из .env | ✓ |
| Все настройки из .env | |

**User's choice:** При первом запуске — bootstrap TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID из .env. Глобальный порог — 60 дней по умолчанию.
