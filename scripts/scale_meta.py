"""scale_meta.py - single source of truth for scale report metadata.

Parses the actual form definitions (forms/app/*.xml) - the same files cht-conf
uploads - and derives, for each scale (ddst, dst, moca_assessment, vineland):

  * field labels        (from XForm body <label> / itext English translations)
  * group labels        (age bands / domains / sections, in form order)
  * choice maps         (per field: stored value -> human label, from the
                         form's own <instance> lists and itext blocks)
  * results             (calculated scoring/result fields, in display order)
  * report_display config (consumed by the cht-core report patch:
                         hide internal fields, join CA display, note values,
                         per-item score joins, empty suppression)

Nothing here invents question text or choice meanings - everything is read
from the form XML. Python 3.8+, stdlib only.
"""

import json
import os
import re
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMS_DIR = os.path.join(REPO_ROOT, 'forms', 'app')

SCALES = {
    'ddst': {
        'file': 'ddst.xml',
        'title': 'Denver Developmental Screening Test II (DDST-II)',
    },
    'dst': {
        'file': 'dst.xml',
        'title': 'Developmental Screening Test (DST)',
    },
    'moca_assessment': {
        'file': 'moca_assessment.xml',
        'title': 'Montreal Cognitive Assessment (MoCA)',
    },
    'vineland': {
        'file': 'vineland.xml',
        'title': 'Vineland-style Social Maturity Scale (VSMS)',
    },
}

# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def _local(tag):
    """Strip any xml namespace: '{ns}name' -> 'name'."""
    return tag.rsplit('}', 1)[-1]


def _children(elem, name):
    return [c for c in elem if _local(c.tag) == name]


def _child(elem, name):
    for c in elem:
        if _local(c.tag) == name:
            return c
    return None


def _text(elem):
    return ''.join(elem.itertext()).strip() if elem is not None else ''


def parse_form_xml(path):
    """Parse a form XML into raw pieces needed downstream."""
    tree = ET.parse(path)
    html = tree.getroot()
    head = _child(html, 'head')
    body = _child(html, 'body')
    model = None
    for cand in _children(head, 'model'):
        model = cand
        break

    # -- itext: first translation (en) block, id -> text ------------------
    itext = {}
    itext_elem = _child(model, 'itext') if model is not None else None
    if itext_elem is not None:
        en = None
        for tr in _children(itext_elem, 'translation'):
            if tr.get('lang') == 'en':
                en = tr
                break
        if en is None and _children(itext_elem, 'translation'):
            en = _children(itext_elem, 'translation')[0]
        if en is not None:
            for t in _children(en, 'text'):
                itext[t.get('id')] = _text(t)

    # -- named choice instances: instance id -> [(name, label)] -----------
    choice_lists = {}
    for inst in _children(model, 'instance'):
        inst_id = inst.get('id')
        if not inst_id or inst_id in ('contact-summary', 'user-contact-summary'):
            continue
        root = _child(inst, 'root')
        if root is None:
            continue
        items = []
        for item in _children(root, 'item'):
            name = _text(_child(item, 'name'))
            if not name:
                continue
            label_elem = _child(item, 'label')
            itext_id_elem = _child(item, 'itextId')
            if label_elem is not None:
                label = _text(label_elem)
            elif itext_id_elem is not None:
                label = itext.get(_text(itext_id_elem), name)
            else:
                label = name
            items.append((name, label))
        if items:
            choice_lists[inst_id] = items

    # -- instance field order (model/instance/data) -----------------------
    field_order = []

    def walk_instance(elem, prefix):
        for c in elem:
            name = _local(c.tag)
            if name in ('meta', 'inputs'):
                continue
            path = prefix + name
            if len(list(c)):
                # has children: a group
                field_order.append(('group', path))
                walk_instance(c, path + '.')
            else:
                field_order.append(('leaf', path))

    data = None
    for inst in _children(model, 'instance'):
        if not inst.get('id'):
            data = _child(inst, 'data') or inst
            break
    if data is not None:
        walk_instance(data, '')

    # -- body: groups and fields, in display order ------------------------
    body_groups = []   # [(ref, group_label, [field dicts])]
    body_loose = []    # top-level fields (ref, label, hint, itemset)

    def parse_field(elem):
        ref = elem.get('ref') or ''
        path = ref.split('/')[-1] if ref else ''
        # full path relative to /data: replace '/' separators
        parts = [p for p in ref.split('/') if p and p != 'data']
        fpath = '.'.join(parts)
        label = _text(_child(elem, 'label'))
        hint = _text(_child(elem, 'hint'))
        itemset = None
        iset = _child(elem, 'itemset')
        if iset is not None:
            nodeset = iset.get('nodeset') or ''
            m = re.search(r"instance\('([^']+)'\)", nodeset)
            itemset = m.group(1) if m else None
        return {
            'ref': ref,
            'path': fpath,
            'name': path,
            'label': label,
            'hint': hint,
            'itemset': itemset,
        }

    def walk_body(parent, depth):
        groups = []
        for elem in parent:
            tag = _local(elem.tag)
            if tag == 'group':
                ref = elem.get('ref') or ''
                parts = [p for p in ref.split('/') if p and p != 'data']
                gpath = '.'.join(parts)
                glabel = _text(_child(elem, 'label'))
                children = []
                for sub in elem:
                    stag = _local(sub.tag)
                    if stag in ('select1', 'select', 'input', 'upload',
                                'repeat'):
                        children.append(parse_field(sub))
                    elif stag == 'group':
                        sub_groups = walk_body(sub, depth + 1)
                        for sg in sub_groups:
                            children.append({'__group__': sg})
                groups.append({
                    'ref': ref,
                    'path': gpath,
                    'label': glabel,
                    'depth': depth,
                    'fields': children,
                })
        return groups

    all_groups = walk_body(body, 0)

    # fields that sit directly in <h:body> outside any group
    direct_children = []
    for elem in body:
        tag = _local(elem.tag)
        if tag in ('select1', 'select', 'input', 'upload'):
            direct_children.append(parse_field(elem))

    title = _text(_child(head, 'title'))

    return {
        'title': title,
        'itext': itext,
        'choice_lists': choice_lists,
        'field_order': field_order,
        'groups': all_groups,
        'body_loose': direct_children,
    }


# ---------------------------------------------------------------------------
# Flatten body structure into ordered field list with group membership
# ---------------------------------------------------------------------------


def flatten_fields(parsed):
    """Return ordered list of dicts:
       {'type': 'group'|'field', 'path':..., 'label':..., 'itemset':...}
    Groups carry their nested order; fields keep form order."""
    out = []

    def emit_group(g):
        if g['path']:
            out.append({'type': 'group', 'path': g['path'],
                        'label': g['label']})
        for f in g['fields']:
            if '__group__' in f:
                emit_group(f['__group__'])
            else:
                out.append({'type': 'field', 'path': f['path'],
                            'label': f['label'], 'hint': f['hint'],
                            'itemset': f['itemset']})

    for g in parsed['groups']:
        emit_group(g)
    for f in parsed['body_loose']:
        out.append({'type': 'field', 'path': f['path'], 'label': f['label'],
                    'hint': f['hint'], 'itemset': f['itemset']})
    return out


def build_choice_maps(parsed, flat):
    """Per-field choice maps from the form's own lists.

    Resolution order: explicit <item> children (none in these forms),
    then <itemset instance('x')> -> model instance x (labels may come from
    itext). Only fields that reference a choice list get a map.
    """
    maps = {}
    for f in flat:
        if f['type'] != 'field' or not f.get('itemset'):
            continue
        items = parsed['choice_lists'].get(f['itemset'])
        if not items:
            continue
        maps[f['path']] = {name: label for name, label in items}
    return maps


# ---------------------------------------------------------------------------
# Per-scale report configuration
# ---------------------------------------------------------------------------


def _all_field_paths(parsed):
    """Every leaf path stored in the doc (from the model instance), covering
    calculated fields that never appear in the form body."""
    paths = []
    for kind, path in parsed.get('field_order', []):
        if kind == 'leaf':
            paths.append(path)
    return paths


def _hidden_scale_fields(flat, form, parsed=None):
    """Internal/calculation field paths to hide, derived programmatically.

    Scans both body fields and model-instance leaves so calculated fields
    (item_N_score, band_N_*, *_delayed) are covered too.
    """
    hidden = {
        'patient_uuid',
        'screened_by',
        'scoring_version',
        'result_complete',
        'result_incomplete',
        'result_invalid',
    }
    every = [item['path'] for item in flat if item['type'] == 'field']
    if parsed is not None:
        every = every + [p for p in _all_field_paths(parsed) if p not in every]
    if form in ('vineland', 'dst'):
        hidden |= {
            'g_child.ca_days',
            'g_child.ca_months_dec',
            'g_child.ca_band',
            'g_child.age_valid',
            'g_child.show_all',
            'show_all',
            'ca_band',
            'score_status',
        }
    if form == 'vineland':
        hidden |= {
            'g_child.ca_months_floor',
            'g_child.ca_years_display',
            'g_child.ca_rem_months',
        }
        # per-item score fields are joined into their question rows instead
        for path in every:
            if re.match(r'item_\d+_score$', path):
                hidden.add(path)
    if form == 'dst':
        # 18 intermediate band calculation blocks (band_N_*)
        for path in every:
            if re.match(r'band_\d+_(passed|failed|not_assessed|earned)', path):
                hidden.add(path)
    if form == 'ddst':
        hidden |= {
            'g_meta.ca_days',
            'g_meta.ca_months_dec',
            'g_meta.ca_band',
            'g_meta.show_all',
            'g_meta.ca_note',
            'caution_domains',
            'any_suspect',
            'result_note',  # composed note; duplicated by the results rows
        }
        # per-item and per-domain delayed flags
        for path in every:
            if path.endswith('_delayed'):
                hidden.add(path)
    if form == 'moca_assessment':
        hidden |= {
            'patient_sex',
            'patient_age',
            'patient_phone',
            'patient_education',
            'moca_delayed_total',   # duplicate of moca_memory_total
            'memory_words',
        }
        for path in every:
            if path.endswith('_inst'):
                hidden.add(path)
    return sorted(hidden)


# Static note fields: stored value is empty; the meaningful text is the
# form label. build_report_display resolves the actual label text from the
# parsed form so no wording is duplicated or invented here.
NOTE_VALUES = {
    'vineland': {
        'g_intro.vineland_disclaimer': None,
        'g_child.dob_warning': None,
    },
    'dst': {
        'g_intro.dst_disclaimer': None,
        'g_child.dob_warning': None,
    },
    'ddst': {
        'g_meta.dob_warning': None,
    },
    'moca_assessment': {},
}

# Short display labels for note-value fields (their VALUE is the full form
# text, e.g. the disclaimer sentence). Without this, the label and value
# would both show the same long text. Purely presentational UI wording.
NOTE_LABELS = {
    'vineland': {
        'g_intro.vineland_disclaimer': 'Disclaimer',
        'g_child.dob_warning': 'Date of birth warning',
    },
    'dst': {
        'g_intro.dst_disclaimer': 'Disclaimer',
        'g_child.dob_warning': 'Date of birth warning',
    },
    'ddst': {
        'g_meta.dob_warning': 'Date of birth warning',
    },
    'moca_assessment': {},
}

# Fields whose value must be kept even when empty (warnings).
KEEP_EMPTY = {
    'vineland': ['g_child.dob_warning'],
    'dst': ['g_child.dob_warning'],
    'ddst': ['g_meta.dob_warning'],
    'moca_assessment': [],
}

# Joined human-readable chronological-age rows.
# target: field path whose value/label is replaced.
#   'years_months_parts': parts = [yearsField, remainingMonthsField]
#   'days_to_years_months': parts = [daysField]
# label: translation key shown for the joined row (shared across scales;
# defined once in messages-en.properties).
CA_LABEL_KEY = 'report.scale.chronological_age'
JOIN_FIELDS = {
    'vineland': [
        {'target': 'g_child.ca_display', 'format': 'years_months_parts',
         'parts': ['g_child.ca_years_display', 'g_child.ca_rem_months'],
         'label': CA_LABEL_KEY},
    ],
    'dst': [
        {'target': 'g_child.ca_days', 'format': 'days_to_years_months',
         'parts': ['g_child.ca_days'], 'label': CA_LABEL_KEY},
    ],
    'ddst': [
        {'target': 'g_meta.ca_days', 'format': 'days_to_years_months',
         'parts': ['g_meta.ca_days'], 'label': CA_LABEL_KEY},
    ],
    'moca_assessment': [],
}

# Date fields to format as readable dates in the report.
DATE_FIELDS = {
    'vineland': ['g_child.assessment_date', 'g_child.child_dob'],
    'dst': ['g_child.assessment_date', 'g_child.child_dob'],
    'ddst': ['g_meta.test_date', 'g_meta.child_dob'],
    'moca_assessment': ['g_admin.assessment_datetime'],
}

# Calculated result fields shown in the results summary, in order.
RESULT_FIELDS = {
    'vineland': [
        'raw_score', 'total_yes_items', 'total_no_items',
        'total_not_assessed_items', 'social_age_months', 'social_age_years',
        'social_age_remaining_months', 'social_quotient_raw',
        'social_quotient_rounded', 'sq_interpretation',
    ],
    'dst': [
        'total_passed_items', 'total_failed_items',
        'total_not_assessed_items', 'developmental_age_months',
        'developmental_age_years', 'developmental_age_remaining_months',
        'developmental_quotient_raw', 'developmental_quotient_rounded',
    ],
    'ddst': [
        'd_ps_status', 'd_fm_status', 'd_lang_status', 'd_gm_status',
        'overall',
    ],
    'moca_assessment': [
        'moca_visuospatial_total', 'moca_naming_total', 'moca_memory_total',
        'moca_attention_total', 'moca_language_total',
        'moca_abstraction_total', 'moca_orientation_total',
        'moca_raw_total', 'moca_education_adj', 'moca_total_score',
        'moca_interpretation',
    ],
}

# Question -> item score field (per-item scores joined into the answer row).
def _score_fields(form, count):
    return {f'item_{i}': f'item_{i}_score' for i in range(1, count + 1)}


SCORE_FIELDS = {
    'vineland': _score_fields('vineland', 89),
    'dst': {},
    'ddst': {},
    'moca_assessment': {},
}

# Free-text/notes fields (kept visible, suppressed when empty).
NOTES_FIELDS = {
    'vineland': ['na_reason', 'clinical_notes', 'scoring_notes'],
    'dst': ['na_reason', 'clinical_notes'],
    'ddst': [],
    'moca_assessment': [],
}

# Supporting-document fields (attachment leaves; suppressed when empty).
SUPPORTING_PREFIX = 'g_supporting_docs.'


def build_report_display(form, flat, choice_maps, parsed=None):
    """The report_display entry for one scale (consumed by cht-core patch)."""
    hidden = _hidden_scale_fields(flat, form, parsed)
    # join targets must stay visible
    join_targets = {j['target'] for j in JOIN_FIELDS[form]}
    hidden = [h for h in hidden if h not in join_targets]

    labels = {item['path']: item['label'] for item in flat}

    def _note_text(path):
        text = ' '.join((labels.get(path) or '').split())
        # strip the form's emphasis markers; Enketo renders them, the
        # report does not
        return text.replace('**', '')

    # score join map: question path (with group prefix) -> score field.
    # Vineland items live in band groups but their *_score fields are
    # top-level, so build full paths from the flat body order.
    score_fields = {}
    for q, s in SCORE_FIELDS[form].items():
        matches = [item['path'] for item in flat
                   if item['type'] == 'field' and item['path'].endswith('.' + q)]
        if matches:
            score_fields[matches[0]] = s
        else:
            score_fields[q] = s
    # questions with score joins get an "Answer:" prefix in the report
    return {
        'title_key': f'report.{form}._title',
        'hide_fields': hidden,
        'suppress_empty': True,
        'keep_empty': KEEP_EMPTY[form],
        'choice_map': {p: m for p, m in choice_maps.items()},
        'score_fields': score_fields,
        'join_fields': JOIN_FIELDS[form],
        'note_values': {
            p: _note_text(p) for p in NOTE_VALUES[form]
        },
        'date_fields': DATE_FIELDS[form],
        'notes_fields': NOTES_FIELDS[form],
        'result_fields': RESULT_FIELDS[form],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_cache = {}


def get_scale_meta(form):
    """Parsed + derived metadata for one scale (cached)."""
    if form not in _cache:
        path = os.path.join(FORMS_DIR, SCALES[form]['file'])
        parsed = parse_form_xml(path)
        flat = flatten_fields(parsed)
        choice_maps = build_choice_maps(parsed, flat)
        labels = {}
        for item in flat:
            if item['type'] == 'group':
                labels[item['path']] = item['label']
            else:
                labels[item['path']] = item['label']
        _cache[form] = {
            'form': form,
            'title': SCALES[form]['title'],
            'xml_title': parsed['title'],
            'flat': flat,
            'labels': labels,
            'choice_maps': choice_maps,
            'report_display': build_report_display(form, flat, choice_maps,
                                                   parsed),
            'result_fields': RESULT_FIELDS[form],
            'notes_fields': NOTES_FIELDS[form],
        }
    return _cache[form]


def all_scale_metas():
    return {form: get_scale_meta(form) for form in SCALES}


def build_message_keys(form):
    """report.<form>.<path> -> label for every group and field that should
    be displayable. Hidden fields are included too (harmless, keeps the
    file complete and future-proof)."""
    meta = get_scale_meta(form)
    prefix = f'report.{form}.'
    out = {f'{prefix}_title': meta['title']}
    for path, label in meta['labels'].items():
        if label:
            out[prefix + path] = label
    # note-value fields get short display labels (value keeps the full text)
    for path, short in NOTE_LABELS[form].items():
        if prefix + path in out or short:
            out[prefix + path] = short
    return out


def build_report_display_config():
    """Full report_display settings object for app_settings.json."""
    return {form: get_scale_meta(form)['report_display']
            for form in SCALES}


if __name__ == '__main__':
    meta = all_scale_metas()
    for form, m in meta.items():
        n_fields = sum(1 for i in m['flat'] if i['type'] == 'field')
        n_groups = sum(1 for i in m['flat'] if i['type'] == 'group')
        print(f"{form}: {n_fields} fields, {n_groups} groups, "
              f"{len(m['choice_maps'])} choice-mapped fields, "
              f"{len(m['report_display']['hide_fields'])} hidden, "
              f"title={m['title']!r}")
    print(json.dumps(meta['vineland']['choice_maps']['g_y0_1.item_1'],
                     indent=2))
