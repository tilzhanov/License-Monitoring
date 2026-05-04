from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import SessionDep
from app.models import Asset, License, Vendor
from app.services.status import enrich_licenses, get_global_threshold
from app.templates import templates

router = APIRouter()


@router.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: SessionDep):
    global_threshold = get_global_threshold(db)
    assets = db.query(Asset).all()
    enriched = enrich_licenses(assets, global_threshold)

    total = len(enriched)
    expiring = sum(1 for e in enriched if e["status"] == "warning")
    expired_count = sum(1 for e in enriched if e["status"] == "expired")

    expiring_soon = sorted(
        [e for e in enriched if e["status"] == "warning"],
        key=lambda e: e["days_remaining"],
    )[:10]

    sorted_licenses = sorted(enriched, key=lambda e: e["license"].expiry_date)

    # Vendor aggregates — top-level summary cards on dashboard
    vendor_rows = []
    vendors = db.query(Vendor).order_by(Vendor.name).all()
    for v in vendors:
        product_ids = [p.id for p in v.products]
        if product_ids:
            v_assets = db.query(Asset).filter(Asset.product_id.in_(product_ids)).all()
        else:
            v_assets = []
        v_enriched = enrich_licenses(v_assets, global_threshold)
        vendor_rows.append({
            "vendor": v,
            "product_count": len(v.products),
            "stats": {
                "total": len(v_enriched),
                "warning": sum(1 for e in v_enriched if e["status"] == "warning"),
                "expired": sum(1 for e in v_enriched if e["status"] == "expired"),
            },
        })

    orphan_count = sum(1 for a in assets if a.product_id is None)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "total": total,
            "expiring": expiring,
            "expired": expired_count,
            "expiring_soon": expiring_soon,
            "licenses": sorted_licenses,
            "current_sort": "expiry_date",
            "current_order": "asc",
            "vendor_rows": vendor_rows,
            "orphan_count": orphan_count,
        },
    )


def _query_and_sort(
    db,
    product: Optional[str],
    status: Optional[str],
    sort: str,
    order: str,
) -> list:
    """Shared filter+sort pipeline for license table partials."""
    global_threshold = get_global_threshold(db)
    query = db.query(License)

    if product:
        query = query.filter(License.product_name.ilike(f"%{product}%"))

    licenses = query.all()
    enriched = enrich_licenses(licenses, global_threshold)

    if status:
        enriched = [e for e in enriched if e["status"] == status]

    sort_key_map = {
        "expiry_date": lambda e: e["license"].expiry_date,
        "product_name": lambda e: e["license"].product_name.lower(),
    }
    sort_fn = sort_key_map.get(sort, sort_key_map["expiry_date"])
    enriched.sort(key=sort_fn, reverse=(order == "desc"))
    return enriched


@router.get("/licenses/table", response_class=HTMLResponse)
def license_table(
    request: Request,
    db: SessionDep,
    product: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort: str = Query("expiry_date"),
    order: str = Query("asc"),
):
    """HTMX partial: filtered/sorted tbody rows. Used by filter inputs."""
    enriched = _query_and_sort(db, product, status, sort, order)
    return templates.TemplateResponse(
        request=request,
        name="partials/license_table.html",
        context={
            "licenses": enriched,
            "current_sort": sort,
            "current_order": order,
        },
    )


@router.get("/licenses/table/full", response_class=HTMLResponse)
def license_table_full(
    request: Request,
    db: SessionDep,
    product: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort: str = Query("expiry_date"),
    order: str = Query("asc"),
):
    """HTMX partial: full table (thead + tbody). Used by sort-header clicks
    so chevron indicators and toggle URLs re-render with new state."""
    enriched = _query_and_sort(db, product, status, sort, order)
    return templates.TemplateResponse(
        request=request,
        name="partials/license_table_full.html",
        context={
            "licenses": enriched,
            "current_sort": sort,
            "current_order": order,
        },
    )
