"""Unit tests for status computation service (app/services/status.py)."""

from datetime import date, timedelta

import pytest

from app.models import AppSettings
from app.services.status import (
    days_until_expiry,
    enrich_licenses,
    get_global_threshold,
    get_license_status,
)


# --- days_until_expiry ---


def test_days_until_expiry_future_date():
    future = date(2099, 1, 1)
    result = days_until_expiry(future)
    assert result > 0


def test_days_until_expiry_today_returns_zero():
    result = days_until_expiry(date.today())
    assert result == 0


def test_days_until_expiry_past_date():
    past = date(2020, 1, 1)
    result = days_until_expiry(past)
    assert result < 0


# --- get_license_status ---


def test_status_expired_past_date():
    yesterday = date.today() - timedelta(days=1)
    assert get_license_status(yesterday, threshold=30) == "expired"


def test_status_expired_today():
    """days=0 is expired per D-01."""
    assert get_license_status(date.today(), threshold=30) == "expired"


def test_status_warning_within_threshold():
    future_15 = date.today() + timedelta(days=15)
    assert get_license_status(future_15, threshold=30) == "warning"


def test_status_warning_at_threshold_boundary():
    """days == threshold should be 'warning'."""
    at_boundary = date.today() + timedelta(days=30)
    assert get_license_status(at_boundary, threshold=30) == "warning"


def test_status_active_beyond_threshold():
    future_31 = date.today() + timedelta(days=31)
    assert get_license_status(future_31, threshold=30) == "active"


# --- get_global_threshold ---


def test_global_threshold_from_db(test_session, seed_default_settings):
    result = get_global_threshold(test_session)
    assert result == 60


def test_global_threshold_fallback_to_env(test_session):
    """No DB setting => falls back to NOTIFY_DAYS_BEFORE env value."""
    from app.config import NOTIFY_DAYS_BEFORE

    result = get_global_threshold(test_session)
    assert result == NOTIFY_DAYS_BEFORE


# --- enrich_licenses ---


def test_enrich_licenses_with_warning_license(make_license):
    lic = make_license(days_until=1)
    enriched = enrich_licenses([lic], global_threshold=30)
    assert len(enriched) == 1
    assert enriched[0]["status"] == "warning"
    assert enriched[0]["days_remaining"] == 1
    assert enriched[0]["status_class"] == "status-warning"
    assert enriched[0]["license"] is lic


def test_enrich_licenses_empty_list():
    result = enrich_licenses([], global_threshold=30)
    assert result == []


def test_enrich_licenses_per_license_threshold(make_license):
    """Per-license threshold override takes precedence over global."""
    lic = make_license(days_until=10, notify_days_before=5)
    enriched = enrich_licenses([lic], global_threshold=30)
    # 10 days remaining with threshold=5 => active
    assert enriched[0]["status"] == "active"


def test_enrich_licenses_expired(make_license):
    lic = make_license(days_until=-5)
    enriched = enrich_licenses([lic], global_threshold=30)
    assert enriched[0]["status"] == "expired"
    assert enriched[0]["days_remaining"] == -5
    assert enriched[0]["status_class"] == "status-expired"
