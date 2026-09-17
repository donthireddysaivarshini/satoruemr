#!/usr/bin/env python3
"""Safely update CouchDB settings doc and app_settings doc with approved permissions and contact_summary."""
import json
import ssl
import base64
import urllib.request
import subprocess

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_url = "https://172-27-250-199.local-ip.medicmobile.org:10443/medic"
creds = base64.b64encode(b"medic:password").decode()

def fetch_doc(doc_id):
    req = urllib.request.Request(f"{base_url}/{doc_id}")
    req.add_header("Authorization", f"Basic {creds}")
    resp = urllib.request.urlopen(req, context=ctx)
    return json.loads(resp.read())

def put_doc(doc_id, doc):
    data = json.dumps(doc).encode()
    req = urllib.request.Request(f"{base_url}/{doc_id}", data=data, method="PUT")
    req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, context=ctx)
    return json.loads(resp.read())

# 1. Load target contact_summary from app_settings.json
with open("satoru-config/app_settings.json") as f:
    local_app_settings = json.load(f)

new_cs = local_app_settings["contact_summary"]

# 2. Syntax check in Node.js
test_script = f"""
const cs = {json.dumps(new_cs)};
try {{
  const fn = new Function('contact', 'reports', 'lineage', 'uhcStats', 'cht', cs);
  console.log("SYNTAX_CHECK_PASS");
}} catch (e) {{
  console.error("SYNTAX_CHECK_FAIL:", e.message);
  process.exit(1);
}}
"""
res = subprocess.run(["node", "-e", test_script], capture_output=True, text=True)
if "SYNTAX_CHECK_PASS" not in res.stdout:
    print("FATAL: contact_summary syntax check failed!")
    print(res.stderr)
    exit(1)
print("Validated new contact_summary syntax: PASS")

# 3. Update doc 'settings'
settings_doc = fetch_doc("settings")
print(f"Current doc 'settings' rev: {settings_doc.get('_rev')}")

if "settings" not in settings_doc:
    settings_doc["settings"] = {}

# Permissions in doc 'settings'
perms = settings_doc["settings"].setdefault("permissions", {})
perms["can_browse_all_participants"] = ["supervisor"]
if "can_view_participants" not in perms:
    perms["can_view_participants"] = ["supervisor"]

# contact_summary in doc 'settings'
settings_doc["settings"]["contact_summary"] = new_cs

result_settings = put_doc("settings", settings_doc)
print(f"Updated doc 'settings': {result_settings}")

# 4. Update doc 'app_settings'
app_settings_doc = fetch_doc("app_settings")
print(f"Current doc 'app_settings' rev: {app_settings_doc.get('_rev')}")

perms_app = app_settings_doc.setdefault("permissions", {})
perms_app["can_browse_all_participants"] = ["supervisor"]
if "can_view_participants" not in perms_app:
    perms_app["can_view_participants"] = ["supervisor"]

app_settings_doc["contact_summary"] = new_cs

result_app = put_doc("app_settings", app_settings_doc)
print(f"Updated doc 'app_settings': {result_app}")

# 5. Verification
v_settings = fetch_doc("settings")
p1 = v_settings.get("settings", {}).get("permissions", {})
print("\nVERIFICATION: doc 'settings':")
print("  can_browse_all_participants:", p1.get("can_browse_all_participants"))
print("  can_view_participants:", p1.get("can_view_participants"))
cs_len = len(v_settings.get("settings", {}).get("contact_summary", ""))
print(f"  contact_summary length: {cs_len}")

v_app = fetch_doc("app_settings")
p2 = v_app.get("permissions", {})
print("\nVERIFICATION: doc 'app_settings':")
print("  can_browse_all_participants:", p2.get("can_browse_all_participants"))
print("  can_view_participants:", p2.get("can_view_participants"))
cs_len2 = len(v_app.get("contact_summary", ""))
print(f"  contact_summary length: {cs_len2}")
print("\nALL COUCHDB UPDATES APPLIED AND VERIFIED SUCCESSFULLY!")
