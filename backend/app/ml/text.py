"""Free-text expense parsing: "Lunch at Kacchi Bhai 850" → amount, description, merchant."""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..synthetic.catalog import all_merchants

_CURRENCY = r"(?:৳|tk\.?|taka|bdt|/-)"
_NUM = r"(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d{1,2}))?"
_PREFIX_AMOUNT = re.compile(rf"{_CURRENCY}\s*{_NUM}", re.IGNORECASE)
_SUFFIX_AMOUNT = re.compile(rf"{_NUM}\s*{_CURRENCY}", re.IGNORECASE)
_TRAILING_AMOUNT = re.compile(rf"(?:^|\s|-|:){_NUM}\s*$")
# Numbers that are part of a place/address ("Mirpur 10", "Sector 7") are not amounts.
_PLACE_WORDS = {"mirpur", "section", "sector", "road", "house", "level", "gulshan", "banani", "uttara", "block",
                "flat", "room", "no", "lane", "dhanmondi", "bashundhara", "for", "x"}
_AT_MERCHANT = re.compile(r"\b(?:at|from|@)\s+([A-Za-z][\w'&.\- ]{1,40})$", re.IGNORECASE)
_GENERIC_PLACES = {"restaurant", "home", "campus", "canteen", "the flat", "flat", "office", "university", "the mall",
                   "mall", "hotel", "the restaurant", "a restaurant", "friends", "class", "market", "bazar", "shop"}
_MERCHANTS = all_merchants()
# Longest first so "Pathao Food" wins over "Pathao".
_MERCHANT_KEYS = sorted(_MERCHANTS, key=len, reverse=True)


@dataclass
class ParsedExpense:
    description: str
    amount: float | None
    merchant: str | None


def _to_float(whole: str, frac: str | None) -> float:
    return float(whole.replace(",", "") + ("." + frac if frac else ""))


def parse_expense_text(text: str) -> ParsedExpense:
    raw = " ".join(text.strip().split())
    amount: float | None = None
    desc = raw
    for pattern in (_PREFIX_AMOUNT, _SUFFIX_AMOUNT):
        m = pattern.search(desc)
        if m:
            amount = _to_float(m.group(1), m.group(2))
            desc = (desc[: m.start()] + " " + desc[m.end():]).strip()
            break
    if amount is None:
        m = _TRAILING_AMOUNT.search(desc)
        if m:
            before = desc[: m.start()].strip().split()
            value = _to_float(m.group(1), m.group(2))
            prev_word = before[-1].lower().strip(".,:-") if before else ""
            if before and prev_word not in _PLACE_WORDS and value >= 20:
                amount = value
                desc = desc[: m.start()].strip()
    desc = desc.strip(" -:,")
    return ParsedExpense(description=desc or raw, amount=amount, merchant=detect_merchant(desc))


def detect_merchant(desc: str) -> str | None:
    low = f" {desc.lower()} "
    for key in _MERCHANT_KEYS:
        if f" {key} " in low or low.strip().startswith(key + " ") or low.strip() == key:
            return _MERCHANTS[key]
    m = _AT_MERCHANT.search(desc)
    if m:
        name = m.group(1).strip()
        if len(name.split()) <= 4 and name.lower() not in _GENERIC_PLACES:
            return name[:1].upper() + name[1:]
    return None


_STRIP = re.compile(r"[^a-zঀ-৿' ]+")


def normalize_for_model(text: str) -> str:
    """Lower-case and drop digits/currency/punctuation so the model learns words, not amounts."""
    low = text.lower().replace("৳", " ")
    low = _STRIP.sub(" ", low)
    return " ".join(low.split())
