"""The survey analysis script reads a Google Forms export correctly (made-up rows, used only to test the code)."""
import csv
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "research" / "analyze_survey.py"
spec = importlib.util.spec_from_file_location("analyze_survey", SCRIPT)
analyze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze)

HEADER = ["Timestamp", "Q0. I am 18 or older and agree to take part", "Q1. Which best describes you?",
          "Q2. How often do you share costs with a group?", "Q4. How do you usually pay your share?",
          "Q5. How does your group keep track?", "Q6. How long does it take to get your money back?",
          "Q7. How much money did you lose?", "Q11. Has your group tried to save together?",
          "Q12. Which of these would you actually use? (choose up to 3)", "Q13. How likely inside your wallet?"]
ROWS = [  # test fixtures only, not survey data
    ["t", "Yes, I agree", "University student", "A few times a week", "bKash, Cash", "From memory", "4–7 days",
     "Less than ৳500", "Yes, but we gave up", "Settle up with one tap from my wallet, A shared savings pocket for a group goal", "5"],
    ["t", "Yes, I agree", "University student", "A few times a month", "Cash", "A splitting app", "Same day",
     "Nothing", "Yes, and we reached it on time", "Settle up with one tap from my wallet", "3"],
    ["t", "", "Other", "Almost every day", "Nagad", "Nobody tracks it", "Often never", "Not sure", "", "", "1"],
]


def test_survey_summary(tmp_path):
    f = tmp_path / "responses.csv"
    with f.open("w", encoding="utf-8", newline="") as h:
        csv.writer(h).writerows([HEADER, *ROWS])
    resp = analyze.load(f)
    assert len(resp) == 2                                   # the row without consent is ignored
    m = analyze.summarize(resp)
    assert m["share_weekly_or_more"]["pct"] == 50.0
    assert m["settle_with_mobile_wallet"]["count"] == 1
    assert m["wait_more_than_3_days"]["count"] == 1 and m["typical_wait"] in analyze.Q6_ORDER
    assert m["goal_late_short_or_abandoned"] == {"pct": 50.0, "count": 1, "n": 2, "moe": 69.3}
    assert m["feature_demand"][0] == {"feature": "Settle up with one tap from my wallet", "pct": 100.0, "count": 2,
                                      "n": 2, "moe": 0.0}
    assert m["use_inside_wallet"]["mean_1_to_5"] == 4.0
    assert "Survey results (2 respondents)" in analyze.to_markdown(m)
