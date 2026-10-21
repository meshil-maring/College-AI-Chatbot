# Backend contributor instructions

Follow [STRUCTURE.md](STRUCTURE.md) for backend file placement, feature ownership,
naming, imports and cleanup. Read the affected layer's README before reorganizing
its modules, and keep its module guide current.

Before creating any file, follow the [shared project rules](../AGENTS.md): inspect
the existing structure, search for an existing implementation, and select the
owning feature and layer.

- Keep each folder at or below 15 directly contained, project-maintained files.
  If a folder already exceeds 15 files, or adding a file would exceed the limit,
  group related modules into descriptive subpackages before adding more files.
  Apply the same limit to every resulting folder; include package markers in
  the direct file count.
- Keep each source, test, and script file at or below 250 physical lines,
  including imports, comments, and blank lines. Split by responsibility before
  exceeding the limit; do not compress code or remove useful documentation to
  make the count smaller.
- Preserve Python package markers, imports, API contracts, and mock targets when
  splitting modules. Update the relevant layer guide with the resulting layout.

Run `python scripts/validation/check_structure.py` from `backend/` after a layout
change, plus regression checks appropriate to the behavior affected. Preserve
existing API contracts, tenant isolation and permission dependencies when moving
code. Keep local verification output in the repository's `logs/backend/` folder.
Check both size limits before finishing; the current backend validator checks
layout and imports, so a passing result alone does not verify the numeric limits.
