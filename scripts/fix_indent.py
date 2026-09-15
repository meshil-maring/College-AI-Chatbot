import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(REPO_ROOT, 'supabase', 'migrations', '20260909000000_phase_admin_1_admin_student_schema.sql')

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix the 'low' line in notices_priority_check (should have 12 spaces)
for i in range(len(lines)):
    if "low" in lines[i] and "text" in lines[i] and "ARRAY" not in lines[i]:
        if i > 0 and "ARRAY" in lines[i-1]:
            old = lines[i]
            lines[i] = "            'low'::\"text\",\n"
            print(f'Fixed line {i+1}: {repr(old)} -> {repr(lines[i])}')

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')

