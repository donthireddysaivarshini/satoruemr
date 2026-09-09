"""Generate forms/app/ddst.xlsx — DDST-II (Denver II) NIMS version.
Scoring: single cutoff per item; NO only on report-eligible items; R only on non-report-eligible.
Domain: 0 delayed=Normal, 1=Caution, 2+=Suspect. Overall Normal iff all Normal and <=1 Caution else Suspect.
Version scoring_version ddst-ii-nims-v1."""
import openpyxl
wb=openpyxl.Workbook()
ws=wb.active
ws.title='survey'
HEADERS=['type','name','label','hint','required','appearance','relevant','constraint','constraint_message','calculation','default','instance::type']
ws.append(HEADERS)
E=''
def row(**kw):
    instance_type = kw.pop('instance_type', E)
    ws.append([kw.get(h, E) for h in HEADERS[:-1]] + [instance_type])

# helpers
def months(y=0,m=0,d=0): return y*12 + m + d/30.4375

# report-eligible set per confirmed list (global item numbers 1..125 where 1-25 PS, 26-54 FM, 55-93 LANG, 94-125 GM)
# Map global -> eligibility. For PS: items 4,6,8,9,13,15,22,25 are eligible (PS 4,6,8,9,13,15,22,25 => global 4,6,8,9,13,15,22,25)
# Language: items 55-69 correspond to LANG 2,3,4,5,8,9,10,11,12,13,14,15,16,17,19 => global 56,57,58,59,62,63,64,65,66,67,68,69,70,71,73
# Actually map properly: LANG 2->global56, 3->57,4->58,5->59,8->62,9->63,10->64,11->65,12->66,13->67,14->68,15->69,16->70,17->71,19->73
# Gross Motor: Roll Over (GM8) and Get to Sitting (GM13) => global 101,106
REPORT_ELIGIBLE_GLOBALS={4,6,8,9,13,15,22,25,56,57,58,59,62,63,64,65,66,67,68,69,70,71,73,101,106}

# Item definitions: list of (global_no, domain, local_no, name, age_months or None, hint)
ITEMS=[]
# PS 1-25 - CORRECTED ages from NIMS DDST-II sheet
ps_data=[
 ("Regard Face", 1.0000, False),
 ("Smile Responsively", 1.3285, False),
 ("Smile Spontaneously", 2.0000, False),
 ("Regard Own Hand", 4.0000, True),
 ("Work for Toy", 5.6571, False),
 ("Feed Self", 6.3285, True),
 ("Play Pat-a-Cake", 11.3285, False),
 ("Indicate Wants", 12.6571, True),
 ("Wave Bye-Bye", 14.0000, True),
 ("Play Ball with Examiner", 15.6571, False),
 ("Imitate Activities", 16.0000, False),
 ("Drink from Cup", 17.0000, False),
 ("Help in House", 17.3285, True),
 ("Use Spoon/Fork", 20.0000, False),
 ("Remove Garment", 23.6571, True),
 ("Feed Doll", 24.0000, False),
 ("Put on Clothing", 30.0000, False),
 ("Brush Teeth with Help", 32.0000, False),
 ("Wash & Dry Hands", 36.4928, False),
 ("Name Friend", 37.0000, False),
 ("Put on T-shirt", 40.4928, False),
 ("Dress, No Help", 53.0000, True),
 ("Play Board/Card Games", 58.4928, False),
 ("Brush Teeth, No Help", 60.0000, False),
 ("Prepare Cereal (simple snack)", 61.0000, True),
]
for i,(name,age,rep) in enumerate(ps_data, start=1):
    ITEMS.append((i, "ps", i, name, age, rep))
# FM 26-54 (29 items) - CORRECTED ages (fixing ×12 bug)
fm_data=[
 ("Follow to Midline", 1.2628, False),
 ("Follow Past Midline", 2.6571, False),
 ("Grasp Rattle", 3.6571, False),
 ("Hands Together", 4.0, False),
 ("Follow 180°", 4.5, False),
 ("Regard Raisin", 5.1971, False),
 ("Reaches", 5.5, False),
 ("Look for Yarn (dropped pompom)", 7.1971, False),
 ("Rake Raisin", 7.2628, False),
 ("Pass Cube (hand to hand)", 7.6571, False),
 ("Take 2 Cubes", 9.1643, False),
 ("Thumb-Finger Grasp", 10.1643, False),
 ("Bang 2 Cubes Held in Hand", 11.0, False),
 ("Put Block in Cup", 13.6571, False),
 ("Scribbles", 16.3285, False),
 ("Dump Raisin, Demonstrated", 19.5, False),
 ("Tower of 2 Cubes", 20.5, False),
 ("Tower of 4 Cubes", 23.6571, False),
 ("Tower of 6 Cubes", 31.5, False),
 ("Imitative Vertical Line", 36.0, False),
 ("Tower of 8 Cubes", 41.5, False),
 ("Thumb Wiggle", 43.5, False),
 ("Copy ○ (circle)", 48.0, False),
 ("Draw Person, 3 Parts", 55.5, False),
 ("Copy + (cross)", 56.5, False),
 ("Pick Longer Line", 63.0, False),
 ("Copy □ (square)", 65.5, False),
 ("Copy □, Demonstrated", 66.0, False),
 ("Draw Person, 6 Parts", 72.0, False),
]
for i,(name,age,rep) in enumerate(fm_data, start=1):
    rep = (25+i) in REPORT_ELIGIBLE_GLOBALS
    ITEMS.append((25+i, "fm", i, name, age, rep))
# Language 55-93 (39 items) - CORRECTED some ages (fixing ×12 bug)
lang_data=[
 ("Responds to Bell", 0.3285, True),  # 10 days
 ("Vocalizes", 0.6571, True),          # 20 days
 ("Ooo/Aah", 2.4928, True),           # 2m 15d
 ("Laughs", 3.0, True),
 ("Squeals", 4.3285, True),           # 4m 10d
 ("Turn to Rattling Sound", 5.5, True),
 ("Turn to Voice", 6.5, True),
 ("Single Syllables", 7.3285, True),   # 7m 10d
 ("Imitate Speech Sounds", 8.6571, True), # 8m 20d
 ("Dada/Mama, Non-specific", 9.0, True),
 ("Combine Syllables", 10.0, True),
 ("Jabbers", 12.0, True),
 ("Dada/Mama, Specific", 13.5, True),
 ("One Word", 15.0, True),
 ("Two Words", 16.5, True),
 ("Three Words", 18.0, True),
 ("Six Words", 21.5, True),
 ("Point to 2 Pictures", 23.5, False),
 ("Combine Words", 24.5, True),
 ("Name 1 Picture", 25.0, True),
 ("Body Parts, 6", 28.5, False),
 ("Point to 4 Pictures", 31.0, False),
 ("Speech Half Understandable", 35.0, False),
 ("Name 4 Pictures", 35.0, True),
 ("Know 2 Actions", 37.5, False),
 ("Know 2 Adjectives", 43.0, False),
 ("Name 1 Colour", 44.0, False),
 ("Use of 2 Objects", 45.0, False),
 ("Count 1 Block", 47.0, False),
 ("Use of 3 Objects", 49.0, False),
 ("Know 4 Actions", 50.0, False),
 ("Understand 4 Prepositions", None, False),
 ("Speech Fully Understandable", None, False),
 ("Define 3 Words", None, False),
 ("Know 3 Adjectives", 40.5, False),
 ("Count 5 Blocks", 40.5, False),
 ("Opposites, 2", 44.0, False),
 ("Define 7 Words", 72.0, False),
 ("Language Item 39 — row count reconciliation [AGE UNCONFIRMED]", None, False),
]
for i,(name,age,rep) in enumerate(lang_data, start=1):
    rep = (55-1+i) in REPORT_ELIGIBLE_GLOBALS
    ITEMS.append((55-1+i, "lang", i, name, age, rep if age is not None else False))

# Gross Motor 94-125 (32 items) - CORRECTED some ages (fixing ×12 bug)
gm_data=[
  ("Equal Movements", 0.1643, False),                   # 5 days
  ("Lift Head", 2.4928, True),                  # 2m 15d
  ("Head Up 45°", 3.4928, False),                # 3m 15d
  ("Head Up 90°", 4.0, False),
  ("Sit, Head Steady", 4.4928, False),           # 4m 15d
  ("Bear Weight on Legs", 4.4928, False),        # 4m 15d
  ("Chest Up, Arm Support", 5.5, False),
  ("Roll Over", 6.0, True),
  ("Pull to Sit, No Head Lag", 6.5, False),
  ("Sit, No Support", 6.5, False),
  ("Stand, Holding On", 8.5, False),
  ("Pull to Stand", 10.0, False),
  ("Get to Sitting", 11.5, True),
  ("Stand – 2 Seconds", 13.5, False),
  ("Stand Alone", 14.5, False),
  ("Stoop and Recover", 15.0, False),
  ("Walk Well", 16.5, False),
  ("Walk Backward", 20.0, False),
  ("Runs", 21.5, False),
  ("Walks Up Steps", 23.0, False),
  ("Kicks Ball Forward", 28.5, False),
  ("Jump Up", 35.0, False),
  ("Throw Ball Overhand", 37.5, False),
  ("Broad Jump", 40.0, False),
  ("Balance Each Foot, 1 sec", 47.0, False),
  ("Balance Each Foot, 2 sec", 51.0, False),
  ("Hops", 55.5, False),
  ("Balance Each Foot, 3 sec", 61.0, False),
  ("Balance Each Foot, 4 sec", 66.0, False),
  ("Balance Each Foot, 5 sec", 68.0, False),
  ("Heel-to-Toe Walk", 72.0, False),
  ("Balance Each Foot, 6 sec", 72.0, False),           # 6 years
]
for i,(name,age,rep) in enumerate(gm_data, start=1):
    ITEMS.append((94-1+i, "gm", i, name, age, rep if age is not None else False))

# ---------- survey ----------
row(type='begin group', name='inputs', label='Participant', appearance='field-list', relevant="./source = 'user'")
row(type='hidden', name='source')
row(type='hidden', name='source_id')
row(type='begin group', name='user', label='User', appearance='field-list')
row(type='hidden', name='contact_id')
row(type='hidden', name='name')
row(type='end group')
row(type='begin group', name='contact', label='Participant', appearance='field-list')
row(type='db:person', name='_id', label='Select participant', appearance='select-contact type-participant')
row(type='hidden', name='patient_id')
row(type='hidden', name='name')
row(type='hidden', name='age')
row(type='hidden', name='gender')
row(type='hidden', name='date_of_birth')
row(type='end group')
row(type='end group')
for n,c in [('patient_uuid','../inputs/contact/_id'),('patient_name','../inputs/contact/name')]:
    row(type='calculate', name=n, calculation=c)
row(type='begin group', name='g_meta', label='Test Information')
row(type='date', name='test_date', label='Test date', required='yes', default='today()')
row(type='date', name='child_dob', label='Child date of birth', required='yes',
    constraint='. <= today()', constraint_message='DOB cannot be in the future.')
row(type='calculate', name='ca_days', calculation='int(${test_date} - ${child_dob})')
row(type='calculate', name='ca_months_dec', calculation='${ca_days} div 30.4375')
row(type='note', name='dob_warning',
    label='**WARNING:** Child date of birth is missing or invalid. Please enter DOB before scoring. Do not guess age.',
    relevant="${child_dob} = '' or ${ca_days} < 0")
row(type='note', name='ca_note', label='Chronological age: ${ca_days} days (${ca_months_dec} months)',
    relevant='${ca_days} >= 0')
# No prematurity adjustment for v1 — flagged as future enhancement
row(type='calculate', name='ca_band', calculation="if(${ca_months_dec} < 12, 1, if(${ca_months_dec} < 24, 2, if(${ca_months_dec} < 36, 3, if(${ca_months_dec} < 48, 4, if(${ca_months_dec} < 60, 5, if(${ca_months_dec} < 72, 6, if(${ca_months_dec} < 84, 7, if(${ca_months_dec} < 96, 8, if(${ca_months_dec} < 108, 9, if(${ca_months_dec} < 120, 10, if(${ca_months_dec} < 132, 11, if(${ca_months_dec} < 144, 12, 13))))))))))))")
row(type='select_one yesno', name='show_all', label='Show all items? (trained assessors)', default='no',
    hint='No = show birth through child age band; future bands hidden. Yes = show all bands.')
row(type='end group')

# Domain groups with per-item relevance — direct per-item cutoff (no shared-band indirection)
def vb_expr_for_age(age):
    if age is None: return "true()"
    return "${show_all} = 'yes' or ${ca_months_dec} >= %.4f" % age

# Group by domain for UX
domains=[("ps","Personal-Social",1,25),("fm","Fine Motor-Adaptive",26,54),("lang","Language",55,93),("gm","Gross Motor",94,125)]
for dom, label, start, end in domains:
    row(type='begin group', name='g_'+dom, label=label)
    for (gno, d, local_no, name, age, rep) in ITEMS:
        if not (start <= gno <= end): continue
        lbl=name
        if age is None: lbl += ' [AGE UNCONFIRMED — TODO]'
        # choice list per eligibility
        list_name='ddst_report' if rep else 'ddst_direct'
        hint='Report-eligible: caregiver report may substitute for observation.' if rep else ''
        rel=vb_expr_for_age(age)
        # For unconfirmed, always visible
        if age is None: rel="true()"
        row(type='select_one '+list_name, name='%s_%02d' % (dom, local_no), label='%d. %s' % (gno, lbl), hint=hint, required='yes', relevant=rel)
    row(type='end group')
    # Notes per domain? single final notes
row(type='text', name='clinical_notes', label='Clinical notes')

# Scoring: per-item delayed flags
for (gno, d, local_no, name, age, rep) in ITEMS:
    var='%s_%02d' % (d, local_no)
    if age is None:
        row(type='calculate', name=var+'_delayed', calculation='0')
    else:
        age_str=str(round(age,4))
        if d in ('ps','lang') and gno in REPORT_ELIGIBLE_GLOBALS or gno in (101,106): # report-eligible
            calc="if(selected(${%s}, 'F') and ${ca_months_dec} >= %s, 1, 0)" % (var, age_str)
        else:
            calc="if((selected(${%s}, 'F') or selected(${%s}, 'R')) and ${ca_months_dec} >= %s, 1, 0)" % (var, var, age_str)
        row(type='calculate', name=var+'_delayed', calculation=calc)

# Domain delayed counts
for dom, label, start, end in domains:
    parts=['${%s_%02d_delayed}' % (dom, ITEMS[i][2]) for i in range(len(ITEMS)) if start <= ITEMS[i][0] <= end]
    row(type='calculate', name='d_'+dom+'_delayed', calculation=' + '.join(parts) if parts else '0')
    row(type='calculate', name='d_'+dom+'_status',
        calculation="if(${%s} >= 2, 'Suspect', if(${%s} = 1, 'Caution', 'Normal'))" % ('d_'+dom+'_delayed','d_'+dom+'_delayed'))

# Overall
row(type='calculate', name='caution_domains',
    calculation="if(${d_ps_status} = 'Caution',1,0) + if(${d_fm_status} = 'Caution',1,0) + if(${d_lang_status} = 'Caution',1,0) + if(${d_gm_status} = 'Caution',1,0)")
row(type='calculate', name='any_suspect',
    calculation="${d_ps_status} = 'Suspect' or ${d_fm_status} = 'Suspect' or ${d_lang_status} = 'Suspect' or ${d_gm_status} = 'Suspect'")
row(type='calculate', name='overall',
    calculation="if(${any_suspect} or ${caution_domains} >= 2, 'Suspect', 'Normal')")
row(type='calculate', name='scoring_version', calculation="'ddst-ii-nims-v1'")
row(type='note', name='result_note', label='Overall: ${overall} — PS:${d_ps_status} FM:${d_fm_status} LANG:${d_lang_status} GM:${d_gm_status} (Scoring: ddst-ii-nims-v1)')

# Supporting Documents / Scale Upload — two fields because single mediatype cannot reliably cover image/* and application/pdf in CHT 5.2.0 Enketo
row(type='begin group', name='g_supporting_docs', label='Supporting Documents / Scale Upload')
row(type='image', name='upload_scale_image', label='Upload completed scale / assessment sheet (image)',
    hint='Upload clear photos of the completed paper scale, consent form, or supporting assessment document. Accepts JPG, JPEG, PNG. For PDF use next field.',
    instance_type='binary')
row(type='file', name='upload_scale_pdf', label='Upload completed scale / assessment sheet (PDF)',
    hint='Upload a PDF of the completed paper scale if not already uploaded as image. Accepts PDF.',
    instance_type='binary')
row(type='text', name='upload_caption', label='Attachment caption / description (optional)')
row(type='end group')

# choices
ws2=wb.create_sheet('choices')
ws2.append(['list_name','name','label'])
for lname, opts in [('yesno',[('yes','Yes'),('no','No')]),
                    ('ddst_report',[('P','Pass'),('F','Fail'),('NO','No Opportunity')]),
                    ('ddst_direct',[('P','Pass'),('F','Fail'),('R','Refusal')])]:
    for n,lbl in opts:
        ws2.append([lname,n,lbl])
ws3=wb.create_sheet('settings')
ws3.append(['form_title','form_id','version','default_language'])
ws3.append(['DDST-II Developmental Screening','ddst','2026-08-27 01-00','en'])
wb.save(r'C:\Projects\EMRCHT\satoru-config\forms\app\ddst.xlsx')
print('ddst.xlsx created with', len(ITEMS), 'items')
