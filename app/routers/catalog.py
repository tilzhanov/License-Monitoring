"""Catalog routes — Vendor / Product CRUD and listing.

Asset CRUD lives in app/routers/licenses.py (legacy /licenses paths) and the
extended asset forms (SSL, support) attach to product detail pages here.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func

from app.database import SessionDep
from app.models import (
    ASSET_TYPE_LICENSE, ASSET_TYPE_SSL, ASSET_TYPE_SUPPORT, ASSET_TYPES,
    Asset, Product, Vendor,
)
from app.services.status import enrich_licenses, get_global_threshold
from app.templates import templates

router = APIRouter(prefix="/catalog", tags=["catalog"])


# ---------- helpers ----------

def _summarize_assets(enriched: list) -> dict:
    """Count totals/warning/expired for a flat list of enriched assets."""
    return {
        "total": len(enriched),
        "warning": sum(1 for e in enriched if e["status"] == "warning"),
        "expired": sum(1 for e in enriched if e["status"] == "expired"),
    }


# ---------- catalog index (list of vendors) ----------

@router.get("", response_class=HTMLResponse)
def catalog_index(request: Request, db: SessionDep):
    """Catalog landing — all vendors with aggregate counts across products."""
    threshold = get_global_threshold(db)
    vendors = db.query(Vendor).order_by(Vendor.name).all()

    rows = []
    for v in vendors:
        product_ids = [p.id for p in v.products]
        if product_ids:
            assets = db.query(Asset).filter(Asset.product_id.in_(product_ids)).all()
        else:
            assets = []
        enriched = enrich_licenses(assets, threshold)
        rows.append({
            "vendor": v,
            "product_count": len(v.products),
            "stats": _summarize_assets(enriched),
        })

    return templates.TemplateResponse(
        request=request,
        name="catalog/index.html",
        context={"rows": rows, "title": "Каталог"},
    )


# ---------- vendor CRUD ----------

@router.get("/vendors/new", response_class=HTMLResponse)
def vendor_new(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="catalog/vendor_form.html",
        context={
            "mode": "add", "title": "Новый вендор",
            "action_url": "/catalog/vendors",
            "submit_text": "Добавить вендора",
            "vendor": None, "errors": {}, "form_data": {},
        },
    )


@router.post("/vendors", response_class=HTMLResponse)
def vendor_create(
    request: Request, db: SessionDep,
    name: str = Form(""), description: str = Form(""),
):
    errors = _validate_vendor(db, name, exclude_id=None)
    if errors:
        return templates.TemplateResponse(
            request=request, name="catalog/vendor_form.html",
            context={
                "mode": "add", "title": "Новый вендор",
                "action_url": "/catalog/vendors",
                "submit_text": "Добавить вендора",
                "vendor": None, "errors": errors,
                "form_data": {"name": name, "description": description},
            },
        )
    v = Vendor(name=name.strip(), description=description.strip() or None)
    db.add(v); db.commit(); db.refresh(v)
    return RedirectResponse(url=f"/catalog/vendors/{v.id}", status_code=303)


@router.get("/vendors/{vendor_id}", response_class=HTMLResponse)
def vendor_detail(vendor_id: int, request: Request, db: SessionDep):
    v = db.get(Vendor, vendor_id)
    if not v:
        return templates.TemplateResponse(
            request=request, name="404.html",
            context={"title": "Вендор не найден"}, status_code=404,
        )
    threshold = get_global_threshold(db)
    rows = []
    for p in v.products:
        enriched = enrich_licenses(p.assets, threshold)
        rows.append({"product": p, "stats": _summarize_assets(enriched)})

    return templates.TemplateResponse(
        request=request, name="catalog/vendor_detail.html",
        context={"vendor": v, "rows": rows, "title": v.name},
    )


@router.get("/vendors/{vendor_id}/edit", response_class=HTMLResponse)
def vendor_edit(vendor_id: int, request: Request, db: SessionDep):
    v = db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    return templates.TemplateResponse(
        request=request, name="catalog/vendor_form.html",
        context={
            "mode": "edit", "title": f"Редактирование: {v.name}",
            "action_url": f"/catalog/vendors/{v.id}",
            "submit_text": "Сохранить",
            "vendor": v, "errors": {}, "form_data": {},
        },
    )


@router.post("/vendors/{vendor_id}", response_class=HTMLResponse)
def vendor_update(
    vendor_id: int, request: Request, db: SessionDep,
    name: str = Form(""), description: str = Form(""),
):
    v = db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    errors = _validate_vendor(db, name, exclude_id=vendor_id)
    if errors:
        return templates.TemplateResponse(
            request=request, name="catalog/vendor_form.html",
            context={
                "mode": "edit", "title": f"Редактирование: {v.name}",
                "action_url": f"/catalog/vendors/{v.id}",
                "submit_text": "Сохранить",
                "vendor": v, "errors": errors,
                "form_data": {"name": name, "description": description},
            },
        )
    v.name = name.strip()
    v.description = description.strip() or None
    db.commit()
    return RedirectResponse(url=f"/catalog/vendors/{v.id}", status_code=303)


@router.delete("/vendors/{vendor_id}")
def vendor_delete(vendor_id: int, db: SessionDep):
    v = db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    db.delete(v); db.commit()
    return Response(status_code=200, headers={"HX-Redirect": "/catalog"})


def _validate_vendor(db, name: str, exclude_id: Optional[int]) -> dict:
    errors = {}
    if not name.strip():
        errors["name"] = "Укажите название вендора"
        return errors
    q = db.query(Vendor).filter(func.lower(Vendor.name) == name.strip().lower())
    if exclude_id is not None:
        q = q.filter(Vendor.id != exclude_id)
    if q.first():
        errors["name"] = "Вендор с таким названием уже существует"
    return errors


# ---------- product CRUD ----------

@router.get("/vendors/{vendor_id}/products/new", response_class=HTMLResponse)
def product_new(vendor_id: int, request: Request, db: SessionDep):
    v = db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    return templates.TemplateResponse(
        request=request, name="catalog/product_form.html",
        context={
            "mode": "add", "title": f"Новый продукт — {v.name}",
            "action_url": f"/catalog/vendors/{v.id}/products",
            "submit_text": "Добавить продукт",
            "vendor": v, "product": None,
            "errors": {}, "form_data": {},
        },
    )


@router.post("/vendors/{vendor_id}/products", response_class=HTMLResponse)
def product_create(
    vendor_id: int, request: Request, db: SessionDep,
    name: str = Form(""), description: str = Form(""),
):
    v = db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    errors = _validate_product(db, vendor_id, name, exclude_id=None)
    if errors:
        return templates.TemplateResponse(
            request=request, name="catalog/product_form.html",
            context={
                "mode": "add", "title": f"Новый продукт — {v.name}",
                "action_url": f"/catalog/vendors/{v.id}/products",
                "submit_text": "Добавить продукт",
                "vendor": v, "product": None, "errors": errors,
                "form_data": {"name": name, "description": description},
            },
        )
    p = Product(vendor_id=vendor_id, name=name.strip(), description=description.strip() or None)
    db.add(p); db.commit(); db.refresh(p)
    return RedirectResponse(url=f"/catalog/products/{p.id}", status_code=303)


@router.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail(product_id: int, request: Request, db: SessionDep):
    p = db.get(Product, product_id)
    if not p:
        return templates.TemplateResponse(
            request=request, name="404.html",
            context={"title": "Продукт не найден"}, status_code=404,
        )
    threshold = get_global_threshold(db)
    enriched = enrich_licenses(p.assets, threshold)
    by_type = {t: [] for t in ASSET_TYPES}
    for e in enriched:
        by_type[e["license"].asset_type].append(e)
    return templates.TemplateResponse(
        request=request, name="catalog/product_detail.html",
        context={
            "product": p, "vendor": p.vendor,
            "assets_by_type": by_type,
            "stats": _summarize_assets(enriched),
            "title": p.name,
        },
    )


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
def product_edit(product_id: int, request: Request, db: SessionDep):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    return templates.TemplateResponse(
        request=request, name="catalog/product_form.html",
        context={
            "mode": "edit", "title": f"Редактирование: {p.name}",
            "action_url": f"/catalog/products/{p.id}",
            "submit_text": "Сохранить",
            "vendor": p.vendor, "product": p,
            "errors": {}, "form_data": {},
        },
    )


@router.post("/products/{product_id}", response_class=HTMLResponse)
def product_update(
    product_id: int, request: Request, db: SessionDep,
    name: str = Form(""), description: str = Form(""),
):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    errors = _validate_product(db, p.vendor_id, name, exclude_id=product_id)
    if errors:
        return templates.TemplateResponse(
            request=request, name="catalog/product_form.html",
            context={
                "mode": "edit", "title": f"Редактирование: {p.name}",
                "action_url": f"/catalog/products/{p.id}",
                "submit_text": "Сохранить",
                "vendor": p.vendor, "product": p, "errors": errors,
                "form_data": {"name": name, "description": description},
            },
        )
    p.name = name.strip()
    p.description = description.strip() or None
    db.commit()
    return RedirectResponse(url=f"/catalog/products/{p.id}", status_code=303)


@router.delete("/products/{product_id}")
def product_delete(product_id: int, db: SessionDep):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    vendor_id = p.vendor_id
    db.delete(p); db.commit()
    return Response(status_code=200, headers={"HX-Redirect": f"/catalog/vendors/{vendor_id}"})


def _validate_product(db, vendor_id: int, name: str, exclude_id: Optional[int]) -> dict:
    errors = {}
    if not name.strip():
        errors["name"] = "Укажите название продукта"
        return errors
    q = db.query(Product).filter(
        Product.vendor_id == vendor_id,
        func.lower(Product.name) == name.strip().lower(),
    )
    if exclude_id is not None:
        q = q.filter(Product.id != exclude_id)
    if q.first():
        errors["name"] = "Продукт с таким названием уже есть у этого вендора"
    return errors


# ---------- asset CRUD (any type, scoped to product) ----------

@router.get("/products/{product_id}/assets/new", response_class=HTMLResponse)
def asset_new(
    product_id: int, request: Request, db: SessionDep,
    type: str = "license",
):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    if type not in ASSET_TYPES:
        type = ASSET_TYPE_LICENSE
    return templates.TemplateResponse(
        request=request, name="catalog/asset_form.html",
        context={
            "mode": "add",
            "title": f"Новый актив — {p.name}",
            "action_url": f"/catalog/products/{p.id}/assets",
            "submit_text": "Добавить актив",
            "product": p, "vendor": p.vendor, "asset": None,
            "asset_type": type, "errors": {}, "form_data": {},
        },
    )


@router.post("/products/{product_id}/assets", response_class=HTMLResponse)
def asset_create(
    product_id: int, request: Request, db: SessionDep,
    asset_type: str = Form(ASSET_TYPE_LICENSE),
    product_name: str = Form(""),
    purchase_date: str = Form(""),
    expiry_date: str = Form(""),
    responsible: str = Form(""),
    cost: str = Form(""),
    comment: str = Form(""),
    notify_days_before: str = Form(""),
    ssl_domain: str = Form(""),
    ssl_issuer: str = Form(""),
    support_contract_no: str = Form(""),
    support_sla: str = Form(""),
):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    if asset_type not in ASSET_TYPES:
        asset_type = ASSET_TYPE_LICENSE

    fields = dict(
        product_name=product_name, purchase_date=purchase_date, expiry_date=expiry_date,
        responsible=responsible, cost=cost, comment=comment,
        notify_days_before=notify_days_before,
        ssl_domain=ssl_domain, ssl_issuer=ssl_issuer,
        support_contract_no=support_contract_no, support_sla=support_sla,
    )
    errors, parsed = _validate_asset_form(asset_type, fields)
    if errors:
        return templates.TemplateResponse(
            request=request, name="catalog/asset_form.html",
            context={
                "mode": "add",
                "title": f"Новый актив — {p.name}",
                "action_url": f"/catalog/products/{p.id}/assets",
                "submit_text": "Добавить актив",
                "product": p, "vendor": p.vendor, "asset": None,
                "asset_type": asset_type, "errors": errors,
                "form_data": fields,
            },
        )

    a = Asset(product_id=p.id, asset_type=asset_type, **parsed)
    db.add(a); db.commit()
    return RedirectResponse(url=f"/catalog/products/{p.id}", status_code=303)


@router.get("/assets/{asset_id}/edit", response_class=HTMLResponse)
def asset_edit(asset_id: int, request: Request, db: SessionDep):
    a = db.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    p = a.product
    return templates.TemplateResponse(
        request=request, name="catalog/asset_form.html",
        context={
            "mode": "edit",
            "title": f"Редактирование актива",
            "action_url": f"/catalog/assets/{a.id}",
            "submit_text": "Сохранить",
            "product": p, "vendor": p.vendor if p else None, "asset": a,
            "asset_type": a.asset_type, "errors": {}, "form_data": {},
        },
    )


@router.post("/assets/{asset_id}", response_class=HTMLResponse)
def asset_update(
    asset_id: int, request: Request, db: SessionDep,
    asset_type: str = Form(ASSET_TYPE_LICENSE),
    product_name: str = Form(""),
    purchase_date: str = Form(""),
    expiry_date: str = Form(""),
    responsible: str = Form(""),
    cost: str = Form(""),
    comment: str = Form(""),
    notify_days_before: str = Form(""),
    ssl_domain: str = Form(""),
    ssl_issuer: str = Form(""),
    support_contract_no: str = Form(""),
    support_sla: str = Form(""),
):
    a = db.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    if asset_type not in ASSET_TYPES:
        asset_type = ASSET_TYPE_LICENSE

    fields = dict(
        product_name=product_name, purchase_date=purchase_date, expiry_date=expiry_date,
        responsible=responsible, cost=cost, comment=comment,
        notify_days_before=notify_days_before,
        ssl_domain=ssl_domain, ssl_issuer=ssl_issuer,
        support_contract_no=support_contract_no, support_sla=support_sla,
    )
    errors, parsed = _validate_asset_form(asset_type, fields)
    if errors:
        return templates.TemplateResponse(
            request=request, name="catalog/asset_form.html",
            context={
                "mode": "edit",
                "title": f"Редактирование актива",
                "action_url": f"/catalog/assets/{a.id}",
                "submit_text": "Сохранить",
                "product": a.product, "vendor": a.product.vendor if a.product else None,
                "asset": a, "asset_type": asset_type, "errors": errors,
                "form_data": fields,
            },
        )

    a.asset_type = asset_type
    for k, v in parsed.items():
        setattr(a, k, v)
    db.commit()
    redirect_url = f"/catalog/products/{a.product_id}" if a.product_id else "/catalog"
    return RedirectResponse(url=redirect_url, status_code=303)


@router.delete("/assets/{asset_id}")
def asset_delete(asset_id: int, db: SessionDep):
    a = db.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    product_id = a.product_id
    db.delete(a); db.commit()
    redirect_url = f"/catalog/products/{product_id}" if product_id else "/catalog"
    return Response(status_code=200, headers={"HX-Redirect": redirect_url})


def _validate_asset_form(asset_type: str, fields: dict) -> tuple[dict, dict]:
    """Validate asset form. Returns (errors, parsed) where parsed maps to Asset columns."""
    errors: dict[str, str] = {}
    parsed: dict = {}

    name = fields.get("product_name", "").strip()
    if not name:
        errors["product_name"] = "Укажите название"
    parsed["product_name"] = name

    expiry_str = fields.get("expiry_date", "").strip()
    parsed_expiry: Optional[date] = None
    if not expiry_str:
        errors["expiry_date"] = "Укажите дату истечения"
    else:
        try:
            parsed_expiry = date.fromisoformat(expiry_str)
        except ValueError:
            errors["expiry_date"] = "Неверный формат даты"
    parsed["expiry_date"] = parsed_expiry

    purchase_str = fields.get("purchase_date", "").strip()
    parsed_purchase: Optional[date] = None
    if purchase_str:
        try:
            parsed_purchase = date.fromisoformat(purchase_str)
        except ValueError:
            errors["purchase_date"] = "Неверный формат даты"
    parsed["purchase_date"] = parsed_purchase

    if parsed_purchase and parsed_expiry and parsed_expiry < parsed_purchase:
        errors["expiry_date"] = "Дата истечения не может быть раньше даты покупки"

    notify_str = fields.get("notify_days_before", "").strip()
    parsed["notify_days_before"] = None
    if notify_str:
        try:
            n = int(notify_str)
            if n <= 0:
                errors["notify_days_before"] = "Укажите положительное целое число"
            else:
                parsed["notify_days_before"] = n
        except ValueError:
            errors["notify_days_before"] = "Укажите положительное целое число"

    parsed["responsible"] = fields.get("responsible", "").strip() or None
    parsed["cost"] = fields.get("cost", "").strip() or None
    parsed["comment"] = fields.get("comment", "").strip() or None

    if asset_type == ASSET_TYPE_SSL:
        parsed["ssl_domain"] = fields.get("ssl_domain", "").strip() or None
        parsed["ssl_issuer"] = fields.get("ssl_issuer", "").strip() or None
        parsed["support_contract_no"] = None
        parsed["support_sla"] = None
        if not parsed["ssl_domain"]:
            errors["ssl_domain"] = "Укажите домен"
    elif asset_type == ASSET_TYPE_SUPPORT:
        parsed["support_contract_no"] = fields.get("support_contract_no", "").strip() or None
        parsed["support_sla"] = fields.get("support_sla", "").strip() or None
        parsed["ssl_domain"] = None
        parsed["ssl_issuer"] = None
    else:
        parsed["ssl_domain"] = None
        parsed["ssl_issuer"] = None
        parsed["support_contract_no"] = None
        parsed["support_sla"] = None

    return errors, parsed
