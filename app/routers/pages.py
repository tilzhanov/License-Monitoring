from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.templates import templates
from app.database import SessionDep
from app.models import License
from app.services.status import get_global_threshold, enrich_licenses

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
