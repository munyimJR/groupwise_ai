"""Public metadata: health check, runtime config for the client, taxonomy, model cards & evaluation."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from ..config import get_settings
from ..db import engine
from ..llm.client import llm_status
from ..ml import anomaly, categorizer, forecast
from ..ml.taxonomy import taxonomy_payload

router = APIRouter(tags=["meta"])
EVAL_PATH = Path(__file__).resolve().parent.parent / "ml" / "evaluation.json"
VALIDATION_PATH = Path(__file__).resolve().parent.parent / "ml" / "validation.json"


@router.get("/health")
def health() -> dict:
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "llm": llm_status()["available"]}


@router.get("/meta/config")
def client_config() -> dict:
    s = get_settings()
    return {"auth": {"supabase": s.supabase_enabled, "local": s.allow_local_auth}, "demo": s.demo_enabled,
            "llm": llm_status(), "currency": "BDT", "timezone": "Asia/Dhaka"}


@router.get("/meta/taxonomy")
def taxonomy() -> list[dict]:
    return taxonomy_payload()


@router.get("/meta/models")
def models() -> dict:
    evaluation = json.loads(EVAL_PATH.read_text(encoding="utf-8")) if EVAL_PATH.exists() else None
    validation = json.loads(VALIDATION_PATH.read_text(encoding="utf-8")) if VALIDATION_PATH.exists() else None
    if validation:  # the page needs the comparisons, not the individual error examples
        validation["categorizer"].get("stress_set", {}).pop("errors", None)
    return {
        "evaluation": evaluation,
        "validation": validation,
        "models": [
            {"key": "categorizer", "name": "Smart expense categorization", "type": "ML classifier",
             "version": categorizer.MODEL_VERSION,
             "method": "TF-IDF word (1–2) + character (2–5) n-grams → multinomial logistic regression, with a "
                       "known-merchant prior and per-group memory of human corrections",
             "inputs": "Expense description text (amounts and digits removed)",
             "outputs": "Category, subcategory, expense type, confidence, alternatives, key word signals",
             "limitations": "Trained on a synthetic Bangladesh-flavoured corpus; unfamiliar merchants rely on context "
                            "words. Low-confidence predictions ask the user to confirm."},
            {"key": "anomaly", "name": "Unusual expense detection", "type": "Hybrid ML + statistics + rules",
             "version": anomaly.MODEL_VERSION,
             "method": "Noisy-OR of Isolation Forest rank, robust z-scores vs subcategory and group history, "
                       "night-time, rare-category and duplicate signals",
             "inputs": "The group's own expense history",
             "outputs": "Anomaly score (0–100%), human-readable reasons",
             "limitations": "Needs ~25 expenses for the Isolation Forest; flags are suggestions — nothing is blocked."},
            {"key": "forecast", "name": "Group cash-flow forecast", "type": "Time-series model",
             "version": forecast.MODEL_VERSION,
             "method": "Calendar-based recurring-bill detection + per-category seasonal exponential smoothing with "
                       "weekday and month-phase factors; intervals from rolling-origin backtests",
             "inputs": "Up to 120 days of the group's expenses (unusual one-offs excluded)",
             "outputs": "Daily and total projections with an 80% range, pressure days and drivers",
             "limitations": "Needs ≈3 weeks of history; cannot anticipate one-off events."},
            {"key": "copilot", "name": "Ask GroupWise", "type": "LLM explanation layer",
             "version": "grounded-1.0",
             "method": "Intent detection → computed facts → LLM wording with fact citations → numeric grounding "
                       "check; deterministic answer when the LLM is unavailable or fails the check",
             "inputs": "The user's question and facts computed from the group's data",
             "outputs": "Answer with cited evidence, labelled as fact / prediction / assumption / recommendation",
             "limitations": "Answers only about the current group's shared finances; no investment, loan or tax advice."},
        ],
        "deterministic": [
            {"name": "Balance engine", "method": "Exact integer (paisa) ledger: paid − share ± settlements"},
            {"name": "Debt simplification", "method": "Greedy minimum cash-flow, ≤ n − 1 transfers"},
            {"name": "Spending intelligence", "method": "Period comparison + driver decomposition"},
            {"name": "Goal planner", "method": "Linear projection + bootstrap Monte-Carlo simulation"},
            {"name": "What-If simulator", "method": "Scenario arithmetic on the forecast baseline"},
            {"name": "Health indicator", "method": "Transparent weighted formula (prototype)"},
        ],
    }
