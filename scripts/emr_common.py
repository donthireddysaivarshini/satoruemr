"""Shared helpers for the Satoru EMR backup/export scripts.

Connection and data-model utilities that are deliberately schema-generic:
new forms, fields, and contact types are captured automatically without any
hard-coded form/field names. Only the EMR exclusion rules (training forms,
SMS/kujua records) and the camp->participant->report parent relationships
are assumed, because those are documented requirements of the project.

Every function here is strictly read-only against CouchDB.
"""

import json
import re
import urllib.parse
from datetime import datetime

import requests


def quote(value):
    return urllib.parse.quote(str(value), safe='')


class EmrDb:
    """Thin read-only client for the CHT `medic` CouchDB database."""

    def __init__(self, url, user=None, password=None, verify=False):
        parsed = urllib.parse.urlsplit(url)
        embedded = None
        if parsed.username:
            embedded = (urllib.parse.unquote(parsed.username),
                        urllib.parse.unquote(parsed.password or ''))
        self.user = user or (embedded[0] if embedded else None)
        self.password = password or (embedded[1] if embedded else None)
        self.verify = verify
        self.session = requests.Session()
        if self.user:
            self.session.auth = (self.user, self.password)
        self.base = urllib.parse.urlunsplit((
            parsed.scheme, parsed.netloc, parsed.path or '/medic', '', '',
        )).rstrip('/')

    @staticmethod
    def quote(value):
        return quote(value)

    def sibling_base(self, db_name):
        """Base URL for another database on the same CouchDB server."""
        parsed = urllib.parse.urlsplit(self.base)
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, db_name, '', ''))

    def _request(self, path, params=None):
        resp = self.session.get(
            f'{self.base}{path}',
            params=params,
            verify=self.verify,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_all_docs(self):
        """Paginated read of every doc in the database (metadata included)."""
        docs = []
        skip = 0
        limit = 1000
        while True:
            data = self._request('/_all_docs', {'include_docs': True, 'limit': limit, 'skip': skip})
            rows = data.get('rows', [])
            for row in rows:
                if row.get('doc'):
                    docs.append(row['doc'])
            if len(rows) < limit:
                break
            skip += limit
        return docs

    def fetch_doc(self, doc_id):
        return self._request(f'/{urllib.parse.quote(doc_id, safe="")}')


def is_emr_report(doc):
    """True for a submission we treat as an EMR clinical report.

    Exclusion rules (documented in the project requirements):
      * only `data_record` docs are reports
      * records with no `form` (SMS / kujua messages) are excluded
      * records whose form starts with `training:` are excluded
    """
    if not isinstance(doc, dict):
        return False
    if doc.get('type') != 'data_record':
        return False
    form = doc.get('form')
    if not form:
        return False
    if str(form).startswith('training:'):
        return False
    if doc.get('kujua_message'):
        return False
    return True


def contact_place_types(docs):
    """Return {place_types, person_types} from the settings contact_types."""
    place, person = set(), set()
    settings = next((d for d in docs if d.get('_id') == 'settings'), None)
    if not settings:
        return place, person
    raw = settings.get('settings') or settings
    for ct in raw.get('contact_types') or []:
        cid = ct.get('id')
        if not cid:
            continue
        if ct.get('person'):
            person.add(cid)
        else:
            place.add(cid)
    return place, person


def classify_contacts(docs):
    """Return (camps, participants) using the configured contact types."""
    place_types, person_types = contact_place_types(docs)
    camps, participants = {}, {}
    for doc in docs:
        if not isinstance(doc, dict) or doc.get('type') != 'contact':
            continue
        ct = doc.get('contact_type')
        if ct in person_types or (not place_types and ct != place_types):
            participants[doc['_id']] = doc
        elif ct in place_types or not ct:
            camps[doc['_id']] = doc
    return camps, participants


def flatten(obj, prefix='', out=None, seen=None):
    """Flatten nested dicts to dot-notation; arrays (repeat groups) as JSON.

    Documented repeat-group choice (see project requirements): arrays of
    objects (repeat instances) and arrays of scalars (multi-selects) are
    stored as a JSON string in a single cell keyed by the flattened path.
    This is guaranteed lossless and schema-generic: no data is dropped, no
    per-form schema is required, and new forms are captured automatically.
    """
    if out is None:
        out = {}
    if seen is None:
        seen = set()
    if id(obj) in seen:
        return out
    seen = seen | {id(obj)}

    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f'{prefix}.{key}' if prefix else key
            flatten(value, child, out, seen)
    elif isinstance(obj, list):
        out[prefix] = json.dumps(obj, ensure_ascii=False)
    else:
        out[prefix] = obj
    return out


def attachment_names(doc):
    """Sorted list of attachment filenames for a doc (for Excel references)."""
    return sorted((doc.get('_attachments') or {}).keys())


def sanitize_filename(name, fallback='export'):
    """Make a string safe for use as a file name."""
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', str(name or '')).strip('._-')
    return cleaned or fallback


def iso_datetime(ms):
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000.0).isoformat(timespec='seconds')
    except (ValueError, OSError, TypeError):
        return ms


def timestamp_stamp():
    return datetime.now().strftime('%Y-%m-%d-%H%M')
