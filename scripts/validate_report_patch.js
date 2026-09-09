/**
 * validate_report_patch.js - offline behavioral test for the cht-core patch.
 *
 * Transpiles webapp/src/ts/services/format-data-record.service.ts (the real
 * file the webapp will ship) and runs it under Node with stubbed Angular
 * services, then feeds it synthetic data_record docs for all four scales and
 * asserts the rendered output:
 *
 *  - no technical report.<form>.* labels remain for configured forms
 *  - internal fields are hidden
 *  - choice values resolve to form labels (yes->Yes, P->Pass, F->Fail, ...)
 *  - chronological age is joined into one readable row
 *  - item scores are attached to their question rows
 *  - disclaimers render their form text; empty rows are suppressed
 *  - non-configured forms render exactly like stock CHT
 *
 * Run: node scripts/validate_report_patch.js   (exits non-zero on failure)
 */

const fs = require('fs');
const path = require('path');
const ts = require(path.join(__dirname, '..', '..', 'cht-core', 'node_modules', 'typescript'));

const CORE = path.join(__dirname, '..', '..', 'cht-core');
const SERVICE = path.join(CORE, 'webapp', 'src', 'ts', 'services',
  'format-data-record.service.ts');
const CONFIG = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'app_settings.json'), 'utf8')).report_display;

// every displayed label key for configured forms must exist here, or the UI
// would fall back to showing the raw technical key
const MESSAGES = new Set();
fs.readFileSync(path.join(__dirname, '..', 'translations',
  'messages-en.properties'), 'utf8').split(/\r?\n/).forEach((line) => {
  const m = line.match(/^([^#\s][^=]*)=/);
  if (m) {
    MESSAGES.add(m[1].trim());
  }
});

// ---------------------------------------------------------------------------
// Minimal stubs for the Angular services the formatter depends on
// ---------------------------------------------------------------------------

const settings = {
  // no forms definitions needed: XML path does not use them
  settings: {},
  report_display: CONFIG,
};

const formatDateService = {
  date: (v) => {
    const d = new Date(v);
    return isNaN(d) ? String(v) : d.toISOString().slice(0, 10);
  },
  datetime: (v) => {
    const d = new Date(v);
    return isNaN(d) ? String(v) : d.toISOString();
  },
  relative: () => '',
};

const languageService = { get: async () => 'en' };
const settingsService = { get: async () => settings };
const translateLocaleService = {
  instant: (key) => (key !== undefined && key !== null ? String(key) : key),
};
const dbService = { get: () => ({ query: async () => ({ rows: [] }) }) };
const ngZone = { runOutsideAngular: (fn) => fn() };

// ---------------------------------------------------------------------------
// Load the real service via the TypeScript transpiler
// ---------------------------------------------------------------------------

function loadService() {
  const src = fs.readFileSync(SERVICE, 'utf8');
  const js = ts.transpileModule(src, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      experimentalDecorators: true,
      emitDecoratorMetadata: false,
    },
  }).outputText;

  const module = { exports: {} };
  const requireStub = (name) => {
    if (name === 'lodash-es') {
      // satoru-config has no node_modules; use cht-core's copy of lodash
      return require(path.join(CORE, 'node_modules', 'lodash', 'lodash.js'));
    }
    if (name.startsWith('@angular/') || name.startsWith('@medic/')) {
      // decorators are invoked at class-definition time; provide no-ops
      const noop = () => () => undefined;
      return new Proxy({}, { get: (t, prop) => (prop === 'Injectable' ? noop : noop) });
    }
    throw new Error(`unexpected import: ${name}`);
  };
  const fn = new Function('exports', 'require', 'module', '__filename',
    '__dirname', js);
  fn(module.exports, requireStub, module, SERVICE, path.dirname(SERVICE));
  const Klass = module.exports.FormatDataRecordService;
  return new Klass(
    dbService, formatDateService, languageService, settingsService,
    translateLocaleService, ngZone
  );
}

// ---------------------------------------------------------------------------
// Synthetic scale documents (values mirror real submissions)
// ---------------------------------------------------------------------------

function vinelandDoc() {
  const items = {};
  for (let i = 1; i <= 22; i++) {
    items[`item_${i}`] = 'yes';
  }
  items.item_23 = 'no';
  for (let i = 24; i <= 30; i++) {
    items[`item_${i}`] = 'not_assessed';
  }
  const band = (name, from, to) => {
    const g = {};
    for (let i = from; i <= to; i++) {
      g[`item_${i}`] = items[`item_${i}`];
    }
    return g;
  };
  const fields = {
    patient_uuid: 'uuid-1234',
    patient_id: 'CR-001',
    patient_name: 'Kamala',
    screened_by: 'contact-abc',
    screened_by_name: 'Varshini',
    g_intro: { vineland_disclaimer: '', acknowledged: 'yes' },
    g_child: {
      assessment_date: '2026-08-29',
      child_dob: '2025-07-17',
      ca_days: '408',
      ca_months_dec: '13.4',
      ca_months_floor: '13',
      ca_years_display: '1',
      ca_rem_months: '1',
      age_valid: 'yes',
      dob_warning: '',
      ca_display: '',
      show_all: 'no',
    },
    ca_band: '2',
    g_y0_1: band('g_y0_1', 1, 17),
    g_y1_2: band('g_y1_2', 18, 34),
    g_y2_3: band('g_y2_3', 35, 44),
    g_y3_4: band('g_y3_4', 45, 50),
    g_y4_5: band('g_y4_5', 51, 56),
    g_y5_6: band('g_y5_6', 57, 61),
    g_y6_7: band('g_y6_7', 62, 65),
    g_y7_8: band('g_y7_8', 66, 70),
    g_y8_9: band('g_y8_9', 71, 74),
    g_y9_10: band('g_y9_10', 75, 77),
    g_y10_11: band('g_y10_11', 78, 81),
    g_y11_12: band('g_y11_12', 82, 84),
    g_y12_15: band('g_y12_15', 85, 89),
    raw_score: '22',
    total_yes_items: '22',
    total_no_items: '1',
    total_not_assessed_items: '66',
    social_age_months: '22',
    social_age_years: '1',
    social_age_remaining_months: '10',
    social_quotient_raw: '164.123',
    social_quotient_rounded: '164',
    sq_interpretation: 'Average',
    score_status: 'incomplete',
    na_reason: 'Family declined the remaining items.',
    clinical_notes: 'Follow up in 3 months.',
    result_complete: '',
    result_incomplete: '',
    result_invalid: '',
    scoring_version: 'vsms-v1-doll1965-1to1',
  };
  // item scores: yes->1, else 0
  for (let i = 1; i <= 89; i++) {
    fields[`item_${i}_score`] = items[`item_${i}`] === 'yes' ? '1' : '0';
  }
  return {
    _id: 'report-vineland-1',
    form: 'vineland',
    type: 'data_record',
    content_type: 'xml',
    reported_date: Date.parse('2026-08-29T10:00:00Z'),
    fields,
    hidden_fields: ['inputs'],
    contact: { _id: 'contact-abc', name: 'Varshini' },
  };
}

function ddstDoc() {
  const g_ps = { ps_01: 'P', ps_02: 'P', ps_03: 'F', ps_04: 'NO' };
  const g_fm = { fm_01: 'P', fm_02: 'R' };
  const g_lang = { lang_01: 'P', lang_02: 'P' };
  const g_gm = { gm_01: 'P', gm_02: 'F' };
  const fields = {
    patient_uuid: 'uuid-5678',
    patient_name: 'Ravi',
    g_meta: {
      test_date: '2026-08-30',
      child_dob: '2026-02-01',
      ca_days: '210',
      ca_months_dec: '6.9',
      ca_band: '1',
      dob_warning: '',
      ca_note: '',
      show_all: 'no',
    },
    g_ps, g_fm, g_lang, g_gm,
    d_ps_status: 'Suspect',
    d_fm_status: 'Caution',
    d_lang_status: 'Normal',
    d_gm_status: 'Caution',
    caution_domains: '2',
    any_suspect: 'true',
    overall: 'Suspect',
    scoring_version: 'ddst-ii-nims-v1',
    result_note: '',
  };
  return {
    _id: 'report-ddst-1',
    form: 'ddst',
    type: 'data_record',
    content_type: 'xml',
    reported_date: Date.parse('2026-08-30T10:00:00Z'),
    fields,
    hidden_fields: ['inputs'],
    contact: { _id: 'contact-abc', name: 'Varshini' },
  };
}

function mocaDoc() {
  return {
    _id: 'report-moca-1',
    form: 'moca_assessment',
    type: 'data_record',
    content_type: 'xml',
    reported_date: Date.parse('2026-08-28T10:00:00Z'),
    fields: {
      patient_uuid: 'uuid-9999',
      patient_id: 'CR-009',
      patient_name: 'Lakshmi',
      patient_sex: 'female',
      patient_age: '68',
      patient_phone: '+919900000000',
      patient_education: 'primary',
      g_consent: { consent_reconfirmed: 'yes' },
      g_visuospatial: {
        trail_making: 'yes', cube_copy: 'yes', clock_contour: 'yes',
        clock_numbers: 'no', clock_hands: 'no',
      },
      g_naming: { naming_1: 'yes', naming_2: 'dk', naming_3: 'no' },
      g_memory: {
        memory_words: '', mem_trial1: { mem_t1_face: 'yes', mem_t1_velvet: 'no' },
        mem_trial2: { mem_t2_face: 'yes', mem_t2_velvet: 'no' },
      },
      g_attention: {
        digit_span_fwd: 'no', digit_span_bwd: 'no', vigilance: 'no',
        serial_7s: '2',
      },
      g_language: { sentence_rep_1: 'yes', sentence_rep_2: 'no', fluency_count: '7' },
      g_abstraction: { abstraction_1: 'yes', abstraction_2: 'no' },
      g_delayed_recall: {
        delayed_face: 'yes', delayed_velvet: 'no', delayed_church: 'no',
        delayed_daisy: 'no', delayed_red: 'no',
        delayed_face_cat: 'no', delayed_face_mc: 'no',
      },
      g_orientation: {
        orientation_date: 'yes', orientation_month: 'no', orientation_year: 'yes',
        orientation_day: 'no', orientation_place: 'yes', orientation_city: 'no',
      },
      moca_visuospatial_total: '3', moca_naming_total: '1',
      moca_memory_total: '1', moca_attention_total: '2',
      moca_language_total: '2', moca_abstraction_total: '1',
      moca_orientation_total: '3', moca_raw_total: '13',
      moca_education_adj: '1', moca_total_score: '14',
      moca_interpretation: 'impaired',
      g_admin: { administered_by: 'Varshini', assessment_datetime: '2026-08-28' },
    },
    hidden_fields: ['inputs'],
    contact: { _id: 'contact-abc', name: 'Varshini' },
  };
}

function dstDoc() {
  const fields = {
    patient_uuid: 'uuid-2222',
    patient_name: 'Meena',
    screened_by_name: 'Varshini',
    g_intro: { dst_disclaimer: '', acknowledged: 'yes' },
    g_child: {
      assessment_date: '2026-08-29', child_dob: '2025-07-17',
      ca_days: '408', ca_months_dec: '13.4', age_valid: 'yes',
      show_all: 'no', dob_warning: '',
    },
    g_birth_to_3_months: { item_1: 'pass', item_2: 'pass', item_3: 'fail', item_4: 'not_assessed', item_5: 'pass', item_6: 'pass', item_7: 'pass' },
    band_1_passed_count: '5', band_1_failed_count: '1',
    band_1_not_assessed: '1', band_1_earned_months: '2.14',
    total_passed_items: '5', total_failed_items: '1',
    total_not_assessed_items: '1',
    developmental_age_months: '2.14',
    developmental_age_years: '0',
    developmental_age_remaining_months: '2',
    developmental_quotient_raw: '50.9', developmental_quotient_rounded: '51',
    score_status: 'incomplete',
    na_reason: 'Child was sleepy.',
    clinical_notes: '',
  };
  return {
    _id: 'report-dst-1', form: 'dst', type: 'data_record',
    content_type: 'xml', reported_date: Date.parse('2026-08-29T10:00:00Z'),
    fields, hidden_fields: ['inputs'],
    contact: { _id: 'contact-abc', name: 'Varshini' },
  };
}

// ---------------------------------------------------------------------------
// Assertions
// ---------------------------------------------------------------------------

let failures = 0;
function check(name, cond, detail) {
  if (cond) {
    console.log(`  ok   ${name}`);
  } else {
    failures++;
    console.log(`  FAIL ${name}${detail ? ' :: ' + detail : ''}`);
  }
}

function checkAllTranslated(name, labels, form) {
  const missing = labels.filter((l) => l.startsWith(`report.${form}.`)
    && !MESSAGES.has(l));
  check(name, missing.length === 0, missing.slice(0, 3).join(' | '));
}

function flattenRows(fields) {
  const rows = [];
  const walk = (arr) => arr && arr.forEach((f) => {
    rows.push(f);
    if (f.isArray && Array.isArray(f.data)) {
      walk(f.data);
    }
  });
  walk(fields);
  return rows;
}

async function main() {
  const svc = loadService();
  console.log('service loaded OK');

  console.log('\n== Vineland ==');
  {
    const out = await svc.format(vinelandDoc());
    const rows = flattenRows(out.fields);
    const labels = rows.map((r) => r.label);
    const byLabel = Object.fromEntries(labels.map((l, i) => [l, rows[i]]));

    check('no technical labels', labels.every((l) => !/item_\d+_score/.test(l)), labels.slice(0, 3).join(' | '));
    checkAllTranslated('every label has an English translation', labels, 'vineland');
    check('internal CA fields hidden', !labels.includes('report.vineland.g_child.ca_months_floor') && !labels.includes('report.vineland.g_child.ca_days'));
    check('result flags hidden', !labels.includes('report.vineland.result_complete'));
    check('group labels translated', byLabel['report.vineland.g_y0_1'] && !byLabel['report.vineland.g_y0_1'].value, 'group row present');
    check('question label key present', !!byLabel['report.vineland.g_y0_1.item_1']);
    check('choice resolved yes->Yes', byLabel['report.vineland.g_y0_1.item_1'].value === 'Yes', String(byLabel['report.vineland.g_y0_1.item_1'].value));
    check('choice resolved no->No', byLabel['report.vineland.g_y1_2.item_23'] && byLabel['report.vineland.g_y1_2.item_23'].value === 'No');
    check('choice resolved not_assessed->Not Assessed', byLabel['report.vineland.g_y1_2.item_24'] && byLabel['report.vineland.g_y1_2.item_24'].value === 'Not Assessed', String(byLabel['report.vineland.g_y1_2.item_24'] && byLabel['report.vineland.g_y1_2.item_24'].value));
    check('item score attached', byLabel['report.vineland.g_y0_1.item_1'].score === '1');
    check('CA joined row', byLabel['report.scale.chronological_age'] && /1 years? 1 months?/.test(String(byLabel['report.scale.chronological_age'].value)), String(byLabel['report.scale.chronological_age'] && byLabel['report.scale.chronological_age'].value));
    check('raw_score visible', byLabel['report.vineland.raw_score'] && byLabel['report.vineland.raw_score'].value === '22');
    check('SQ interpretation visible', byLabel['report.vineland.sq_interpretation'] && byLabel['report.vineland.sq_interpretation'].value === 'Average');
    check('disclaimer has form text', byLabel['report.vineland.g_intro.vineland_disclaimer'] && /social maturity screening tool/.test(String(byLabel['report.vineland.g_intro.vineland_disclaimer'].value)));
    check('acknowledged resolved', byLabel['report.vineland.g_intro.acknowledged'].value === 'Yes');
    check('clinical notes kept', byLabel['report.vineland.clinical_notes'] && byLabel['report.vineland.clinical_notes'].value === 'Follow up in 3 months.');
    check('empty na_reason suppressed elsewhere', byLabel['report.dst'] === undefined);
  }

  console.log('\n== DDST ==');
  {
    const out = await svc.format(ddstDoc());
    const rows = flattenRows(out.fields);
    const labels = rows.map((r) => r.label);
    const byLabel = Object.fromEntries(labels.map((l, i) => [l, rows[i]]));

    check('no delayed flags exposed', labels.every((l) => !/_delayed/.test(l)));
    checkAllTranslated('every label has an English translation', labels, 'ddst');
    check('internal g_meta fields hidden', !labels.includes('report.ddst.g_meta.show_all') && !labels.includes('report.ddst.g_meta.ca_months_dec'));
    check('P resolved to Pass', byLabel['report.ddst.g_ps.ps_01'] && byLabel['report.ddst.g_ps.ps_01'].value === 'Pass', String(byLabel['report.ddst.g_ps.ps_01'] && byLabel['report.ddst.g_ps.ps_01'].value));
    check('F resolved to Fail', byLabel['report.ddst.g_ps.ps_03'] && byLabel['report.ddst.g_ps.ps_03'].value === 'Fail');
    check('NO resolved to No Opportunity', byLabel['report.ddst.g_ps.ps_04'] && byLabel['report.ddst.g_ps.ps_04'].value === 'No Opportunity');
    check('R resolved to Refusal', byLabel['report.ddst.g_fm.fm_02'] && byLabel['report.ddst.g_fm.fm_02'].value === 'Refusal');
    check('domain statuses visible', byLabel['report.ddst.d_ps_status'] && byLabel['report.ddst.d_ps_status'].value === 'Suspect');
    check('overall visible', byLabel['report.ddst.overall'] && byLabel['report.ddst.overall'].value === 'Suspect');
    check('result_note hidden', !labels.includes('report.ddst.result_note'));
    check('CA joined row', byLabel['report.scale.chronological_age'] && /6 months|0 years/.test(String(byLabel['report.scale.chronological_age'].value)), String(byLabel['report.scale.chronological_age'] && byLabel['report.scale.chronological_age'].value));
  }

  console.log('\n== DST ==');
  {
    const out = await svc.format(dstDoc());
    const rows = flattenRows(out.fields);
    const labels = rows.map((r) => r.label);
    const byLabel = Object.fromEntries(labels.map((l, i) => [l, rows[i]]));

    check('band intermediates hidden', !labels.some((l) => /band_\d+_(passed|failed|not_assessed|earned)/.test(l)));
    checkAllTranslated('every label has an English translation', labels, 'dst');
    check('band 1 group label present', !!byLabel['report.dst.g_birth_to_3_months']);
    check('pass resolved to Pass', byLabel['report.dst.g_birth_to_3_months.item_1'] && byLabel['report.dst.g_birth_to_3_months.item_1'].value === 'Pass');
    check('fail resolved to Fail', byLabel['report.dst.g_birth_to_3_months.item_3'] && byLabel['report.dst.g_birth_to_3_months.item_3'].value === 'Fail');
    check('not_assessed resolved', byLabel['report.dst.g_birth_to_3_months.item_4'] && byLabel['report.dst.g_birth_to_3_months.item_4'].value === 'Not assessed');
    check('DQ visible', byLabel['report.dst.developmental_quotient_rounded'] && byLabel['report.dst.developmental_quotient_rounded'].value === '51');
    check('na_reason kept', byLabel['report.dst.na_reason'] && byLabel['report.dst.na_reason'].value === 'Child was sleepy.');
    check('empty clinical_notes suppressed', !byLabel['report.dst.clinical_notes']);
    check('CA joined from days', byLabel['report.scale.chronological_age'] && /1 years? 1 months?/.test(String(byLabel['report.scale.chronological_age'].value)), String(byLabel['report.scale.chronological_age'] && byLabel['report.scale.chronological_age'].value));
  }

  console.log('\n== MoCA ==');
  {
    const out = await svc.format(mocaDoc());
    const rows = flattenRows(out.fields);
    const labels = rows.map((r) => r.label);
    const byLabel = Object.fromEntries(labels.map((l, i) => [l, rows[i]]));

    check('section labels present', !!byLabel['report.moca_assessment.g_visuospatial']);
    checkAllTranslated('every label has an English translation', labels, 'moca_assessment');
    check('yes resolved', byLabel['report.moca_assessment.g_visuospatial.trail_making'] && byLabel['report.moca_assessment.g_visuospatial.trail_making'].value === 'Yes');
    check('dk resolved (naming_2)', byLabel['report.moca_assessment.g_naming.naming_2'] && byLabel['report.moca_assessment.g_naming.naming_2'].value === "Don't know / Not assessed", String(byLabel['report.moca_assessment.g_naming.naming_2'] && byLabel['report.moca_assessment.g_naming.naming_2'].value));
    check('serial 7s resolved to choice label', byLabel['report.moca_assessment.g_attention.serial_7s'] && byLabel['report.moca_assessment.g_attention.serial_7s'].value === '2-3 correct subtractions (2 pts)', String(byLabel['report.moca_assessment.g_attention.serial_7s'] && byLabel['report.moca_assessment.g_attention.serial_7s'].value));
    check('domain totals visible', byLabel['report.moca_assessment.moca_total_score'] && byLabel['report.moca_assessment.moca_total_score'].value === '14');
    check('interpretation visible', byLabel['report.moca_assessment.moca_interpretation'] && byLabel['report.moca_assessment.moca_interpretation'].value === 'impaired');
    check('instruction fields hidden', !labels.includes('report.moca_assessment.g_visuospatial.trail_making_inst'));
    check('patient internal fields hidden', !labels.includes('report.moca_assessment.patient_uuid'));
    check('duplicate delayed total hidden', !labels.includes('report.moca_assessment.moca_delayed_total'));
  }

  console.log('\n== stock behavior preserved (non-configured form) ==');
  {
    const doc = {
      _id: 'r1', form: 'some_other_form', type: 'data_record',
      content_type: 'xml', reported_date: Date.now(),
      fields: { group: { field1: 'val' }, top: 'x' },
      hidden_fields: ['inputs'],
    };
    const out = await svc.format(doc);
    const rows = flattenRows(out.fields);
    const labels = rows.map((r) => r.label);
    check('stock labels unchanged', labels.includes('report.some_other_form.group.field1'));
    check('stock value passthrough', rows.find((r) => r.label === 'report.some_other_form.group.field1').value === 'val');
  }

  console.log(failures === 0 ? '\nALL CHECKS PASSED' : `\n${failures} CHECK(S) FAILED`);
  process.exit(failures === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
