/**
 * satoru-config - tasks
 *
 * The follow-up engine. This is the reason the programme is on CHT rather
 * than KoBoToolbox: KoBo records that a referral happened, CHT remembers that
 * it is still owed and puts it in front of the right intern on the right day.
 *
 * Each task answers four questions:
 *   appliesTo / appliesToType  what does it hang off?
 *   appliesIf                  should it exist at all?
 *   events                     when is it due, how wide is the window?
 *   resolvedIf                 what makes it disappear?
 *
 * `Utils` is a global injected by the rules engine.
 */

const {
  CONFIG,
  FORMS,
  CONTACT_TYPES,
  getField,
  reportsSince,
  reportsOf,
  latestReport,
  addDays,
  isActive,
  isExited,
  stage1NeedsFollowUp,
  stage1FlagCount,
  stage2DoneAfter,
  stage2NeedsReferral,
  isUrgent,
  isSafeguarding,
  followUpAttemptsSince,
  appointmentBooked,
  nextReviewDue,
} = require('./nools-extras');

const PRIORITY_HIGH = { level: 'high', label: 'task.priority.high' };

module.exports = [

  // ---------------------------------------------------------------------
  // 1. URGENT SAME-DAY ESCALATION
  //    PHQ-9 item 9 endorsed, or a critical capillary glucose value.
  // ---------------------------------------------------------------------
  {
    name: 'satoru.urgent-escalation',
    icon: 'icon-risk',
    title: 'task.urgent_escalation.title',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    appliesIf: (contact, report) => isUrgent(report),
    resolvedIf: (contact, report, event, dueDate) =>
      reportsSince(contact, [FORMS.FOLLOW_UP, FORMS.REFERRAL],
        report.reported_date)
        .some((r) => r.reported_date
          <= addDays(dueDate, event.end + 1).getTime()),
    events: [{
      id: 'urgent-24h',
      start: 0,
      end: CONFIG.URGENT_ESCALATION_DAYS,
      dueDate: (event, contact, report) => new Date(report.reported_date),
    }],
    priority: PRIORITY_HIGH,
    actions: [{
      type: 'report',
      form: FORMS.FOLLOW_UP,
      label: 'task.urgent_escalation.action',
      modifyContent: (content, contact, report) => {
        content.trigger = 'urgent_escalation';
        content.source_report_uuid = report._id;
      },
    }],
  },

  // ---------------------------------------------------------------------
  // 2. SAFEGUARDING ESCALATION (EASI positive)
  //    Separate task, not an else-branch, because the response pathway is
  //    different: safeguarding lead, not clinical supervisor. A participant
  //    with both suicidal ideation and a positive EASI gets both tasks.
  // ---------------------------------------------------------------------
  {
    name: 'satoru.safeguarding-escalation',
    icon: 'icon-risk',
    title: 'task.safeguarding.title',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    appliesIf: (contact, report) => isSafeguarding(report),
    resolvedIf: (contact, report, event, dueDate) =>
      reportsSince(contact, FORMS.FOLLOW_UP, report.reported_date)
        .some((r) => r.reported_date
          <= addDays(dueDate, event.end + 1).getTime()),
    events: [{
      id: 'safeguarding-72h',
      start: 0,
      end: CONFIG.SAFEGUARDING_ESCALATION_DAYS,
      dueDate: (event, contact, report) => new Date(report.reported_date),
    }],
    priority: PRIORITY_HIGH,
    actions: [{
      type: 'report',
      form: FORMS.FOLLOW_UP,
      label: 'task.safeguarding.action',
      modifyContent: (content, contact, report) => {
        content.trigger = 'safeguarding';
        content.source_report_uuid = report._id;
      },
    }],
  },

  // ---------------------------------------------------------------------
  // 3. STAGE 2 ASSESSMENT DUE
  //    Raised the moment Stage 1 says "refer" and Stage 2 was not done at
  //    the same camp. Open for the full window so any camp team can close it.
  // ---------------------------------------------------------------------
  {
    name: 'satoru.stage2-due',
    icon: 'icon-healthcare-assessment',
    title: 'task.stage2_due.title',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE1],
    appliesIf: (contact, report) =>
      stage1NeedsFollowUp(report) && !isExited(contact),
    resolvedIf: (contact, report) => stage2DoneAfter(contact, report),
    events: [{
      id: 'stage2-window',
      start: 0,
      end: CONFIG.STAGE2_WINDOW_DAYS,
      dueDate: (event, contact, report) => new Date(report.reported_date),
    }],
    // Two independent positive domains is a materially different pre-test
    // probability from one, and should be seen first in a long task list.
    priority: (contact, report) =>
      (stage1FlagCount(report) >= 2 ? PRIORITY_HIGH : null),
    actions: [{
      type: 'report',
      form: FORMS.STAGE2,
      label: 'task.stage2_due.action',
      modifyContent: (content, contact, report) => {
        content.stage1_report_uuid = report._id;
        content.stage1_flag_count = stage1FlagCount(report);
        content.camp_code = getField(report, 'g_context.camp_code');
      },
    }],
  },

  // ---------------------------------------------------------------------
  // 4. LEAD PURSUIT - three chase attempts at day 3, 10 and 21
  //    One definition, three events. Each event clears once the matching
  //    attempt is logged; all three clear if an appointment gets booked or
  //    Stage 2 happens.
  // ---------------------------------------------------------------------
  {
    name: 'satoru.lead-pursuit',
    icon: 'icon-followup-general',
    title: 'task.lead_pursuit.title',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE1],
    appliesIf: (contact, report) =>
      stage1NeedsFollowUp(report) && !isExited(contact),
    resolvedIf: (contact, report, event) => {
      if (stage2DoneAfter(contact, report)) { return true; }
      if (appointmentBooked(contact, report.reported_date)) { return true; }
      const attemptIndex = CONFIG.FOLLOW_UP_DAYS.indexOf(event.days) + 1;
      return followUpAttemptsSince(contact, report.reported_date)
        >= attemptIndex;
    },
    events: CONFIG.FOLLOW_UP_DAYS.map((days, i) => ({
      id: `lead-pursuit-${i + 1}`,
      days,
      start: 2,
      end: 6,
    })),
    actions: [{
      type: 'report',
      form: FORMS.FOLLOW_UP,
      label: 'task.lead_pursuit.action',
      modifyContent: (content, contact, report) => {
        content.trigger = 'stage1_referral';
        content.source_report_uuid = report._id;
        content.suggested_attempt_number =
          followUpAttemptsSince(contact, report.reported_date) + 1;
      },
    }],
  },

  // ---------------------------------------------------------------------
  // 5. BOOKED APPOINTMENT REMINDER
  // ---------------------------------------------------------------------
  {
    name: 'satoru.appointment-reminder',
    icon: 'icon-healthcare-assessment',
    title: 'task.appointment.title',
    appliesTo: 'reports',
    appliesToType: [FORMS.FOLLOW_UP],
    appliesIf: (contact, report) =>
      getField(report, 'g_fu.outcome') === 'scheduled'
      && !!getField(report, 'g_fu.appointment_date')
      && !isExited(contact),
    resolvedIf: (contact, report) =>
      reportsSince(contact, FORMS.STAGE2, report.reported_date).length > 0,
    events: [{
      id: 'appointment-day',
      start: 2,
      end: 7,
      dueDate: (event, contact, report) =>
        new Date(getField(report, 'g_fu.appointment_date')),
    }],
    actions: [{
      type: 'report',
      form: FORMS.STAGE2,
      label: 'task.appointment.action',
    }],
  },

  // ---------------------------------------------------------------------
  // 6. REFERRAL OUTCOME CAPTURE
  //    Did the participant actually reach the memory clinic? This is the
  //    loop a form collector cannot close.
  // ---------------------------------------------------------------------
  {
    name: 'satoru.referral-outcome',
    icon: 'icon-healthcare-referral',
    title: 'task.referral_outcome.title',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    appliesIf: (contact, report) =>
      stage2NeedsReferral(report) && !isExited(contact),
    resolvedIf: (contact, report) =>
      reportsSince(contact, FORMS.REFERRAL, report.reported_date)
        .some((r) => getField(r, 'g_ref.referral_closed') === 'yes'),
    events: [{
      id: 'referral-confirm',
      days: 14,
      start: 7,
      end: CONFIG.REFERRAL_CONFIRM_DAYS,
    }],
    actions: [{
      type: 'report',
      form: FORMS.REFERRAL,
      label: 'task.referral_outcome.action',
      modifyContent: (content, contact, report) => {
        content.source_report_uuid = report._id;
        content.facility = getField(report, 'g_disposition.referral_facility');
        content.disposition = getField(report, 'g_disposition.disposition');
      },
    }],
  },

  // ---------------------------------------------------------------------
  // 7. LONGITUDINAL REVIEW DUE
  //    Hangs off the CONTACT, not a report, which is what makes it recur for
  //    the life of the cohort. Report-anchored tasks fire once per report.
  // ---------------------------------------------------------------------
  {
    name: 'satoru.longitudinal-review',
    icon: 'icon-followup-general',
    title: 'task.review.title',
    appliesTo: 'contacts',
    appliesToType: [CONTACT_TYPES.PARTICIPANT],
    appliesIf: (contact) => isActive(contact) && !!nextReviewDue(contact),
    resolvedIf: (contact, report, event, dueDate) => {
      const since = addDays(dueDate, -event.start).getTime();
      return reportsSince(contact, [FORMS.STAGE2, FORMS.REVIEW], since)
        .length > 0;
    },
    events: [{
      id: 'review-due',
      start: 30,
      end: 60,
      dueDate: (event, contact) => nextReviewDue(contact),
    }],
    actions: [{
      type: 'report',
      form: FORMS.REVIEW,
      label: 'task.review.action',
    }],
  },

  // ---------------------------------------------------------------------
  // 8. STAGE 1 NOT YET DONE
  //    Catches camp-day registrations that were never followed by a
  //    screening - the commonest data gap in a busy camp.
  // ---------------------------------------------------------------------
  {
    name: 'satoru.stage1-missing',
    icon: 'icon-healthcare-assessment',
    title: 'task.stage1_missing.title',
    appliesTo: 'contacts',
    appliesToType: [CONTACT_TYPES.PARTICIPANT],
    appliesIf: (contact) =>
      isActive(contact) && reportsOf(contact, FORMS.STAGE1).length === 0,
    resolvedIf: (contact) => reportsOf(contact, FORMS.STAGE1).length > 0,
    events: [{
      id: 'stage1-missing',
      start: 0,
      end: CONFIG.STAGE1_MISSING_DAYS,
      dueDate: (event, contact) =>
        new Date((contact.contact && contact.contact.reported_date)
          || Utils.now()),
    }],
    actions: [{
      type: 'report',
      form: FORMS.STAGE1,
      label: 'task.stage1_missing.action',
    }],
  },
];

// Keep the linter honest about helpers imported for future use.
void latestReport;
