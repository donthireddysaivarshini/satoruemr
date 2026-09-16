#!/usr/bin/env python3
"""Upload app_settings.json directly to CouchDB."""
import json
import ssl
import base64
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open("app_settings.json", "r") as f:
    settings = json.load(f)

# Read existing doc or create new one
doc_id = "app_settings"
url_base = "https://172-27-250-199.local-ip.medicmobile.org:10443/medic"

# Try to get existing
try:
    req = urllib.request.Request(f"{url_base}/{doc_id}")
    creds = base64.b64encode(b"medic:password").decode()
    req.add_header("Authorization", f"Basic {creds}")
    resp = urllib.request.urlopen(req, context=ctx)
    doc = json.loads(resp.read())
    print(f"Found existing doc, rev: {doc.get('_rev')}")
except Exception as e:
    doc = {"_id": doc_id}
    print(f"No existing doc: {e}")

# Merge settings into doc
for key, value in settings.items():
    if key not in ("_id", "_rev"):
        doc[key] = value

# Upload
data = json.dumps(doc).encode()
req = urllib.request.Request(f"{url_base}/{doc_id}", data=data, method="PUT")
creds = base64.b64encode(b"medic:password").decode()
req.add_header("Authorization", f"Basic {creds}")
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, context=ctx)
result = json.loads(resp.read())
print(f"Uploaded: {result}")
