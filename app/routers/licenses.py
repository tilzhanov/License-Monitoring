from datetime import date

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.database import SessionDep
from app.models import License
from app.templates import templates

router = APIRouter(tags=["licenses"])


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
):
    errors = {}
    if not product_name.strip():
        errors["product_name"] = "Укажите название продукта"
    if not purchase_date.strip():
        errors["purchase_date"] = "Укажите дату покупки"
    if not expiry_date.strip():
        errors["expiry_date"] = "Укажите дату истечения"

    if errors:
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
                "form_data": {
                    "product_name": product_name,
                    "purchase_date": purchase_date,
                    "expiry_date": expiry_date,
                    "responsible": responsible,
                    "cost": cost,
                    "comment": comment,
                },
            },
        )

    license_obj = License(
        product_name=product_name.strip(),
        purchase_date=date.fromisoformat(purchase_date),
        expiry_date=date.fromisoformat(expiry_date),
        responsible=responsible.strip() or None,
        cost=cost.strip() or None,
        comment=comment.strip() or None,
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
):
    license_obj = db.get(License, license_id)
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")

    errors = {}
    if not product_name.strip():
        errors["product_name"] = "Укажите название продукта"
    if not purchase_date.strip():
        errors["purchase_date"] = "Укажите дату покупки"
    if not expiry_date.strip():
        errors["expiry_date"] = "Укажите дату истечения"

    if errors:
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
                "form_data": {
                    "product_name": product_name,
                    "purchase_date": purchase_date,
                    "expiry_date": expiry_date,
                    "responsible": responsible,
                    "cost": cost,
                    "comment": comment,
                },
            },
        )

    license_obj.product_name = product_name.strip()
    license_obj.purchase_date = date.fromisoformat(purchase_date)
    license_obj.expiry_date = date.fromisoformat(expiry_date)
    license_obj.responsible = responsible.strip() or None
    license_obj.cost = cost.strip() or None
    license_obj.comment = comment.strip() or None
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
