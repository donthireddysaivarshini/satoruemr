/**
 * satoru-config - shared helpers
 *
 * Used by tasks.js, targets.js and contact-summary.templated.js.
 * cht-conf webpacks these files, so a syntax error here fails
 * `compile-app-settings` rather than breaking silently at runtime.
 *
 * Two rules for editing this file:
 *   1. Every field path below corresponds to a real group and field in
 *      forms/app/*.xlsx. If you rename a group in a form, grep for it here.
 *   2. Contact type ids must match app_settings/base_settings.json.
 */

const MS_IN_DAY = 24 * 60 * 60 * 1000;

const CONTACT_TYPES = {
  CAMP: 'screening_camp',
  PARTICIPANT: 'participant',
};

const FORMS = {
  STAGE1: 'stage1_screening',
  STAGE2: 'stage2_assessment',
  FOLLOW_UP: 'follow_up_contact',
  REFERRAL: 'referral_outcome',
  REVIEW: 'longitudinal_review',
};

/**
 * Programme timing. These are policy, not data. Change them here and every
 * task picks up the new value on the next compile.
 */
const CONFIG = {
  STAGE2_WINDOW_DAYS: 30,       // how long a Stage 1 referral stays open
  FOLLOW_UP_DAYS: [3, 10, 21],  // lead-pursuit chase schedule
  MAX_FOLLOW_UP_ATTEMPTS: 3,
  REFERRAL_CONFIRM_DAYS: 21,
  REVIEW_DAYS_COGNITIVE: 180,
  REVIEW_DAYS_ROUTINE: 365,
  REVIEW_DAYS_RE_REFER: 90,
  URGENT_ESCALATION_DAYS: 1,
  SAFEGUARDING_ESCALATION_DAYS: 3,
  STAGE1_MISSING_DAYS: 14,
};

// ---------------------------------------------------------------------------
// Generic accessors
// ---------------------------------------------------------------------------

/** Read a dot-path out of a report's `fields`. Returns null, never throws. */
function getField(report, path) {
  if (!report || !path) { return null; }
  return String(path).split('.').reduce(
    (acc, key) => (acc && acc[key] !== undefined ? acc[key] : null),
    report.fields
  );
}

/**
 * getField coerced to a number. XLSForm calculates arrive as strings, so every
 * numeric comparison must go through here. Returns null (not NaN) when absent,
 * so callers can distinguish "not recorded" from "zero".
 */
function num(report, path) {
  const raw = getField(report, path);
  if (raw === null || raw === '') { return null; }
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function isForm(report, formName) {
  return !!report && report.form === formName;
}

function reportsOf(contact, formName) {
  if (!contact || !contact.reports) { return []; }
  return contact.reports.filter((r) => r.form === formName);
}

function latestReport(contact, formName) {
  const all = reportsOf(contact, formName);
  if (!all.length) { return null; }
  return all.reduce((a, b) => (a.reported_date > b.reported_date ? a : b));
}

/** Reports of any of `formNames` submitted strictly after `since` (epoch ms). */
function reportsSince(contact, formNames, since) {
  if (!contact || !contact.reports) { return []; }
  const names = [].concat(formNames);
  return contact.reports.filter(
    (r) => names.indexOf(r.form) !== -1 && r.reported_date > since
  );
}

function daysBetween(fromMs, toMs) {
  return Math.floor((toMs - fromMs) / MS_IN_DAY);
}

function addDays(dateOrMs, days) {
  const d = new Date(dateOrMs);
  d.setDate(d.getDate() + days);
  return d;
}

// ---------------------------------------------------------------------------
// Contact predicates
//
// The rules engine already normalises contact type as
//   type === 'contact' ? contact_type : type
// before comparing against appliesToType, so tasks and targets do not need
// this. contact-summary and any custom check does.
// ---------------------------------------------------------------------------

function contactType(contact) {
  const c = contact && (contact.contact || contact);
  if (!c) { return null; }
  return c.type === 'contact' ? c.contact_type : (c.contact_type || c.type);
}

function isParticipant(contact) {
  return contactType(contact) === CONTACT_TYPES.PARTICIPANT;
}

function isCamp(contact) {
  return contactType(contact) === CONTACT_TYPES.CAMP;
}

/**
 * Age today, not age at registration.
 * `age` is captured once as an integer; CHT stamps `reported_date` on the
 * contact. A participant registered at 68 in 2026 is 71 in 2029, and the
 * profile must say so.
 */
function currentAge(contactDoc, nowMs) {
  if (!contactDoc || contactDoc.age === undefined || contactDoc.age === null) {
    return null;
  }
  const base = Number(contactDoc.age);
  if (!Number.isFinite(base)) { return null; }
  if (!contactDoc.reported_date) { return base; }
  const now = nowMs || Date.now();
  const elapsed = Math.floor(
    (now - contactDoc.reported_date) / (MS_IN_DAY * 365.25)
  );
  return base + Math.max(0, elapsed);
}

/**
 * Consent.
 * Participants registered before consent_given existed have no such field.
 * Treat missing as consented so Phase 1 data is not silently excluded; only an
 * explicit 'no' blocks the workflow.
 */
function hasConsent(contact) {
  const c = contact && (contact.contact || contact);
  return !c || c.consent_given !== 'no';
}

// ---------------------------------------------------------------------------
// Workflow state
// ---------------------------------------------------------------------------

const EXIT_OUTCOMES = ['deceased', 'moved', 'refused', 'done_elsewhere'];

/**
 * A participant leaves the active workflow when they die, move away, refuse
 * further assessment, or were assessed elsewhere. Every task checks this so
 * the team never chases a closed case. The record is kept, not deleted -
 * denominators need it.
 */
function isExited(contact) {
  const closed = reportsOf(contact, FORMS.FOLLOW_UP).some(
    (r) => EXIT_OUTCOMES.indexOf(getField(r, 'g_fu.outcome')) !== -1
  );
  if (closed) { return true; }
  const review = latestReport(contact, FORMS.REVIEW);
  return !!review && getField(review, 'g_rev.alive') === 'no';
}

function isActive(contact) {
  return hasConsent(contact) && !isExited(contact);
}

// ---- Stage 1 ----

function stage1Result(report) {
  return getField(report, 'g_outcome.stage1_result');
}

function stage1Referred(report) {
  return isForm(report, FORMS.STAGE1) && stage1Result(report) === 'refer';
}

/** A referral that still needs chasing: not done same-day at the camp. */
function stage1NeedsFollowUp(report) {
  return stage1Referred(report)
    && getField(report, 'g_outcome.stage2_same_day') !== 'yes';
}

function stage1FlagCount(report) {
  return num(report, 'g_outcome.stage1_flag_count') || 0;
}

// ---- Stage 2 ----

function stage2DoneAfter(contact, stage1Report) {
  return reportsSince(contact, FORMS.STAGE2, stage1Report.reported_date)
    .length > 0;
}

function stage2Disposition(report) {
  return getField(report, 'g_disposition.disposition');
}

function stage2NeedsReferral(report) {
  return getField(report, 'g_disposition.referral_needed') === 'yes';
}

function isUrgent(report) {
  return stage2Disposition(report) === 'urgent_same_day';
}

function isSafeguarding(report) {
  return num(report, 'g_easi.easi_positive') === 1;
}

function cognitiveFlag(report) {
  return num(report, 'g_disposition.cognitive_flag') === 1;
}

// ---- follow-up ----

function followUpAttemptsSince(contact, sinceMs) {
  return reportsSince(contact, FORMS.FOLLOW_UP, sinceMs).length;
}

function appointmentBooked(contact, sinceMs) {
  return reportsSince(contact, FORMS.FOLLOW_UP, sinceMs)
    .some((r) => getField(r, 'g_fu.outcome') === 'scheduled');
}

// ---- review scheduling ----

/**
 * When the next periodic review is due, based on the most recent encounter.
 * 90 days if the last review said re-refer, 180 if a cognitive flag was ever
 * raised at Stage 2, otherwise annual.
 */
function nextReviewDue(contact) {
  const review = latestReport(contact, FORMS.REVIEW);
  const stage2 = latestReport(contact, FORMS.STAGE2);
  const stage1 = latestReport(contact, FORMS.STAGE1);
  const anchor = review || stage2 || stage1;
  if (!anchor) { return null; }

  let days = CONFIG.REVIEW_DAYS_ROUTINE;
  if (anchor.form === FORMS.STAGE2 && cognitiveFlag(anchor)) {
    days = CONFIG.REVIEW_DAYS_COGNITIVE;
  }
  if (anchor.form === FORMS.REVIEW
    && getField(anchor, 'g_rev.review_result') === 're_refer') {
    days = CONFIG.REVIEW_DAYS_RE_REFER;
  }
  return addDays(anchor.reported_date, days);
}

// ---- reporting ----

/** Did Stage 2 follow this Stage 1 within the programme window? */
function convertedInWindow(contact, stage1Report) {
  const deadline = addDays(
    stage1Report.reported_date, CONFIG.STAGE2_WINDOW_DAYS
  ).getTime();
  return reportsSince(contact, FORMS.STAGE2, stage1Report.reported_date)
    .some((r) => r.reported_date <= deadline);
}

/** Contact id of the user who submitted a report. Set by every app form. */
function screenedBy(report) {
  return getField(report, 'screened_by');
}

module.exports = {
  MS_IN_DAY,
  CONTACT_TYPES,
  FORMS,
  CONFIG,
  EXIT_OUTCOMES,
  getField,
  num,
  isForm,
  reportsOf,
  latestReport,
  reportsSince,
  daysBetween,
  addDays,
  contactType,
  isParticipant,
  isCamp,
  currentAge,
  hasConsent,
  isExited,
  isActive,
  stage1Result,
  stage1Referred,
  stage1NeedsFollowUp,
  stage1FlagCount,
  stage2DoneAfter,
  stage2Disposition,
  stage2NeedsReferral,
  isUrgent,
  isSafeguarding,
  cognitiveFlag,
  followUpAttemptsSince,
  appointmentBooked,
  nextReviewDue,
  convertedInWindow,
  screenedBy,
};
