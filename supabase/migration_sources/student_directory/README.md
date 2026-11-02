# Student directory

Adds a tenant-scoped, read-only directory RPC for administrator student profiles
and pending setup invitations. Academic placement is derived from each student's
latest semester registration; sign-in timestamps come from Supabase Auth.

Generate using `python scripts/maintenance/student_directory/build_migration.py`;
use `--check` to verify parity. The later academic-scope migration corrects the
program tenant join to derive ownership through its department, matching the
exported academic schema. The generated migrations do not deploy SQL.
