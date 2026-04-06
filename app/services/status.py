"""Status computation service — single source of truth for license status logic."""

from datetime import date

from sqlalchemy.orm import Session

from app.config import NOTIFY_DAYS_BEFORE
from app.models import AppSettings, License


def days_until_expiry(expiry_date: date) -> int:
    """Return number of days from today until *expiry_date*.

    Positive = future, 0 = today, negative = past.
    """
    return (expiry_date - date.today()).days


def get_license_status(expiry_date: date, threshold: int) -> str:
    """Classify licence status based on days remaining and threshold.

    Returns:
        "expired"  — days <= 0
        "warning"  — 0 < days <= threshold
        "active"   — days > threshold
    """
    days = days_until_expiry(expiry_date)
    if days <= 0:
        return "expired"
    elif days <= threshold:
        return "warning"
    return "active"


def get_global_threshold(db: Session) -> int:
    """Resolve notification threshold via fallback chain.

    Priority: DB setting -> NOTIFY_DAYS_BEFORE env -> hardcoded 60.
    """
    setting = db.query(AppSettings).filter_by(key="notify_days_before").first()
    if setting and setting.value:
        return int(setting.value)
    return NOTIFY_DAYS_BEFORE


def enrich_licenses(licenses: list, global_threshold: int) -> list:
    """Add computed status fields to a list of License objects.

    Each item in the returned list is a dict with:
        license, days_remaining, status, status_class
    """
    result = []
    for lic in licenses:
        threshold = lic.notify_days_before or global_threshold
        days = days_until_expiry(lic.expiry_date)
        status = get_license_status(lic.expiry_date, threshold)
        result.append({
            "license": lic,
            "days_remaining": days,
            "status": status,
            "status_class": f"status-{status}",
        })
    return result
