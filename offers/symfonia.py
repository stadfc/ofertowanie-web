"""Read-only helpers for Symfonia (SQL Server)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pyodbc
from django.conf import settings


class SymfoniaConfigError(Exception):
    pass


class SymfoniaQueryError(Exception):
    pass


def build_odbc_connection_string() -> str:
    if settings.SYMFONIA_ODBC:
        return settings.SYMFONIA_ODBC
    uid = settings.SYMFONIA_UID
    pwd = settings.SYMFONIA_PWD
    if not uid or not pwd:
        raise SymfoniaConfigError(
            "Brak danych połączenia Symfonia. Ustaw SYMFONIA_ODBC "
            "albo SYMFONIA_UID + SYMFONIA_PWD."
        )
    return (
        f"DRIVER={{{settings.SYMFONIA_DRIVER}}};"
        f"SERVER={settings.SYMFONIA_SERVER};"
        f"DATABASE={settings.SYMFONIA_DATABASE};"
        f"UID={uid};"
        f"PWD={pwd};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "LongAsMax=yes;"
    )


def connect():
    return pyodbc.connect(build_odbc_connection_string(), timeout=30)


# Same base query as Do_realizacji/main.py, then keep only positive open qty
# (Do_realizacji > 0). Zero = fully shipped; negative = over-settled vs order.
ORDERS_SQL = """
SELECT
    dane_platnika.Shortcut AS platnik,
    dane_odbiorcy.Shortcut AS odbiorca,
    CAST(HM.ZO.data AS date) AS data,
    HM.ZO.kod AS kod_zamowienia,
    HM.ZP.Kod AS kod_produktu,
    HM.TW.nazwa AS nazwa,
    HM.ZP.ilosc AS ilosc,
    HM.ZP.cena AS cena,
    HM.ZP.wartNetto AS wart_netto,
    COALESCE(SUM(sett.Quantity), 0) AS zrealizowano,
    HM.ZP.ilosc - COALESCE(SUM(sett.Quantity), 0) AS do_realizacji
FROM HM.ZP
INNER JOIN HM.ZO ON HM.ZP.super = HM.ZO.id
INNER JOIN SSCommon.STContractors AS dane_platnika ON HM.ZO.khid = dane_platnika.Id
INNER JOIN SSCommon.STContractors AS dane_odbiorcy ON HM.ZO.odid = dane_odbiorcy.Id
INNER JOIN HM.TW ON HM.TW.id = HM.ZP.idtw
LEFT OUTER JOIN HM.dbo_ForeignOrderPositionSettlementsView AS sett
    ON HM.ZP.id = sett.OrderPositionId
WHERE HM.ZO.znacznik = ?
  AND HM.ZO.kod LIKE ?
  AND (
    (HM.ZP.ilosc - sett.Quantity) <> 0
    OR sett.Quantity IS NULL
  )
GROUP BY
    dane_platnika.Shortcut,
    dane_odbiorcy.Shortcut,
    HM.ZO.data,
    HM.ZO.kod,
    HM.ZP.kod,
    HM.TW.nazwa,
    HM.ZP.ilosc,
    HM.ZP.cena,
    HM.ZP.wartNetto
HAVING HM.ZP.ilosc - COALESCE(SUM(sett.Quantity), 0) > 0
ORDER BY HM.ZO.kod, HM.ZP.kod
"""


@dataclass
class OrderLineStatus:
    platnik: str
    odbiorca: str
    data: date | None
    kod_zamowienia: str
    kod_produktu: str
    nazwa: str
    ilosc: Decimal
    cena: Decimal
    wart_netto: Decimal
    zrealizowano: Decimal
    do_realizacji: Decimal


def _dec(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _is_tra_transport(kod_produktu: str, nazwa: str) -> bool:
    """True for the standalone TRA transport service line."""
    kod = (kod_produktu or "").strip().upper()
    name = (nazwa or "").strip().casefold()
    if kod == "TRA":
        return True
    return name == "usługa transportowa" or name == "usluga transportowa"


def _drop_tra_only_orders(lines: list[OrderLineStatus]) -> list[OrderLineStatus]:
    """Hide orders whose only remaining open line is TRA transport."""
    by_order: dict[str, list[OrderLineStatus]] = {}
    for line in lines:
        by_order.setdefault(line.kod_zamowienia, []).append(line)
    keep: list[OrderLineStatus] = []
    for order_lines in by_order.values():
        if len(order_lines) == 1 and _is_tra_transport(
            order_lines[0].kod_produktu, order_lines[0].nazwa
        ):
            continue
        keep.extend(order_lines)
    return keep


def fetch_open_order_lines(znacznik: int, year: int | None = None) -> list[OrderLineStatus]:
    """Open foreign-order positions for a salesperson marker (e.g. D = 68)."""
    if year is None:
        year = date.today().year
    yy = f"{year % 100:02d}"
    kod_like = f"%/{yy}/ZMO"
    try:
        cnxn = connect()
    except (pyodbc.Error, SymfoniaConfigError) as exc:
        raise SymfoniaQueryError(str(exc)) from exc
    try:
        cursor = cnxn.cursor()
        cursor.execute(ORDERS_SQL, (znacznik, kod_like))
        rows = cursor.fetchall()
    except pyodbc.Error as exc:
        raise SymfoniaQueryError(str(exc)) from exc
    finally:
        cnxn.close()

    out: list[OrderLineStatus] = []
    for row in rows:
        # Keep only still-open qty (exclude fully shipped and over-settled).
        do_real = _dec(row.do_realizacji)
        if do_real <= 0:
            continue
        out.append(
            OrderLineStatus(
                platnik=str(row.platnik or "").strip(),
                odbiorca=str(row.odbiorca or "").strip(),
                data=_as_date(row.data),
                kod_zamowienia=str(row.kod_zamowienia or "").strip(),
                kod_produktu=str(row.kod_produktu or "").strip(),
                nazwa=str(row.nazwa or "").strip(),
                ilosc=_dec(row.ilosc),
                cena=_dec(row.cena),
                wart_netto=_dec(row.wart_netto),
                zrealizowano=_dec(row.zrealizowano),
                do_realizacji=do_real,
            )
        )
    return _drop_tra_only_orders(out)
