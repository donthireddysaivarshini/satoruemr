"""Read-only Satoru EMR -> Excel exporter.

Produces one .xlsx per run. The workbook contents depend on --scope:

  all                      Sheets: Camps | Participants | Reports
  camp=<campId>            Sheets: Camp | Participants | Reports
  participants_in_camp=..  Sheets: Participants | Reports
  participant=<id>         Sheets: Participant | Reports

Relationships are by exact _id only:
  participant.parent._id  == campId
  report.contact._id      == participantId
  report.contact.parent._id == campId

Repeat-group choice (documented in requirements): arrays are stored as JSON
in a single cell (lossless, schema-generic). Attachments are NOT embedded in
Excel; the `attachments` column lists file names, referenced as
`attachment/<report-id>/<file-name>`.

Read-only: only GET requests are made. No data is ever modified.

Usage:
  python scripts/export_emr.py --url https://user:pass@host:port/medic [--scope ...] [--out DIR]
"""

import argparse
import json
import os
import sys

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emr_common import (EmrDb, attachment_names, classify_contacts, flatten,
                        iso_datetime, is_emr_report, sanitize_filename,
                        timestamp_stamp)


def fixed_columns_first(columns, priority):
    """Order columns: priority ones first (in given order), rest sorted."""
    present = [c for c in priority if c in columns]
    rest = sorted(c for c in columns if c not in priority)
    return present + rest


def collect_report_rows(reports, participants, camps):
    """Map each EMR report to its participant and camp by exact _id."""
    rows = []
    for doc in reports:
        contact = doc.get('contact') or {}
        participant_id = contact.get('_id') if isinstance(contact, dict) else None
        parent = contact.get('parent') or {}
        camp_id = parent.get('_id') if isinstance(parent, dict) else None
        participant = participants.get(participant_id) if participant_id else None
        camp = camps.get(camp_id) if camp_id else None

        fields = flatten(doc.get('fields') or {})
        row = {
            '_id': doc.get('_id'),
            'form': doc.get('form'),
            'content_type': doc.get('content_type'),
            'reported_date': iso_datetime(doc.get('reported_date')),
            'reported_date_ms': doc.get('reported_date'),
            'from': doc.get('from'),
            'participant_id': participant_id,
            'camp_id': camp_id,
            'participant_name': participant.get('name') if participant else None,
            'camp_name': camp.get('name') if camp else None,
            'form_version': doc.get('form_version'),
            'hidden_fields': doc.get('hidden_fields'),
            'geolocation': doc.get('geolocation'),
            'geolocation_log': doc.get('geolocation_log'),
            'attachments': attachment_names(doc),
        }
        row.update(fields)
        rows.append(row)
    return rows


def flatten_contact_columns(doc, link_cols):
    """Flatten a contact doc, carrying exact-id link columns forward."""
    fields = flatten({k: v for k, v in doc.items()
                      if k not in ('_id', '_rev', 'parent', '_attachments')})
    row = {'_id': doc.get('_id')}
    row.update(link_cols)
    row.update(fields)
    row['attachments'] = attachment_names(doc)
    return row


def write_sheet(wb, name, rows):
    """Schema-generic sheet writer: columns = union of all row keys."""
    ws = wb.create_sheet(name)
    if not rows:
        ws.append(['_id'])
        return ws
    columns = list(rows[0].keys())
    for row in rows[1:]:
        for key in row.keys():
            if key not in columns:
                columns.append(key)
    ws.append(columns)
    for row in rows:
        ws.append([json.dumps(row.get(col), ensure_ascii=False)
                   if isinstance(row.get(col), (dict, list))
                   else row.get(col) for col in columns])
    return ws


def build_workbook(scope, db):
    docs = db.fetch_all_docs()
    camps, participants = classify_contacts(docs)
    reports = [d for d in docs if is_emr_report(d)]

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    if scope == 'all':
        camp_rows = [flatten_contact_columns(d, {}) for d in camps.values()]
        part_rows = [flatten_contact_columns(d, {'camp_id': (d.get('parent') or {}).get('_id')})
                     for d in participants.values()]
        report_rows = collect_report_rows(reports, participants, camps)
        write_sheet(wb, 'Camps', camp_rows)
        write_sheet(wb, 'Participants', part_rows)
        write_sheet(wb, 'Reports', report_rows)

    elif scope.startswith('camp='):
        camp_id = scope.split('=', 1)[1]
        camp = camps.get(camp_id)
        if not camp:
            raise SystemExit(f'camp not found: {camp_id}')
        camp_rows = [flatten_contact_columns(camp, {})]
        part_rows = [flatten_contact_columns(d, {'camp_id': camp_id})
                     for d in participants.values()
                     if (d.get('parent') or {}).get('_id') == camp_id]
        camp_participant_ids = {r['_id'] for r in part_rows}
        report_rows = collect_report_rows(reports, participants, camps)
        report_rows = [r for r in report_rows if r['camp_id'] == camp_id]
        write_sheet(wb, 'Camp', camp_rows)
        write_sheet(wb, 'Participants', part_rows)
        write_sheet(wb, 'Reports', report_rows)

    elif scope.startswith('participants_in_camp='):
        camp_id = scope.split('=', 1)[1]
        part_rows = [flatten_contact_columns(d, {'camp_id': camp_id})
                     for d in participants.values()
                     if (d.get('parent') or {}).get('_id') == camp_id]
        report_rows = collect_report_rows(reports, participants, camps)
        report_rows = [r for r in report_rows if r['camp_id'] == camp_id]
        write_sheet(wb, 'Participants', part_rows)
        write_sheet(wb, 'Reports', report_rows)

    elif scope.startswith('participant='):
        participant_id = scope.split('=', 1)[1]
        participant = participants.get(participant_id)
        if not participant:
            raise SystemExit(f'participant not found: {participant_id}')
        part_rows = [flatten_contact_columns(
            participant, {'camp_id': (participant.get('parent') or {}).get('_id')})]
        report_rows = collect_report_rows(reports, participants, camps)
        report_rows = [r for r in report_rows if r['participant_id'] == participant_id]
        write_sheet(wb, 'Participant', part_rows)
        write_sheet(wb, 'Reports', report_rows)

    else:
        raise SystemExit(f'unknown scope: {scope}')

    return wb


def default_output_name(scope, wb, db=None):
    stamp = timestamp_stamp()
    if scope == 'all':
        return f'satoru-emr-all-data-{stamp}.xlsx'
    if scope.startswith('camp='):
        camp_sheet = wb['Camp']
        name = None
        header = [c.value for c in camp_sheet[1]]
        if 'name' in header:
            name = camp_sheet[2][header.index('name')].value
        return f'satoru-emr-camp-{sanitize_filename(name, "camp")}-{stamp}.xlsx'
    if scope.startswith('participants_in_camp='):
        camp_id = scope.split('=', 1)[1]
        camp_name = None
        if db:
            camp_doc = db.fetch_doc(camp_id)
            camp_name = camp_doc.get('name') if camp_doc else None
        return (f'satoru-emr-camp-{sanitize_filename(camp_name or camp_id, "camp")}'
                f'-participants-{stamp}.xlsx')
    if scope.startswith('participant='):
        part_sheet = wb['Participant']
        header = [c.value for c in part_sheet[1]]
        cr = part_sheet[2][header.index('cr_no')].value if 'cr_no' in header else None
        name = part_sheet[2][header.index('name')].value if 'name' in header else None
        label = cr or name or scope.split('=', 1)[1]
        return f'satoru-emr-participant-{sanitize_filename(label, "participant")}-{stamp}.xlsx'
    raise SystemExit(f'unknown scope: {scope}')


def main():
    parser = argparse.ArgumentParser(description='Satoru EMR -> Excel exporter (read-only)')
    parser.add_argument('--url', required=True, help='CouchDB URL, e.g. https://user:pass@host:port/medic')
    parser.add_argument('--scope', default='all',
                        help='all | camp=<campId> | participants_in_camp=<campId> | participant=<participantId>')
    parser.add_argument('--out', default='.', help='output directory (default: current directory)')
    parser.add_argument('--verify', action='store_true', help='verify TLS certificates (default: off for self-signed)')
    args = parser.parse_args()

    db = EmrDb(args.url, verify=args.verify)
    wb = build_workbook(args.scope, db)
    filename = default_output_name(args.scope, wb, db)
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, filename)
    wb.save(path)
    for ws in wb.worksheets:
        print(f'  {ws.title}: {ws.max_row - 1} rows x {ws.max_column} cols')
    print(f'wrote {path}')


if __name__ == '__main__':
    main()
