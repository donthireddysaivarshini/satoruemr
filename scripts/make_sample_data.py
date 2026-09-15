"""make_sample_data.py - realistic synthetic EMR docs for offline testing/demo.

No network. Builds a screening camp, participants, a submitter contact, the
settings doc, and fully-populated scale reports (DDST-II / DST / MoCA / VSMS)
by walking the SAME form metadata the exporter uses (scripts/scale_meta.py),
so every question path and choice value is valid for the real forms.

Uses:
  python scripts/make_sample_data.py --json out/sample_data.json
      write the raw CouchDB-style docs (feed to anything expecting _all_docs)

  python scripts/make_sample_data.py --xlsx out/
      write sample workbooks for every export scope, straight from the docs
      (no CouchDB needed) - this is what you review to sign off the format

Deterministic: same seed -> same docs every run.
"""

import argparse
import json
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scale_meta import SCALES, get_scale_meta, JOIN_FIELDS

SEED = 20260909
CAMP_ID = 'camp-nims-0001'
OTHER_CAMP_ID = 'camp-other-0002'
SUBMITTER = {
    '_id': 'person-varshini', 'type': 'contact', 'contact_type': 'participant',
    'name': 'Varshini (screener)', 'phone': '+91 90000 00009',
    'parent': {'_id': CAMP_ID},
}

SETTINGS = {
    '_id': 'settings',
    'settings': {
        'contact_types': [
            {'id': 'screening_camp', 'person': False},
            {'id': 'participant', 'person': True},
        ],
    },
}

# Five participants in the NIMS camp + one in another camp (isolation check).
PARTICIPANTS = [
    {'name': 'Kamala Devi', 'cr_no': 'NIMS-79704', 'age': 1, 'gender': 'female',
     'dob': date(2025, 7, 17), 'scales': ['ddst', 'dst', 'moca_assessment', 'vineland']},
    {'name': 'Ravi Kumar', 'cr_no': 'NIMS-79711', 'age': 4, 'gender': 'male',
     'dob': date(2022, 3, 2), 'scales': ['ddst', 'vineland']},
    {'name': 'Anjali Rao', 'cr_no': 'NIMS-79725', 'age': 6, 'gender': 'female',
     'dob': date(2020, 1, 11), 'scales': ['dst']},
    {'name': 'Suresh Naidu', 'cr_no': 'NIMS-79730', 'age': 68, 'gender': 'male',
     'dob': date(1958, 6, 20), 'scales': ['moca_assessment']},
    {'name': 'Lakshmi Bai', 'cr_no': 'NIMS-79742', 'age': 3, 'gender': 'female',
     'dob': date(2023, 9, 5), 'scales': []},
]
OTHER_PARTICIPANT = {
    'name': 'Not In This Camp', 'cr_no': 'OTHER-00001', 'age': 5,
    'gender': 'male', 'dob': date(2021, 2, 2), 'scales': ['ddst'],
}

ASSESSMENT_DATE = date(2026, 8, 29)


def _iso(d):
    return d.isoformat()


def contact_doc(idx, spec, camp_id):
    return {
        '_id': f'participant-{idx:04d}',
        'type': 'contact',
        'contact_type': 'participant',
        'name': spec['name'],
        'cr_no': spec['cr_no'],
        'age': spec['age'],
        'gender': spec['gender'],
        'phone': f'+91 90000 {10000 + idx:05d}',
        'hospital_name': 'NIMS Hospital',
        'ward_dept_no': f'W-{10 + idx}',
        'address': 'Punjagutta, Hyderabad',
        'education_level': 'primary' if spec['age'] < 18 else 'secondary',
        'occupation': '' if spec['age'] < 18 else 'farmer',
        'referred_by': 'Dr Rao',
        'referral_department': 'Paediatrics' if spec['age'] < 18 else 'Neurology',
        'referral_complaint': 'Developmental concern',
        'registration_date': 1756339200000,
        'parent': {'_id': camp_id},
    }


def _age_parts(dob, on):
    days = (on - dob).days
    years = int(days // 365.25)
    months = int((days - years * 365.25) // 30.4375)
    return days, years, months


def _pick_choice(rng, codes, path):
    """Bias toward the first (usually 'positive') choice, but vary."""
    if not codes:
        return None
    positive_first = [c for c in codes
                      if c not in ('', 'not_assessed', 'na', 'dk', 'no_response')]
    ordered = positive_first + [c for c in codes if c not in positive_first]
    weights = [max(1, 10 - i * 3) for i in range(len(ordered))]
    return rng.choices(ordered, weights=weights, k=1)[0]


def _numeric_result(rng, path):
    p = path.lower()
    if 'quotient' in p or p.endswith('_dq') or p.endswith('_sq'):
        return rng.randint(70, 130)
    if 'year' in p:
        return rng.randint(0, 6)
    if 'month' in p:
        return rng.randint(0, 24)
    if 'adj' in p:
        return rng.choice([0, 1])
    if any(t in p for t in ('total', 'score', 'count', 'items', 'raw', 'passed',
                            'failed', 'yes', 'no')):
        return rng.randint(0, 20)
    return rng.randint(0, 10)


def build_report(form, participant_doc, dob):
    """A fully-populated report doc for one scale, valid for the real form."""
    rng = random.Random(f'{SEED}:{form}:{participant_doc["_id"]}')
    meta = get_scale_meta(form)
    flat = meta['flat']
    cmaps = meta['choice_maps']
    rd = meta['report_display']
    fields = {
        'patient_uuid': participant_doc['_id'],
        'patient_id': participant_doc['cr_no'],
        'patient_name': participant_doc['name'],
    }

    def put(path, value):
        parts = path.split('.')
        cur = fields
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value

    days, years, months = _age_parts(dob, ASSESSMENT_DATE)

    # dates / DOB
    for path in rd['date_fields']:
        if 'dob' in path or 'birth' in path:
            put(path, _iso(dob))
        elif 'datetime' in path:
            put(path, ASSESSMENT_DATE.isoformat() + 'T10:30:00.000Z')
        else:
            put(path, _iso(ASSESSMENT_DATE))

    # chronological-age helper fields (so the joined row renders)
    for j in JOIN_FIELDS[form]:
        if j['format'] == 'years_months_parts':
            put(j['parts'][0], years)
            put(j['parts'][1], months)
        elif j['format'] == 'days_to_years_months':
            put(j['parts'][0], days)

    # every question field: a valid choice / plausible value
    for item in flat:
        if item['type'] != 'field':
            continue
        path = item['path']
        if path in fields or _get(fields, path) is not None:
            continue
        if path in rd['result_fields']:
            continue
        codes = list(cmaps.get(path, {}).keys())
        if codes:
            put(path, _pick_choice(rng, codes, path))
        elif path in rd['date_fields']:
            continue
        elif path.endswith('_inst') or 'disclaimer' in path or 'warning' in path \
                or path.endswith('_note'):
            put(path, '')            # instruction / note fields: stored empty
        # other bare calc fields left unset - exporter derives what it needs

    # per-item score joins (VSMS): 1 when the answer is the positive choice
    for qpath, spath in rd['score_fields'].items():
        ans = _get(fields, qpath)
        codes = list(cmaps.get(qpath, {}).keys())
        positive = codes[0] if codes else None
        put(spath, 1 if ans == positive else 0)

    # tallies from the answers actually recorded, so the sample is internally
    # consistent (real docs compute these in the form binds)
    answers = [_get(fields, i['path']) for i in flat
               if i['type'] == 'field' and i['path'] in cmaps
               and i['path'] not in rd['result_fields']]
    n_yes = sum(1 for a in answers if a in ('yes', 'pass', 'P'))
    n_no = sum(1 for a in answers if a in ('no', 'fail', 'F'))
    n_na = sum(1 for a in answers if a in ('not_assessed', 'NO', 'R', 'na'))
    tally = {'yes': n_yes, 'passed': n_yes, 'no': n_no, 'failed': n_no,
             'not_assessed': n_na, 'raw': n_yes, 'total_yes': n_yes}

    # calculated result fields
    for path in rd['result_fields']:
        leaf = path.lower().split('.')[-1]
        codes = list(cmaps.get(path, {}).keys())
        matched = next((v for k, v in tally.items() if k in leaf), None)
        if codes:
            put(path, _pick_choice(rng, codes, path))
        elif any(t in leaf for t in ('interpretation', 'status', 'overall',
                                     'category')):
            put(path, rng.choice(['Normal', 'Borderline', 'Delayed']))
        elif matched is not None:
            put(path, matched)
        else:
            put(path, _numeric_result(rng, path))

    # free-text notes
    for path in rd['notes_fields']:
        put(path, {
            'clinical_notes': 'Cooperative throughout. Good rapport.',
            'scoring_notes': 'Scored strictly per manual.',
            'na_reason': '',
        }.get(path.split('.')[-1], 'See case file.'))

    reported = int(
        (ASSESSMENT_DATE - date(1970, 1, 1)).total_seconds() * 1000
        + hash(form) % 86_400_000)
    return {
        '_id': f'report-{form}-{participant_doc["_id"]}',
        'type': 'data_record',
        'form': form,
        'content_type': 'xml',
        'reported_date': abs(reported),
        'contact': SUBMITTER,
        'fields': fields,
        'hidden_fields': [],
    }


def _get(d, path):
    cur = d
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def build_docs():
    docs = [SETTINGS, SUBMITTER]
    docs.append({'_id': CAMP_ID, 'type': 'contact',
                 'contact_type': 'screening_camp', 'name': 'NIMS Camp',
                 'address': 'Punjagutta, Hyderabad',
                 'contact': {'_id': SUBMITTER['_id']}})
    docs.append({'_id': OTHER_CAMP_ID, 'type': 'contact',
                 'contact_type': 'screening_camp', 'name': 'Other Camp'})

    for idx, spec in enumerate(PARTICIPANTS, start=1):
        pdoc = contact_doc(idx, spec, CAMP_ID)
        docs.append(pdoc)
        for form in spec['scales']:
            docs.append(build_report(form, pdoc, spec['dob']))

    other = contact_doc(99, OTHER_PARTICIPANT, OTHER_CAMP_ID)
    docs.append(other)
    for form in OTHER_PARTICIPANT['scales']:
        docs.append(build_report(form, other, OTHER_PARTICIPANT['dob']))
    return docs


class _MemDb:
    def __init__(self, docs):
        self._docs = docs

    def fetch_all_docs(self):
        return self._docs

    def fetch_doc(self, doc_id):
        return next((d for d in self._docs if d.get('_id') == doc_id), None)


def write_xlsx(docs, out_dir):
    import export_emr
    os.makedirs(out_dir, exist_ok=True)
    db = _MemDb(docs)
    part_id = 'participant-0001'  # Kamala - completed all four
    scopes = [
        'all',
        f'camp-workbook={CAMP_ID}',
        f'participant-report={part_id}',
    ]
    written = []
    for scope in scopes:
        wb = export_emr.build_workbook(scope, db)
        name = export_emr.default_output_name(scope, wb, db)
        path = os.path.join(out_dir, name)
        wb.save(path)
        sheets = [f'{ws.title}({ws.max_row - 1}r)' for ws in wb.worksheets]
        written.append((scope, path, sheets))
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', metavar='FILE', help='write raw docs as JSON')
    ap.add_argument('--xlsx', metavar='DIR', help='write sample workbooks')
    args = ap.parse_args()
    if not args.json and not args.xlsx:
        ap.error('give --json FILE and/or --xlsx DIR')

    docs = build_docs()
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)
        print(f'wrote {len(docs)} docs -> {args.json}')
    if args.xlsx:
        for scope, path, sheets in write_xlsx(docs, args.xlsx):
            print(f'{scope}\n  -> {path}\n     {", ".join(sheets)}')


if __name__ == '__main__':
    main()
