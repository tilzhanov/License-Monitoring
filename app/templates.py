from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def format_money(value) -> str:
    """Render numeric cost with thin-space thousands separator + KZT.

    Falls back to the raw string when the value isn't a clean number,
    so legacy free-form costs ("~120 000 USD") render unchanged.
    """
    if value is None or value == "":
        return "—"
    raw = str(value).strip()
    cleaned = raw.replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        if "." in cleaned:
            num = float(cleaned)
            if num.is_integer():
                formatted = f"{int(num):,}".replace(",", " ")
            else:
                formatted = f"{num:,.2f}".replace(",", " ")
        else:
            formatted = f"{int(cleaned):,}".replace(",", " ")
    except (ValueError, TypeError):
        return raw
    return f"{formatted} ₸"


templates.env.filters["money"] = format_money
