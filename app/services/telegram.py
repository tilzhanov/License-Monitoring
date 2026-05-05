"""Telegram notification service — sends messages and formats asset digest.

Uses parse_mode=HTML on send. All user-controlled strings flow through
html.escape() before being interpolated into the message.
"""

import html
from datetime import date

import httpx

# Per-asset-type icon shown next to the asset name
_TYPE_EMOJI = {
    "license": "\U0001f4dc",  # 📜
    "support": "\U0001f6e0",  # 🛠
    "ssl": "\U0001f512",      # 🔒
}

# Russian error messages for Telegram API error codes
_ERROR_MESSAGES = {
    401: "Неверный токен бота",
    400: "Некорректный запрос (проверьте chat_id)",
    403: "Бот заблокирован или не добавлен в чат",
    429: "Слишком много запросов, попробуйте позже",
}


def send_telegram_message(token: str, chat_id: str, text: str) -> dict:
    """Send a message via Telegram Bot API with parse_mode=HTML.

    Returns:
        {"ok": True} on success.
        {"ok": False, "error": str, "error_code": int} on failure.

    NOTE: Never logs the full URL — it contains the token.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            data = response.json()

        if data.get("ok"):
            return {"ok": True}

        error_code = data.get("error_code", 0)
        description = _ERROR_MESSAGES.get(error_code, data.get("description", "Неизвестная ошибка"))
        return {"ok": False, "error": description, "error_code": error_code}

    except httpx.TimeoutException:
        return {"ok": False, "error": "Тайм-аут соединения с Telegram", "error_code": 0}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"Ошибка HTTP: {exc}", "error_code": 0}


# ---------------------------------------------------------------------------
# Digest formatting
# ---------------------------------------------------------------------------

def _days_label(days: int) -> str:
    """Human-readable days remaining: positive, zero, or overdue."""
    if days > 0:
        return f"{days} дн."
    if days == 0:
        return "истекает сегодня"
    return f"просрочено {-days} дн."


def _context_parts(asset, asset_type: str) -> list[str]:
    """Build the breadcrumb / type-specific context segments for a digest line.

    All values are html.escape()d before being added.
    """
    parts: list[str] = []

    product = getattr(asset, "product", None)
    if product is not None:
        vendor = getattr(product, "vendor", None)
        product_name = getattr(product, "name", None)
        vendor_name = getattr(vendor, "name", None) if vendor else None
        if vendor_name and product_name:
            parts.append(f"{html.escape(vendor_name)} / {html.escape(product_name)}")
        elif product_name:
            parts.append(html.escape(product_name))

    if asset_type == "ssl":
        domain = getattr(asset, "ssl_domain", None)
        issuer = getattr(asset, "ssl_issuer", None)
        if domain:
            parts.append(html.escape(domain))
        if issuer:
            parts.append(html.escape(issuer))
    elif asset_type == "support":
        contract_no = getattr(asset, "support_contract_no", None)
        sla = getattr(asset, "support_sla", None)
        if contract_no:
            parts.append(html.escape(contract_no))
        if sla:
            parts.append(f"SLA: {html.escape(sla)}")

    return parts


def format_license_line(enriched_item: dict) -> str:
    """Format one asset as a 2-line block with HTML markup.

    Layout:
        {emoji} <b>{name}</b>
           {context} · {date} · {days_label}[ · {responsible}]

    Where {context} is a `vendor / product` breadcrumb plus any type-specific
    fields (SSL domain/issuer, support contract no/SLA). When asset_type is a
    plain MagicMock or otherwise unknown the emoji falls back to •, which keeps
    legacy callers' output recognizable.
    """
    asset = enriched_item["license"]
    days = enriched_item["days_remaining"]

    asset_type_raw = getattr(asset, "asset_type", "license") or "license"
    asset_type = asset_type_raw if isinstance(asset_type_raw, str) else "license"
    emoji = _TYPE_EMOJI.get(asset_type, "•")

    name = html.escape(asset.product_name)
    date_str = asset.expiry_date.strftime("%d.%m.%Y")
    days_str = _days_label(days)

    trail = _context_parts(asset, asset_type)
    trail.append(date_str)
    trail.append(days_str)
    if getattr(asset, "responsible", None):
        trail.append(html.escape(asset.responsible))

    return f"{emoji} <b>{name}</b>\n   {' · '.join(trail)}"


def format_digest(enriched_assets: list) -> str | None:
    """Build a presentable HTML digest grouped by urgency.

    Layout:
        <b>📋 License Monitor</b>
        Отчёт за DD.MM.YYYY · требуют внимания: N

        <b>🔴 Истекло (n)</b>
        {asset block}
        ...

        <b>🟡 Истекает скоро (n)</b>
        {asset block}
        ...

    Active assets are excluded. Returns None if no qualifying assets exist
    so the scheduler can skip sending an empty notification.

    Within each section, items are sorted by days_remaining ascending so the
    most urgent items appear first.
    """
    expired = sorted(
        [e for e in enriched_assets if e["status"] == "expired"],
        key=lambda e: e["days_remaining"],
    )
    warning = sorted(
        [e for e in enriched_assets if e["status"] == "warning"],
        key=lambda e: e["days_remaining"],
    )

    if not expired and not warning:
        return None

    today_str = date.today().strftime("%d.%m.%Y")
    total = len(expired) + len(warning)

    lines: list[str] = []
    lines.append("<b>\U0001f4cb License Monitor</b>")
    lines.append(f"Отчёт за {today_str} · требуют внимания: {total}")
    lines.append("")

    if expired:
        lines.append(f"<b>\U0001f534 Истекло ({len(expired)})</b>")
        for e in expired:
            lines.append(format_license_line(e))
        lines.append("")

    if warning:
        lines.append(f"<b>\U0001f7e1 Истекает скоро ({len(warning)})</b>")
        for e in warning:
            lines.append(format_license_line(e))

    return "\n".join(lines).rstrip()
