# Maintained migration sources

The approved academic domain removal uses focused, ordered SQL fragments
in [academic_decommission/](academic_decommission/README.md), assembled by
`scripts/maintenance/migrations/build_academic_decommission.py` into the flat
`supabase/migrations/` directory required by Supabase migration discovery.

Edit the sources and regenerate the output. The generated migration has an
explicit generator header and per-fragment hashes; generated output is outside
the maintained source size/count limits. Existing historical migrations retain
their original paths and bytes; this convention does not rewrite applied files.

Fragments must contain at most 250 physical lines, and each source folder at
most 15 directly contained maintained files. Use meaningful responsibility
subfolders as needed. The manifest lists dependency order explicitly.

The generator owns the outer BEGIN/COMMIT and schema-cache notification. SQL
function bodies may contain their normal procedural blocks. A separate reviewed
deployment step applies the generated migration after local validation.
