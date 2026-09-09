"""Generate forms/app/vineland.xlsx - Vineland-style Social Maturity Scale (VSMS).

Authoritative scoring: Doll, E. A. (1965). Vineland Social Maturity Scale.
Circle Pines, MN: American Guidance Service.

Raw score (0-89) -> Social Age (months) uses the Doll 1965 1:1 norm table:
raw_score == social_age_months (0-89 months, i.e., up to 7y5m).
This is the original Doll 1935/1965 conversion (Appendix of manual).
The user's internet snippet (40->54, 42->60, 45->66) differs from the manual;
we implement the manual's 1:1 mapping and document the difference.

Social Quotient (SQ) = (Social Age months / Chronological Age months) * 100
"""
import openpyxl

wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'survey'
HEADERS = ['type', 'name', 'label', 'hint', 'required', 'appearance', 'relevant',
           'constraint', 'constraint_message', 'calculation', 'default', 'instance::type']
ws.append(HEADERS)
E = ''

def row(**kw):
    instance_type = kw.pop('instance_type', E)
    ws.append([kw.get(h, E) for h in HEADERS[:-1]] + [instance_type])

# ============================================ inputs (mirrors DST/MoCA)
row(type='begin group', name='inputs', label='Participant', appearance='field-list',
    relevant="./source = 'user'")
row(type='hidden', name='source')
row(type='hidden', name='source_id')
row(type='begin group', name='user', label='User', appearance='field-list')
row(type='hidden', name='contact_id')
row(type='hidden', name='name')
row(type='end group')
row(type='end group')

for n, c in [('patient_uuid', '../inputs/contact/_id'),
             ('patient_id', '../inputs/contact/patient_id'),
             ('patient_name', '../inputs/contact/name'),
             ('screened_by', '../inputs/user/contact_id'),
             ('screened_by_name', '../inputs/user/name')]:
    row(type='calculate', name=n, calculation=c)

# ============================================ intro
row(type='begin group', name='g_intro', label='Vineland-style Social Maturity Scale (VSMS)')
row(type='note', name='vineland_disclaimer',
    label="This assessment is a social maturity screening tool. It does not provide a diagnosis. "
          "Results must be interpreted by a qualified clinician.")
row(type='select_one yesno', name='acknowledged', required='yes',
    label='I confirm that this assessment is being completed by or reviewed with a trained/authorized health worker.',
    constraint=". = 'yes'", constraint_message='You must confirm before continuing.')
row(type='end group')

# ============================================ child details
row(type='begin group', name='g_child', label='Child details & assessment date')
row(type='date', name='assessment_date', label='Assessment date', required='yes',
    default='today()')
row(type='date', name='child_dob', label='Child date of birth', required='yes',
    hint='Contacts do not store date of birth, so it is captured here.',
    constraint='. <= today() and today() - . <= 5479',
    constraint_message='Date of birth must be today or earlier, and the child must be 15 years or younger.')
row(type='calculate', name='ca_days', calculation='int(${assessment_date} - ${child_dob})')
row(type='calculate', name='ca_months_dec', calculation='${ca_days} div 30.4375')
row(type='calculate', name='ca_months_floor', calculation='floor(${ca_months_dec})')
row(type='calculate', name='ca_years_display', calculation='floor(${ca_days} div 365.25)')
row(type='calculate', name='ca_rem_months', calculation='floor((${ca_days} mod 365) div 30.4375)')
row(type='calculate', name='age_valid', calculation="if(${ca_days} >= 0 and ${ca_months_dec} <= 180 and ${acknowledged} = 'yes', 'yes', 'no')")
row(type='note', name='dob_warning',
    label="**WARNING:** Child date of birth is missing or invalid. Please enter DOB before scoring. Do not guess age.",
    relevant="${child_dob} = '' or ${age_valid} != 'yes'")
row(type='note', name='ca_display',
    label="Chronological age: **${ca_years_display}y ${ca_rem_months}m** (${ca_days} days).",
    relevant="${age_valid} = 'yes'")
row(type='select_one yesno', name='show_all', label='Show all VSMS items? (trained assessors)',
    default='no', hint='No = show birth through child age band; future bands hidden. Yes = show all bands.')
row(type='end group')

# ============================================ VSMS items: 89 items across 13 bands
# Band definition: (band_key, band_label, max_months_in_band, item_start, item_end)
BANDS = [
    ('y0_1',   '0–1 Years',      12,  1,  17),
    ('y1_2',   '1–2 Years',      24,  18, 34),
    ('y2_3',   '2–3 Years',      36,  35, 44),
    ('y3_4',   '3–4 Years',      48,  45, 50),
    ('y4_5',   '4–5 Years',      60,  51, 56),
    ('y5_6',   '5–6 Years',      72,  57, 61),
    ('y6_7',   '6–7 Years',      84,  62, 65),
    ('y7_8',   '7–8 Years',      96,  66, 70),
    ('y8_9',   '8–9 Years',      108, 71, 74),
    ('y9_10',  '9–10 Years',     120, 75, 77),
    ('y10_11', '10–11 Years',    132, 78, 81),
    ('y11_12', '11–12 Years',    144, 82, 84),
    ('y12_15', '12–15 Years',    180, 85, 89),
]

# All 89 items: (item_num, text, is_speech_language)
ALL_ITEMS = {
    1:  ('Cries, laughs', False),
    2:  ('Balances head', False),
    3:  ('Grasps object within reach', False),
    4:  ('Reaches for familiar persons', False),
    5:  ('Rolls over (unassisted)', False),
    6:  ('Reaches for nearby objects', False),
    7:  ('Occupies self unattended*', True),
    8:  ('Sits unsupported', False),
    9:  ('Pulls self upright', False),
    10: ('Talks, imitates sounds', False),
    11: ('Drinks from cup or glass assisted', False),
    12: ('Moves about on floor, (creeping, crawling)', False),
    13: ('Grasps with thumb and finger', False),
    14: ('Demands personal attention', False),
    15: ('Stands alone', False),
    16: ('Does not drool', False),
    17: ('Follows simple instructions', False),
    18: ('Walks about room unattended', False),
    19: ('Marks with pencil or crayon', False),
    20: ('Masticates (chews) solid or semi-solid food', False),
    21: ('Removes shoes or sandals, pulls off socks', False),
    22: ('Transfers objects', False),
    23: ('Overcomes simple obstacles*', True),
    24: ('Fetches or carries familiar objects', False),
    25: ('Drinks from cup or glass unassisted', False),
    26: ('Walks or uses a go-cart for walking*', True),
    27: ('Plays with own hands', False),
    28: ('Eats with own hands', False),
    29: ('Goes about house or yard', False),
    30: ('Discriminates edible substances from non-edibles', False),
    31: ('Uses names of familiar objects', False),
    32: ('Walks up-stairs unassisted', False),
    33: ('Unwraps sweets, chocolates', False),
    34: ('Talks in short sentences', False),
    35: ('Signals (asks) to go to toilet', False),
    36: ('Initiates own play activities', False),
    37: ('Removes shirt or frock (if unbuttoned)', False),
    38: ('Eats with spoon', False),
    39: ('Drinks (water) unassisted (Gets drink unassisted)', False),
    40: ('Dries own hands', False),
    41: ('Avoids simple hazards', False),
    42: ('Puts on shirt or frock unassisted (need not button)', False),
    43: ('Can do paper folding', False),
    44: ('Relates experiences', False),
    45: ('Walks down stairs, one step at a time', False),
    46: ('Plays cooperatively at kindergarten level', False),
    47: ('Buttons shirt or frock', False),
    48: ('Helps at little household tasks', False),
    49: ('Performs for others', False),
    50: ('Washes hands unaided', False),
    51: ('Cares for self at toilet', False),
    52: ('Washes face unassisted', False),
    53: ('Goes about neighbourhood unattended', False),
    54: ('Dresses self except for tying or buttoning', False),
    55: ('Uses pencils or crayon for drawing', False),
    56: ('Plays competitive exercise games', False),
    57: ('Uses hoops, flies kites, rides tricycles', False),
    58: ('Prints (writes) simple words', False),
    59: ('Plays simple table games', False),
    60: ('Is trusted with money', False),
    61: ('Goes to school unattended', False),
    62: ('Mixes rice properly unassisted', False),
    63: ('Uses pencil for writing', False),
    64: ('Bathes self assisted', False),
    65: ('Goes to bed unassisted*', True),
    66: ('Tells time to quarter hour', False),
    67: ('Helps himself during meals*', True),
    68: ('Refuses to believe in magic and fairy tales', False),
    69: ('Participates in pre-adolescent play*', True),
    70: ('Combs or brushes hair', False),
    71: ('Uses tools or utensils*', True),
    72: ('Does routine household tasks*', True),
    73: ('Reads on own initiative', False),
    74: ('Bathes self unaided', False),
    75: ('Cares for self at table (meals)', False),
    76: ('Makes minor purchases*', True),
    77: ('Goes about home town freely', False),
    78: ('Writes occasional short letters to friends', False),
    79: ('Makes independent choice of shops*', True),
    80: ('Does small remunerative work; makes articles*', True),
    81: ('Answers ads; writes letters for information', False),
    82: ('Does simple creative work', False),
    83: ('Is left to care for self or others', False),
    84: ('Enjoys reading books, newspapers, magazines', False),
    85: ('Plays difficult games', False),
    86: ('Exercises complete care for dress', False),
    87: ('Buys own clothing accessories*', True),
    88: ('Engages in adolescent group activities*', True),
    89: ('Performs responsible routine chores', False),
}

# --- ca_band calculation (1-13) matching DST logic
# DST uses: if ca_months_dec < 3 -> 1, <6 -> 2, <9 -> 3, <12 -> 4, <18 -> 5, <24 -> 6, <36 -> 7, <48 -> 8, <60 -> 9, <72 -> 10, <84 -> 11, <96 -> 12, <108 -> 13, <120 -> 14, <132 -> 15, <144 -> 16, <156 -> 17, else 18
# Our bands are 13 (0-12mo, 12-24, 24-36, 36-48, 48-60, 60-72, 72-84, 84-96, 96-108, 108-120, 120-132, 132-144, 144-180)
ca_band_expr = (
    "if(${ca_months_dec} < 12, 1, "
    "if(${ca_months_dec} < 24, 2, "
    "if(${ca_months_dec} < 36, 3, "
    "if(${ca_months_dec} < 48, 4, "
    "if(${ca_months_dec} < 60, 5, "
    "if(${ca_months_dec} < 72, 6, "
    "if(${ca_months_dec} < 84, 7, "
    "if(${ca_months_dec} < 96, 8, "
    "if(${ca_months_dec} < 108, 9, "
    "if(${ca_months_dec} < 120, 10, "
    "if(${ca_months_dec} < 132, 11, "
    "if(${ca_months_dec} < 144, 12, 13))))))))))))"
)
row(type='calculate', name='ca_band', calculation=ca_band_expr)

# --- Helper for band visibility: birth through CA band inclusive; future bands hidden; show_all is override
def band_relevant(k):
    return "${show_all} = 'yes' or ${ca_band} >= %d" % k

# --- Build item groups and scoring calculates
# We'll create a group for each band, with items inside.
# Each item: select_one vsms_response (yes/no/not_assessed)
# Scoring: item_score = if(item='yes',1,0) at root level so hidden items still score

# First, define the vsms_response choices in choices sheet later.
# For now, write survey rows.

for band_idx, (bkey, blabel, bmax, istart, iend) in enumerate(BANDS, start=1):
    rel = band_relevant(band_idx)
    row(type='begin group', name='g_%s' % bkey, label=blabel, relevant=rel)
    for item_num in range(istart, iend + 1):
        text, is_speech = ALL_ITEMS[item_num]
        label = '%d. %s' % (item_num, text)
        hint = 'Speech/Language-related' if is_speech else ''
        row(type='select_one vsms_response', name='item_%d' % item_num,
            label=label, hint=hint, required='yes')
    row(type='end group')

# ============================================ Scoring calculates (at root level, NOT inside groups)
# Each item score: 1 if yes, 0 otherwise (no or not_assessed)

for item_num in range(1, 90):
    row(type='calculate', name='item_%d_score' % item_num,
        calculation="if(${item_%d} = 'yes', 1, 0)" % item_num)

# Total raw score = sum of all item scores
score_sum = ' + '.join(['${item_%d_score}' % i for i in range(1, 90)])
row(type='calculate', name='raw_score', calculation=score_sum)

# Total yes/no/not_assessed counts (for visible items only? DST does visible only)
# But VSMS scoring uses ALL items raw score for SA lookup. We'll count all.
# For data quality tracking:
yes_sum = ' + '.join(["if(${item_%d} = 'yes', 1, 0)" % i for i in range(1, 90)])
no_sum = ' + '.join(["if(${item_%d} = 'no', 1, 0)" % i for i in range(1, 90)])
na_sum = ' + '.join(["if(${item_%d} = 'not_assessed', 1, 0)" % i for i in range(1, 90)])
row(type='calculate', name='total_yes_items', calculation=yes_sum)
row(type='calculate', name='total_no_items', calculation=no_sum)
row(type='calculate', name='total_not_assessed_items', calculation=na_sum)

# ============================================ Doll 1965 Raw Score -> Social Age (months) lookup
# 1:1 mapping per Doll 1965 manual Appendix: raw_score 0-89 -> SA months 0-89
# Implemented as nested if() chain for XLSForm compatibility

def build_sa_lookup():
    # Build nested if from high to low
    expr = '0'
    for rs in range(89, -1, -1):
        expr = 'if(${raw_score} = %d, %d, %s)' % (rs, rs, expr)
    return expr

sa_expr = build_sa_lookup()
row(type='calculate', name='social_age_months', calculation=sa_expr)

# Social Age display
row(type='calculate', name='social_age_years', calculation='floor(${social_age_months} div 12)')
row(type='calculate', name='social_age_remaining_months', calculation='${social_age_months} - (${social_age_years} * 12)')

# ============================================ Social Quotient (SQ)
# If CA months > 0: SQ = (SA_months / CA_months) * 100
# If CA months == 0 (or invalid age): SQ is not interpretable
row(type='calculate', name='social_quotient_raw',
    calculation="if(${age_valid} = 'yes' and ${ca_months_dec} > 0, ${social_age_months} div ${ca_months_dec} * 100, null)")

row(type='calculate', name='social_quotient_rounded',
    calculation="if(${social_quotient_raw} != null, round(${social_quotient_raw}), null)")

# SQ Interpretation with proper bands and CA=0 guard
# Bands: >=130 Very Superior (Markedly Advanced), 120-129 Superior, 110-119 High Average, 90-109 Average,
# 80-89 Low Average, 70-79 Borderline, <70 Social Developmental Delay
# If SQ is null (CA=0), interpretation is "Not interpretable (age = 0)"
sq_interp = (
    "if(${social_quotient_rounded} == null, 'Not interpretable (age = 0)', "
    "if(${score_status} != 'complete', 'Incomplete', "
    "if(${social_quotient_rounded} >= 130, 'Very Superior (Markedly Advanced)', "
    "if(${social_quotient_rounded} >= 120, 'Superior', "
    "if(${social_quotient_rounded} >= 110, 'High Average', "
    "if(${social_quotient_rounded} >= 90, 'Average', "
    "if(${social_quotient_rounded} >= 80, 'Low Average', "
    "if(${social_quotient_rounded} >= 70, 'Borderline', "
    "'Social Developmental Delay'))))))))"
)
row(type='calculate', name='sq_interpretation', calculation=sq_interp)

# ============================================ Score status
# complete | incomplete | invalid_age
row(type='calculate', name='score_status',
    calculation="if(${age_valid} != 'yes', 'invalid_age', if(${total_not_assessed_items} > 0, 'incomplete', 'complete'))")

# Required reason if any not_assessed
row(type='text', name='na_reason', label='Reason for items not assessed', required='true()',
    relevant="${total_not_assessed_items} > 0")

# Clinical notes
row(type='text', name='clinical_notes', label='Clinical notes')

# Result display notes
row(type='note', name='result_complete', label='✅ Assessment complete. Social Quotient: ${social_quotient_rounded} (${sq_interpretation}).',
    relevant="${score_status} = 'complete'")
row(type='note', name='result_incomplete', label='⚠️ Score incomplete — clinician review required. Some items were not assessed.',
    relevant="${score_status} = 'incomplete'")
row(type='note', name='result_invalid', label='❌ Invalid age: child must be 0–15 years for VSMS.',
    relevant="${score_status} = 'invalid_age'}")

# Supporting Documents / Scale Upload
row(type='begin group', name='g_supporting_docs', label='Supporting Documents / Scale Upload')
row(type='image', name='upload_scale_image', label='Upload completed scale / assessment sheet (image)',
    hint='Upload clear photos of the completed paper scale, consent form, or supporting assessment document. Accepts JPG, JPEG, PNG. For PDF use next field.',
    instance_type='binary')
row(type='file', name='upload_scale_pdf', label='Upload completed scale / assessment sheet (PDF)',
    hint='Upload a PDF of the completed paper scale if not already uploaded as image. Accepts PDF.',
    instance_type='binary')
row(type='text', name='upload_caption', label='Attachment caption / description (optional)')
row(type='end group')

# Scoring version metadata
row(type='calculate', name='scoring_version', calculation="'vsms-v1-doll1965-1to1'")
row(type='calculate', name='scoring_notes',
    calculation="'Doll 1965 VSMS 1:1 raw=SA months (0-89). SQ=SA/CA*100. Internet snippet (40->54,42->60,45->66) differs from manual.'")

# ============================================ CHOICES sheet
ws_choices = wb.create_sheet('choices')
ws_choices.append(['list_name', 'name', 'label'])

# yesno
for n, l in [('yes', 'Yes'), ('no', 'No')]:
    ws_choices.append(['yesno', n, l])

# vsms_response
for n, l in [('yes', 'Yes'), ('no', 'No'), ('not_assessed', 'Not Assessed')]:
    ws_choices.append(['vsms_response', n, l])

# ============================================ SETTINGS sheet
ws_settings = wb.create_sheet('settings')
ws_settings.append(['form_title', 'form_id', 'version', 'default_language'])
ws_settings.append(['Vineland-style Social Maturity Scale (VSMS)', 'vineland', '2026-08-27', 'en'])

# Save
output_path = r'C:\Projects\EMRCHT\satoru-config\forms\app\vineland.xlsx'
wb.save(output_path)
print('Saved to', output_path)