"""scale_export.py - human-readable Excel row/section builders for scales.

Shared by the individual-participant export and the camp workbook so both
present identical labels. Consumer: scripts/export_emr.py.

Sources of truth (no hard-coded clinical text):
  * forms/app/*.xml                     - via scale_meta.py (order, groups,
                                          labels, choice maps, display config)
  * translations/messages-en.properties - result-field and group labels

Mirrors the cht-core report patch exactly: same hide list, choice-value
resolution, joined chronological age, per-item score columns, note values,
empty suppression. Scoring is never recalculated - stored results are used.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scale_meta import SCALES, get_scale_meta, JOIN_FIELDS, NOTE_LABELS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESSAGES_PATH = os.path.join(REPO_ROOT, 'translations', 'messages-en.properties')

CA_KEY = 'report.scale.chronological_age'
FIXED_INFO = ['Participant ID', 'Participant', 'DOB', 'Assessment date',
              'Submitted by']

# DOB / assessment-date fields are already covered by the fixed info columns
# and must not appear as question columns/rows a second time.
INFO_FIELD_PATHS = {
    'ddst': ('g_meta.child_dob', 'g_meta.test_date'),
    'dst': ('g_child.child_dob', 'g_child.assessment_date'),
    'vineland': ('g_child.child_dob', 'g_child.assessment_date'),
    'moca_assessment': ('g_admin.assessment_datetime',),
}

# Short sheet names for the camp workbook
SHEET_TITLES = {
    'ddst': 'DDST-II',
    'dst': 'DST',
    'moca_assessment': 'MoCA',
    'vineland': 'VSMS',
}

_messages_cache = None


def load_messages():
    global _messages_cache
    if _messages_cache is None:
        _messages_cache = {}
        with open(MESSAGES_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                _messages_cache[key.strip()] = value.strip()
    return _messages_cache


def sheet_title(form):
    return SHEET_TITLES[form]


def label_for(form, path, fallback=None):
    key = f'report.{form}.{path}'
    label = load_messages().get(key)
    if label:
        return label
    return fallback if fallback is not None else path


def _lookup(values, path):
    cur = values
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _format_date(value):
    if value in (None, ''):
        return None
    text = str(value)
    if text.endswith('T00:00:00.000Z'):
        return text[:10]
    if text.endswith('Z') and 'T' in text:
        return text[:16].replace('T', ' ')
    return text


def _ca_value(form, fields):
    for j in JOIN_FIELDS[form]:
        if j['format'] == 'years_months_parts':
            years = _lookup(fields, j['parts'][0])
            months = _lookup(fields, j['parts'][1])
            if years in (None, '') or months in (None, ''):
                continue
            years = int(float(years))
            months = int(float(months))
            if years <= 0:
                return f"{months} month{'s' if months != 1 else ''}"
            return (f"{years} year{'s' if years != 1 else ''} "
                    f"{months} month{'s' if months != 1 else ''}")
        if j['format'] == 'days_to_years_months':
            days = _lookup(fields, j['parts'][0])
            try:
                days = float(days)
            except (TypeError, ValueError):
                continue
            if days < 0:
                continue
            years = int(days // 365.25)
            months = int((days - years * 365.25) // 30.4375)
            if years <= 0 and months <= 0:
                return f'{int(days)} days'
            if years <= 0:
                return f"{months} month{'s' if months != 1 else ''}"
            return (f"{years} year{'s' if years != 1 else ''} "
                    f"{months} month{'s' if months != 1 else ''}")
    return None


class _Walker:
    """One walk over the form's fields shared by headers() and row()."""

    def __init__(self, form):
        meta = get_scale_meta(form)
        self.form = form
        self.cfg = meta['report_display']
        self.flat = meta['flat']
        self.hidden = set(self.cfg['hide_fields'])
        self.join_targets = {j['target'] for j in JOIN_FIELDS[form]}

    def is_displayable(self, path):
        if path == 'patient_uuid' or path in self.join_targets:
            return False
        if path in self.hidden:
            return False
        for h in self.hidden:
            if path.startswith(h + '.'):
                return False
        return True

    def is_question(self, item):
        path = item['path']
        if item['type'] != 'field':
            return False
        if path == 'patient_uuid' or path in INFO_FIELD_PATHS[self.form]:
            return False
        if path in self.join_targets:  # CA is shown as its own joined row
            return False
        if path in self.hidden:
            return False
        for h in self.hidden:
            if path.startswith(h + '.'):
                return False
        if (path in self.cfg['result_fields']
                or path in self.cfg['notes_fields']
                or path.startswith('g_supporting_docs.')):
            return False
        return True

    def label(self, item):
        path = item['path']
        # note-value fields show a short label (their value is the full text)
        if path in NOTE_LABELS[self.form]:
            return NOTE_LABELS[self.form][path]
        label = label_for(self.form, path, item.get('label') or None)
        if label is None or label.startswith('report.'):
            label = item.get('label') or item['path']
        return label

    def value(self, item, fields):
        path = item['path']
        raw = _lookup(fields, path)
        cfg = self.cfg
        if path in cfg.get('note_values', {}):
            return cfg['note_values'][path]
        if raw in (None, ''):
            return None
        cmap = cfg['choice_map'].get(path)
        if cmap and isinstance(raw, str) and raw in cmap:
            return cmap[raw]
        if path in cfg.get('date_fields', []):
            return _format_date(raw)
        return raw


def question_items(form):
    """Ordered question field items (the per-question columns/rows)."""
    w = _Walker(form)
    return [item for item in w.flat if w.is_question(item)]


def scale_headers(form):
    """Full ordered human column list for a scale sheet (camp export)."""
    w = _Walker(form)
    cfg = w.cfg
    cols = []

    def add(col):
        if col not in cols:
            cols.append(col)

    for f in FIXED_INFO:
        add(f)
    for item in w.flat:
        if not w.is_question(item):
            continue
        label = w.label(item)
        add(label)
        if item['path'] in cfg['score_fields']:
            add(f'{label} - score')
    add(load_messages().get(CA_KEY, 'Chronological age'))
    for path in cfg['result_fields']:
        add(label_for(form, path, path))
    for path in sorted(cfg['notes_fields']):
        add(label_for(form, path, path))
    add('Attachments')
    return cols


def scale_row(form, fields, participant, submitter, attachments):
    """Values aligned 1:1 with scale_headers(form) for one report."""
    w = _Walker(form)
    cfg = w.cfg
    row = {
        'Participant ID': participant.get('cr_no') or participant.get('patient_id')
        or _lookup(fields, 'patient_id') or '',
        'Participant': participant.get('name') or _lookup(fields, 'patient_name') or '',
        'DOB': '',
        'Assessment date': '',
        'Submitted by': submitter or '',
    }
    # DOB comes from the scale form (participant contacts have none)
    dob_path = {'ddst': 'g_meta.child_dob'}.get(form, 'g_child.child_dob')
    dob = _lookup(fields, dob_path)
    if dob:
        row['DOB'] = _format_date(dob)
    # assessment date from the form
    adate_path = {'ddst': 'g_meta.test_date'}.get(form,
                                                  'g_child.assessment_date')
    adate = _lookup(fields, adate_path)
    if form == 'moca_assessment':
        adate = _lookup(fields, 'g_admin.assessment_datetime') or adate
    if adate:
        row['Assessment date'] = _format_date(adate)

    values = [row[f] for f in FIXED_INFO]
    for item in w.flat:
        if not w.is_question(item):
            continue
        v = w.value(item, fields)
        values.append('' if v is None else v)
        if item['path'] in cfg['score_fields']:
            score = _lookup(fields, cfg['score_fields'][item['path']])
            values.append('' if score in (None, '') else score)
    ca = _ca_value(form, fields)
    values.append(ca or '')
    for path in cfg['result_fields']:
        raw = _lookup(fields, path)
        if raw in (None, ''):
            values.append('')
            continue
        cmap = cfg['choice_map'].get(path)
        if cmap and isinstance(raw, str) and raw in cmap:
            raw = cmap[raw]
        values.append(raw)
    for path in sorted(cfg['notes_fields']):
        raw = _lookup(fields, path)
        values.append('' if raw in (None, '') else raw)
    values.append(', '.join(attachments) if attachments else '')
    return values


def scale_sections(form, fields, participant, submitter, attachments):
    """Individual-report layout: ordered [(section, rows)], rows are
    (label, value, score_or_None). Mirrors the report patch."""
    w = _Walker(form)
    cfg = w.cfg
    sections = []

    # ---- assessment information ----
    info_rows = []
    meta_info = {
        'Participant ID': participant.get('cr_no')
        or _lookup(fields, 'patient_id') or '',
        'Participant': participant.get('name')
        or _lookup(fields, 'patient_name') or '',
        'Submitted by': submitter or '',
    }
    for k, v in meta_info.items():
        if v not in (None, ''):
            info_rows.append((k, v, None))
    dob_path = {'ddst': 'g_meta.child_dob'}.get(form, 'g_child.child_dob')
    dob = _format_date(_lookup(fields, dob_path))
    if dob:
        info_rows.append(('Date of birth', dob, None))
    adate_path = {'ddst': 'g_meta.test_date'}.get(form,
                                                  'g_child.assessment_date')
    if form == 'moca_assessment':
        adate_path = 'g_admin.assessment_datetime'
    adate = _format_date(_lookup(fields, adate_path))
    if adate:
        info_rows.append(('Assessment date', adate, None))
    ca = _ca_value(form, fields)
    if ca:
        info_rows.append((load_messages().get(CA_KEY, 'Chronological age'),
                          ca, None))
    # remaining non-question, non-result fields with human labels
    skip = set(cfg['result_fields']) | set(cfg['notes_fields']) | set(meta_info)
    for item in w.flat:
        if not w.is_question(item):
            continue
        path = item['path']
        if path in (dob_path, adate_path):
            continue
        if path in cfg.get('note_values', {}) or path in skip:
            continue
        v = w.value(item, fields)
        if v in (None, ''):
            continue
        info_rows.append((w.label(item), v, None))
    if info_rows:
        sections.append(('Assessment information', info_rows))

    # ---- questions grouped by the form's own groups ----
    current = None
    q_rows = []
    for item in w.flat:
        if item['type'] == 'group':
            if q_rows and current:
                sections.append((current, q_rows))
                q_rows = []
            current = w.label(item)
            continue
        if not w.is_question(item):
            continue
        v = w.value(item, fields)
        score = None
        if item['path'] in cfg['score_fields']:
            score = _lookup(fields, cfg['score_fields'][item['path']])
        if v in (None, '') and score in (None, ''):
            continue
        q_rows.append((w.label(item), '' if v is None else v,
                       None if score in (None, '') else score))
    if q_rows:
        sections.append((current or 'Questions', q_rows))

    # ---- results ----
    res_rows = []
    for path in cfg['result_fields']:
        raw = _lookup(fields, path)
        if raw in (None, ''):
            continue
        cmap = cfg['choice_map'].get(path)
        if cmap and isinstance(raw, str) and raw in cmap:
            raw = cmap[raw]
        res_rows.append((label_for(form, path, path), raw, None))
    if res_rows:
        sections.append(('Scoring results', res_rows))

    # ---- notes ----
    note_rows = []
    for path in sorted(cfg['notes_fields']):
        raw = _lookup(fields, path)
        if raw in (None, ''):
            continue
        note_rows.append((label_for(form, path, path), raw, None))
    if note_rows:
        sections.append(('Notes', note_rows))

    # ---- supporting documents ----
    sup = fields.get('g_supporting_docs') or {}
    support_rows = []
    for key, value in sup.items():
        if value in (None, ''):
            continue
        support_rows.append((label_for(form, f'g_supporting_docs.{key}', key),
                             value, None))
    if attachments:
        support_rows.append(('Attachments', ', '.join(attachments), None))
    if support_rows:
        sections.append(('Supporting documents', support_rows))

    return sections
