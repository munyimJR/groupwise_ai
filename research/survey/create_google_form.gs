/**
 * Creates the GroupWise AI user survey as a Google Form in your Google Drive.
 *
 * How to use (about 2 minutes):
 *   1. Open https://script.google.com and click "New project".
 *   2. Replace the editor contents with this file and click Save.
 *   3. Select the function "createSurvey" and click Run. Approve the permission prompt (it only creates a form).
 *   4. Open "Execution log": it prints the link to share and the link to edit the form.
 *   5. In the form's Responses tab, link a Google Sheet. Later: File > Download > CSV, then run
 *      `python research/analyze_survey.py <downloaded.csv>`.
 *
 * The question codes (Q0., Q1., ...) must stay at the start of each title: the analysis script relies on them.
 */
function createSurvey() {
  var form = FormApp.create('GroupWise AI — how students share money (3 min, anonymous)');
  form.setDescription(
    'This anonymous survey takes about 3 minutes. It is for a student hackathon project (GroupWise AI, Daffodil ' +
    'International University) about how friends, flat mates and travel groups share money. We do not collect names, ' +
    'phone numbers or email addresses, and results are reported only as totals. You can stop at any time.');
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);
  form.setShowLinkToRespondAgain(false);
  form.setProgressBar(true);

  form.addMultipleChoiceItem().setTitle('Q0. I am 18 or older and agree to take part')
    .setChoiceValues(['Yes, I agree']).setRequired(true);

  form.addPageBreakItem().setTitle('About you');
  single(form, 'Q1. Which best describes you?',
    ['University student', 'Recent graduate (up to 2 years)', 'Working professional', 'Other'], true);
  single(form, 'Q2. How often do you share costs with a group (meals, rides, rent, trips, events)?',
    ['Almost every day', 'A few times a week', 'About once a week', 'A few times a month', 'Rarely or never'], true);
  multi(form, 'Q3. Which groups do you share money with?',
    ['Roommates or flat mates', 'Friends eating out', 'Trip or tour groups', 'Club or event teams',
     'Class project groups', 'Family', 'Other']);

  form.addPageBreakItem().setTitle('How you handle it today');
  multi(form, 'Q4. How do you usually pay your share or pay friends back?',
    ['Cash', 'bKash', 'Nagad', 'upay', 'Rocket', 'Bank transfer or card', 'Other']);
  single(form, 'Q5. How does your group keep track of who owes whom?',
    ['Nobody tracks it', 'From memory', 'Chat messages (Messenger, WhatsApp)', 'Notes or a spreadsheet',
     'A splitting app', 'Other'], true);
  single(form, 'Q6. When you pay for the group, how long does it usually take to get your money back?',
    ['Same day', '1–3 days', '4–7 days', '1–2 weeks', 'More than 2 weeks', 'Often never'], true);
  single(form, 'Q7. In the last 6 months, about how much money did you lose because someone never paid you back?',
    ['Nothing', 'Less than ৳500', '৳500–2,000', '৳2,000–5,000', 'More than ৳5,000', 'Not sure'], true);
  single(form, 'Q8. In the last 6 months, has shared money caused an argument or an awkward moment in your group?',
    ['Never', 'Once', 'A few times', 'Often'], true);
  single(form, 'Q9. Does one person in your group usually end up paying first for most things?',
    ['Yes, usually me', 'Yes, someone else', 'No, it is fairly even', 'Not sure'], true);
  single(form, 'Q10. Do you know roughly how much your group spent last month, and on what?',
    ['Yes, quite exactly', 'Roughly', 'Not really', 'No idea'], true);
  single(form, 'Q11. Has your group tried to save together for something (a trip, an event, a shared purchase)?',
    ['Yes, and we reached it on time', 'Yes, but we were late or short', 'Yes, but we gave up', 'No, never tried'], true);

  form.addPageBreakItem().setTitle('What would help');
  var q12 = multi(form, 'Q12. Which of these would you actually use? (choose up to 3)',
    ['Settle up with one tap from my wallet', 'Import my wallet transactions automatically',
     'A shared savings pocket for a group goal', 'Alerts for unusual or duplicate expenses',
     "A forecast of next week's group spending", 'Automatic categories for expenses',
     'A fairness view of who pays first', 'Asking questions in plain language']);
  q12.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(3).build());
  form.addScaleItem()
    .setTitle('Q13. How likely would you be to use group expense and savings features inside the wallet app you already use?')
    .setBounds(1, 5).setLabels('Not at all likely', 'Very likely').setRequired(true);
  single(form, 'Q14. Which mobile wallet do you use most?',
    ['bKash', 'Nagad', 'upay', 'Rocket', 'Other', "I don't use a mobile wallet"], true);
  form.addParagraphTextItem()
    .setTitle('Q15. (Optional) What is the most annoying thing about sharing money with friends?')
    .setHelpText('Please do not write names or phone numbers.');

  Logger.log('Share this link:  ' + form.getPublishedUrl());
  Logger.log('Edit the form:    ' + form.getEditUrl());
}

function single(form, title, options, required) {
  return form.addMultipleChoiceItem().setTitle(title).setChoiceValues(options).setRequired(!!required);
}

function multi(form, title, options) {
  return form.addCheckboxItem().setTitle(title).setChoiceValues(options);
}
