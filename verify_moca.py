import openpyxl
wb = openpyxl.load_workbook(r'C:\Projects\EMRCHT\satoru-config\forms\app\moca_assessment.xlsx')
ws = wb['survey']

# Check the education adjustment row
print('=== moca_education_adj ===')
for row_idx in range(120, 132):
    calc = ws.cell(row=row_idx, column=11).value
    name = ws.cell(row=row_idx, column=2).value
    print(f'Row {row_idx}: name={name}, calc={calc}')

print()

# Check final score
print('=== moca_total_score ===')
for row_idx in range(120, 132):
    calc = ws.cell(row=row_idx, column=11).value
    name = ws.cell(row=row_idx, column=2).value
    print(f'Row {row_idx}: name={name}, calc={calc}')

print()

# Check interpretation
print('=== moca_interpretation ===')
for row_idx in range(120, 132):
    calc = ws.cell(row=row_idx, column=11).value
    name = ws.cell(row=row_idx, column=2).value
    print(f'Row {row_idx}: name={name}, calc={calc}')