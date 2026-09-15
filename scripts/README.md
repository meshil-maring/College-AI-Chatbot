# Repository maintenance scripts

One-off scripts used to prepare repository assets. Both are **historical**: their outputs are already
committed, so they are kept for provenance rather than routine use.

| Script | Purpose | Notes |
| --- | --- | --- |
| `write_migration.py` | Regenerates `supabase/migrations/20260909000001_phase_admin_2_extracted_text_column.sql` (adds `document_versions.extracted_text`) | The migration is already applied — running this overwrites the file, so only use it to reproduce it |
| `fix_indent.py` | Corrects the mis-indented `'low'` entry of the `notices_priority_check` array in `supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql` | Already applied; re-running is a no-op unless that migration is regenerated |

Both resolve the repository root from their own file location
(`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`), so they can be executed from any
working directory:

```powershell
python scripts/write_migration.py
python scripts/fix_indent.py
```