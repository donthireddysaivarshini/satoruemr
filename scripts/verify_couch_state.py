import json
import ssl
import base64
import urllib.request

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

for doc_id in ['settings', 'app_settings']:
    doc = fetch_doc(doc_id)
    perms = doc.get('settings', {}).get('permissions') if doc_id == 'settings' else doc.get('permissions')
    cs = doc.get('settings', {}).get('contact_summary') if doc_id == 'settings' else doc.get('contact_summary')

    print(f'=== Document: {doc_id} ===')
    print('can_browse_all_participants:', perms.get('can_browse_all_participants'))
    print('can_view_participants:', perms.get('can_view_participants'))
    print('contact_summary contains access_restricted:', 'access_restricted' in (cs or ''))
    print('contact_summary contains is_participant in restricted context:', 'context:{is_participant:true,access_restricted:true}' in (cs or ''))
    print('contact_summary contains supervisor view permission check:', "cht.v1.hasPermissions('can_view_participants')" in (cs or ''))
