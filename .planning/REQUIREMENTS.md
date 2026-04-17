# Requirements: License Monitoring Dashboard

**Defined:** 2026-04-03
**Core Value:** Никогда не пропустить истечение лицензии — Telegram-уведомление приходит заранее

## v1 Requirements

### Dashboard

- [x] **DASH-01**: Главная страница отображает общую статистику: всего лицензий, истекает в ближайшее время, уже истекло
- [x] **DASH-02**: На главной странице есть виджет «Скоро истекающие» со списком критичных лицензий
- [x] **DASH-03**: Таблица всех лицензий с цветовой подсветкой строк по статусу (красный / жёлтый / зелёный)
- [x] **DASH-04**: Таблица поддерживает фильтрацию (по продукту, статусу) и сортировку (по дате, названию)
- [x] **DASH-05**: Страница детали лицензии показывает все поля и историю изменений

### License Management

- [x] **LIC-01**: Пользователь может добавить лицензию через форму
- [x] **LIC-02**: Пользователь может редактировать любое поле лицензии
- [x] **LIC-03**: Пользователь может удалить лицензию (с подтверждением)
- [ ] **LIC-04**: Лицензия содержит поля: продукт/система, дата покупки, дата истечения, ответственный, стоимость, комментарий
- [ ] **LIC-05**: Статус вычисляется автоматически: активна / скоро истекает / истекла
- [ ] **LIC-06**: Порог «скоро истекает» задаётся глобально (по умолчанию 30 дней) и может быть переопределён для отдельной лицензии

### Notifications

- [ ] **NOTF-01**: Telegram-бот отправляет уведомления в настроенный чат/группу
- [ ] **NOTF-02**: Уведомления отправляются автоматически по расписанию (раз в день)
- [ ] **NOTF-03**: Уведомление содержит: название продукта, дату истечения, количество дней до истечения, ответственного
- [x] **NOTF-04**: Глобальный порог уведомлений настраивается через интерфейс (за сколько дней предупреждать)
- [ ] **NOTF-05**: Для отдельной лицензии можно задать свой порог уведомления, переопределив глобальный
- [x] **NOTF-06**: Настройки Telegram (токен бота, chat_id) задаются через .env или веб-интерфейс настроек

### Settings

- [x] **SETT-01**: Страница настроек: Telegram токен, chat_id, глобальный порог уведомлений
- [ ] **SETT-02**: Кнопка «Отправить тестовое уведомление» для проверки конфигурации
- [x] **SETT-03**: Настройки сохраняются в БД (приоритет над .env значениями)

### Infrastructure

- [x] **INFRA-01**: Приложение запускается через `docker-compose up`
- [x] **INFRA-02**: Конфигурация через `.env` файл: порт, секреты, параметры по умолчанию
- [x] **INFRA-03**: SQLite как хранилище данных (файл монтируется как volume)
- [ ] **INFRA-04**: Планировщик уведомлений запускается внутри Python-процесса (APScheduler)

### UI Polish (Phase 03.1)

- [x] **UI-01**: Introduce a single token-driven CSS design system (colors, spacing, typography, radius, shadow) declared on `:root` in `static/css/app.css`
- [x] **UI-02**: Load Inter + JetBrains Mono via Google Fonts CDN with preconnect and `display=swap`, injected in `templates/base.html` `<head>` BEFORE the stylesheet link
- [x] **UI-03**: Redesign top navigation bar: 56px tall, slate-900 background, `layout-dashboard` icon before brand, 14px uppercase letter-spacing 0.02em brand, accent-600 underline on current link
- [x] **UI-04**: Redesign stat counter cards: label-first then count, 24px tabular-nums count, variant color on count text only, 16px muted icon next to label, no shadow by default
- [x] **UI-05**: Redesign expiring-soon widget: slate-900 h2 with amber `alert-triangle` icon, slate-100 dividers, weight-600 product name, days-badge pill with warning or expired tokens
- [x] **UI-06**: Redesign license table: `.table-container` wrapper, slate-50 thead with uppercase 12px labels, 36px row content height, status row background + 4px inset left bar, product name cell as weight-600 link
- [x] **UI-07**: Replace `▲▼` Unicode sort indicators with inline Lucide `chevron-up` / `chevron-down` SVG in accent-600 12px, add `role="button"`, `tabindex="0"`, and hover `--slate-100` background to sortable headers
- [x] **UI-08**: Redesign filter controls: flex row 8px gap, 36px inputs with slate-200 border, inline `search` icon left 12px in search input, focus ring, primary "+ Добавить лицензию" button with `plus` icon
- [x] **UI-09**: Redesign buttons (primary / secondary / destructive / action-btn / action-link / action-edit / action-delete) with exact height/padding/color/hover/focus matrix from UI-SPEC §Component 8 including universal `:focus-visible` outline
- [x] **UI-10**: Redesign forms: max-width 640px, form-card with slate-200 border + radius-md + space-5 padding + shadow-sm, 12px weight-600 slate-700 labels, 36px inputs with focus ring, `.field-error` with `alert-triangle` icon, required-label `::after " *"`
- [x] **UI-11**: Redesign detail page: max-width 840px, breadcrumb with `arrow-left` icon, detail-card shadow-sm, detail-header flex-between with h1 + status badge, detail-fields grid `200px 1fr` with `8px 24px` gap, detail-comment border-top divider
- [x] **UI-12**: Redesign 404 page: centered layout, `x-circle` 48px slate-300 icon, dynamic `<h1>{{ title if title else "Страница не найдена" }}</h1>`, 14px slate-500 body, `.btn-secondary` back link with locked Russian copy
- [x] **UI-13**: Implement three empty states per UI-SPEC §Component 11 with locked Russian copy (no-licenses full empty, no-filter-match inline row, expiring-widget empty state)
- [x] **UI-14**: Ship reusable `.status-badge` component (inline-flex, 2px 8px padding, radius-lg pill, 12px weight-600, inline SVG icon, three variants), used in table Status column and detail-page header via Jinja macro
- [x] **UI-15**: Update copy throughout templates to match the locked verb+noun Russian copy table in UI-SPEC §Copywriting Contract
- [x] **UI-16**: Add HTMX visual indicators: `.htmx-request { opacity: 0.6; transition: opacity 120ms }` on `#license-tbody`, `pointer-events: none` during swap, `@keyframes fadeIn` on swapped rows, `#stats-section` opacity fade on `license-changed`
- [x] **UI-17**: Accessibility gate: skip-link visually hidden until `:focus`, universal `:focus-visible` accent-600 outline, sortable `<th>` reachable via Tab/Enter/Space, `@media (prefers-reduced-motion: reduce)` disables transitions
- [x] **UI-18**: Test preservation gate: all Phase 2 & Phase 3 test assertions (test_dashboard.py, test_licenses.py, test_health.py, test_status.py) MUST still pass after UI retrofit — hard constraint on every other UI-xx requirement

## v2 Requirements

### Authentication

- **AUTH-01**: Интеграция с Keycloak OIDC для авторизации пользователей
- **AUTH-02**: Управление ролями: просмотр vs. редактирование

### Audit & Export

- **AUDIT-01**: История изменений для каждой лицензии (кто/когда изменил)
- **EXPORT-01**: Экспорт таблицы лицензий в CSV/Excel
- **IMPORT-01**: Импорт лицензий из CSV

### Enhanced Notifications

- **NOTF-07**: Несколько Telegram-чатов с разной адресацией (по проекту/ответственному)
- **NOTF-08**: Уведомление после истечения (напоминание, что лицензия просрочена)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Авторизация в v1 | Инструмент работает во внутренней сети; Keycloak — v2 |
| Авто-получение данных из vCenter/vCD/Veeam API | Требует доступа к API и сложной конфигурации; ручной ввод достаточен для v1 |
| Email-уведомления | Только Telegram в v1 |
| Мобильное приложение | Веб-первый подход |
| Multi-tenant / разграничение по организациям | Один экземпляр для одной команды |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DASH-01 | Phase 2 | Complete |
| DASH-02 | Phase 2 | Complete |
| DASH-03 | Phase 2 | Complete |
| DASH-04 | Phase 2 | Complete |
| DASH-05 | Phase 3 | Complete |
| LIC-01 | Phase 3 | Complete |
| LIC-02 | Phase 3 | Complete |
| LIC-03 | Phase 3 | Complete |
| LIC-04 | Phase 1 | Pending |
| LIC-05 | Phase 2 | Pending |
| LIC-06 | Phase 4 | Pending |
| NOTF-01 | Phase 4 | Pending |
| NOTF-02 | Phase 4 | Pending |
| NOTF-03 | Phase 4 | Pending |
| NOTF-04 | Phase 4 | Complete |
| NOTF-05 | Phase 4 | Pending |
| NOTF-06 | Phase 4 | Complete |
| SETT-01 | Phase 4 | Complete |
| SETT-02 | Phase 4 | Pending |
| SETT-03 | Phase 4 | Complete |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 4 | Pending |
| UI-01 | Phase 03.1 | Complete |
| UI-02 | Phase 03.1 | Complete |
| UI-03 | Phase 03.1 | Complete |
| UI-04 | Phase 03.1 | Complete |
| UI-05 | Phase 03.1 | Complete |
| UI-06 | Phase 03.1 | Complete |
| UI-07 | Phase 03.1 | Complete |
| UI-08 | Phase 03.1 | Complete |
| UI-09 | Phase 03.1 | Complete |
| UI-10 | Phase 03.1 | Complete |
| UI-11 | Phase 03.1 | Complete |
| UI-12 | Phase 03.1 | Complete |
| UI-13 | Phase 03.1 | Complete |
| UI-14 | Phase 03.1 | Complete |
| UI-15 | Phase 03.1 | Complete |
| UI-16 | Phase 03.1 | Complete |
| UI-17 | Phase 03.1 | Complete |
| UI-18 | Phase 03.1 | Complete |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-03 after initial definition*
