"""export_server.py - point-and-click UI for the Excel exports.

A tiny local web page so nobody has to type a command. Same exporter as
scripts/export_emr.py (identical output), just driven from a browser:

    python scripts/export_server.py --url "https://medic:PASSWORD@HOST:10443/medic"

then open http://127.0.0.1:8095

  * "All participants"        -> all-workbook
  * pick a camp               -> camp-workbook=<id>
  * pick a participant        -> participant-report=<id>

Stdlib only (plus openpyxl/requests, already required by export_emr).
Read-only: only GET requests are made against CouchDB.

The CouchDB URL (with its password) stays on the server side - it is never
sent to the browser. Binds to 127.0.0.1 by default; pass --host 0.0.0.0 to
expose it on the LAN (only do that on a trusted network).
"""

import argparse
import html
import io
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from emr_common import EmrDb, classify_contacts, is_emr_report
import export_emr

XLSX_MIME = ('application/vnd.openxmlformats-officedocument'
             '.spreadsheetml.sheet')

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Satoru EMR exports</title>
<style>
 body{{font:15px/1.5 system-ui,sans-serif;margin:0;background:#f2f2f3;color:#1a1a1a}}
 .wrap{{max-width:760px;margin:0 auto;padding:32px 20px 64px}}
 h1{{font-size:22px;margin:0 0 4px}}
 .sub{{color:#666;font-size:13px;margin-bottom:28px}}
 .card{{background:#fff;border:1px solid #e2e2e5;border-radius:8px;padding:20px;margin-bottom:16px}}
 .card h2{{font-size:16px;margin:0 0 6px}}
 .card p{{color:#666;font-size:13px;margin:0 0 14px}}
 select{{font:inherit;padding:8px;border:1px solid #ccc;border-radius:5px;min-width:280px;background:#fff}}
 button{{font:inherit;padding:9px 16px;border:0;border-radius:5px;background:#0a5ca8;color:#fff;cursor:pointer}}
 button:hover{{background:#08498a}}
 .row{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
 .empty{{color:#999;font-style:italic}}
 code{{background:#eee;padding:1px 5px;border-radius:3px;font-size:12px}}
</style></head><body><div class="wrap">
<h1>Satoru EMR &mdash; Excel exports</h1>
<div class="sub">Connected to <code>{host}</code> &middot; {ncamps} camps, {nparts} participants, {nreports} assessments</div>

<div class="card">
  <h2>Everyone</h2>
  <p>All participants across every camp. One sheet per scale, plus a Camp column.</p>
  <form action="export" method="get"><input type="hidden" name="scope" value="all-workbook">
  <button type="submit">Download all participants</button></form>
</div>

<div class="card">
  <h2>One camp</h2>
  <p>Participants sheet plus one sheet per scale completed in that camp.</p>
  <form action="export" method="get" class="row">
    <select name="scope">{camp_options}</select>
    <button type="submit">Download camp workbook</button>
  </form>
</div>

<div class="card">
  <h2>One participant</h2>
  <p>Report-style workbook: a sectioned sheet per completed assessment.</p>
  <form action="export" method="get" class="row">
    <select name="scope">{part_options}</select>
    <button type="submit">Download participant report</button>
  </form>
</div>
</div></body></html>"""


def _options(pairs, prefix):
    if not pairs:
        return '<option value="">(none found)</option>'
    return ''.join(
        f'<option value="{html.escape(prefix + i)}">{html.escape(label)}</option>'
        for i, label in pairs)


def _snapshot(db):
    """Camps and participants for the dropdowns (one read)."""
    docs = db.fetch_all_docs()
    camps, participants = classify_contacts(docs)
    reports = [d for d in docs if is_emr_report(d)]
    staff = export_emr.report_submitter_ids(reports)

    camp_pairs = sorted(
        ((cid, c.get('name') or cid) for cid, c in camps.items()),
        key=lambda p: p[1].lower())
    part_pairs = sorted(
        ((pid, ' — '.join(x for x in (p.get('cr_no'), p.get('name')) if x) or pid)
         for pid, p in participants.items() if pid not in staff),
        key=lambda p: p[1].lower())
    return camp_pairs, part_pairs, len(reports)


def make_handler(url, base_path=''):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            sys.stderr.write('  %s\n' % (fmt % args))

        def _db(self):
            return EmrDb(url, verify=False)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            # strip the reverse-proxy prefix, if any
            if base_path and path.startswith(base_path):
                path = path[len(base_path):] or '/'
            if path in ('/', ''):
                return self._page()
            if path == '/export':
                qs = urllib.parse.parse_qs(parsed.query)
                return self._export((qs.get('scope') or [''])[0])
            self.send_error(404)

        def _page(self):
            try:
                camps, parts, nreports = _snapshot(self._db())
            except Exception as exc:                      # noqa: BLE001
                return self._fail(f'Could not read CouchDB: {exc}')
            host = urllib.parse.urlsplit(url).hostname or url
            body = PAGE.format(
                host=html.escape(host), ncamps=len(camps),
                nparts=len(parts), nreports=nreports,
                camp_options=_options(camps, 'camp-workbook='),
                part_options=_options(parts, 'participant-report='),
            ).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _export(self, scope):
            if not scope:
                return self._fail('No export selected.')
            try:
                db = self._db()
                wb = export_emr.build_workbook(scope, db)
                name = export_emr.default_output_name(scope, wb, db)
                buf = io.BytesIO()
                wb.save(buf)
            except SystemExit as exc:                     # build_workbook's own errors
                return self._fail(str(exc))
            except Exception as exc:                      # noqa: BLE001
                return self._fail(f'Export failed: {exc}')
            data = buf.getvalue()
            self.send_response(200)
            self.send_header('Content-Type', XLSX_MIME)
            self.send_header('Content-Disposition',
                             f'attachment; filename="{name}"')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            sys.stderr.write(f'  -> sent {name} ({len(data):,} bytes)\n')

        def _fail(self, message):
            body = (f'<!doctype html><meta charset="utf-8">'
                    f'<body style="font:15px system-ui;padding:32px">'
                    f'<p style="color:#b00">{html.escape(message)}</p>'
                    f'<p><a href=".">Back</a></p>').encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', required=True,
                    help='CouchDB medic URL with credentials')
    ap.add_argument('--port', type=int, default=8095)
    ap.add_argument('--host', default='127.0.0.1',
                    help='bind address (default localhost only)')
    ap.add_argument('--base-path', default='',
                    help='path prefix when served behind a reverse proxy, '
                         'e.g. /exports')
    args = ap.parse_args()

    base_path = '/' + args.base_path.strip('/') if args.base_path.strip('/') else ''
    server = HTTPServer((args.host, args.port),
                        make_handler(args.url, base_path))
    print(f'Satoru EMR exports  ->  http://{args.host}:{args.port}')
    print('Ctrl+C to stop.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nstopped')


if __name__ == '__main__':
    main()
