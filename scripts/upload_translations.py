#!/usr/bin/env python3
"""Upload custom translations to CouchDB."""
import argparse
import json
import sys
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import base64
import ssl

def upload_translations(url, translations_file):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Read translations file
    with open(translations_file, 'r') as f:
        content = f.read()

    # Parse key=value pairs
    translations = {}
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            translations[key.strip()] = value.strip()

    print(f"Found {len(translations)} translation keys")

    # Get existing translations doc
    doc_id = "messages-en"
    try:
        req = Request(f"{url}/medic/{doc_id}")
        creds = base64.b64encode(b"medic:password").decode()
        req.add_header("Authorization", f"Basic {creds}")
        resp = urlopen(req, context=ctx)
        doc = json.loads(resp.read())
        print(f"Found existing {doc_id}, rev: {doc.get('_rev')}")
    except HTTPError as e:
        if e.code == 404:
            doc = {"_id": doc_id, "type": "translations", "code": "en", "name": "English"}
            print(f"Creating new {doc_id}")
        else:
            raise

    # Merge translations
    if "values" not in doc:
        doc["values"] = {}
    doc["values"].update(translations)

    # Upload
    data = json.dumps(doc).encode()
    req = Request(f"{url}/medic/{doc_id}", data=data, method='PUT')
    creds = base64.b64encode(b"medic:password").decode()
    req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Content-Type", "application/json")
    resp = urlopen(req, context=ctx)
    result = json.loads(resp.read())
    print(f"Uploaded: {result}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--file", default="translations/messages-en.properties")
    args = parser.parse_args()
    upload_translations(args.url, args.file)
