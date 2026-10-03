"""Grounding check: every figure in an LLM answer must trace back to a computed fact.

Numbers are extracted from the answer and matched (allowing normal rounding) against numbers in
the facts and the user's own question. Any unmatched figure fails the check, and the caller
replaces the LLM text with the deterministic answer.
"""
from __future__ import annotations

import re

_CITATION = re.compile(r"\[F\d+\]")
_NUM = re.compile(r"(?<![A-Za-z\d])(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?\s*(k|K)?(?![A-Za-z\d])")
SMALL_INT_EXEMPT = 10  # small counts ("3 payments", "2 members") read naturally without a fact id


def extract_numbers(text: str) -> list[float]:
    text = _CITATION.sub(" ", text)
    out = []
    for m in _NUM.finditer(text):
        value = float(m.group(1).replace(",", "") + ("." + m.group(2) if m.group(2) else ""))
        if m.group(3):
            value *= 1000
        out.append(value)
    return out


def _matches(n: float, candidates: list[float]) -> bool:
    for f in candidates:
        if f == n:
            return True
        tolerance = max(1.0, 0.015 * abs(f))  # rounding like 28.4 → 28 or 62,910 → 63,000
        if abs(n - f) <= tolerance:
            return True
    return False


def check(answer: str, fact_texts: list[str], question: str = "") -> dict:
    allowed = extract_numbers(" ".join(fact_texts) + " " + question)
    found = extract_numbers(answer)
    unverified = []
    checked = 0
    for n in found:
        if n <= SMALL_INT_EXEMPT and float(n).is_integer():
            continue
        checked += 1
        if not _matches(n, allowed):
            unverified.append(n)
    return {"numbers_checked": checked, "verified": checked - len(unverified), "unverified": unverified,
            "passed": not unverified}


def cited_ids(answer: str) -> list[str]:
    return list(dict.fromkeys(m.strip("[]") for m in _CITATION.findall(answer)))
