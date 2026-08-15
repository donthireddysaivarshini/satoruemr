import sys, json
d = json.load(sys.stdin)
ids = [r['id'] for r in d['rows']]
need = ['form:stage1_screening','form:stage2_assessment','form:assessment_visit','form:follow_up_contact','form:longitudinal_review','form:referral_outcome','org.couchdb.user:varshini']
print('=== present in medic ===')
for n in need:
    print(n, '->', 'YES' if n in ids else 'NO')
print()
print('=== all contacts (name) ===')
for r in d['rows']:
    doc = r.get('doc') or {}
    if doc.get('type') == 'contact':
        name = doc.get('name') or (doc.get('contact') or {}).get('name')
        print(r['id'], '->', name, '|', (doc.get('contact') or {}).get('type'))
print()
print('=== users in _users (separate query needed) ===')
