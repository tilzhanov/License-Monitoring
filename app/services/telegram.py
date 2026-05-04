"""Telegram notification service — sends messages and formats license digest."""

import html
import httpx

# Russian error messages for Telegram API error codes
_ERROR_MESSAGES = {
    401: "Неверный токен бота",
    400: "Некорректный запрос (проверьте chat_id)",
    403: "Бот заблокирован или не добавлен в чат",
    429: "Слишком много запросов, попробуйте позже",
}


def send_telegram_message(token: str, chat_id: str, text: str) -> dict:
    """Send a plain-text message via Telegram Bot API.

    Returns:
        {"ok": True} on success.
        {"ok": False, "error": str, "error_code": int} on failure.

    NOTE: Never logs the full URL — it contains the token.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

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


def format_license_line(enriched_item: dict) -> str:
    """Format a single license as a digest line.

    Format (D-03): • ProductName — DD.MM.YYYY (N дн.) — Responsible
    Responsible is omitted if None or empty.
    Uses bullet character (•), not asterisk.
    html.escape() applied to user strings per coding convention.
    """
    lic = enriched_item["license"]
    days = enriched_item["days_remaining"]
    date_str = lic.expiry_date.strftime("%d.%m.%Y")
    product = html.escape(lic.product_name)
    line = f"\u2022 {product} \u2014 {date_str} ({days} \u0434\u043d.) "

    if lic.responsible:
        responsible = html.escape(lic.responsible)
        line += f"\u2014 {responsible}"
    else:
        # Strip trailing space if no responsible
        line = line.rstrip()

    return line


def format_digest(enriched_licenses: list) -> str | None:
    """Format urgency-tiered digest message for Telegram.

    Groups licenses by urgency:
        🔴 Истекло  — expired licenses
        🟡 Истекает скоро — warning licenses

    Active licenses are excluded (D-02).
    Returns None if no qualifying licenses exist (D-04).
    """
    expired = [e for e in enriched_licenses if e["status"] == "expired"]
    warning = [e for e in enriched_licenses if e["status"] == "warning"]

    if not expired and not warning:
        return None

    lines = []

    if expired:
        lines.append("\U0001f534 \u0418\u0441\u0442\u0435\u043a\u043b\u043e")
        for e in expired:
            lines.append(format_license_line(e))

    if warning:
        lines.append("\U0001f7e1 \u0418\u0441\u0442\u0435\u043a\u0430\u0435\u0442 \u0441\u043a\u043e\u0440\u043e")
        for e in warning:
            lines.append(format_license_line(e))

    return "\n".join(lines)
