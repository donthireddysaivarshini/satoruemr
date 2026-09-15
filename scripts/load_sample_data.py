"""load_sample_data.py - push synthetic camp/participant/assessment docs
straight into a CHT CouchDB for local testing (so you don't hand-fill forms).

Builds the same docs as make_sample_data.py, wraps them in CHT-valid
envelopes (parent lineage, reported_date, submitter contact) and POSTs them
via /medic/_bulk_docs.

  python scripts/load_sample_data.py --url https://medic:PASSWORD@HOST:10443/medic

Add --wipe to first delete any docs a previous run of this script created.
Deterministic ids ('sample-...') so re-runs update in place.
"""

import argparse
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_sample_data as sd

CAMP_ID = 'sample-camp-nims'
OTHER_CAMP_ID = 'sample-camp-other'
SUBMITTER_ID = 'sample-person-screener'


def _lineage(*ids):
    node = None
    for cid in reversed(ids):
        node = {'_id': cid, 'parent': node} if node else {'_id': cid}
    return node


def build_docs():
    submitter = {
        '_id': SUBMITTER_ID, 'type': 'contact', 'contact_type': 'participant',
        'name': 'Varshini (screener)', 'phone': '+91 90000 00009',
        'reported_date': sd.ASSESSMENT_DATE.toordinal() * 86400000,
        'parent': _lineage(CAMP_ID),
    }
    sd.SUBMITTER = submitter  # so build_report embeds the right submitter

    docs = [
        {'_id': 'settings', 'type': 'meta'},  # placeholder, skipped on load
        {'_id': CAMP_ID, 'type': 'contact', 'contact_type': 'screening_camp',
         'name': 'NIMS Camp', 'address': 'Punjagutta, Hyderabad',
         'reported_date': submitter['reported_date'],
         'contact': {'_id': SUBMITTER_ID}},
        {'_id': OTHER_CAMP_ID, 'type': 'contact',
         'contact_type': 'screening_camp', 'name': 'Other Camp',
         'reported_date': submitter['reported_date']},
        submitter,
    ]

    def participant(idx, spec, camp_id):
        d = sd.contact_doc(idx, spec, camp_id)
        d['_id'] = f'sample-participant-{idx:02d}'
        d['reported_date'] = submitter['reported_date']
        d['parent'] = _lineage(camp_id)
        return d

    for idx, spec in enumerate(sd.PARTICIPANTS, start=1):
        pdoc = participant(idx, spec, CAMP_ID)
        docs.append(pdoc)
        for form in spec['scales']:
            r = sd.build_report(form, pdoc, spec['dob'])
            r['_id'] = f'sample-report-{form}-{idx:02d}'
            r['contact'] = dict(submitter, parent=_lineage(CAMP_ID))
            r['from'] = submitter['phone']
            docs.append(r)

    other = participant(90, sd.OTHER_PARTICIPANT, OTHER_CAMP_ID)
    docs.append(other)
    for form in sd.OTHER_PARTICIPANT['scales']:
        r = sd.build_report(form, other, sd.OTHER_PARTICIPANT['dob'])
        r['_id'] = f'sample-report-{form}-90'
        r['contact'] = dict(submitter, parent=_lineage(OTHER_CAMP_ID))
        docs.append(r)

    return [d for d in docs if d['_id'] != 'settings']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True, help='CouchDB medic URL with creds')
    ap.add_argument('--wipe', action='store_true',
                    help='delete previously-loaded sample-* docs first')
    args = ap.parse_args()

    base = args.url.rstrip('/')
    s = requests.Session()
    s.verify = False
    requests.packages.urllib3.disable_warnings()

    docs = build_docs()
    ids = [d['_id'] for d in docs]

    # attach current _rev for any doc that already exists (update in place)
    existing = s.post(f'{base}/_all_docs', json={'keys': ids},
                      params={'include_docs': 'false'}).json()
    # NOTE: _all_docs also returns tombstones, as {rev, deleted: true}. A
    # deleted doc must be recreated WITHOUT a _rev - passing the tombstone's
    # rev is a conflict, because CouchDB treats the doc as non-existent. So
    # only carry a rev forward for docs that are actually live.
    revs = {}
    deleted = set()
    for row in existing.get('rows', []):
        if not row.get('id') or row.get('error') or 'value' not in row:
            continue
        if row['value'].get('deleted'):
            deleted.add(row['id'])
        else:
            revs[row['id']] = row['value']['rev']
    if deleted:
        print(f'recreating {len(deleted)} previously deleted doc(s)')
    for d in docs:
        if d['_id'] in revs:
            d['_rev'] = revs[d['_id']]

    if args.wipe:
        dels = [{'_id': i, '_rev': r, '_deleted': True} for i, r in revs.items()]
        if dels:
            s.post(f'{base}/_bulk_docs', json={'docs': dels})
            print(f'wiped {len(dels)} existing sample docs')
        for d in docs:
            d.pop('_rev', None)

    resp = s.post(f'{base}/_bulk_docs', json={'docs': docs})
    resp.raise_for_status()
    result = resp.json()
    ok = sum(1 for r in result if r.get('ok'))
    errs = [r for r in result if not r.get('ok')]
    print(f'loaded {ok}/{len(docs)} docs into {base}')
    for e in errs:
        print('  ERROR', e)
    print(f'\ncamp id:            {CAMP_ID}')
    print(f'participant (all 4): sample-participant-01  (Kamala Devi)')
    print('scales completed:   Kamala 4, Ravi 2, Anjali 1, Suresh 1, Lakshmi 0')


if __name__ == '__main__':
    main()
