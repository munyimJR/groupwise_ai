"""Summarize the GroupWise AI user survey from a Google Forms CSV export.

    python research/analyze_survey.py responses.csv            # writes research/results/survey_summary.{md,json}
    python research/analyze_survey.py responses.csv --out DIR

Columns are found by the question code at the start of each title ("Q6. When you pay ..."), so the wording can be
edited without breaking the analysis. Only respondents who consented (Q0) are counted. Every percentage is reported
with its 95% margin of error, and the sample is described as a convenience sample, never as "all students".
Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

Q12_OPTIONS = [
    "Settle up with one tap from my wallet", "Import my wallet transactions automatically",
    "A shared savings pocket for a group goal", "Alerts for unusual or duplicate expenses",
    "A forecast of next week's group spending", "Automatic categories for expenses",
    "A fairness view of who pays first", "Asking questions in plain language",
]
Q4_WALLETS = ["bKash", "Nagad", "upay", "Rocket"]
Q6_ORDER = ["Same day", "1–3 days", "4–7 days", "1–2 weeks", "More than 2 weeks", "Often never"]


def _columns(header: list[str]) -> dict[str, int]:
    cols = {}
    for i, h in enumerate(header):
        m = re.match(r"\s*(Q\d{1,2})[.:)]", h)
        if m and m.group(1) not in cols:
            cols[m.group(1)] = i
    return cols


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return []
    cols = _columns(rows[0])
    missing = [q for q in ("Q0", "Q2", "Q4", "Q6") if q not in cols]
    if missing:
        raise SystemExit(f"Missing survey columns {missing}. Keep the 'Q#.' codes at the start of each question title.")
    out = []
    for r in rows[1:]:
        rec = {q: (r[i].strip() if i < len(r) else "") for q, i in cols.items()}
        if rec.get("Q0", "").lower().startswith("yes"):
            out.append(rec)
    return out


def share(n_yes: int, n: int) -> dict:
    if n == 0:
        return {"pct": None, "n": 0, "moe": None}
    p = n_yes / n
    return {"pct": round(100 * p, 1), "count": n_yes, "n": n, "moe": round(196 * math.sqrt(p * (1 - p) / n), 1)}


def summarize(resp: list[dict[str, str]]) -> dict:
    n = len(resp)

    def where(q, pred):
        answered = [r for r in resp if r.get(q)]
        return share(sum(1 for r in answered if pred(r[q])), len(answered))

    def has_any(text, options):
        return any(o.lower() in text.lower() for o in options)

    tried = [r for r in resp if r.get("Q11", "").startswith("Yes")]
    q12 = Counter(o for r in resp for o in Q12_OPTIONS if o.lower() in r.get("Q12", "").lower())
    q13 = [int(r["Q13"]) for r in resp if r.get("Q13", "").strip().isdigit()]
    q6 = [Q6_ORDER.index(r["Q6"]) for r in resp if r.get("Q6") in Q6_ORDER]
    return {
        "respondents": n,
        "students": where("Q1", lambda v: v == "University student"),
        "share_weekly_or_more": where("Q2", lambda v: v in ("Almost every day", "A few times a week", "About once a week")),
        "settle_with_mobile_wallet": where("Q4", lambda v: has_any(v, Q4_WALLETS)),
        "no_real_tracking": where("Q5", lambda v: v in ("Nobody tracks it", "From memory")
                                  or v.startswith("Chat messages")),
        "wait_more_than_3_days": where("Q6", lambda v: v in Q6_ORDER[2:]),
        "typical_wait": Q6_ORDER[round(statistics.median(q6))] if q6 else None,
        "lost_money_6_months": where("Q7", lambda v: v not in ("Nothing", "Not sure")),
        "money_caused_friction": where("Q8", lambda v: v != "Never"),
        "one_person_pays_first": where("Q9", lambda v: v.startswith("Yes")),
        "dont_know_group_spending": where("Q10", lambda v: v in ("Not really", "No idea")),
        "tried_group_goal": where("Q11", lambda v: v.startswith("Yes")),
        "goal_late_short_or_abandoned": share(sum(1 for r in tried if "on time" not in r["Q11"]), len(tried)),
        "feature_demand": [{"feature": f, **share(c, n)} for f, c in q12.most_common()],
        "use_inside_wallet": {"mean_1_to_5": round(statistics.mean(q13), 2) if q13 else None,
                              "likely_4_or_5": share(sum(1 for v in q13 if v >= 4), len(q13))},
        "main_wallet": dict(Counter(r["Q14"] for r in resp if r.get("Q14")).most_common()),
        "open_comments": sum(1 for r in resp if r.get("Q15")),
        "sample_note": "Convenience sample. Percentages describe these respondents only; ± is the 95% margin of error.",
    }


def _fmt(s: dict) -> str:
    return "n/a" if s.get("pct") is None else f"{s['pct']}% ± {s['moe']} ({s['count']} of {s['n']})"


def to_markdown(m: dict) -> str:
    lines = [f"# Survey results ({m['respondents']} respondents)", "", "| Finding | Result |", "|---|---|"]
    rows = [
        ("University students", m["students"]),
        ("Share costs with a group at least weekly", m["share_weekly_or_more"]),
        ("Pay or settle with a mobile wallet (bKash, Nagad, upay, Rocket)", m["settle_with_mobile_wallet"]),
        ("Track debts only by memory, chat, or not at all", m["no_real_tracking"]),
        ("Usually wait more than 3 days to be paid back", m["wait_more_than_3_days"]),
        ("Lost money in the last 6 months to someone not paying back", m["lost_money_6_months"]),
        ("Shared money caused an argument or awkward moment (6 months)", m["money_caused_friction"]),
        ("One person usually pays first", m["one_person_pays_first"]),
        ("Don't know what the group spent last month", m["dont_know_group_spending"]),
        ("Tried to save together for a group goal", m["tried_group_goal"]),
        ("…of those, finished late, short, or gave up", m["goal_late_short_or_abandoned"]),
        ("Likely (4–5 of 5) to use these features inside their wallet", m["use_inside_wallet"]["likely_4_or_5"]),
    ]
    lines += [f"| {k} | {_fmt(v)} |" for k, v in rows]
    lines += ["", f"Typical wait to be paid back: **{m['typical_wait'] or 'n/a'}**. "
                  f"Mean likelihood of using it inside a wallet: **{m['use_inside_wallet']['mean_1_to_5'] or 'n/a'} / 5**.",
              "", "## Most wanted features", "", "| Feature | Chosen by |", "|---|---|"]
    lines += [f"| {f['feature']} | {_fmt(f)} |" for f in m["feature_demand"]]
    lines += ["", "## Main wallet", "", "| Wallet | Respondents |", "|---|---|"]
    lines += [f"| {w} | {c} |" for w, c in m["main_wallet"].items()]
    lines += ["", f"_{m['sample_note']}_", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize the GroupWise AI survey (Google Forms CSV export).")
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    args = ap.parse_args()
    resp = load(args.csv)
    if not resp:
        raise SystemExit("No consenting responses found in this file.")
    m = summarize(resp)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "survey_summary.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    md = to_markdown(m)
    (args.out / "survey_summary.md").write_text(md, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(md)
    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()
