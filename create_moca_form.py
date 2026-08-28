import openpyxl

wb = openpyxl.Workbook()

# ============================================================
# SURVEY SHEET
# ============================================================
ws = wb.active
ws.title = 'survey'

headers = ['type', 'name', 'label::en', 'label::te', 'hint::en', 'appearance', 'relevant', 'constraint', 'constraint_message::en', 'required', 'calculation', 'default', 'read_only', 'image']
ws.append(headers)

rows = [
    ['begin group', 'inputs', 'Participant', '', '', 'field-list', "./source = 'user'", '', '', '', '', '', ''],
    ['hidden', 'source', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'source_id', '', '', '', '', '', '', '', '', '', '', ''],
    ['begin group', 'user', 'User', '', '', 'field-list', '', '', '', '', '', '', ''],
    ['hidden', 'contact_id', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'name', '', '', '', '', '', '', '', '', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],
    ['begin group', 'contact', 'Participant', '', '', 'field-list', '', '', '', '', '', '', ''],
    ['db:person', '_id', 'Select participant', '', '', 'select-contact type-participant', '', '', '', '', '', '', ''],
    ['hidden', 'patient_id', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'name', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'age', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'gender', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'phone', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'education_level', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'consent_given', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'informant_name', '', '', '', '', '', '', '', '', '', '', ''],
    ['hidden', 'informant_phone', '', '', '', '', '', '', '', '', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['calculate', 'patient_uuid', '', '', '', '', '', '', '', '', '../inputs/contact/_id', '', ''],
    ['calculate', 'patient_id', '', '', '', '', '', '', '', '', '../inputs/contact/patient_id', '', ''],
    ['calculate', 'patient_name', '', '', '', '', '', '', '', '', '../inputs/contact/name', '', ''],
    ['calculate', 'patient_sex', '', '', '', '', '', '', '', '', '../inputs/contact/gender', '', ''],
    ['calculate', 'patient_age', '', '', '', '', '', '', '', '', '../inputs/contact/age', '', ''],
    ['calculate', 'patient_phone', '', '', '', '', '', '', '', '', '../inputs/contact/phone', '', ''],
    ['calculate', 'patient_education', '', '', '', '', '', '', '', '', '../inputs/contact/education_level', '', ''],
    ['calculate', 'screened_by', '', '', '', '', '', '', '', '', '../inputs/user/contact_id', '', ''],
    ['calculate', 'screened_by_name', '', '', '', '', '', '', '', '', '../inputs/user/name', '', ''],

    ['begin group', 'g_consent', 'Consent', '', '', 'field-list', '', '', '', '', '', '', ''],
    ['select_one yesno', 'consent_reconfirmed', 'Consent re-confirmed for the MoCA assessment?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['begin group', 'g_visuospatial', 'Visuospatial / Executive', '', '', 'field-list', "${consent_reconfirmed} = 'yes'", '', '', '', '', '', ''],
    ['note', 'trail_making_inst', 'Please draw a line, going from a number to a letter in ascending order. Begin here [point to (1)] and draw a line from 1 then to A then to 2 and so on. End here [point to (E)].', '', '', '', '', '', '', '', '', '', '', 'trail_making.png'],
    ['select_one yesno', 'trail_making', 'Trail Making (1-A-2-B-3-C-4-D-5-E, no crossing lines)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['note', 'cube_inst', 'Copy this drawing as accurately as you can, in the space below.', '', '', '', '', '', '', '', '', '', '', 'cube.png'],
    ['select_one yesno', 'cube_copy', 'Cube Copy (3D, all lines, no extra lines, parallel lines)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['note', 'clock_inst', 'Draw a clock. Put in all the numbers and set the time to 10 past 11.', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'clock_contour', 'Clock - Contour (circle, minor distortion OK)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'clock_numbers', 'Clock - Numbers (all 12 present, correct order, correct quadrants)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'clock_hands', 'Clock - Hands (two hands, 10:11, hour hand shorter, centered)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['begin group', 'g_naming', 'Naming', '', '', 'field-list', "${consent_reconfirmed} = 'yes'", '', '', '', '', '', ''],
    ['note', 'naming_inst', 'Beginning on the left, point to each figure and say: Tell me the name of this animal.', '', '', '', '', '', '', '', '', '', '', 'naming.png'],
    ['select_one naming_score', 'naming_1', 'Figure 1 (Lion)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one naming_score', 'naming_2', 'Figure 2 (Rhinoceros / Rhino)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one naming_score', 'naming_3', 'Figure 3 (Camel / Dromedary)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['begin group', 'g_memory', 'Memory', '', '', 'field-list', "${consent_reconfirmed} = 'yes'", '', '', '', '', '', ''],
    ['note', 'memory_inst_trial1', 'This is a memory test. I am going to read a list of words that you will have to remember now and later on. Listen carefully. When I am through, tell me as many words as you can remember. It does not matter in what order you say them.', '', '', '', '', '', '', '', '', '', ''],
    ['note', 'memory_words', 'Words: FACE, VELVET, CHURCH, DAISY, RED', '', '', '', '', '', '', '', '', '', '', ''],
    ['begin group', 'mem_trial1', 'Trial 1', '', '', 'field-list', '', '', '', '', '', '', ''],
    ['select_one yesno', 'mem_t1_face', 'FACE', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'mem_t1_velvet', 'VELVET', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'mem_t1_church', 'CHURCH', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'mem_t1_daisy', 'DAISY', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'mem_t1_red', 'RED', '', '', '', '', '', '', 'yes', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],
    ['note', 'memory_inst_trial2', 'I am going to read the same list for a second time. Try to remember and tell me as many words as you can, including words you said the first time.', '', '', '', '', '', '', '', '', '', ''],
    ['begin group', 'mem_trial2', 'Trial 2', '', '', 'field-list', '', '', '', '', '', '', ''],
    ['select_one yesno', 'mem_t2_face', 'FACE', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'mem_t2_velvet', 'VELVET', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'mem_t2_church', 'CHURCH', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'mem_t2_daisy', 'DAISY', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'mem_t2_red', 'RED', '', '', '', '', '', '', 'yes', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],
    ['note', 'memory_inst_delayed', 'I will ask you to recall those words again at the end of the test.', '', '', '', '', '', '', '', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['begin group', 'g_attention', 'Attention', '', '', 'field-list', "${consent_reconfirmed} = 'yes'", '', '', '', '', '', ''],
    ['note', 'attention_fwd_inst', 'I am going to say some numbers and when I am through, repeat them to me exactly as I said them. Sequence: 2 1 8 5 4 (1 digit/sec).', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'digit_span_fwd', 'Forward Digit Span (2-1-8-5-4) correct?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['note', 'attention_bwd_inst', 'Now I am going to say some more numbers, but when I am through you must repeat them to me in the backwards order. Sequence: 7 4 2 (1 digit/sec). Correct backward: 2-4-7.', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'digit_span_bwd', 'Backward Digit Span (2-4-7) correct?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['note', 'vigilance_inst', 'I am going to read a sequence of letters. Every time I say the letter A, tap your hand once. If I say a different letter, do not tap your hand. Letters: F B A C M N A A J K L B A F A K D E A A A J A M O F A A B (read at 1/sec).', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'vigilance', 'Vigilance (A-tapping) - 0 or 1 error?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['note', 'serial7_inst', 'Count by subtracting seven from 100, and then keep subtracting seven from your answer until I tell you to stop. (Max 5 subtractions: 93, 86, 79, 72, 65)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one serial7_score', 'serial_7s', 'Serial 7s score (0-3)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['begin group', 'g_language', 'Language', '', '', 'field-list', "${consent_reconfirmed} = 'yes'", '', '', '', '', '', ''],
    ['note', 'sentence1_inst', 'Repeat: I only know that John is the one to help today. (Must be exact)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'sentence_rep_1', 'Sentence 1: I only know that John is the one to help today. (Exact)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['note', 'sentence2_inst', 'The cat always hid under the couch when dogs were in the room. (Must be exact)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'sentence_rep_2', 'Sentence 2: The cat always hid under the couch when dogs were in the room. (Exact)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['note', 'fluency_inst', 'Tell me as many words as you can think of that begin with the letter F. No proper nouns, numbers, or same-sound-different-suffix words. 60 seconds.', '', '', '', '', '', '', '', '', '', ''],
    ['integer', 'fluency_count', 'Fluency count (F words, >=11 = 1 pt)', '', '', '', '', '', '. >= 0', '', 'yes', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['begin group', 'g_abstraction', 'Abstraction', '', '', 'field-list', "${consent_reconfirmed} = 'yes'", '', '', '', '', '', ''],
    ['note', 'abstraction_inst_practice', 'Practice: Tell me how an orange and a banana are alike. If concrete, prompt once: Tell me another way. If not fruit, say: Yes, and they are also both fruit.', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'abstraction_1', 'Train - Bicycle (conceptual: transportation/travelling/trips = 1 pt; wheels = 0)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'abstraction_2', 'Ruler - Watch (conceptual: measuring instruments/measure = 1 pt; numbers = 0)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['begin group', 'g_delayed_recall', 'Delayed Recall', '', '', 'field-list', "${consent_reconfirmed} = 'yes'", '', '', '', '', '', ''],
    ['note', 'delayed_inst', 'I read some words to you earlier, which I asked you to remember. Tell me as many of those words as you can remember.', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'delayed_face', 'FACE (free recall)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one delayed_cue', 'delayed_face_cat', 'FACE - Category cue (part of body)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one delayed_cue', 'delayed_face_mc', 'FACE - Multiple choice (nose/face/hand)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'delayed_velvet', 'VELVET (free recall)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one delayed_cue', 'delayed_velvet_cat', 'VELVET - Category cue (type of fabric)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one delayed_cue', 'delayed_velvet_mc', 'VELVET - Multiple choice (denim/cotton/velvet)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'delayed_church', 'CHURCH (free recall)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one delayed_cue', 'delayed_church_cat', 'CHURCH - Category cue (type of building)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one delayed_cue', 'delayed_church_mc', 'CHURCH - Multiple choice (church/school/hospital)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'delayed_daisy', 'DAISY (free recall)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one delayed_cue', 'delayed_daisy_cat', 'DAISY - Category cue (type of flower)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one delayed_cue', 'delayed_daisy_mc', 'DAISY - Multiple choice (rose/daisy/tulip)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'delayed_red', 'RED (free recall)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one delayed_cue', 'delayed_red_cat', 'RED - Category cue (a colour)', '', '', '', '', '', '', '', '', '', ''],
    ['select_one delayed_cue', 'delayed_red_mc', 'RED - Multiple choice (red/blue/green)', '', '', '', '', '', '', '', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['begin group', 'g_orientation', 'Orientation', '', '', 'field-list', "${consent_reconfirmed} = 'yes'", '', '', '', '', '', ''],
    ['note', 'orientation_inst', 'Tell me the date today. If incomplete, prompt for year, month, exact date, day. Then: Tell me the name of this place, and which city it is in. No points if off by one day.', '', '', '', '', '', '', '', '', '', ''],
    ['select_one yesno', 'orientation_date', 'Exact date correct?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'orientation_month', 'Month correct?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'orientation_year', 'Year correct?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'orientation_day', 'Day of week correct?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'orientation_place', 'Place (hospital/clinic/office) correct?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['select_one yesno', 'orientation_city', 'City correct?', '', '', '', '', '', '', 'yes', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    ['calculate', 'moca_visuospatial_total', '', '', '', '', '', '', '', '', 'if(${trail_making} = "yes", 1, 0) + if(${cube_copy} = "yes", 1, 0) + if(${clock_contour} = "yes", 1, 0) + if(${clock_numbers} = "yes", 1, 0) + if(${clock_hands} = "yes", 1, 0)', '', ''],
    ['calculate', 'moca_naming_total', '', '', '', '', '', '', '', '', 'if(${naming_1} = "yes", 1, 0) + if(${naming_2} = "yes", 1, 0) + if(${naming_3} = "yes", 1, 0)', '', ''],
    ['calculate', 'moca_memory_total', '', '', '', '', '', '', '', '', 'if(${delayed_face} = "yes", 1, 0) + if(${delayed_velvet} = "yes", 1, 0) + if(${delayed_church} = "yes", 1, 0) + if(${delayed_daisy} = "yes", 1, 0) + if(${delayed_red} = "yes", 1, 0)', '', ''],
    ['calculate', 'moca_attention_total', '', '', '', '', '', '', '', '', 'if(${digit_span_fwd} = "yes", 1, 0) + if(${digit_span_bwd} = "yes", 1, 0) + if(${vigilance} = "yes", 1, 0) + ${serial_7s}', '', ''],
    ['calculate', 'moca_language_total', '', '', '', '', '', '', '', '', 'if(${sentence_rep_1} = "yes", 1, 0) + if(${sentence_rep_2} = "yes", 1, 0) + if(${fluency_count} >= 11, 1, 0)', '', ''],
    ['calculate', 'moca_abstraction_total', '', '', '', '', '', '', '', '', 'if(${abstraction_1} = "yes", 1, 0) + if(${abstraction_2} = "yes", 1, 0)', '', ''],
    ['calculate', 'moca_delayed_total', '', '', '', '', '', '', '', '', 'if(${delayed_face} = "yes", 1, 0) + if(${delayed_velvet} = "yes", 1, 0) + if(${delayed_church} = "yes", 1, 0) + if(${delayed_daisy} = "yes", 1, 0) + if(${delayed_red} = "yes", 1, 0)', '', ''],
    ['calculate', 'moca_orientation_total', '', '', '', '', '', '', '', '', 'if(${orientation_date} = "yes", 1, 0) + if(${orientation_month} = "yes", 1, 0) + if(${orientation_year} = "yes", 1, 0) + if(${orientation_day} = "yes", 1, 0) + if(${orientation_place} = "yes", 1, 0) + if(${orientation_city} = "yes", 1, 0)', '', ''],
    ['calculate', 'moca_raw_total', '', '', '', '', '', '', '', '', '${moca_visuospatial_total} + ${moca_naming_total} + ${moca_memory_total} + ${moca_attention_total} + ${moca_language_total} + ${moca_abstraction_total} + ${moca_orientation_total}', '', ''],
    ['calculate', 'moca_education_adj', '', '', '', '', '', '', '', '', 'if(${patient_education} = "illiterate" or ${patient_education} = "primary", 1, 0)', '', ''],
    ['calculate', 'moca_total_score', '', '', '', '', '', '', '', '', 'min(${moca_raw_total} + ${moca_education_adj}, 30)', '', ''],
    ['calculate', 'moca_interpretation', '', '', '', '', '', '', '', '', 'if(${moca_total_score} >= 26, "normal", "impaired")', '', ''],

    ['begin group', 'g_admin', 'Administrator', '', '', 'field-list', '', '', '', '', '', '', ''],
    ['string', 'administered_by', 'Administered by (staff name)', '', '', '', '', '', '', 'yes', '', '', ''],
    ['dateTime', 'assessment_datetime', 'Date & Time of Assessment', '', '', '', '', '', '', 'yes', 'now()', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],

    # ===== MOCA SHEET UPLOAD (last section) =====
    ['begin group', 'g_moca_sheets', 'MoCA sheet / supporting documents', '', '', 'field-list', '', '', '', '', '', '', ''],
    ['begin repeat', 'moca_sheets', 'MoCA sheet upload', 'Upload the completed paper MoCA sheet (image or PDF). Add more than one if needed.', '', 'field-list', '', '', '', '', '', '', ''],
    ['file', 'moca_sheet', 'Upload MoCA sheet (image or PDF)', '', '', '', '', '', '', '', '', '', 'binary'],
    ['end repeat', '', '', '', '', '', '', '', '', '', '', '', ''],
    ['end group', '', '', '', '', '', '', '', '', '', '', '', ''],
]

for r in rows:
    ws.append(r)

# ============================================================
# CHOICES SHEET
# ============================================================
ws_choices = wb.create_sheet('choices')
ws_choices.append(['list_name', 'name', 'label::en', 'label::te'])

choices = [
    ['yesno', 'yes', 'Yes', 'అవును'],
    ['yesno', 'no', 'No', 'కాదు'],
    ['yesnodk', 'yes', 'Yes', 'అవును'],
    ['yesnodk', 'no', 'No', 'కాదు'],
    ['yesnodk', 'dk', "Don't know / Not assessed", 'తెలియదు'],
    ['naming_score', 'yes', 'Correct', 'చక్కగా'],
    ['naming_score', 'no', 'Incorrect', 'తప్పు'],
    ['naming_score', 'dk', "Don't know / Not assessed", 'తెలియదు'],
    ['serial7_score', '0', '0 correct subtractions (0 pts)', '0 సరిగా 없지'],
    ['serial7_score', '1', '1 correct subtraction (1 pt)', '1 సరిగ్గా అవుటుంది'],
    ['serial7_score', '2', '2-3 correct subtractions (2 pts)', '2-3 సరిగ్గాయి'],
    ['serial7_score', '3', '4-5 correct subtractions (3 pts)', '3-5 సరిగ్గాయి'],
    ['delayed_cue', 'yes', 'Recalled with cue', 'సూచనతో మrode'],
    ['delayed_cue', 'no', 'Not recalled even with cue', 'సూచనతో కాదు మrode'],
    ['orientation_month', '1', 'January', 'జనవరి'],
    ['orientation_month', '2', 'February', 'ఫిబ్రవరి'],
    ['orientation_month', '3', 'March', 'మార్చి'],
    ['orientation_month', '4', 'April', 'ఏప్రిల్'],
    ['orientation_month', '5', 'May', 'మే'],
    ['orientation_month', '6', 'June', 'జూన్'],
    ['orientation_month', '7', 'July', 'జూలై'],
    ['orientation_month', '8', 'August', 'ఆగస్టు'],
    ['orientation_month', '9', 'September', 'September'],
    ['orientation_month', '10', 'October', 'అక్టోబర్'],
    ['orientation_month', '11', 'November', 'నవంబర్'],
    ['orientation_month', '12', 'December', 'డిసెంబర్'],
    ['orientation_day', 'monday', 'Monday', 'సోమవారం'],
    ['orientation_day', 'tuesday', 'Tuesday', 'మంగళవారం'],
    ['orientation_day', 'wednesday', 'Wednesday', 'బుధవారం'],
    ['orientation_day', 'thursday', 'Thursday', 'గురువారం'],
    ['orientation_day', 'friday', 'Friday', 'శుక్రవారం'],
    ['orientation_day', 'saturday', 'Saturday', 'శనివారం'],
    ['orientation_day', 'sunday', 'Sunday', 'ఆదివారం'],
]

for c in choices:
    ws_choices.append(c)

# ============================================================
# SETTINGS SHEET
# ============================================================
ws_settings = wb.create_sheet('settings')
ws_settings.append(['form_title', 'form_id', 'version', 'default_language'])
ws_settings.append(['MoCA Assessment', 'moca_assessment', '2026-08-22 03-00', 'en'])

wb.save(r'C:\Projects\EMRCHT\satoru-config\forms\app\moca_assessment.xlsx')
print('moca_assessment.xlsx created successfully')