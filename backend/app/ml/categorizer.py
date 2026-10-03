"""AI Feature 1 — Smart expense categorization.

Model: TF-IDF (word 1–2 grams + character 2–5 grams) → multinomial logistic regression,
predicting one of ~34 subcategories; category and expense type follow from the taxonomy.

Why this model: expense descriptions are short, noisy, often Banglish, and full of merchant
names. Character n-grams handle typos/transliteration, word n-grams give human-readable
explanations ("signals"), and logistic regression gives calibrated-enough probabilities to
drive a "please confirm" UX when the model is unsure. It trains in seconds on CPU.

Evaluation is done on a held-out set built from merchants *and* phrasings that never appear in
training (see build_corpus), so reported accuracy reflects generalization, not memorization.
"""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.pipeline import FeatureUnion, Pipeline

from ..synthetic.catalog import CATALOG, MONTHS, PEOPLE, merchant_subcategories
from .taxonomy import SUBCATEGORIES, get_subcategory
from .text import detect_merchant, normalize_for_model

MODEL_NAME = "expense-categorizer"
MODEL_VERSION = "tfidf-logreg-1.1"
LOW_CONFIDENCE = 0.45
MERCHANT_PRIOR_WEIGHT = 3.0  # known-merchant knowledge base boosts its usual subcategories
_MERCHANT_SUBS = merchant_subcategories()


@dataclass
class CorpusSplit:
    train: list[tuple[str, str]]
    test: list[tuple[str, str]]


def _fill(template: str, merchant: str, rng: random.Random) -> str:
    return template.format(m=merchant, month=rng.choice(MONTHS), person=rng.choice(PEOPLE))


def _variants(text: str, rng: random.Random) -> list[str]:
    out = [text]
    r = rng.random()
    if r < 0.35:
        out.append(text.lower())
    elif r < 0.55:
        out.append(f"{text} {rng.choice([120, 250, 380, 850, 1200, 2450, 4800])}")
    elif r < 0.7:
        words = text.split()
        idx = rng.randrange(len(words))
        w = words[idx]
        if len(w) > 4:  # simulate a typo
            cut = rng.randrange(1, len(w) - 1)
            words[idx] = w[:cut] + w[cut + 1:]
            out.append(" ".join(words))
    return out


def build_corpus(seed: int = 42, holdout_frac: float = 0.25) -> CorpusSplit:
    """Synthetic labeled corpus with a strict split: held-out merchants and held-out templates
    are only ever used for testing."""
    rng = random.Random(seed)
    train: list[tuple[str, str]] = []
    test: list[tuple[str, str]] = []
    for label, spec in CATALOG.items():
        merchants = spec["merchants"][:]
        templates = spec["templates"][:]
        rng.shuffle(merchants)
        rng.shuffle(templates)
        n_m_test = max(1, round(len(merchants) * holdout_frac)) if len(merchants) >= 3 else 0
        n_t_test = max(1, round(len(templates) * holdout_frac))
        m_test, m_train = merchants[:n_m_test], merchants[n_m_test:]
        t_test, t_train = templates[:n_t_test], templates[n_t_test:]

        def gen(tmpls: list[str], merchs: list[str], per_template: int) -> list[str]:
            texts = []
            for t in tmpls:
                if "{m}" in t:
                    for m in rng.sample(merchs, min(per_template, len(merchs))):
                        texts.append(_fill(t, m, rng))
                else:
                    texts.append(_fill(t, merchs[0] if merchs else "", rng))
            return texts

        train_texts = gen(t_train, m_train, 4) + [m for m in m_train]
        test_texts = gen(t_test, merchants, 2) + gen([t for t in t_train if "{m}" in t], m_test, 1) + m_test
        for t in train_texts:
            train.extend((v, label) for v in _variants(t, rng))
        for t in test_texts:
            test.append((t if rng.random() > 0.3 else t.lower(), label))
    rng.shuffle(train)
    return CorpusSplit(train=train, test=test)


class ExpenseCategorizer:
    def __init__(self) -> None:
        self.pipeline: Pipeline | None = None
        self.classes_: list[str] = []
        self._n_word = 0

    def fit(self, texts: list[str], labels: list[str]) -> ExpenseCategorizer:
        self.pipeline = Pipeline(
            [
                (
                    "features",
                    FeatureUnion(
                        [
                            ("word", TfidfVectorizer(ngram_range=(1, 2), token_pattern=r"(?u)\b\w[\w']*\b", sublinear_tf=True)),
                            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)),
                        ]
                    ),
                ),
                ("clf", LogisticRegression(C=12.0, max_iter=3000)),
            ]
        )
        self.pipeline.fit([normalize_for_model(t) for t in texts], labels)
        self.classes_ = list(self.pipeline.named_steps["clf"].classes_)
        self._n_word = len(self.pipeline.named_steps["features"].transformer_list[0][1].vocabulary_)
        return self

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        assert self.pipeline is not None
        return self.pipeline.predict_proba([normalize_for_model(t) for t in texts])

    def predict(self, text: str, use_merchant_prior: bool = True) -> dict:
        probs = self.predict_proba([text])[0]
        merchant = detect_merchant(text)
        prior_used = False
        if use_merchant_prior and merchant in _MERCHANT_SUBS:
            boost = np.array([MERCHANT_PRIOR_WEIGHT if c in _MERCHANT_SUBS[merchant] else 1.0 for c in self.classes_])
            probs = probs * boost / float((probs * boost).sum())
            prior_used = True
        order = np.argsort(probs)[::-1]
        best = self.classes_[order[0]]
        sub = get_subcategory(best)
        confidence = float(probs[order[0]])
        alternatives = [
            {
                "subcategory": self.classes_[i],
                "label": get_subcategory(self.classes_[i]).label,
                "category": get_subcategory(self.classes_[i]).category,
                "probability": round(float(probs[i]), 3),
            }
            for i in order[1:4]
        ]
        return {
            "subcategory": sub.key,
            "subcategory_label": sub.label,
            "category": sub.category,
            "expense_type": sub.expense_type,
            "confidence": round(confidence, 3),
            "needs_confirmation": confidence < LOW_CONFIDENCE,
            "alternatives": alternatives,
            "signals": self._signals(text, order[0]),
            "known_merchant": merchant if prior_used else None,
            "model": {"name": MODEL_NAME, "version": MODEL_VERSION},
        }

    def _signals(self, text: str, class_idx: int) -> list[str]:
        """Words that pushed the prediction toward the chosen class (linear contribution)."""
        assert self.pipeline is not None
        feats = self.pipeline.named_steps["features"]
        word_vec: TfidfVectorizer = feats.transformer_list[0][1]
        x = word_vec.transform([normalize_for_model(text)])
        coef = self.pipeline.named_steps["clf"].coef_[class_idx][: self._n_word]
        contrib = x.multiply(coef).tocoo()
        names = word_vec.get_feature_names_out()
        pairs = sorted(((v, names[j]) for j, v in zip(contrib.col, contrib.data) if v > 0), reverse=True)
        out: list[str] = []
        for _, name in pairs:
            if not any(name in o or o in name for o in out):
                out.append(name)
            if len(out) == 3:
                break
        return out


def evaluate(model: ExpenseCategorizer, test: list[tuple[str, str]]) -> dict:
    texts = [t for t, _ in test]
    y_true = [y for _, y in test]
    probs = model.predict_proba(texts)
    y_pred = [model.classes_[i] for i in probs.argmax(axis=1)]
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    cat_true = [SUBCATEGORIES[y].category for y in y_true]
    cat_pred = [SUBCATEGORIES[y].category for y in y_pred]
    cp, cr, cf, _ = precision_recall_fscore_support(cat_true, cat_pred, average="macro", zero_division=0)
    conf = probs.max(axis=1)
    confident = conf >= LOW_CONFIDENCE
    acc_conf = accuracy_score(np.array(y_true)[confident], np.array(y_pred)[confident]) if confident.any() else 0.0
    return {
        "n_test": len(test),
        "subcategory": {"accuracy": round(accuracy_score(y_true, y_pred), 4), "precision_macro": round(p, 4),
                        "recall_macro": round(r, 4), "f1_macro": round(f, 4)},
        "category": {"accuracy": round(accuracy_score(cat_true, cat_pred), 4), "precision_macro": round(cp, 4),
                     "recall_macro": round(cr, 4), "f1_macro": round(cf, 4),
                     "f1_weighted": round(f1_score(cat_true, cat_pred, average="weighted", zero_division=0), 4)},
        "confident_share": round(float(confident.mean()), 4),
        "accuracy_when_confident": round(float(acc_conf), 4),
        "low_confidence_threshold": LOW_CONFIDENCE,
    }


_lock = threading.Lock()
_model: ExpenseCategorizer | None = None


def get_categorizer(extra_examples: list[tuple[str, str]] | None = None, retrain: bool = False) -> ExpenseCategorizer:
    """Process-wide model, trained on the synthetic corpus plus any human corrections."""
    global _model
    with _lock:
        if _model is None or retrain:
            corpus = build_corpus()
            data = corpus.train + corpus.test  # production model uses all synthetic data
            for text, label in extra_examples or []:
                if label in SUBCATEGORIES:
                    data.extend([(text, label)] * 3)  # human corrections weigh more
            texts, labels = zip(*data)
            _model = ExpenseCategorizer().fit(list(texts), list(labels))
        return _model
