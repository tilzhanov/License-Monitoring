"""Unit tests for the Telegram notification service.

All HTTP calls are mocked via unittest.mock — no real network calls.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.telegram import (
    format_digest,
    format_license_line,
    send_telegram_message,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_enriched(
    product_name="vCenter 7.0",
    days=5,
    status="warning",
    responsible="Иванов",
    expiry_offset=None,
    asset_type="license",
    product=None,
    ssl_domain=None,
    ssl_issuer=None,
    support_contract_no=None,
    support_sla=None,
):
    """Build a minimal enriched-asset dict for testing."""
    lic = MagicMock()
    lic.product_name = product_name
    lic.expiry_date = date.today() + timedelta(days=expiry_offset if expiry_offset is not None else days)
    lic.responsible = responsible
    lic.asset_type = asset_type
    lic.product = product
    lic.ssl_domain = ssl_domain
    lic.ssl_issuer = ssl_issuer
    lic.support_contract_no = support_contract_no
    lic.support_sla = support_sla
    return {
        "license": lic,
        "days_remaining": days,
        "status": status,
        "status_class": f"status-{status}",
    }


def _mock_client_post(status_code: int, json_body: dict):
    """Return a configured mock for httpx.Client context manager."""
    mock_response = MagicMock()
    mock_response.json.return_value = json_body

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response

    return mock_client


# ---------------------------------------------------------------------------
# send_telegram_message tests
# ---------------------------------------------------------------------------

def test_send_telegram_success():
    """send_telegram_message returns {"ok": True} on successful API response."""
    mock_client = _mock_client_post(200, {"ok": True, "result": {}})

    with patch("app.services.telegram.httpx.Client", return_value=mock_client):
        result = send_telegram_message("TOKEN", "12345", "Hello")

    assert result == {"ok": True}


def test_send_telegram_invalid_token():
    """send_telegram_message returns 401 error with Russian message for invalid token."""
    mock_client = _mock_client_post(
        401, {"ok": False, "error_code": 401, "description": "Unauthorized"}
    )

    with patch("app.services.telegram.httpx.Client", return_value=mock_client):
        result = send_telegram_message("BAD_TOKEN", "12345", "Hello")

    assert result["ok"] is False
    assert result["error_code"] == 401
    assert "Неверный токен бота" in result["error"]


def test_send_telegram_bad_request():
    """send_telegram_message returns 400 error for bad chat_id."""
    mock_client = _mock_client_post(
        400, {"ok": False, "error_code": 400, "description": "Bad Request"}
    )

    with patch("app.services.telegram.httpx.Client", return_value=mock_client):
        result = send_telegram_message("TOKEN", "BADCHAT", "Hello")

    assert result["ok"] is False
    assert result["error_code"] == 400
    assert "Некорректный запрос" in result["error"]


def test_send_telegram_bot_blocked():
    """send_telegram_message returns 403 error when bot is blocked."""
    mock_client = _mock_client_post(
        403, {"ok": False, "error_code": 403, "description": "Forbidden: bot was blocked by the user"}
    )

    with patch("app.services.telegram.httpx.Client", return_value=mock_client):
        result = send_telegram_message("TOKEN", "12345", "Hello")

    assert result["ok"] is False
    assert result["error_code"] == 403
    assert "заблокирован" in result["error"]


def test_send_telegram_timeout():
    """send_telegram_message returns timeout error on httpx.TimeoutException."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.side_effect = httpx.TimeoutException("timeout")

    with patch("app.services.telegram.httpx.Client", return_value=mock_client):
        result = send_telegram_message("TOKEN", "12345", "Hello")

    assert result["ok"] is False
    assert "Тайм-аут" in result["error"]
    assert result["error_code"] == 0


def test_send_telegram_http_error():
    """send_telegram_message returns generic HTTP error on httpx.HTTPError."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.side_effect = httpx.HTTPError("connection failed")

    with patch("app.services.telegram.httpx.Client", return_value=mock_client):
        result = send_telegram_message("TOKEN", "12345", "Hello")

    assert result["ok"] is False
    assert "Ошибка HTTP" in result["error"]
    assert result["error_code"] == 0


# ---------------------------------------------------------------------------
# format_digest tests
# ---------------------------------------------------------------------------

def test_format_digest_empty_returns_none():
    """format_digest returns None when given an empty list (D-04)."""
    assert format_digest([]) is None


def test_format_digest_all_active_returns_none():
    """format_digest returns None when all licenses are active (D-04)."""
    items = [make_enriched(status="active") for _ in range(3)]
    assert format_digest(items) is None


def test_format_digest_groups_by_urgency():
    """format_digest groups expired under red-circle and warning under yellow-circle headers (D-01)."""
    expired_item = make_enriched(product_name="Expired Product", days=-5, status="expired")
    warning_item = make_enriched(product_name="Warning Product", days=10, status="warning")

    result = format_digest([expired_item, warning_item])

    assert result is not None
    # Red circle header for expired
    assert "\U0001f534" in result
    assert "Истекло" in result
    # Yellow circle header for warning
    assert "\U0001f7e1" in result
    assert "Истекает скоро" in result
    # Expired section comes before warning section
    red_pos = result.index("\U0001f534")
    yellow_pos = result.index("\U0001f7e1")
    assert red_pos < yellow_pos


def test_format_digest_only_expired():
    """format_digest works with only expired items — no yellow-circle header."""
    expired_item = make_enriched(product_name="Expired Prod", days=-10, status="expired")
    result = format_digest([expired_item])

    assert result is not None
    assert "\U0001f534" in result
    assert "\U0001f7e1" not in result


def test_format_digest_only_warning():
    """format_digest works with only warning items — no red-circle header."""
    warning_item = make_enriched(product_name="Warning Prod", days=15, status="warning")
    result = format_digest([warning_item])

    assert result is not None
    assert "\U0001f7e1" in result
    assert "\U0001f534" not in result


# ---------------------------------------------------------------------------
# format_license_line tests
# ---------------------------------------------------------------------------

def test_format_license_line_with_responsible():
    """format_license_line starts with bullet, includes product, date, days, responsible (D-03)."""
    item = make_enriched(
        product_name="vCenter 7.0",
        days=5,
        responsible="Иванов",
        expiry_offset=5,
    )
    line = format_license_line(item)

    # Must start with bullet character (•), NOT asterisk
    assert line.startswith("\U0001f4dc"), f"Expected line to start with 📜, got: {line[:4]!r}"
    # Bold-wrapped product name
    assert "<b>vCenter 7.0</b>" in line
    # 2-line block — context line indented after the title line
    assert "\n   " in line
    # Date in DD.MM.YYYY format
    expected_date = (date.today() + timedelta(days=5)).strftime("%d.%m.%Y")
    assert expected_date in line
    # Days remaining label
    assert "5 дн." in line
    # Responsible
    assert "Иванов" in line


def test_format_license_line_without_responsible():
    """format_license_line omits responsible when None (D-03)."""
    item = make_enriched(
        product_name="Veeam Backup",
        days=3,
        responsible=None,
        expiry_offset=3,
    )
    line = format_license_line(item)

    assert line.startswith("\U0001f4dc"), f"Expected 📜, got: {line[:4]!r}"
    assert "Veeam Backup" in line
    # Line must not end with a separator " — " (trailing separator omitted)
    assert not line.endswith(" \u2014 ")
    assert not line.endswith(" — ")
    assert not line.endswith(" · ")


def test_format_license_line_overdue_label():
    """Negative days_remaining shows просрочено label."""
    item = make_enriched(product_name="X", days=-7, status="expired", expiry_offset=-7)
    line = format_license_line(item)
    assert "просрочено 7 дн." in line


def test_format_license_line_today_label():
    """Zero days_remaining shows истекает сегодня."""
    item = make_enriched(product_name="X", days=0, status="warning", expiry_offset=0)
    line = format_license_line(item)
    assert "истекает сегодня" in line


def test_format_license_line_ssl_includes_domain_and_issuer():
    item = make_enriched(
        product_name="Wildcard cert",
        days=20,
        asset_type="ssl",
        ssl_domain="*.example.com",
        ssl_issuer="DigiCert",
    )
    line = format_license_line(item)
    assert line.startswith("\U0001f512")
    assert "*.example.com" in line
    assert "DigiCert" in line


def test_format_license_line_support_includes_contract_and_sla():
    item = make_enriched(
        product_name="Premier Support",
        days=30,
        asset_type="support",
        support_contract_no="TT-2026-0042",
        support_sla="24x7",
    )
    line = format_license_line(item)
    assert line.startswith("\U0001f6e0")
    assert "TT-2026-0042" in line
    assert "SLA: 24x7" in line


def test_format_license_line_includes_vendor_product_breadcrumb():
    vendor = MagicMock()
    vendor.name = "vmware"
    product = MagicMock()
    product.name = "vCloud Director"
    product.vendor = vendor
    item = make_enriched(product_name="License A", days=10, product=product)
    line = format_license_line(item)
    assert "vmware / vCloud Director" in line


def test_format_digest_html_escapes_user_strings():
    """format_digest escapes HTML in product_name (security / D-03)."""
    item = make_enriched(
        product_name="<script>alert(1)</script>",
        days=5,
        status="warning",
        responsible="<b>Admin</b>",
        expiry_offset=5,
    )
    result = format_digest([item])

    assert result is not None
    # User-supplied script tag is escaped
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in result
    assert "<script>" not in result
    # User-supplied <b> in responsible is escaped (not interpreted as bold)
    assert "&lt;b&gt;Admin&lt;/b&gt;" in result
    # Intentional bold wrappers around the escaped product_name remain
    assert "<b>&lt;script&gt;alert(1)&lt;/script&gt;</b>" in result


def test_format_digest_header_contains_title_date_and_total():
    """Digest opens with a bold title, today's date, and the attention count."""
    items = [
        make_enriched(product_name="A", days=-2, status="expired", expiry_offset=-2),
        make_enriched(product_name="B", days=10, status="warning", expiry_offset=10),
    ]
    result = format_digest(items)
    assert result is not None
    assert "<b>\U0001f4cb License Monitor</b>" in result
    assert date.today().strftime("%d.%m.%Y") in result
    assert "требуют внимания: 2" in result


def test_format_digest_section_headers_show_counts():
    """Each urgency section header includes the item count."""
    items = [
        make_enriched(product_name="A", days=-3, status="expired", expiry_offset=-3),
        make_enriched(product_name="B", days=-1, status="expired", expiry_offset=-1),
        make_enriched(product_name="C", days=10, status="warning", expiry_offset=10),
    ]
    result = format_digest(items)
    assert result is not None
    assert "Истекло (2)" in result
    assert "Истекает скоро (1)" in result


def test_format_digest_orders_by_days_within_section():
    """Most urgent items (smallest days_remaining) appear first within each section."""
    items = [
        make_enriched(product_name="LATE", days=20, status="warning", expiry_offset=20),
        make_enriched(product_name="EARLY", days=2, status="warning", expiry_offset=2),
    ]
    result = format_digest(items)
    assert result is not None
    assert result.index("EARLY") < result.index("LATE")


def test_format_license_line_date_format():
    """format_license_line uses DD.MM.YYYY date format."""
    item = make_enriched(expiry_offset=10, days=10)
    line = format_license_line(item)
    expected_date = (date.today() + timedelta(days=10)).strftime("%d.%m.%Y")
    assert expected_date in line
