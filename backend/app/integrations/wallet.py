"""Mobile-wallet (MFS) adapter: statement parsing and signed payment events.

Two touch points connect GroupWise to a wallet such as a future upay integration:

1. **Statement in.** A wallet transaction export (CSV) is parsed into normalized rows. Column names
   differ between providers, so headers are matched by meaning ("TrxID", "Transaction ID" and
   "Reference" all become the transaction id).
2. **Payments out.** GroupWise creates a payment request (amount, payee, reference); the wallet
   executes it and reports the result as an event signed with a shared secret (HMAC-SHA256).
   GroupWise records the settlement only after a valid, matching event. It never holds money.

The sandbox provider plays the wallet's role so the whole flow can be shown without real money.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime

MAX_STATEMENT_BYTES = 200_000
MAX_STATEMENT_ROWS = 500
SIGNATURE_HEADER = "X-GroupWise-Signature"
TIMESTAMP_HEADER = "X-GroupWise-Timestamp"
SIGNATURE_TOLERANCE_SECONDS = 300


class StatementError(ValueError):
    pass


# ----------------------------------------------------------------------------- statement parsing
_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "txn_id": ("trxid", "trx id", "txnid", "txn id", "transaction id", "transactionid", "reference", "ref", "ref no"),
    "date": ("date", "date time", "datetime", "transaction date", "txn date", "time stamp", "timestamp"),
    "time": ("time", "transaction time"),
    "type": ("type", "transaction type", "txn type", "service", "category"),
    "counterparty": ("counterparty", "account", "to/from", "to", "from", "receiver", "recipient", "merchant", "name",
                     "party", "wallet"),
    "description": ("description", "details", "detail", "note", "purpose", "remarks", "narration"),
    "amount": ("amount", "amount (bdt)", "amount (tk)", "amount(bdt)", "transaction amount"),
    "debit": ("debit", "out", "money out", "withdrawal", "dr"),
    "credit": ("credit", "in", "money in", "deposit", "cr"),
    "direction": ("direction", "dr/cr", "in/out"),
}

# Normalized wallet transaction kinds
_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("bill_pay", re.compile(r"\bbill\b")),
    ("payment", re.compile(r"\b(payment|merchant|qr|purchase|pay)\b")),
    ("recharge", re.compile(r"recharge|top.?up|airtime")),
    ("send_money", re.compile(r"send|transfer|p2p|sent")),
    ("received", re.compile(r"receiv|incoming")),
    ("cash_out", re.compile(r"cash.?out|withdraw")),
    ("cash_in", re.compile(r"cash.?in")),
    ("add_money", re.compile(r"add.?money|from bank|card")),
]
_OUTFLOW_KINDS = {"payment", "bill_pay", "recharge", "send_money", "cash_out"}


@dataclass
class StatementRow:
    line: int
    txn_id: str
    occurred_at: datetime
    kind: str  # payment|bill_pay|recharge|send_money|received|cash_out|cash_in|add_money|other
    direction: str  # out|in
    counterparty: str
    description: str
    amount_paisa: int


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-.]", " ", h.strip().lower().lstrip("﻿"))).strip()


def _map_headers(headers: list[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    normalized = [_norm_header(h) for h in headers]
    for field, aliases in _HEADER_ALIASES.items():
        for i, h in enumerate(normalized):
            if h in aliases and i not in found.values():
                found[field] = i
                break
    return found


def _amount_paisa(text: str) -> int | None:
    t = (text or "").strip()
    if not t:
        return None
    negative = t.startswith("-") or (t.startswith("(") and t.endswith(")"))
    digits = re.sub(r"[^0-9.]", "", t)
    if not digits or digits.count(".") > 1:
        return None
    value = round(float(digits) * 100)
    return -value if negative else value


_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                 "%d/%m/%Y %I:%M %p", "%d/%m/%Y", "%d-%m-%Y %H:%M", "%d-%m-%Y", "%d %b %Y %I:%M %p", "%d %b %Y %H:%M",
                 "%d %b %Y", "%d-%b-%Y %I:%M %p", "%d-%b-%Y")


def _parse_datetime(date_text: str, time_text: str = "") -> datetime | None:
    raw = " ".join(x for x in (date_text.strip(), time_text.strip()) if x)
    raw = raw.replace("T", " ").replace("Z", "")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _kind(type_text: str, direction: str) -> str:
    t = type_text.strip().lower()
    for kind, pattern in _TYPE_PATTERNS:
        if pattern.search(t):
            if kind == "send_money" and direction == "in":
                return "received"
            return kind
    return "other"


def parse_statement(text: str) -> list[StatementRow]:
    """Parse a wallet statement CSV. Raises StatementError with a human-readable message."""
    if len(text.encode("utf-8")) > MAX_STATEMENT_BYTES:
        raise StatementError("That statement is too large. Export a shorter date range (up to about 500 transactions).")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [r for r in reader if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise StatementError("The statement has no transactions. Upload the CSV export from your wallet app.")
    cols = _map_headers(rows[0])
    missing = [f for f in ("date",) if f not in cols]
    if "amount" not in cols and not ({"debit", "credit"} & cols.keys()):
        missing.append("amount")
    if missing:
        raise StatementError("Couldn't find the " + " and ".join(missing) + " column in this statement. "
                             "Expected columns like Date, Type, Counterparty, Amount and TrxID.")
    out: list[StatementRow] = []
    for line, r in enumerate(rows[1:MAX_STATEMENT_ROWS + 1], start=2):
        def cell(field: str, r: list[str] = r) -> str:
            i = cols.get(field)
            return r[i].strip() if i is not None and i < len(r) else ""

        when = _parse_datetime(cell("date"), cell("time"))
        if when is None:
            continue
        amount = None
        direction_text = cell("direction").lower()
        if "debit" in cols or "credit" in cols:
            debit, credit = _amount_paisa(cell("debit")), _amount_paisa(cell("credit"))
            if debit:
                amount, direction = abs(debit), "out"
            elif credit:
                amount, direction = abs(credit), "in"
        if amount is None:
            value = _amount_paisa(cell("amount"))
            if not value:
                continue
            if direction_text in ("out", "dr", "debit", "-"):
                direction = "out"
            elif direction_text in ("in", "cr", "credit", "+"):
                direction = "in"
            else:
                direction = "out" if value < 0 else ("in" if _kind(cell("type"), "in") in ("received", "cash_in", "add_money")
                                                     else "out")
            amount = abs(value)
        kind = _kind(cell("type"), direction)
        if kind in _OUTFLOW_KINDS and direction == "in":
            kind = "received" if kind == "send_money" else "other"
        txn_id = cell("txn_id") or f"line-{line}-{when:%Y%m%d%H%M}-{amount}"
        out.append(StatementRow(line=line, txn_id=txn_id[:64], occurred_at=when.replace(second=0, microsecond=0),
                                kind=kind, direction=direction, counterparty=cell("counterparty")[:80],
                                description=cell("description")[:160], amount_paisa=amount))
    if not out:
        raise StatementError("No transactions could be read. Check that the Date and Amount columns are filled in.")
    return out


# ----------------------------------------------------------------------------- payment requests & signed events
def new_reference() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "GW-" + "".join(secrets.choice(alphabet) for _ in range(8))


def sign(body: bytes, secret: str, timestamp: int | None = None) -> tuple[str, str]:
    """Signature headers for an event body: HMAC-SHA256 over "<timestamp>.<body>"."""
    ts = str(timestamp if timestamp is not None else int(time.time()))
    digest = hmac.new(secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    return ts, f"sha256={digest}"


def verify(body: bytes, secret: str, timestamp: str | None, signature: str | None, now: float | None = None) -> bool:
    if not secret or not timestamp or not signature or not timestamp.isdigit():
        return False
    if abs((now if now is not None else time.time()) - int(timestamp)) > SIGNATURE_TOLERANCE_SECONDS:
        return False  # stale or future-dated: rejects replays
    _, expected = sign(body, secret, int(timestamp))
    return hmac.compare_digest(expected, signature.strip())


class SandboxWallet:
    """Plays the wallet provider in demos: approving produces the same signed event a real wallet would send."""

    name = "sandbox"

    @staticmethod
    def txn_id() -> str:
        return "SBX" + secrets.token_hex(5).upper()
