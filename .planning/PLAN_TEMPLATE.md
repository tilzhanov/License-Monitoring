# PLAN TEMPLATE — компактный формат для экономии токенов
# Используй этот шаблон вместо текущего 300-строчного формата

---
phase: XX-name
plan: NN
requirements: [REQ-01, REQ-02]
files_modified:
  - app/routers/example.py
  - templates/example.html
---

## Objective
Одно предложение: что строим и зачем.

## Tasks

### Task 1: Название
**Files:** `app/routers/x.py`, `templates/x.html`  
**Read first:** `app/models.py`, `app/database.py`

Что делать (кратко, без примеров кода — Claude знает синтаксис):
- Создать endpoint `GET /x` возвращающий TemplateResponse
- Валидация: поле Y обязательно
- При ошибке: re-render формы с `errors` dict

**Verify:** `pytest tests/test_x.py -v`

**Done when:**
- [ ] endpoint возвращает 200
- [ ] тест проходит

### Task 2: Название
...

## Success Criteria
1. Все тесты зелёные
2. [конкретный observable behavior]
