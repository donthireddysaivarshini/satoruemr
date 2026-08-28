"""Append DST report-label keys to messages-en.properties (idempotent)."""
P = r'C:\Projects\EMRCHT\satoru-config\translations\messages-en.properties'
content = open(P, encoding='utf-8').read()

MARK = '# ---------- DST report ----------'
if MARK in content:
    content = content[:content.index(MARK)]

BANDS = [
    ('birth_to_3_months', 'Birth to 3 months'),
    ('m3_to_6', '3 to 6 months'), ('m6_to_9', '6 to 9 months'),
    ('m9_to_12', '9 to 12 months'), ('m12_to_18', '12 to 18 months'),
    ('m18_to_24', '18 to 24 months'), ('m24_to_36', '2 to 3 years'),
    ('m36_to_48', '3 to 4 years'), ('m48_to_60', '4 to 5 years'),
    ('m60_to_72', '5 to 6 years'), ('m72_to_84', '6 to 7 years'),
    ('m84_to_96', '7 to 8 years'), ('m96_to_108', '8 to 9 years'),
    ('m108_to_120', '9 to 10 years'), ('m120_to_132', '10 to 11 years'),
    ('m132_to_144', '11 to 12 years'), ('m144_to_156', '12 to 13 years'),
    ('m156_to_180', '13 to 15 years'),
]
RAW = [
    "1. birth cry present*|2. equal bilateral movements|3. responds to bell|4. vocalises sounds*|5. smiles spontaneously|6. eyes follow moving objects|7. head steady",
    "8. reaches for objects|9. laughs aloud*|10. recognizes mother|11. vocalizes for pleasure/babbles*|12. carries objects to mouth|13. rolls over",
    "14. imitates speech sounds*|15. sits by self|16. thumb finger grasp|17. shows curiosity",
    "18. says 3 word, dada, mama etc*|19. stands alone well|20. follows simple instructions*|21. cooperates for dressing",
    "22. many intelligible words*|23. walks, runs well|24. indicates wants|25. scribbles spontaneously",
    "26. says sentences of 2/3 words*|27. points out objects in pictures|28. shows body parts|29. participates in play",
    "30. copies O|31. relates experiences*|32. knows names, uses of common objects|33. begins to ask why?*|34. takes food by self|35. toilet control present",
    "36. buttons up|37. comprehends hunger, cold*|38. plays cooperatively with children|39. repeats 3 digits*|40. tells stories*",
    "41. defines words*|42. makes simple drawings|43. dresses with no supervision|44. describes actions in pictures*|45. gives sensible answers to questions*|46. goes about neighborhood",
    "47. can name primary color|48. plays games governed by rules|49. writes simple words*|50. gains admission to school|51. enjoys constructive play",
    "52. adapts to home, school|53. tells differences of objects|54. spells, reads, writes simple words*|55. enjoys group play|56. knows comparative value of coins",
    "57. combs hair by self|58. makes small purchases|59. competition in school/play|60. tells time",
    "61. tells day, month, year*|62. reads on own initiative*|63. recognizes property rights|64. favourite of fairy tales*|65. muscle coordination games (marbles)|66. bathes self unaided",
    "67. cooperates keenly with companions|68. has various hobbies, collections|69. goes about town freely|70. sex difference in play becomes marked|71. can stay away from home",
    "72. writes occasional short letters|73. comprehends social situations|74. physical feats liked|75. able to discuss problems*",
    "76. enjoys books, newspapers, magazines|77. more independent in spending|78. capable of self-criticism",
    "79. shows foresight, planning, judgment|80. learns from experiences|81. plays difficult games|82. interested in dressing up|83. understands abstract ideas (justice)",
    "84. makes sensible plans for future (job)|85. follows current events*|86. buys own clothing|87. systematises own work|88. purchases for others",
]

L = []
L.append(MARK)
L.append('report.dst.patient_uuid = Participant')
L.append('report.dst.patient_id = Participant ID')
L.append('report.dst.patient_name = Child Name')
L.append('report.dst.screened_by = Submitted by (user ID)')
L.append('report.dst.screened_by_name = Submitted by')
L.append('report.dst.g_intro = Developmental Screening Test (DST)')
L.append('report.dst.g_intro.dst_disclaimer = Disclaimer')
L.append('report.dst.g_intro.acknowledged = Trained health worker confirmation')
L.append('report.dst.g_child = Child details & assessment date')
L.append('report.dst.g_child.assessment_date = Assessment date')
L.append('report.dst.g_child.child_dob = Child date of birth')
L.append('report.dst.g_child.ca_days = Chronological age (days)')
L.append('report.dst.g_child.ca_months_dec = Chronological age (months)')
L.append('report.dst.g_child.age_valid = Age within DST range')
L.append('report.dst.g_child.show_all = Show all items mode')
L.append('report.dst.show_all = Show all items mode')
for key, label in BANDS:
    L.append('report.dst.g_%s = %s' % (key, label))
k = 0
for bi, raw in enumerate(RAW):
    band_key = BANDS[bi][0]
    for txt in raw.split('|'):
        k += 1
        num, _, rest = txt.partition('. ')
        speech = rest.endswith('*')
        name = rest.rstrip('*').strip()
        lbl = '%d. %s' % (int(num), name)
        if speech:
            lbl += ' [Speech/Language-related]'
        L.append('report.dst.g_%s.item_%d = %s' % (band_key, int(num), lbl))

audit = [
    ('ca_band', 'Chronological age band'), ('ca_months_floor', 'Chronological age (months)'),
    ('total_passed_items', 'Total passed items'), ('total_failed_items', 'Total failed items'),
    ('total_not_assessed_items', 'Total not-assessed items'),
    ('developmental_age_months', 'Developmental Age (months)'),
    ('developmental_age_years', 'Developmental Age (years)'),
    ('developmental_age_remaining_months', 'Developmental Age (remaining months)'),
    ('score_status', 'Score status'), ('na_reason', 'Reason items were not assessed'),
    ('clinical_notes', 'Clinical notes'),
    ('developmental_quotient_raw', 'DQ (raw)'),
    ('developmental_quotient_rounded', 'Developmental Quotient (DQ)'),
]
WEIGHTS = ['3 div 7', '0.5', '0.75', '0.75', '1.5', '1.5', '2', '2.4', '2', '2.4',
           '2.4', '3', '2', '2.4', '3', '4', '2.4', '4.8']
MAXM = [3, 3, 3, 3, 6, 6, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 24]
for i in range(1, 19):
    audit.append(('band_%d_passed_count' % i, 'Band %d passed count' % i))
    audit.append(('band_%d_failed_count' % i, 'Band %d failed count' % i))
    audit.append(('band_%d_not_assessed' % i, 'Band %d not assessed count' % i))
    audit.append(('band_%d_earned_months' % i,
                  'Band %d earned months (max %s)' % (i, MAXM[i - 1])))
for name, label in audit:
    L.append('report.dst.%s = %s' % (name, label))
L.append('report.dst.scoring_version = dst-v1-provided-weight-table')

block = '\n'.join(L) + '\n'
open(P, 'w', encoding='utf-8').write(content + block)
print('appended', len(L), 'keys; total file lines:', block.count('\n') + content.count('\n'))
