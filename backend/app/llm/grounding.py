"""Grounding check: an LLM answer may only say what the computed facts say.

Numbers alone aren't enough (an answer can reuse a real figure in a false sentence), so the check has two layers:

* Numeric: every figure must match (allowing normal rounding) a number in the facts the answer *cites*, or in the
  user's own question. With no citations at all, figures can't be traced and the answer fails.
* Semantic:
  - citations must point to facts that exist;
  - people, categories and goals the answer names must appear in the facts or the question (no invented subjects);
  - direction words (rose / fell, more / less) in a sentence must agree with the sign of the facts it cites;
  - "A owes B" must not reverse a debt stated in the facts.

Any failure makes the caller show the deterministic, fact-built answer instead.
"""
from __future__ import annotations

import re

_CITATION = re.compile(r"\[(F\d+)\]")
_NUM = re.compile(r"(?<![A-Za-z\d])(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?\s*(k|K)?(?![A-Za-z\d])")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_OWES = re.compile(r"\b([A-Z][\w'-]*|you|You)\s+owes?\s+([A-Z][\w'-]*|you)\b")
_UP_WORDS = re.compile(r"\b(increas\w*|rose|rise[sn]?|rising|up|higher|more than|grew|grow\w*|jump\w*|climb\w*|spik\w*)\b", re.I)
_DOWN_WORDS = re.compile(r"\b(decreas\w*|fell|fall\w*|down|lower|less than|dropp?\w*|declin\w*|shr[iu]nk\w*|cut)\b", re.I)
_SIGNED = re.compile(r"(?<![\w.])([+\-−])\d")
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


def _direction(text: str) -> set[str]:
    out = set()
    if _UP_WORDS.search(text):
        out.add("up")
    if _DOWN_WORDS.search(text):
        out.add("down")
    for sign in _SIGNED.findall(text):
        out.add("up" if sign == "+" else "down")
    return out


def _owes_pairs(text: str) -> set[tuple[str, str]]:
    return {(a.lower(), b.lower()) for a, b in _OWES.findall(text)}


def _mentions(text: str, term: str) -> bool:
    # Case-sensitive: names are proper nouns, and "health" the word isn't the "Health" category.
    return re.search(rf"(?<![\w]){re.escape(term)}(?![\w])", text) is not None


def check(answer: str, facts: list[str] | list[dict], question: str = "", vocabulary: list[str] | None = None) -> dict:
    """`facts` are fact dicts ({id, statement}) or bare statements (numeric check only, as for older callers)."""
    by_id = {f["id"]: f["statement"] for f in facts if isinstance(f, dict)}
    texts = [f["statement"] if isinstance(f, dict) else f for f in facts]
    cited = list(dict.fromkeys(_CITATION.findall(answer)))
    unknown_citations = [c for c in cited if by_id and c not in by_id]

    # numeric: figures must come from the cited evidence (or, for plain statements, from any fact)
    if by_id:
        evidence = " ".join(by_id[c] for c in cited if c in by_id)
    else:
        evidence = " ".join(texts)
    allowed = extract_numbers(evidence + " " + question)
    unverified, checked = [], 0
    for n in extract_numbers(answer):
        if n <= SMALL_INT_EXEMPT and float(n).is_integer():
            continue
        checked += 1
        if not _matches(n, allowed):
            unverified.append(n)

    # semantic: subjects, direction of change, direction of debts
    all_facts = " ".join(texts) + " " + question
    unsupported = sorted({t for t in (vocabulary or []) if len(t) > 2 and _mentions(answer, t) and not _mentions(all_facts, t)})
    contradictions = []
    for sentence in _SENTENCE.split(answer):
        ids = [c for c in _CITATION.findall(sentence) if c in by_id]
        if not ids:
            continue
        said, backed = _direction(_CITATION.sub(" ", sentence)), _direction(" ".join(by_id[c] for c in ids))
        if said and backed and not (said & backed):
            contradictions.append({"sentence": sentence.strip()[:160], "issue": "direction", "facts": ids})
    fact_debts = _owes_pairs(all_facts)
    for a, b in _owes_pairs(answer):
        if (b, a) in fact_debts and (a, b) not in fact_debts:
            contradictions.append({"sentence": f"{a} owes {b}", "issue": "debt reversed", "facts": []})

    passed = not (unverified or unknown_citations or unsupported or contradictions)
    return {"numbers_checked": checked, "verified": checked - len(unverified), "unverified": unverified,
            "unknown_citations": unknown_citations, "unsupported_entities": unsupported,
            "contradictions": contradictions, "passed": passed}


def cited_ids(answer: str) -> list[str]:
    return list(dict.fromkeys(_CITATION.findall(answer)))
