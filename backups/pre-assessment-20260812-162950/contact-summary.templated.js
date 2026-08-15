/**
 * satoru-config - contact summary
 *
 * The participant profile: what an intern sees before they knock on the door,
 * and the screening history the programme asked for.
 *
 * Globals available here: `contact`, `reports`, `lineage`.
 *
 * IMPORTANT: appliesToType must be the contact type id ('participant'), NOT
 * 'person'. The contact-summary runtime resolves a doc's type as
 *   type === 'contact' ? contact_type : type
 * so 'person' matches nothing and the card silently disappears.
 */

const {
  FORMS,
  CONTACT_TYPES,
  getField,
  num,
  currentAge,
  EXIT_OUTCOMES,
} = require('./nools-extras');

const PARTICIPANT = CONTACT_TYPES.PARTICIPANT;

const byForm = (form) => (reports || [])
  .filter((r) => r.form === form)
  .sort((a, b) => b.reported_date - a.reported_date);

const stage1 = byForm(FORMS.STAGE1);
const stage2 = byForm(FORMS.STAGE2);
const followUps = byForm(FORMS.FOLLOW_UP);
const referrals = byForm(FORMS.REFERRAL);
const reviews = byForm(FORMS.REVIEW);

const lastStage1 = stage1[0];
const lastStage2 = stage2[0];
const lastFollowUp = followUps[0];
const lastReferral = referrals[0];
const lastReview = reviews[0];

const isExited = followUps.some(
  (r) => EXIT_OUTCOMES.indexOf(getField(r, 'g_fu.outcome')) !== -1
) || (!!lastReview && getField(lastReview, 'g_rev.alive') === 'no');

const pendingStage2 = !!lastStage1
  && getField(lastStage1, 'g_outcome.stage1_result') === 'refer'
  && getField(lastStage1, 'g_outcome.stage2_same_day') !== 'yes'
  && (!lastStage2 || lastStage2.reported_date < lastStage1.reported_date)
  && !isExited;

/**
 * Every risk flag raised at the most recent Stage 2, as translation keys.
 * Computed once so the card's visibility and its contents can never disagree.
 */
const riskFlags = !lastStage2 ? [] : [
  ['contact.flag_cognitive',
    num(lastStage2, 'g_disposition.cognitive_flag') === 1],
  ['contact.flag_depression', num(lastStage2, 'g_phq.phq_flag') === 1],
  ['contact.flag_self_harm',
    num(lastStage2, 'g_phq.phq9_item9_positive') === 1],
  ['contact.flag_abuse', num(lastStage2, 'g_easi.easi_positive') === 1],
  ['contact.flag_frailty',
    num(lastStage2, 'g_disposition.physical_flag') === 1],
  ['contact.flag_glucose', num(lastStage2, 'g_glucose.glucose_flag') > 0],
].filter((pair) => pair[1]).map((pair) => pair[0]);

// ---------------------------------------------------------------------------
// Header fields
// ---------------------------------------------------------------------------
const fields = [
  {
    appliesToType: PARTICIPANT,
    label: 'contact.age',
    // Age today, not age at registration.
    value: currentAge(contact),
    width: 3,
  },
  {
    appliesToType: PARTICIPANT,
    label: 'contact.gender',
    value: contact.gender,
    width: 3,
  },
  {
    appliesToType: PARTICIPANT,
    label: 'contact.education',
    value: contact.education_level,
    width: 6,
  },
  {
    appliesToType: PARTICIPANT,
    label: 'contact.phone',
    value: contact.phone,
    filter: 'phone',
    width: 6,
  },
  {
    appliesToType: PARTICIPANT,
    label: 'contact.informant',
    value: contact.informant_name,
    width: 6,
  },
  {
    appliesToType: PARTICIPANT,
    label: 'contact.informant_phone',
    value: contact.informant_phone,
    filter: 'phone',
    width: 6,
  },
  {
    appliesToType: PARTICIPANT,
    label: 'contact.consent',
    value: contact.consent_given,
    width: 6,
  },
];

// ---------------------------------------------------------------------------
// Cards
// ---------------------------------------------------------------------------
const cards = [

  // ---- where this person is in the workflow ----
  {
    label: 'contact.card.status',
    appliesToType: [PARTICIPANT],
    appliesIf: () => !!lastStage1 || followUps.length > 0,
    fields: () => {
      const out = [];
      let status = 'status.screened_normal';
      if (isExited) {
        status = 'status.exited';
      } else if (lastStage2) {
        status = 'status.stage2_complete';
      } else if (pendingStage2) {
        status = 'status.awaiting_stage2';
      } else if (!lastStage1) {
        status = 'status.not_screened';
      }
      out.push({
        label: 'contact.workflow_status', value: status,
        translate: true, width: 6,
      });
      out.push({
        label: 'contact.followup_attempts', value: followUps.length, width: 6,
      });
      if (lastFollowUp) {
        out.push({
          label: 'contact.last_contact_outcome',
          value: getField(lastFollowUp, 'g_fu.outcome'), width: 6,
        });
        out.push({
          label: 'contact.last_contact_date',
          value: lastFollowUp.reported_date, filter: 'simpleDate', width: 6,
        });
      }
      return out;
    },
  },

  // ---- Stage 1 ----
  {
    label: 'contact.card.stage1',
    appliesToType: [PARTICIPANT],
    appliesIf: () => !!lastStage1,
    fields: () => [
      { label: 'contact.stage1_date', value: lastStage1.reported_date,
        filter: 'simpleDate', width: 6 },
      { label: 'contact.stage1_result',
        value: getField(lastStage1, 'g_outcome.stage1_result'), width: 6 },
      { label: 'contact.pmis',
        value: `${getField(lastStage1, 'g_pmis.pmis_score')} / 8`, width: 4 },
      { label: 'contact.symbol_match',
        value: getField(lastStage1, 'g_symbol.symbol_correct'), width: 4 },
      { label: 'contact.gait_speed',
        value: `${getField(lastStage1, 'g_mcr.gait_speed_mps')} m/s`,
        width: 4 },
      { label: 'contact.mcr',
        value: num(lastStage1, 'g_mcr.mcr_positive') === 1
          ? 'label.positive' : 'label.negative',
        translate: true, width: 6 },
      { label: 'contact.flags_raised',
        value: getField(lastStage1, 'g_outcome.stage1_flag_count'), width: 6 },
    ],
  },

  // ---- Stage 2 ----
  {
    label: 'contact.card.stage2',
    appliesToType: [PARTICIPANT],
    appliesIf: () => !!lastStage2,
    fields: () => [
      { label: 'contact.stage2_date', value: lastStage2.reported_date,
        filter: 'simpleDate', width: 6 },
      { label: 'contact.disposition',
        value: getField(lastStage2, 'g_disposition.disposition'), width: 6 },
      { label: 'contact.ad8',
        value: `${getField(lastStage2, 'g_ad8.ad8_total')} / 8`, width: 4 },
      { label: 'contact.hmse',
        value: `${getField(lastStage2, 'g_hmse.hmse_total')} / 31`, width: 4 },
      { label: 'contact.phq9',
        value: `${getField(lastStage2, 'g_phq.phq_total')} / 27`, width: 4 },
      { label: 'contact.sppb',
        value: `${getField(lastStage2, 'g_sppb.sppb_total')} / 12`, width: 4 },
      { label: 'contact.grip',
        value: `${getField(lastStage2, 'g_grip.grip_max')} kg`, width: 4 },
      { label: 'contact.glucose',
        value: getField(lastStage2, 'g_glucose.glucose_mgdl'), width: 4 },
    ],
  },

  // ---- risk flags ----
  {
    label: 'contact.card.risk',
    appliesToType: [PARTICIPANT],
    // Gated on the flags themselves, NOT on risk_total. risk_total sums
    // phq_flag (PHQ-9 >= 10), so a participant who endorses item 9 while
    // scoring under 10 overall has risk_total 0 - and would have had the card
    // hidden with the self-harm flag inside it. Never gate a card on a
    // different number from the one it displays.
    appliesIf: () => riskFlags.length > 0,
    fields: () => riskFlags.map((label) => ({
      label, value: 'label.flagged', translate: true, width: 6,
      icon: 'icon-risk',
    })),
  },

  // ---- referral ----
  {
    label: 'contact.card.referral',
    appliesToType: [PARTICIPANT],
    appliesIf: () => !!lastReferral,
    fields: () => [
      { label: 'contact.referral_facility',
        value: getField(lastReferral, 'g_ref.facility'), width: 6 },
      { label: 'contact.referral_attended',
        value: getField(lastReferral, 'g_ref.attended'), width: 6 },
      { label: 'contact.diagnosis',
        value: getField(lastReferral, 'g_ref.diagnosis'), width: 6 },
      { label: 'contact.referral_date', value: lastReferral.reported_date,
        filter: 'simpleDate', width: 6 },
    ],
  },

  // ---- latest review ----
  {
    label: 'contact.card.review',
    appliesToType: [PARTICIPANT],
    appliesIf: () => !!lastReview,
    fields: () => [
      { label: 'contact.review_date', value: lastReview.reported_date,
        filter: 'simpleDate', width: 6 },
      { label: 'contact.review_result',
        value: getField(lastReview, 'g_rev.review_result'), width: 6 },
      { label: 'contact.review_trend',
        value: getField(lastReview, 'g_rev.caregiver_reported_trend'),
        width: 6 },
      { label: 'contact.caregiver_strain',
        value: getField(lastReview, 'g_rev.caregiver_strain'), width: 6 },
    ],
  },

  // ---- full encounter history ----
  {
    label: 'contact.card.history',
    appliesToType: [PARTICIPANT],
    appliesIf: () => (reports || []).length > 0,
    fields: () => (reports || [])
      .slice()
      .sort((a, b) => b.reported_date - a.reported_date)
      .slice(0, 12)
      .map((r) => ({
        label: `history.${r.form}`,
        value: r.reported_date,
        filter: 'simpleDate',
        width: 6,
      })),
  },
];

// ---------------------------------------------------------------------------
// Context - read by the app forms' properties.json expressions
// ---------------------------------------------------------------------------
const context = {
  is_participant: contact
    && (contact.type === 'contact'
      ? contact.contact_type === PARTICIPANT
      : contact.type === PARTICIPANT),
  has_stage1: !!lastStage1,
  has_stage2: !!lastStage2,
  pending_stage2: pendingStage2,
  is_exited: isExited,
  follow_up_attempts: followUps.length,
  cognitive_flag: lastStage2
    ? num(lastStage2, 'g_disposition.cognitive_flag') : 0,
};

module.exports = { fields, cards, context };
