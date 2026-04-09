# License Monitoring Dashboard

## What This Is

Внутренний веб-дашборд для команды Эксплуатации Облачных Сервисов АО «Транстелеком» для централизованного учёта и мониторинга лицензий на ключевые продукты инфраструктуры (vCenter, vCloud Director, Veeam и др.). Система уведомляет команду через Telegram заблаговременно до истечения лицензий, исключая человеческий фактор. Пользователи самостоятельно добавляют и редактируют записи о лицензиях через интерфейс.

## Core Value

Никогда не пропустить истечение лицензии — Telegram-уведомление приходит заранее, до того как поддержка или сервис перестанут работать.

## Requirements

### Validated

- [x] Деплой через Docker Compose, конфигурация через .env файл — *Validated in Phase 1: Infrastructure*
- [x] Поля лицензии: продукт/система, дата покупки, дата истечения, ответственный, стоимость, комментарий — *Validated in Phase 1: Infrastructure (schema defined)*
- [x] Дашборд с общей статистикой: всего лицензий, истекает скоро, уже истекло — *Validated in Phase 2: Dashboard*
- [x] Таблица лицензий с фильтрацией и сортировкой — *Validated in Phase 2: Dashboard*
- [x] Цветовая подсветка строк по статусу: красный (истекло / критично), жёлтый (скоро), зелёный (активно) — *Validated in Phase 2: Dashboard*
- [x] Виджет «Скоро истекающие» на главной странице — *Validated in Phase 2: Dashboard*
- [x] CRUD лицензий через веб-интерфейс (добавить / редактировать / удалить) — *Validated in Phase 3: License CRUD*
- [x] Детальная страница лицензии — *Validated in Phase 3: License CRUD*

### Active
- [ ] Telegram-уведомления: один бот → один чат/группа
- [ ] Глобальный порог уведомлений (например, за 30/60/90 дней) + возможность переопределить на уровне конкретной лицензии
- [ ] Расписание: уведомления проверяются и отправляются автоматически (cron/scheduler)
- [ ] Настройки Telegram (токен бота, chat_id, пороги) через интерфейс или .env
- [ ] Деплой через Docker Compose, конфигурация через .env файл

### Out of Scope

- Авторизация / логин-пароль — не в v1, будет добавлена позже через Keycloak (уже используется в компании)
- Автоматическое получение данных о лицензиях из vCenter/vCD/Veeam API — пользователи вводят данные вручную
- Мультитенантность / разграничение прав по ролям — не в v1
- Email-уведомления — только Telegram

## Context

- Облако развёрнуто на VMware vCenter + vCloud Director; бэкапы — Veeam
- Команда уже использует Keycloak — интеграция авторизации запланирована на следующий этап
- Инфраструктура: Linux-серверы, Docker доступен, docker-compose доступен
- Внутренний инструмент — внешний доступ не предполагается, работает в корпоративной сети
- Критичность: пропуск срока лицензии — прямые операционные риски (недоступность поддержки, блокировка сервиса)

## Constraints

- **Tech Stack**: Python (FastAPI) + SQLite + Jinja2/HTMX — легковесный стек, без внешних зависимостей по БД для v1
- **Deployment**: Docker Compose обязателен; конфигурация только через .env
- **Auth**: Без авторизации в v1 (внутренняя сеть); Keycloak-интеграция в следующем milestone
- **Notifications**: Только Telegram Bot API; один бот / один чат-назначение
- **Data entry**: Ручной ввод данных — нет интеграций с API продуктов

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + FastAPI вместо Django | Легче и быстрее для простого CRUD+дашборд; Django избыточен без нужды в встроенной админке | — Pending |
| SQLite в v1 | Один контейнер, нет зависимости от внешней БД; достаточно для команды из десятков пользователей | — Pending |
| Jinja2 + HTMX для фронтенда | Минимальный JS, серверный рендеринг, без сборщика — проще поддерживать | — Pending |
| APScheduler для cron-уведомлений | Встроен в Python-процесс, не нужен отдельный контейнер celery/redis | — Pending |
| Keycloak-авторизация отложена на v2 | Не блокирует запуск; инструмент работает во внутренней сети | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-09 after Phase 3 completion*
