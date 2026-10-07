# User research kit

The Phase 1 judges asked for **real user evidence** instead of synthetic statistics only. This folder holds
everything needed to collect it quickly and honestly. The team runs it; nothing here contains invented results.

| Step | Time | What | Files |
|---|---|---|---|
| 1. Survey | 2–3 days | Anonymous 3-minute survey of DIU students (target **≥ 100 responses**, at least 30) | [survey/questions.md](survey/questions.md), [survey/create_google_form.gs](survey/create_google_form.gs) |
| 2. Interviews | 2 days | 5–8 short interviews for real stories and quotes | [interviews/interview_guide.md](interviews/interview_guide.md) |
| 3. Pilot | 2 weeks | 5–8 real groups use the deployed app; behavior measured automatically | [pilot/pilot_plan.md](pilot/pilot_plan.md), `backend/scripts/pilot_metrics.py` |
| 4. Analyze | 10 min | Turn the exports into report-ready tables | [analyze_survey.py](analyze_survey.py), `pilot_metrics.py --out research/results` |

## Quick start for the survey

1. Create the form: open <https://script.google.com>, paste `survey/create_google_form.gs`, run `createSurvey`,
   and copy the share link from the log.
2. Share it in class groups, department pages and hall groups. Ask people to forward it.
3. Export the answers: in the form's Responses tab, open the linked Sheet, then File → Download → CSV.
4. Analyze:

   ```bash
   python research/analyze_survey.py path/to/responses.csv
   ```

   This writes `research/results/survey_summary.md` and `.json`, ready to paste into the report and deck.

## Rules we follow

- **No invented numbers.** Until responses exist, the report says "survey in progress" and shows only the
  public (secondary) evidence in [docs/PROBLEM_EVIDENCE.md](../docs/PROBLEM_EVIDENCE.md).
- **Anonymous by design:** no names, phone numbers or emails are collected. Open answers are read by the team and
  never published with identifying details.
- **Honest reporting:** every percentage comes with its sample size and margin of error. A convenience sample of
  DIU students is described as exactly that.
- **Pilot data** stays in the project's own database, is reported only as totals, and is deleted within 30 days
  after the hackathon.
