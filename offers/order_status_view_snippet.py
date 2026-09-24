# Drop-in replacement for order_status() in offers/views.py
# (keeps existing imports: Decimal, date, login_required, render, symfonia_db, _get_profile, DEFAULT_ZNACZNIK)

@login_required
def order_status(request):
    profile = _get_profile(request.user)
    znacznik = profile.znacznik_symfonia or DEFAULT_ZNACZNIK
    year = date.today().year
    raw_year = (request.GET.get("rok") or "").strip()
    if raw_year.isdigit() and 2000 <= int(raw_year) <= 2100:
        year = int(raw_year)

    error = ""
    lines: list[symfonia_db.OrderLineStatus] = []
    try:
        lines = symfonia_db.fetch_open_order_lines(znacznik, year)
    except symfonia_db.SymfoniaQueryError as exc:
        error = str(exc)

    orders: dict[str, dict] = {}
    for line in lines:
        bucket = orders.setdefault(
            line.kod_zamowienia,
            {
                "kod": line.kod_zamowienia,
                "data": line.data,
                "platnik": line.platnik,
                "odbiorca": line.odbiorca,
                "lines": [],
                "do_realizacji_sum": Decimal("0"),
                "wart_netto_open": Decimal("0"),
            },
        )
        bucket["lines"].append(line)
        bucket["do_realizacji_sum"] += line.do_realizacji
        bucket["wart_netto_open"] += line.wart_netto_open

    order_list = sorted(
        orders.values(),
        key=lambda o: (o["data"] or date.min, o["kod"]),
        reverse=True,
    )
    total_wart_netto_open = sum(
        (o["wart_netto_open"] for o in order_list),
        Decimal("0.00"),
    )

    return render(
        request,
        "offers/order_status.html",
        {
            "orders": order_list,
            "line_count": len(lines),
            "order_count": len(order_list),
            "total_wart_netto_open": total_wart_netto_open,
            "znacznik": znacznik,
            "year": year,
            "error": error,
            "handlowiec": request.user.get_full_name() or request.user.username,
            "years": list(range(date.today().year, date.today().year - 5, -1)),
        },
    )
