"""Read-only Satoru EMR -> Excel exporter.

Produces one .xlsx per run. The workbook contents depend on --scope:

  all                      Sheets: Camps | Participants | Reports
  camp=<campId>            Sheets: Camp | Participants | Reports
  participants_in_camp=..  Sheets: Participants | Reports
  participant=<id>         Sheets: Participant | Reports
  camp-workbook=<campId>   One workbook per camp, organised by scale:
                           Participants | DDST-II | DST | MoCA | VSMS
                           (only scales actually completed in that camp;
                           one row per participant per scale sheet)
  participant-report=<id>  Human-readable workbook for one participant's
                           completed assessments: Participant sheet + one
                           sheet per completed scale (sectioned rows)

Relationships are by exact _id only:
  participant.parent._id  == campId
  report.contact._id      == participantId
  report.contact.parent._id == campId

NOTE: on a CHT doc, `report.contact` is the SUBMITTER's contact; the
subject of a scale report is `report.fields.patient_uuid` (== the
participant contact _id). The camp of a report is therefore derived from
the SUBJECT participant's parent, not from report.contact.parent.

Repeat-group choice (documented in requirements): arrays are stored as JSON
in a single cell (lossless, schema-generic). Attachments are NOT embedded in
Excel; the `attachments` column lists file names, referenced as
`attachment/<report-id>/<file-name>`.

Scale sheets (camp-workbook / participant-report) are built through
scripts/scale_export.py, which reads the form XMLs and the English
translation file - the same sources as the Reports UI - so labels can never
drift between UI and exports. Scoring fields are consumed as stored; no
score is recalculated.

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
import scale_export

SCALE_ORDER = ['ddst', 'dst', 'moca_assessment', 'vineland']
GENDER_LABELS = {'male': 'Male', 'female': 'Female'}


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


def subject_id_of(doc):
    """The assessed participant's contact _id (NOT the submitter)."""
    sid = (doc.get('fields') or {}).get('patient_uuid')
    return sid if isinstance(sid, str) and sid else None


def submitter_label(doc):
    """Human name (+phone) of the submitting user's contact."""
    contact = doc.get('contact') or {}
    if not isinstance(contact, dict):
        return None
    name = contact.get('name')
    phone = contact.get('phone')
    if name and phone:
        return f'{name} ({phone})'
    return name


def scale_reports_by_participant(reports, participant_ids):
    """form -> list of (doc, participant) for reports whose SUBJECT is one of
    participant_ids, ordered by reported_date (then _id for stability)."""
    by_form = {form: [] for form in SCALE_ORDER}
    for doc in reports:
        sid = subject_id_of(doc)
        if sid not in participant_ids:
            continue
        form = doc.get('form')
        if form in by_form:
            by_form[form].append(doc)
    for docs in by_form.values():
        docs.sort(key=lambda d: (d.get('reported_date') or 0, d.get('_id') or ''))
    return by_form


def write_scale_sheet(wb, form, reports, participants):
    """One row per completed assessment of `form`, human-readable columns."""
    ws = wb.create_sheet(scale_export.sheet_title(form))
    ws.append(scale_export.scale_headers(form))
    for doc in reports:
        participant = participants.get(subject_id_of(doc)) or {}
        ws.append(scale_export.scale_row(
            form,
            doc.get('fields') or {},
            participant,
            submitter_label(doc),
            attachment_names(doc),
        ))
    return ws


def build_camp_workbook(wb, camp_id, camp, participants, reports):
    """Participants sheet + one sheet per scale completed in the camp."""
    members = {pid: p for pid, p in participants.items()
               if (p.get('parent') or {}).get('_id') == camp_id}
    by_form = scale_reports_by_participant(reports, set(members))

    rows = []
    for pid, p in members.items():
        scales_done = [scale_export.sheet_title(f) for f in SCALE_ORDER
                       if any(subject_id_of(d) == pid for d in by_form[f])]
        rows.append({
            'Participant ID': p.get('cr_no'),
            'Name': p.get('name'),
            'Age': p.get('age'),
            'Gender': GENDER_LABELS.get(p.get('gender'), p.get('gender')),
            'Phone': p.get('phone'),
            'Hospital': p.get('hospital_name'),
            'Ward/Dept No': p.get('ward_dept_no'),
            'Address': p.get('address'),
            'Registration date': iso_datetime(p.get('registration_date')),
            'Scales completed': ', '.join(scales_done),
        })
    rows.sort(key=lambda r: (r.get('Participant ID') or '', r.get('Name') or ''))
    write_sheet(wb, 'Participants', rows)

    for form in SCALE_ORDER:
        if by_form[form]:
            write_scale_sheet(wb, form, by_form[form], participants)
    return by_form


def write_participant_sheet(wb, participant, camp, scales_done):
    """Field | Value summary sheet for one participant."""
    rows = [
        {'Field': 'Participant ID', 'Value': participant.get('cr_no')},
        {'Field': 'Name', 'Value': participant.get('name')},
        {'Field': 'Age', 'Value': participant.get('age')},
        {'Field': 'Gender', 'Value': GENDER_LABELS.get(participant.get('gender'),
                                                       participant.get('gender'))},
        {'Field': 'Phone', 'Value': participant.get('phone')},
        {'Field': 'Address', 'Value': participant.get('address')},
        {'Field': 'Hospital', 'Value': participant.get('hospital_name')},
        {'Field': 'Ward/Dept No', 'Value': participant.get('ward_dept_no')},
        {'Field': 'Camp', 'Value': camp.get('name') if camp else None},
        {'Field': 'Registration date',
         'Value': iso_datetime(participant.get('registration_date'))},
        {'Field': 'Education', 'Value': participant.get('education_level')},
        {'Field': 'Occupation', 'Value': participant.get('occupation')},
        {'Field': 'Referred by', 'Value': participant.get('referred_by')},
        {'Field': 'Referral department',
         'Value': participant.get('referral_department')},
        {'Field': 'Referral complaint',
         'Value': participant.get('referral_complaint')},
        {'Field': 'Notes', 'Value': participant.get('notes')},
        {'Field': 'Scales completed', 'Value': ', '.join(scales_done)},
    ]
    rows = [r for r in rows if r['Value'] not in (None, '')]
    return write_sheet(wb, 'Participant', rows)


def write_participant_scale_sheet(wb, form, doc, participant):
    """Sectioned human-readable sheet for one participant's completed scale."""
    ws = wb.create_sheet(scale_export.sheet_title(form))
    sections = scale_export.scale_sections(
        form,
        doc.get('fields') or {},
        participant,
        submitter_label(doc),
        attachment_names(doc),
    )
    for section, rows in sections:
        ws.append([section])
        ws.append(['Question / Field', 'Answer / Value', 'Score'])
        for label, value, score in rows:
            ws.append([label, value, score if score is not None else ''])
        ws.append([])
    return ws


def build_participant_report_workbook(wb, participant_id, participants, camps, reports):
    """Participant sheet + one sectioned sheet per completed scale."""
    participant = participants.get(participant_id)
    if not participant:
        raise SystemExit(f'participant not found: {participant_id}')
    camp = camps.get((participant.get('parent') or {}).get('_id'))
    by_form = scale_reports_by_participant(reports, {participant_id})
    scales_done = [scale_export.sheet_title(f) for f in SCALE_ORDER if by_form[f]]

    write_participant_sheet(wb, participant, camp, scales_done)
    for form in SCALE_ORDER:
        for doc in by_form[form]:  # a re-completed scale gets its own sheet copy
            write_participant_scale_sheet(wb, form, doc, participant)
    return by_form


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

    elif scope.startswith('camp-workbook='):
        camp_id = scope.split('=', 1)[1]
        camp = camps.get(camp_id)
        if not camp:
            raise SystemExit(f'camp not found: {camp_id}')
        build_camp_workbook(wb, camp_id, camp, participants, reports)

    elif scope.startswith('participant-report='):
        build_participant_report_workbook(
            wb, scope.split('=', 1)[1], participants, camps, reports)

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
    if scope.startswith('camp-workbook='):
        camp_id = scope.split('=', 1)[1]
        camp_name = None
        if db:
            camp_doc = db.fetch_doc(camp_id)
            camp_name = camp_doc.get('name') if camp_doc else None
        return (f'satoru-emr-camp-{sanitize_filename(camp_name or camp_id, "camp")}'
                f'-scales-{stamp}.xlsx')
    if scope.startswith('participant-report='):
        part_id = scope.split('=', 1)[1]
        label = part_id
        if db:
            part_doc = db.fetch_doc(part_id)
            if part_doc:
                label = part_doc.get('cr_no') or part_doc.get('name') or part_id
        return (f'satoru-emr-participant-{sanitize_filename(label, "participant")}'
                f'-report-{stamp}.xlsx')
    raise SystemExit(f'unknown scope: {scope}')


def main():
    parser = argparse.ArgumentParser(description='Satoru EMR -> Excel exporter (read-only)')
    parser.add_argument('--url', required=True, help='CouchDB URL, e.g. https://user:pass@host:port/medic')
    parser.add_argument('--scope', default='all',
                        help='all | camp=<campId> | participants_in_camp=<campId> | '
                             'participant=<participantId> | camp-workbook=<campId> | '
                             'participant-report=<participantId>')
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
