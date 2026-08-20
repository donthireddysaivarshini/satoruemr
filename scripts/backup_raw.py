"""Read-only Satoru EMR raw backup -> timestamped ZIP.

Creates satoru-emr-raw-YYYY-MM-DD-HHmm.zip containing:
  manifest.json                 export metadata + file index (sha256, bytes)
  documents/<doc-id>.json       every document from the `medic` database
  attachments/<doc-id>/<name>   every binary attachment, full fidelity
  audit/audit-<rev>.json        medic-audit history for EMR reports

This is the portable raw data backup (layer 2 of the 3-layer backup design).
It is intentionally NOT scoped: it is a complete snapshot of the database and
preserves every document, revision, attachment, and audit record, including
kujua/SMS and training records. Exclusions apply only to the human-readable
Excel export (scripts/export_emr.py), not to this raw backup.

Read-only: only GET requests are made. No data is ever modified or deleted.
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emr_common import EmrDb, is_emr_report, timestamp_stamp


def safe_doc_name(doc_id):
    """Turn a doc id into a filesystem-safe name (id may contain '/' etc.)."""
    return re.sub(r'[^A-Za-z0-9._-]+', '_', doc_id) or 'doc'


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description='Satoru EMR raw backup -> ZIP (read-only)')
    parser.add_argument('--url', required=True, help='CouchDB URL, e.g. https://user:pass@host:port/medic')
    parser.add_argument('--out', default='.', help='output directory (default: current directory)')
    parser.add_argument('--verify', action='store_true', help='verify TLS certificates (default: off for self-signed)')
    parser.add_argument('--audit-db', default='medic-audit', help='audit database name (default: medic-audit)')
    args = parser.parse_args()

    db = EmrDb(args.url, verify=args.verify)
    docs = db.fetch_all_docs()

    manifest = {
        'generated_at': timestamp_stamp(),
        'source': db.base,
        'doc_count': len(docs),
        'emr_report_count': sum(1 for d in docs if is_emr_report(d)),
        'files': [],
    }

    stamp = timestamp_stamp()
    filename = f'satoru-emr-raw-{stamp}.zip'
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, filename)

    doc_paths = {}
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        audit_entries = {}

        for doc in docs:
            doc_id = doc.get('_id', '')
            doc_bytes = json.dumps(doc, ensure_ascii=False, sort_keys=True).encode('utf-8')
            doc_name = f'documents/{safe_doc_name(doc_id)}.json'
            zf.writestr(doc_name, doc_bytes)
            doc_paths[doc_id] = doc_name
            manifest['files'].append({
                'path': doc_name,
                'doc_id': doc_id,
                'sha256': sha256_bytes(doc_bytes),
                'bytes': len(doc_bytes),
            })

            for att_name, att_info in (doc.get('_attachments') or {}).items():
                resp = db.session.get(
                    f'{db.base}/{db.quote(doc_id)}/{db.quote(att_name)}',
                    auth=(db.user, db.password) if db.user else None,
                    verify=db.verify, timeout=120,
                )
                resp.raise_for_status()
                att_bytes = resp.content
                att_path = f'attachments/{safe_doc_name(doc_id)}/{safe_doc_name(att_name)}'
                zf.writestr(att_path, att_bytes)
                manifest['files'].append({
                    'path': att_path,
                    'doc_id': doc_id,
                    'attachment': att_name,
                    'sha256': sha256_bytes(att_bytes),
                    'bytes': len(att_bytes),
                    'content_type': att_info.get('content_type'),
                })

            if is_emr_report(doc):
                try:
                    audit = db.session.get(
                        f'{db.sibling_base(args.audit_db)}/{db.quote(doc_id)}',
                        auth=(db.user, db.password) if db.user else None,
                        verify=db.verify, timeout=120,
                    )
                    if audit.status_code == 200:
                        audit_entries[doc_id] = audit.json()
                    elif audit.status_code != 404:
                        audit.raise_for_status()
                except Exception as exc:
                    print(f'  audit fetch warning for {doc_id}: {exc}')

        for doc_id, audit_doc in audit_entries.items():
            audit_bytes = json.dumps(audit_doc, ensure_ascii=False, sort_keys=True).encode('utf-8')
            audit_path = f'audit/audit-{safe_doc_name(doc_id)}.json'
            zf.writestr(audit_path, audit_bytes)
            manifest['files'].append({
                'path': audit_path,
                'doc_id': doc_id,
                'sha256': sha256_bytes(audit_bytes),
                'bytes': len(audit_bytes),
            })

        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
        zf.writestr('manifest.json', manifest_bytes)

    print(f'  docs: {len(docs)}')
    print(f'  attachments: {sum(1 for f in manifest["files"] if "attachment" in f)}')
    print(f'  audit docs: {len(audit_entries)}')
    print(f'  files indexed: {len(manifest["files"])}')
    print(f'wrote {path}')


if __name__ == '__main__':
    main()
