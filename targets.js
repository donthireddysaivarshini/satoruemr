/**
 * satoru-config - targets
 *
 * This is the intern dashboard. Targets are computed on the device from the
 * documents that device has replicated, so an intern assigned to their own
 * screening_camp sees their own numbers and nobody else's. If two interns
 * share a camp, their numbers merge - see IMPLEMENTATION-GUIDE.md.
 *
 * `screened_by` is recorded on every report regardless, so a supervisor can
 * always break the numbers down by intern from an export.
 */

const {
  FORMS,
  CONTACT_TYPES,
  getField,
  num,
  stage1Referred,
  convertedInWindow,
} = require('./nools-extras');

const consented = (contact, report) =>
  getField(report, 'g_consent.consent_confirmed') === 'yes';

module.exports = [

  // ---------------- The funnel ----------------
  {
    id: 'participants-registered',
    type: 'count',
    icon: 'icon-person',
    goal: -1,
    translation_key: 'targets.registered.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'contacts',
    appliesToType: [CONTACT_TYPES.PARTICIPANT],
    idType: 'contact',
    date: 'reported',
  },
  {
    id: 'stage1-completed',
    type: 'count',
    icon: 'icon-healthcare-assessment',
    goal: -1,
    translation_key: 'targets.stage1.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE1],
    appliesIf: consented,
    date: 'reported',
  },
  {
    id: 'stage1-referral-rate',
    type: 'percent',
    icon: 'icon-healthcare-referral',
    goal: -1,
    translation_key: 'targets.referral_rate.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE1],
    appliesIf: consented,
    passesIf: (contact, report) => stage1Referred(report),
    date: 'reported',
  },
  {
    // The number that matters. Current programme performance is 141 of 357.
    // The goal is set above that on purpose: a target you already meet does
    // not change behaviour.
    id: 'stage2-conversion',
    type: 'percent',
    icon: 'icon-healthcare-assessment',
    goal: 60,
    translation_key: 'targets.stage2_conversion.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE1],
    appliesIf: (contact, report) => stage1Referred(report),
    passesIf: (contact, report) => convertedInWindow(contact, report),
    date: 'reported',
  },
  {
    id: 'stage2-completed',
    type: 'count',
    icon: 'icon-healthcare-assessment',
    goal: -1,
    translation_key: 'targets.stage2.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    date: 'reported',
  },

  // ---------------- Clinical yield ----------------
  {
    id: 'cognitive-flag-count',
    type: 'count',
    icon: 'icon-healthcare-diagnosis',
    goal: -1,
    translation_key: 'targets.cognitive_flag.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    appliesIf: (contact, report) =>
      num(report, 'g_disposition.cognitive_flag') === 1,
    date: 'reported',
  },
  {
    id: 'depression-flag-count',
    type: 'count',
    icon: 'icon-healthcare-diagnosis',
    goal: -1,
    translation_key: 'targets.depression_flag.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    appliesIf: (contact, report) => num(report, 'g_phq.phq_flag') === 1,
    date: 'reported',
  },
  {
    id: 'safeguarding-flag-count',
    type: 'count',
    icon: 'icon-risk',
    goal: -1,
    translation_key: 'targets.safeguarding_flag.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    appliesIf: (contact, report) => num(report, 'g_easi.easi_positive') === 1,
    date: 'reported',
  },
  {
    id: 'frailty-flag-count',
    type: 'count',
    icon: 'icon-risk',
    goal: -1,
    translation_key: 'targets.frailty_flag.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    appliesIf: (contact, report) =>
      num(report, 'g_disposition.physical_flag') === 1,
    date: 'reported',
  },

  // ---------------- Process quality ----------------
  {
    id: 'referral-loop-closed',
    type: 'percent',
    icon: 'icon-healthcare-referral',
    goal: 70,
    translation_key: 'targets.referral_closed.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    appliesIf: (contact, report) =>
      getField(report, 'g_disposition.referral_needed') === 'yes',
    passesIf: (contact, report) =>
      (contact.reports || []).some(
        (r) => r.form === FORMS.REFERRAL
          && r.reported_date > report.reported_date
          && getField(r, 'g_ref.attended') === 'attended'),
    date: 'reported',
  },
  {
    // AD8 is an informant instrument. Administering it to the participant
    // alone is a protocol deviation that quietly degrades the dataset, so it
    // is worth watching from day one.
    id: 'informant-availability',
    type: 'percent',
    icon: 'icon-person',
    goal: 80,
    translation_key: 'targets.informant.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.STAGE2],
    passesIf: (contact, report) =>
      getField(report, 'g_ad8.informant_available') === 'yes',
    date: 'reported',
  },
  {
    id: 'follow-up-attempts',
    type: 'count',
    icon: 'icon-followup-general',
    goal: -1,
    translation_key: 'targets.follow_up.title',
    subtitle_translation_key: 'targets.this_month.subtitle',
    appliesTo: 'reports',
    appliesToType: [FORMS.FOLLOW_UP],
    date: 'reported',
  },
];
