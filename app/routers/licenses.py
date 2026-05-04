from datetime import date
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.database import SessionDep
from app.models import License
from app.services.status import days_until_expiry, get_license_status, get_global_threshold
from app.templates import templates

router = APIRouter(tags=["licenses"])


def _validate_license_form(
    product_name: str,
    purchase_date_str: str,
    expiry_date_str: str,
    notify_days_before_str: str = "",
) -> tuple[dict[str, str], Optional[date], Optional[date], Optional[int]]:
    """Validate license form fields. Returns (errors, purchase_date, expiry_date, notify_days)."""
    errors: dict[str, str] = {}
    parsed_purchase: Optional[date] = None
    parsed_expiry: Optional[date] = None
    parsed_notify: Optional[int] = None

    if not product_name.strip():
        errors["product_name"] = "Укажите название продукта"

    if not purchase_date_str.strip():
        errors["purchase_date"] = "Укажите дату покупки"
    else:
        try:
            parsed_purchase = date.fromisoformat(purchase_date_str)
        except ValueError:
            errors["purchase_date"] = "Укажите дату покупки"

    if not expiry_date_str.strip():
        errors["expiry_date"] = "Укажите дату истечения"
    else:
        try:
            parsed_expiry = date.fromisoformat(expiry_date_str)
        except ValueError:
            errors["expiry_date"] = "Укажите дату истечения"

    if parsed_purchase and parsed_expiry and parsed_expiry < parsed_purchase:
        errors["expiry_date"] = "Дата истечения не может быть раньше даты покупки"

    if notify_days_before_str.strip():
        try:
            n = int(notify_days_before_str)
            if n <= 0:
                errors["notify_days_before"] = "Укажите положительное целое число"
            else:
                parsed_notify = n
        except ValueError:
            errors["notify_days_before"] = "Укажите положительное целое число"

    return errors, parsed_purchase, parsed_expiry, parsed_notify


@router.get("/licenses/new", response_class=HTMLResponse)
def new_license(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="license_form.html",
        context={
            "mode": "add",
            "title": "Новая лицензия",
            "action_url": "/licenses",
            "submit_text": "Добавить лицензию",
            "license": None,
            "errors": {},
            "form_data": {},
        },
    )


@router.get("/licenses/{license_id}", response_class=HTMLResponse)
def license_detail(license_id: int, request: Request, db: SessionDep):
    license_obj = db.get(License, license_id)
    if not license_obj:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"title": "Лицензия не найдена"},
            status_code=404,
        )
    threshold = get_global_threshold(db)
    effective_threshold = license_obj.notify_days_before if license_obj.notify_days_before is not None else threshold
    days_left = days_until_expiry(license_obj.expiry_date)
    status = get_license_status(license_obj.expiry_date, effective_threshold)
    return templates.TemplateResponse(
        request=request,
        name="license_detail.html",
        context={
            "license": license_obj,
            "status": status,
            "days_left": days_left,
            "title": license_obj.product_name,
        },
    )


@router.post("/licenses", response_class=HTMLResponse)
def create_license(
    request: Request,
    db: SessionDep,
    product_name: str = Form(""),
    purchase_date: str = Form(""),
    expiry_date: str = Form(""),
    responsible: str = Form(""),
    cost: str = Form(""),
    comment: str = Form(""),
    notify_days_before: str = Form(""),
):
    errors, parsed_purchase, parsed_expiry, parsed_notify = _validate_license_form(
        product_name, purchase_date, expiry_date, notify_days_before,
    )

    if errors:
        form_data = {
            "product_name": product_name,
            "purchase_date": purchase_date,
            "expiry_date": expiry_date,
            "responsible": responsible,
            "cost": cost,
            "comment": comment,
            "notify_days_before": notify_days_before,
        }
        return templates.TemplateResponse(
            request=request,
            name="license_form.html",
            context={
                "mode": "add",
                "title": "Новая лицензия",
                "action_url": "/licenses",
                "submit_text": "Добавить лицензию",
                "license": None,
                "errors": errors,
                "form_data": form_data,
            },
        )

    license_obj = License(
        product_name=product_name.strip(),
        purchase_date=parsed_purchase,
        expiry_date=parsed_expiry,
        responsible=responsible.strip() or None,
        cost=cost.strip() or None,
        comment=comment.strip() or None,
        notify_days_before=parsed_notify,
    )
    db.add(license_obj)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.get("/licenses/{license_id}/edit", response_class=HTMLResponse)
def edit_license(license_id: int, request: Request, db: SessionDep):
    license_obj = db.get(License, license_id)
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    return templates.TemplateResponse(
        request=request,
        name="license_form.html",
        context={
            "mode": "edit",
            "title": "Редактирование лицензии",
            "action_url": f"/licenses/{license_id}",
            "submit_text": "Сохранить лицензию",
            "license": license_obj,
            "errors": {},
            "form_data": {},
        },
    )


@router.post("/licenses/{license_id}", response_class=HTMLResponse)
def update_license(
    license_id: int,
    request: Request,
    db: SessionDep,
    product_name: str = Form(""),
    purchase_date: str = Form(""),
    expiry_date: str = Form(""),
    responsible: str = Form(""),
    cost: str = Form(""),
    comment: str = Form(""),
    notify_days_before: str = Form(""),
):
    license_obj = db.get(License, license_id)
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    errors, parsed_purchase, parsed_expiry, parsed_notify = _validate_license_form(
        product_name, purchase_date, expiry_date, notify_days_before,
    )

    if errors:
        form_data = {
            "product_name": product_name,
            "purchase_date": purchase_date,
            "expiry_date": expiry_date,
            "responsible": responsible,
            "cost": cost,
            "comment": comment,
            "notify_days_before": notify_days_before,
        }
        return templates.TemplateResponse(
            request=request,
            name="license_form.html",
            context={
                "mode": "edit",
                "title": "Редактирование лицензии",
                "action_url": f"/licenses/{license_id}",
                "submit_text": "Сохранить лицензию",
                "license": license_obj,
                "errors": errors,
                "form_data": form_data,
            },
        )

    license_obj.product_name = product_name.strip()
    license_obj.purchase_date = parsed_purchase
    license_obj.expiry_date = parsed_expiry
    license_obj.responsible = responsible.strip() or None
    license_obj.cost = cost.strip() or None
    license_obj.comment = comment.strip() or None
    license_obj.notify_days_before = parsed_notify
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.delete("/licenses/{license_id}")
def delete_license(license_id: int, db: SessionDep):
    license_obj = db.get(License, license_id)
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    db.delete(license_obj)
    db.commit()
    return Response(
        status_code=200,
        content="",
        headers={"HX-Trigger": "license-changed"},
    )
