def fmt_money(v):
    try: return f"${int(v):,}".replace(",", ".")
    except Exception: return f"${v}"
