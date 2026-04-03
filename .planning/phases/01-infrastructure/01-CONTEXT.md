# Phase 1: Infrastructure - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Запущенное контейнеризированное приложение с определённой схемой БД, которое команда может поднять командой `docker-compose up` на любом Linux-хосте. Никакого UI кроме placeholder-страницы. Цель — правильная основа для всех последующих фаз.

</domain>

<decisions>
## Implementation Decisions

### Port & Deployment

- **D-01:** Порт хоста — `8080`. Порт задаётся через `APP_PORT` в `.env` (дефолт 8080), docker-compose пробрасывает `${APP_PORT}:8080`.
- **D-02:** Политика перезапуска контейнера — `unless-stopped` (авторестарт после ребута сервера, но не после `docker stop`).
- **D-03:** SQLite volume — именованный Docker volume (не bind-mount), чтобы избежать проблем с правами на разных хостах.

### DB Schema — таблица `licenses`

- **D-04:** Обязательные поля (NOT NULL): `product_name`, `purchase_date`, `expiry_date`. Остальные поля (`responsible`, `cost`, `comment`, `notify_days_before`) — опциональные (nullable).
- **D-05:** Поле `cost` — тип `VARCHAR` (текст). Пользователь вводит произвольно: "1 500 000 тенге", "$5000/год". Без числовой агрегации.
- **D-06:** Поля дат (`purchase_date`, `expiry_date`) — тип `DATE` (только дата, без времени).
- **D-07:** Поле `notify_days_before` (INTEGER, nullable) — переопределяет глобальный порог для конкретной лицензии. NULL = использовать глобальный.

### DB Schema — таблица `app_settings`

- **D-08:** Таблица хранит 4 настройки: `telegram_bot_token`, `telegram_chat_id`, `notify_days_before` (глобальный порог, дефолт 60), `notifications_enabled` (BOOLEAN, дефолт true).
- **D-09:** При первом запуске (`on startup`): если `.env` содержит `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` — записать их в `app_settings` как начальные значения (только при пустой таблице). Глобальный порог по умолчанию — **60 дней**.
- **D-10:** Приоритет настроек: значения в `app_settings` (БД) всегда имеют приоритет над `.env`. `.env` — только начальный bootstrap.

### Claude's Discretion

- Точная структура `app_settings` (key-value таблица vs отдельные колонки — Claude выбирает что проще)
- Healthcheck endpoint — формат ответа (/health → {"status": "ok"} или просто 200)
- Структура директорий внутри `app/`
- Названия модулей/файлов

</decisions>

<specifics>
## Specific Ideas

- Деплой ориентирован на внутреннюю сеть, нет реверс-прокси требований в v1
- Команда использует Linux-серверы с Docker Compose — экзотических дистрибутивов нет
- Инструмент должен работать "из коробки" после `cp .env.example .env && docker-compose up -d`

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project requirements
- `.planning/PROJECT.md` — Project context, stack decisions, constraints
- `.planning/REQUIREMENTS.md` — Requirements INFRA-01, INFRA-02, INFRA-03, LIC-04
- `.planning/ROADMAP.md` — Phase 1 success criteria and plan breakdown

### Research
- `.planning/research/STACK.md` — FastAPI+SQLite patterns, Docker Compose setup, APScheduler, project structure
- `.planning/research/NOTIFICATIONS.md` — app_settings config precedence pattern, DB-over-env approach

No external specs or ADRs — all requirements captured above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Нет существующего кода — greenfield проект

### Established Patterns
- Нет существующих паттернов — устанавливаем базовые в этой фазе

### Integration Points
- Эта фаза создаёт все integration points для последующих фаз: SQLAlchemy models, FastAPI app instance, Jinja2 templates engine, static files serving

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-infrastructure*
*Context gathered: 2026-04-03*
