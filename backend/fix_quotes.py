#!/usr/bin/env python3
"""Fix test_approval_workflow_phase_6_13_4.py - fix nonexistent function calls and syntax issues."""
from pathlib import Path
import re

path = Path(
    "f:/Git Project/CollegeAIChatbot/backend/tests/"
    "test_approval_workflow_phase_6_13_4.py"
)
content = path.read_text()

# 1. Fix line 703: there's a line with escaped backslashes causing syntax errors
# Pattern: authz.assert_in_organization({...}) with escaped quotes
old_pattern = r'    authz\.assert_in_organization\([^)]+\)'
new_line = (
    '    authz.assert_institution_in_organization(\n'
    '        ORG_A, context_a.get("organization_id")\n'
    '    )\n'
)

# Find and replace the problematic line
if re.search(old_pattern, content):
    content = re.sub(old_pattern, new_line, content)
    print(f"Fixed assert_in_organization -> assert_institution_in_organization")
else:
    print("Pattern not found, checking for other issues...")
    for i, line in enumerate(content.split('\n')):
        if 'assert_in_organization' in line and 'assert_can' not in line:
            print(f"Line {i+1}: {repr(line)}")

path.write_text(content)
print("Done")
