import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from urllib.request import Request, urlopen
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .excel_export import build_offer_xlsx
from .models import Client, FxRate, Offer, OfferLine, Product, SalespersonProfile

EMPTY_ROWS = 5


def _ensure_rows(offer: Offer, count: int = EMPTY_ROWS) -> None:
    existing = offer.lines.count()
    for i in range(existing + 1, count + 1):
        OfferLine.objects.create(offer=offer, position=i)


def _dec(value, default="0"):
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _fx_map() -> dict:
    return {r.waluta.upper(): r.kurs_pln for r in FxRate.objects.all()}


def _norm_ccy(code: str) -> str:
    raw = (code or "PLN").strip().upper().replace("ZŁ", "PLN").replace("ZL", "PLN")
    return raw or "PLN"


def _koszt_pln(product, rates):
    if not product:
        return Decimal("0"), "PLN", Decimal("0"), Decimal("1"), False
    raw = Decimal(product.cena_baz or 0)
    code = _norm_ccy(product.waluta)
    if code == "PLN":
        return raw.quantize(Decimal("0.01")), code, raw, Decimal("1"), False
    rate = rates.get(code)
    missing = rate is None
    if missing:
        rate = Decimal("1")
    pln = (raw * rate).quantize(Decimal("0.01"))
    return pln, code, raw, rate, missing


def _get_profile(user):
    profile, _created = SalespersonProfile.objects.get_or_create(user=user)
    return profile


def _line_payload(line: OfferLine, show_codes: bool, rates=None) -> dict:
    product = line.product
    rates = rates if rates is not None else _fx_map()
    cena = Decimal(product.cena_det) if product else None
    koszt, waluta, koszt_src, kurs, kurs_brak = _koszt_pln(product, rates)
    rabat = line.rabat or Decimal("0")
    netto = (cena * (Decimal("1") - rabat)).quantize(Decimal("0.01")) if cena is not None else None
    wartosc = (netto * line.ilosc).quantize(Decimal("0.01")) if netto is not None and line.ilosc else None
    qty = line.ilosc or Decimal("0")
    zysk_szt = (netto - koszt).quantize(Decimal("0.01")) if netto is not None else None
    zysk = (zysk_szt * qty).quantize(Decimal("0.01")) if zysk_szt is not None else None
    marza = None
    if netto and netto != 0:
        marza = ((netto - koszt) / netto * Decimal("100")).quantize(Decimal("0.01"))
    opis = ""
    if line.combi:
        opis = line.combi if show_codes else (product.nazwa if product else line.combi.split(" ", 1)[-1])
    photo = product.photo_url if product else ""
    return {
        "id": line.id,
        "position": line.position,
        "combi": line.combi,
        "opis": opis,
        "cena": str(cena) if cena is not None else "",
        "koszt": str(koszt),
        "koszt_src": str(koszt_src),
        "waluta": waluta,
        "kurs": str(kurs),
        "kurs_brak": kurs_brak,
        "rabat": str((rabat * Decimal("100")).quantize(Decimal("0.01"))) if product else "",
        "marza": str(marza) if marza is not None else "",
        "netto": str(netto) if netto is not None else "",
        "ilosc": str(line.ilosc) if line.ilosc is not None else "",
        "wartosc": str(wartosc) if wartosc is not None else "",
        "zysk": str(zysk) if zysk is not None else "",
        "zysk_szt": str(zysk_szt) if zysk_szt is not None else "",
        "zdjecie": photo,
        "zdjecie_plik": product.zdjecie if product else "",
        "kod": product.kod if product else "",
    }


def _offer_metrics(lines, transport: Decimal) -> dict:
    wartosc = Decimal("0")
    koszt = Decimal("0")
    for line in lines:
        if not line.get("wartosc"):
            continue
        wartosc += Decimal(line["wartosc"])
        qty = Decimal(line["ilosc"] or "0")
        koszt += Decimal(line["koszt"] or "0") * qty
    transport = transport or Decimal("0")
    wartosc = (wartosc + transport).quantize(Decimal("0.01"))
    koszt = koszt.quantize(Decimal("0.01"))
    zysk = (wartosc - koszt).quantize(Decimal("0.01"))
    marza = Decimal("0")
    if wartosc:
        marza = (zysk / wartosc * Decimal("100")).quantize(Decimal("0.01"))
    return {
        "wartosc": str(wartosc),
        "koszt": str(koszt),
        "transport": str(transport.quantize(Decimal("0.01"))),
        "zysk": str(zysk),
        "marza": str(marza),
    }


@login_required
def offer_list(request):
    offers = Offer.objects.filter(created_by=request.user)
    q = (request.GET.get("q") or "").strip()
    if q:
        offers = offers.filter(
            Q(nazwa__icontains=q) | Q(odbiorca_nazwa__icontains=q) | Q(platnik_nazwa__icontains=q)
        )
    return render(request, "offers/offer_list.html", {"offers": offers, "q": q})


@login_required
def offer_create(request):
    offer = Offer.objects.create(
        created_by=request.user,
        created_on=date.today(),
        nazwa="Propozycja",
    )
    _ensure_rows(offer)
    return redirect("offer_edit", pk=offer.pk)


@login_required
def offer_edit(request, pk):
    offer = get_object_or_404(Offer, pk=pk, created_by=request.user)
    _ensure_rows(offer)
    rates = _fx_map()
    lines = [_line_payload(line, offer.show_codes, rates) for line in offer.lines.all()]
    valid_to = offer.created_on + timedelta(days=offer.valid_days)
    profile = _get_profile(request.user)
    return render(
        request,
        "offers/offer_edit.html",
        {
            "offer": offer,
            "lines": lines,
            "metrics": _offer_metrics(lines, offer.koszt_transportu),
            "valid_to": valid_to,
            "handlowiec": request.user.get_full_name() or request.user.username,
            "profile": profile,
            "contact_line": " · ".join(
                x
                for x in [
                    request.user.get_full_name() or request.user.username,
                    profile.stanowisko,
                    profile.telefon,
                    profile.email,
                ]
                if x
            ),
        },
    )


@login_required
@require_POST
def offer_save(request, pk):
    offer = get_object_or_404(Offer, pk=pk, created_by=request.user)
    payload = json.loads(request.body.decode("utf-8"))
    offer.nazwa = payload.get("nazwa") or "Propozycja"
    offer.platnik_nazwa = payload.get("platnik_nazwa") or ""
    offer.platnik_adres = payload.get("platnik_adres") or ""
    offer.platnik_nip = payload.get("platnik_nip") or ""
    offer.odbiorca_nazwa = payload.get("odbiorca_nazwa") or ""
    offer.odbiorca_adres = payload.get("odbiorca_adres") or ""
    platnik_id = payload.get("platnik_id")
    odbiorca_id = payload.get("odbiorca_id")
    offer.platnik_id = int(platnik_id) if platnik_id else None
    offer.odbiorca_id = int(odbiorca_id) if odbiorca_id else None
    offer.with_photos = bool(payload.get("with_photos"))
    offer.show_codes = bool(payload.get("show_codes", True))
    offer.koszt_transportu = _dec(payload.get("koszt_transportu"), "20")
    offer.save()

    rates = _fx_map()
    for row in payload.get("lines", []):
        line = get_object_or_404(OfferLine, pk=row["id"], offer=offer)
        line.combi = (row.get("combi") or "").strip()
        product = line.product
        edited = row.get("edited") or "rabat"
        if edited == "marza" and product and product.cena_det:
            marza = _dec(row.get("marza"), "0") / Decimal("100")
            if marza >= Decimal("1"):
                marza = Decimal("0.99")
            if marza < 0:
                marza = Decimal("0")
            koszt, _waluta, _src, _kurs, _brak = _koszt_pln(product, rates)
            cena = product.cena_det
            if marza >= 1 or cena <= 0:
                rabat = Decimal("0")
            else:
                netto = (koszt / (Decimal("1") - marza)) if (Decimal("1") - marza) else cena
                rabat = Decimal("1") - (netto / cena)
            rabat = min(max(rabat, Decimal("0")), Decimal("0.99"))
        else:
            rabat = _dec(row.get("rabat") or "0") / Decimal("100")
            rabat = min(max(rabat, Decimal("0")), Decimal("0.99"))
        line.rabat = rabat.quantize(Decimal("0.0001"))
        ilosc_raw = str(row.get("ilosc") or "").strip()
        line.ilosc = _dec(ilosc_raw) if ilosc_raw else None
        line.save()

    extra = int(payload.get("add_rows") or 0)
    if extra > 0:
        start = offer.lines.count()
        for i in range(1, extra + 1):
            OfferLine.objects.create(offer=offer, position=start + i)

    if payload.get("clear"):
        offer.lines.all().delete()
        _ensure_rows(offer)

    lines = [_line_payload(line, offer.show_codes, rates) for line in offer.lines.all()]
    return JsonResponse(
        {
            "ok": True,
            "lines": lines,
            "show_codes": offer.show_codes,
            "metrics": _offer_metrics(lines, offer.koszt_transportu),
        }
    )


@login_required
@require_GET
def product_search(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"results": []})
    qs = Product.objects.filter(
        Q(combi__icontains=q) | Q(kod__icontains=q) | Q(nazwa__icontains=q)
    )[:300]
    return JsonResponse({"results": [p.combi for p in qs]})


PASTE_FORMATS = {
    "kod_ilosc": ("kod", "ilosc"),
    "kod_ilosc_cena": ("kod", "ilosc", "cena"),
    "kod_cena_ilosc": ("kod", "cena", "ilosc"),
}


def _parse_paste_number(raw: str):
    text = (raw or "").strip().replace("\u00a0", " ").replace(" ", "")
    if not text:
        return None
    text = text.replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _split_clipboard_rows(text: str):
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    rows = []
    for line in normalized.split("\n"):
        if not line.strip():
            continue
        if "\t" in line:
            cells = line.split("\t")
        elif ";" in line:
            cells = line.split(";")
        else:
            cells = line.split(",")
        rows.append([c.strip() for c in cells])
    return rows


@login_required
@require_POST
def offer_paste(request, pk):
    """Apply Excel clipboard rows (TSV) into the offer. Unknown codes are skipped."""
    offer = get_object_or_404(Offer, pk=pk, created_by=request.user)
    payload = json.loads(request.body.decode("utf-8"))
    text = payload.get("text") or ""
    has_header = bool(payload.get("has_header"))
    fmt = (payload.get("format") or "kod_ilosc").strip()
    columns = PASTE_FORMATS.get(fmt)
    if not columns:
        return JsonResponse({"ok": False, "error": "Nieznany format wklejania"}, status=400)

    raw_rows = _split_clipboard_rows(text)
    if has_header and raw_rows:
        raw_rows = raw_rows[1:]

    expected = len(columns)
    accepted = []
    dropped = []
    for idx, cells in enumerate(raw_rows, start=1 + (1 if has_header else 0)):
        # Ignore trailing empty cells from Excel
        while cells and cells[-1] == "":
            cells.pop()
        if len(cells) < expected:
            dropped.append(
                {
                    "row": idx,
                    "kod": cells[0] if cells else "",
                    "reason": f"Za mało kolumn (oczekiwano {expected}, jest {len(cells)})",
                }
            )
            continue
        mapped = {name: cells[i] for i, name in enumerate(columns)}
        kod = (mapped.get("kod") or "").strip()
        if not kod:
            dropped.append({"row": idx, "kod": "", "reason": "Brak kodu produktu"})
            continue
        product = Product.objects.filter(kod__iexact=kod).first()
        if not product:
            dropped.append({"row": idx, "kod": kod, "reason": "Nie znaleziono produktu w katalogu"})
            continue
        ilosc = _parse_paste_number(mapped.get("ilosc", ""))
        if ilosc is None or ilosc <= 0:
            dropped.append({"row": idx, "kod": kod, "reason": "Nieprawidłowa ilość"})
            continue
        rabat = Decimal("0")
        if "cena" in mapped:
            cena = _parse_paste_number(mapped.get("cena", ""))
            if cena is None or cena < 0:
                dropped.append({"row": idx, "kod": kod, "reason": "Nieprawidłowa cena"})
                continue
            katalog = Decimal(product.cena_det or 0)
            if katalog > 0:
                rabat = Decimal("1") - (cena / katalog)
                rabat = min(max(rabat, Decimal("0")), Decimal("0.99"))
        accepted.append(
            {
                "kod": product.kod,
                "combi": product.combi,
                "ilosc": str(ilosc.quantize(Decimal("0.01"))),
                "rabat": str((rabat * Decimal("100")).quantize(Decimal("0.01"))),
            }
        )

    if not accepted and not dropped:
        return JsonResponse(
            {
                "ok": False,
                "error": "Schowek jest pusty lub nie zawiera wierszy danych",
                "accepted": [],
                "dropped": [],
            },
            status=400,
        )

    # Fill existing empty lines first, then append.
    empty_lines = list(offer.lines.filter(combi="").order_by("position", "id"))
    used = 0
    for item in accepted:
        if used < len(empty_lines):
            line = empty_lines[used]
            used += 1
        else:
            line = OfferLine.objects.create(
                offer=offer,
                position=offer.lines.count() + 1,
            )
        line.combi = item["combi"]
        line.ilosc = _dec(item["ilosc"])
        line.rabat = (_dec(item["rabat"]) / Decimal("100")).quantize(Decimal("0.0001"))
        line.save()

    rates = _fx_map()
    lines = [_line_payload(line, offer.show_codes, rates) for line in offer.lines.all()]
    smooth = len(dropped) == 0 and len(accepted) > 0
    return JsonResponse(
        {
            "ok": True,
            "smooth": smooth,
            "accepted_count": len(accepted),
            "dropped_count": len(dropped),
            "dropped": dropped,
            "lines": lines,
            "metrics": _offer_metrics(lines, offer.koszt_transportu),
            "message": (
                f"Wklejono {len(accepted)} pozycji bez problemów."
                if smooth
                else (
                    f"Wklejono {len(accepted)} pozycji. "
                    f"Pominięto {len(dropped)} wierszy z powodu błędów."
                    if accepted
                    else f"Nie wklejono żadnej pozycji. Pominięto {len(dropped)} wierszy."
                )
            ),
        }
    )


@login_required
@require_GET
def client_search(request):
    q = (request.GET.get("q") or "").strip()
    qs = Client.objects.all()
    if q:
        qs = qs.filter(Q(nazwa__icontains=q) | Q(nip__icontains=q) | Q(adres__icontains=q))
    data = [
        {"id": c.id, "nazwa": c.nazwa, "adres": c.adres, "nip": c.nip}
        for c in qs[:50]
    ]
    return JsonResponse({"results": data})


@login_required
@require_GET
def product_photo(request, filename):
    name = filename.replace("\\", "/").split("/")[-1]
    if not name or ".." in name:
        raise Http404()
    url = settings.PHOTO_BASE_URL.rstrip("/") + "/" + quote(name)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=20) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "image/jpeg")
    except Exception as exc:
        raise Http404(str(exc)) from exc
    response = HttpResponse(data, content_type=ctype)
    response["Cache-Control"] = "public, max-age=86400"
    return response


@login_required
def offer_print(request, pk):
    offer = get_object_or_404(Offer, pk=pk, created_by=request.user)
    rates = _fx_map()
    lines = [_line_payload(line, offer.show_codes, rates) for line in offer.lines.all() if line.combi]
    valid_to = offer.created_on + timedelta(days=offer.valid_days)
    profile = _get_profile(request.user)
    return render(
        request,
        "offers/offer_print.html",
        {
            "offer": offer,
            "lines": lines,
            "metrics": _offer_metrics(lines, offer.koszt_transportu),
            "profile": profile,
            "valid_to": valid_to,
            "handlowiec": request.user.get_full_name() or request.user.username,
        },
    )


@login_required
def offer_excel(request, pk):
    offer = get_object_or_404(Offer, pk=pk, created_by=request.user)
    rates = _fx_map()
    lines = [_line_payload(line, offer.show_codes, rates) for line in offer.lines.all() if line.combi]
    valid_to = offer.created_on + timedelta(days=offer.valid_days)
    profile = _get_profile(request.user)
    handlowiec = request.user.get_full_name() or request.user.username
    payload = build_offer_xlsx(
        offer,
        lines,
        profile,
        handlowiec,
        valid_to,
        _offer_metrics(lines, offer.koszt_transportu),
    )
    name = (offer.nazwa or "oferta").replace('"', "").replace("/", "-")[:80]
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{name}.xlsx"'
    return response


@login_required
def settings_view(request):
    profile = _get_profile(request.user)
    is_admin = request.user.is_superuser
    if request.method == "POST":
        profile.telefon = (request.POST.get("telefon") or "").strip()
        profile.email = (request.POST.get("email") or "").strip()
        profile.stanowisko = (request.POST.get("stanowisko") or "").strip()
        profile.kontakt = (request.POST.get("kontakt") or "").strip()
        profile.komunikat_otwarcia = request.POST.get("komunikat_otwarcia") or ""
        profile.komunikat_zamkniecia = request.POST.get("komunikat_zamkniecia") or ""
        if request.POST.get("usun_zdjecie") and profile.zdjecie:
            profile.zdjecie.delete(save=False)
            profile.zdjecie = None
        uploaded = request.FILES.get("zdjecie")
        if uploaded:
            profile.zdjecie = uploaded
        profile.save()
        if is_admin:
            for rate in FxRate.objects.all():
                val = request.POST.get(f"kurs_{rate.id}")
                if val is None:
                    continue
                rate.kurs_pln = _dec(val, str(rate.kurs_pln))
                if rate.kurs_pln <= 0:
                    rate.kurs_pln = Decimal("0.0001")
                rate.save(update_fields=["kurs_pln"])
            new_ccy = _norm_ccy(request.POST.get("nowa_waluta") or "")
            new_rate = (request.POST.get("nowy_kurs") or "").strip()
            if new_ccy and new_ccy != "PLN" and new_rate:
                FxRate.objects.update_or_create(
                    waluta=new_ccy,
                    defaults={"kurs_pln": _dec(new_rate, "1"), "nazwa": new_ccy},
                )
            delete_id = request.POST.get("usun_kurs")
            if delete_id:
                FxRate.objects.filter(pk=delete_id).delete()
        messages.success(request, "Ustawienia zapisane.")
        return redirect("settings")
    return render(
        request,
        "offers/settings.html",
        {
            "profile": profile,
            "rates": FxRate.objects.all(),
            "is_admin": is_admin,
        },
    )
