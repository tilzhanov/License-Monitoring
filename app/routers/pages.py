from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import SessionDep
from app.models import License
from app.services.status import enrich_licenses, get_global_threshold
from app.templates import templates

router = APIRouter()


@router.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: SessionDep):
    global_threshold = get_global_threshold(db)
    licenses = db.query(License).all()
    enriched = enrich_licenses(licenses, global_threshold)

    total = len(enriched)
    expiring = sum(1 for e in enriched if e["status"] == "warning")
    expired_count = sum(1 for e in enriched if e["status"] == "expired")

    # Expiring soon widget: warning licenses sorted by days_remaining asc, top 10
    expiring_soon = sorted(
        [e for e in enriched if e["status"] == "warning"],
        key=lambda e: e["days_remaining"],
    )[:10]

    # Default sort: expiry_date ascending
    sorted_licenses = sorted(enriched, key=lambda e: e["license"].expiry_date)

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
        },
    )


@router.get("/licenses/table", response_class=HTMLResponse)
def license_table(
    request: Request,
    db: SessionDep,
    product: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort: str = Query("expiry_date"),
    order: str = Query("asc"),
):
    """HTMX partial: returns filtered/sorted tbody rows for the license table."""
    global_threshold = get_global_threshold(db)
    query = db.query(License)

    # Filter by product name -- case-insensitive LIKE
    if product:
        query = query.filter(License.product_name.ilike(f"%{product}%"))

    licenses = query.all()
    enriched = enrich_licenses(licenses, global_threshold)

    # Filter by computed status
    if status:
        enriched = [e for e in enriched if e["status"] == status]

    # Sort
    sort_key_map = {
        "expiry_date": lambda e: e["license"].expiry_date,
        "product_name": lambda e: e["license"].product_name.lower(),
    }
    sort_fn = sort_key_map.get(sort, sort_key_map["expiry_date"])
    enriched.sort(key=sort_fn, reverse=(order == "desc"))

    return templates.TemplateResponse(
        request=request,
        name="partials/license_table.html",
        context={
            "licenses": enriched,
            "current_sort": sort,
            "current_order": order,
        },
    )
