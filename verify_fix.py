import openpyxl
import re

wb = openpyxl.load_workbook(r'C:\Projects\EMRCHT\satoru-config\forms\app\ddst.xlsx')
ws = wb['survey']

# Print Gross Motor items (rows 95-128, items 94-125)
print('=== Gross Motor Items relevant expressions ===')
for row_idx in range(95, 128):  # items 94-125
    relevant = ws.cell(row=row_idx, column=7).value
    name = ws.cell(row=row_idx, column=3).value
    local_no = row_idx - 93
    print(f'GM{local_no}: relevant={relevant}, label={name}')

print()

# Now check which GM items are visible at 9 months age
print('=== Gross Motor items visible at 9 months age (assuming show_all=no) ===')
visible_at_9m = []
for row_idx in range(95, 128):
    relevant = ws.cell(row=row_idx, column=7).value
    name = ws.cell(row=row_idx, column=3).value
    local_no = row_idx - 93
    # Item visible if: show_all='yes' OR ca_months_dec >= age
    # With show_all='no', item visible if age is None or ca_months_dec >= age
    # For our check, we look at the age value in the relevant expression
    if relevant and 'ca_months_dec' in str(relevant):
        # Extract the age threshold from the relevant expression
        match = re.search(r'>= (\S+)', str(relevant))
        if match:
            age_threshold = float(match.group(1))
            if age_threshold <= 9.0:
                visible_at_9m.append((local_no, name, age_threshold))

visible_at_9m.sort(key=lambda x: x[0])
print(f'GM items visible at 9 months (with show_all=no): {[(n, a) for n, _, a in visible_at_9m]}')

print()
print('=== Expected: At 9 months, GM items #2, #3, #4, #5, #6, #7-10 should be visible ===')
print('Checking if items #2, #3, #5, #6 appear alongside #4, #7-10, producing a clean sequential item list with no gaps.')

# GM items and their ages (from the corrected data):
# GM1: Symmetrical Movements - None (always visible)
# GM2: Lift Head - 2.4928 months
# GM3: Head Up 45° - 3.4928 months
# GM4: Head Up 90° - 4.0 months
# GM5: Sit, Head Steady - 4.4928 months
# GM6: Bear Weight on Legs - 4.4928 months
# GM7: Chest Up, Arm Support - 5.5 months
# GM8: Roll Over - 6.0 months
# GM9: Pull to Sit, No Head Lag - 6.5 months
# GM10: Sit, No Support - 8.5 months
# GM11: Stand, Holding On - 9.5 months (NOT visible at 9 months)

print('GM items with age <= 9.0 months:')
for n, name, age in visible_at_9m:
    print(f'  GM{n}: {name} (age {age} months)')

# Check if we have a clean sequential list
ages_visible = [age for _, _, age in visible_at_9m]
print(f'\nAges visible at 9 months: {ages_visible}')
print(f'Number of GM items visible at 9 months: {len(ages_visible)}')

# The expected items visible at 9 months should be:
# GM1 (always), GM2 (2.4928), GM3 (3.4928), GM4 (4.0), GM5 (4.4928), GM6 (4.4928), GM7 (5.5), GM8 (6.0), GM9 (6.5), GM10 (8.5)
# That's 10 items (GM1-GM10), which is a clean sequential list with no gaps from 1 to 10
expected_visible = list(range(1, 11))  # GM1 through GM10
actual_visible = [n for n, _, _ in visible_at_9m]
print(f'Expected visible: GM1-GM10')
print(f'Actual visible: {actual_visible}')
if actual_visible == expected_visible:
    print('PASS: Clean sequential item list with no gaps at 9 months!')
else:
    print('FAIL: Item list has gaps or missing items')
    print(f'Missing: {set(expected_visible) - set(actual_visible)}')
    print(f'Extra: {set(actual_visible) - set(expected_visible)}')