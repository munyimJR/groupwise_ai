# GroupWise AI — user survey (about 3 minutes)

Anonymous survey to measure how students share money today. Each question title starts with its code
(`Q1.`, `Q2.` …) so `research/analyze_survey.py` can read the Google Forms export. Keep the codes if you edit wording.

**Intro text (shown at the top of the form)**

> This anonymous survey takes about 3 minutes. It is for a student hackathon project (GroupWise AI, Daffodil
> International University) about how friends, flat mates and travel groups share money. We do not collect names,
> phone numbers or email addresses, and results are reported only as totals. You can stop at any time.

| Code | Question | Type | Options |
|---|---|---|---|
| Q0 | I am 18 or older and agree to take part | Required, single choice | Yes, I agree |
| **A. About you** | | | |
| Q1 | Which best describes you? | Single choice | University student · Recent graduate (up to 2 years) · Working professional · Other |
| Q2 | How often do you share costs with a group (meals, rides, rent, trips, events)? | Single choice | Almost every day · A few times a week · About once a week · A few times a month · Rarely or never |
| Q3 | Which groups do you share money with? | Checkboxes | Roommates or flat mates · Friends eating out · Trip or tour groups · Club or event teams · Class project groups · Family · Other |
| **B. How you handle it today** | | | |
| Q4 | How do you usually pay your share or pay friends back? | Checkboxes | Cash · bKash · Nagad · upay · Rocket · Bank transfer or card · Other |
| Q5 | How does your group keep track of who owes whom? | Single choice | Nobody tracks it · From memory · Chat messages (Messenger, WhatsApp) · Notes or a spreadsheet · A splitting app · Other |
| Q6 | When you pay for the group, how long does it usually take to get your money back? | Single choice | Same day · 1–3 days · 4–7 days · 1–2 weeks · More than 2 weeks · Often never |
| Q7 | In the last 6 months, about how much money did you lose because someone never paid you back? | Single choice | Nothing · Less than ৳500 · ৳500–2,000 · ৳2,000–5,000 · More than ৳5,000 · Not sure |
| Q8 | In the last 6 months, has shared money caused an argument or an awkward moment in your group? | Single choice | Never · Once · A few times · Often |
| Q9 | Does one person in your group usually end up paying first for most things? | Single choice | Yes, usually me · Yes, someone else · No, it is fairly even · Not sure |
| Q10 | Do you know roughly how much your group spent last month, and on what? | Single choice | Yes, quite exactly · Roughly · Not really · No idea |
| Q11 | Has your group tried to save together for something (a trip, an event, a shared purchase)? | Single choice | Yes, and we reached it on time · Yes, but we were late or short · Yes, but we gave up · No, never tried |
| **C. What would help** | | | |
| Q12 | Which of these would you actually use? (choose up to 3) | Checkboxes (max 3) | Settle up with one tap from my wallet · Import my wallet transactions automatically · A shared savings pocket for a group goal · Alerts for unusual or duplicate expenses · A forecast of next week's group spending · Automatic categories for expenses · A fairness view of who pays first · Asking questions in plain language |
| Q13 | How likely would you be to use group expense and savings features inside the wallet app you already use? | Linear scale 1–5 | 1 = Not at all likely … 5 = Very likely |
| Q14 | Which mobile wallet do you use most? | Single choice | bKash · Nagad · upay · Rocket · Other · I don't use a mobile wallet |
| Q15 | (Optional) What is the most annoying thing about sharing money with friends? | Paragraph | — |

## How each question maps to the judges' questions

| What we need to show | Questions |
|---|---|
| The problem is frequent and real for students | Q1, Q2, Q3 |
| Money already moves through mobile wallets (the MFS link) | Q4, Q14 |
| Current tracking is informal and causes delay, loss and friction | Q5, Q6, Q7, Q8, Q9 |
| Groups lack visibility and miss shared goals | Q10, Q11 |
| Demand for the specific solution, inside a wallet | Q12, Q13 |
