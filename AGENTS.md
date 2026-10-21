# Project structure rules

These rules apply to both `frontend/` and `backend/`. Read the relevant local
`AGENTS.md` and structure guide before making changes:

- [Frontend instructions](frontend/AGENTS.md) and [structure guide](frontend/docs/STRUCTURE.md)
- [Backend instructions](backend/AGENTS.md) and [structure guide](backend/STRUCTURE.md)

## Before creating a file

1. Inspect the existing folders, nearby files, and the owning feature or layer.
   Search for an existing implementation before adding another one.
2. Reuse an existing file when the responsibility belongs there and it can stay
   within the size limit. Otherwise, choose a focused module in the existing
   feature structure. Do not create unrelated files in project or layer roots.
3. Check the destination folder's direct file count before adding the file.
   If adding it would exceed 15 files, group related files into meaningful
   subfolders first. If the folder already exceeds 15 files, reorganize the
   affected folder before adding more files.
4. Check the planned file size. If the change would exceed 250 physical lines,
   split the responsibility into focused modules before completing the change.

## Folder and file limits

- A folder may contain at most **15 directly contained, project-maintained
  files**. Count source, tests, documentation, configuration, and package markers.
  Subfolders do not count as files; apply the limit to each subfolder as well.
- Group by feature, workflow, or responsibility. Use descriptive folder names
  consistent with the existing project. Do not use numbered folders, arbitrary
  equal-sized groups, or generic dumping grounds to satisfy the limit.
- Keep each source, test, stylesheet, and script file at or below **250 physical
  lines**, including imports, comments, and blank lines. This is a hard limit.
  Do not compress statements, remove useful comments, or reduce formatting to
  conceal an oversized file.
- Generated dependencies, build output, caches, lockfiles, and archived evidence
  are outside these maintenance limits. Do not move maintained application code
  into an excluded location to bypass a rule. Do not split generated output by
  hand; change its generator when necessary.

## When splitting or moving code

Keep related components, hooks, helpers, contracts, and tests with their owning
feature or backend layer. Extract shared code only when it has real consumers.
Preserve application behavior, public contracts, permissions, and tenant isolation.
Update imports, exports, mock targets, and documentation links together; avoid
circular dependencies and unnecessary forwarding modules.

Before finishing, check the affected folders against both limits, run the local
structure validator, and run regression checks appropriate to the change. Keep
verification logs in `logs/frontend/` or `logs/backend/`, outside the code roots.
