"""Intent detection for Ask GroupWise.

High-precision rules first, then a small TF-IDF + logistic-regression classifier trained on
example questions. Out-of-scope requests (investment/loan advice, prompt-injection attempts,
unrelated tasks) are recognised explicitly so they never reach the LLM as financial questions.
"""
from __future__ import annotations

import re
import threading

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

INTENTS = {
    "spending_change": "Why spending changed",
    "category_breakdown": "Where the money goes",
    "goal_status": "Goal outlook",
    "goal_actions": "How to reach the goal",
    "forecast": "What's coming next",
    "dynamics": "Who pays what",
    "balances": "Who owes whom",
    "anomalies": "Unusual expenses",
    "health": "Financial health",
    "overview": "Group overview",
    "greeting": "Greeting",
    "advice_out_of_scope": "Out of scope (regulated advice)",
    "out_of_scope": "Out of scope",
    "injection": "Unsafe instruction",
}

EXAMPLES: dict[str, list[str]] = {
    "spending_change": ["why did our spending increase this month", "why are we spending more", "what changed in our spending",
                        "why did expenses go up", "spending went up why", "why is our food spending higher",
                        "explain the increase in spending", "did we spend more than last month", "why did costs rise",
                        "why are expenses lower this month", "compare this month with last month"],
    "category_breakdown": ["which category increased the most", "where is our money going", "what do we spend the most on",
                           "breakdown by category", "biggest spending category", "top categories", "how much on food",
                           "how much did we spend on transport", "category wise spending", "what are we spending on"],
    "goal_status": ["can we afford our trip", "will we reach our goal", "are we on track for the trip",
                    "how is our savings goal going", "can we make it to cox's bazar", "goal progress",
                    "how much have we saved", "will we have enough money for the trip", "is the trip affordable"],
    "goal_actions": ["what can we change to reach our goal", "how can we save more for the trip",
                     "what should we cut to reach the target", "how do we close the gap", "how to reach our goal faster",
                     "what should we do to afford the trip", "how much should each of us contribute",
                     "what can we do to save money"],
    "forecast": ["what caused our financial pressure", "how much will we spend next week", "predict next week",
                 "forecast our spending", "what should we expect next week", "upcoming expenses",
                 "when will spending be highest", "is next week going to be expensive", "financial pressure ahead"],
    "dynamics": ["who is paying most of the group expenses", "who pays the most", "is payment fair", "who covers the bills",
                 "who pays upfront", "who is slow to pay back", "how long do people take to settle",
                 "is anyone paying too much", "payment balance in the group"],
    "balances": ["who owes whom", "how much do i owe", "settle up", "what is my balance", "who owes me money",
                 "how do we settle", "outstanding balances", "how much does rony owe"],
    "anomalies": ["anything unusual", "any suspicious expenses", "unusual transactions", "weird expense",
                  "any mistakes in expenses", "duplicate expense", "flagged expenses", "strange spending"],
    "health": ["how healthy are our finances", "what is our financial health score", "health score", "are we doing well",
               "how is the group doing financially", "rate our finances"],
    "overview": ["summary", "give me an overview", "how are we doing", "tell me about this group", "status update",
                 "what should i know", "quick summary of our finances"],
    "greeting": ["hi", "hello", "hey", "good morning", "assalamualaikum", "thanks", "thank you"],
}

_RULES: list[tuple[str, re.Pattern]] = [
    ("injection", re.compile(r"ignore (all |the |your )?(previous|prior|above) (instructions|rules)|system prompt|"
                             r"you are now|jailbreak|developer mode|reveal (your|the) (prompt|instructions)", re.I)),
    ("advice_out_of_scope", re.compile(r"\b(invest|investment|stock|stocks|share market|crypto|bitcoin|forex|loan|"
                                       r"mortgage|interest rate|tax|insurance policy|dps|fdr|savings certificate)\b", re.I)),
    ("anomalies", re.compile(r"unusual|suspicious|weird|strange|anomal|fraud|duplicate|mistake|flagged", re.I)),
    ("balances", re.compile(r"\bowe|owes|owed|settle|balance\b|pay (me|back)|outstanding", re.I)),
    ("health", re.compile(r"health|score", re.I)),
    ("dynamics", re.compile(r"who (is |are )?(pay|paying|paid|covers|covering)|fair(ly)?\b|upfront|slow to pay|"
                            r"paying (the )?most", re.I)),
    ("goal_actions", re.compile(r"(what|how) (can|should|do) (we|i).*(change|cut|save|reach|close|afford|contribute)|"
                                r"close the gap|reach (the|our) (goal|target)", re.I)),
    ("forecast", re.compile(r"next (week|month|7 days)|forecast|predict|pressure|upcoming|coming week|expect", re.I)),
    ("goal_status", re.compile(r"goal|trip|afford|target|on track|saved|saving", re.I)),
    ("spending_change", re.compile(r"why .*(increase|went up|higher|more|rise|rose|drop|lower|decrease)|"
                                   r"(increase|decrease) in (our )?spending", re.I)),
    ("category_breakdown", re.compile(r"categor|where .*money|breakdown|spend (the )?most on|how much (did we )?spend on",
                                      re.I)),
]

_lock = threading.Lock()
_model: Pipeline | None = None


def _get_model() -> Pipeline:
    global _model
    with _lock:
        if _model is None:
            texts, labels = [], []
            for intent, examples in EXAMPLES.items():
                texts += examples
                labels += [intent] * len(examples)
            _model = Pipeline([
                ("f", FeatureUnion([("w", TfidfVectorizer(ngram_range=(1, 2))),
                                    ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)))])),
                ("clf", LogisticRegression(C=10, max_iter=2000)),
            ]).fit(texts, labels)
        return _model


def classify(question: str) -> dict:
    q = question.strip()
    for intent, pattern in _RULES:
        if pattern.search(q):
            return {"name": intent, "label": INTENTS[intent], "confidence": 0.95, "method": "rules"}
    model = _get_model()
    probs = model.predict_proba([q.lower()])[0]
    idx = int(probs.argmax())
    intent = model.classes_[idx]
    conf = float(probs[idx])
    if conf < 0.25:
        intent, conf = "overview", conf
    return {"name": intent, "label": INTENTS[intent], "confidence": round(conf, 2), "method": "classifier"}
