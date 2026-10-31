/** In-memory PostgreSQL fallback; never reads .env or opens a database URL. */
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = fileURLToPath(new URL("../../../", import.meta.url));
const runtimePath = process.argv[2];
if (!runtimePath)
  throw new Error(
    "Pass the path to an installed @electric-sql/pglite package directory.",
  );
const runtime = resolve(runtimePath, "dist");
const { PGlite } = await import(pathToFileURL(resolve(runtime, "index.js")));
const { btree_gist } = await import(
  pathToFileURL(resolve(runtime, "contrib/btree_gist.js"))
);
const database = new PGlite({ extensions: { btree_gist } });

async function run(relative) {
  console.log(`CHECK ${relative}`);
  await database.exec(await readFile(resolve(root, relative), "utf8"));
}

try {
  await run("backend/tests/academics/deletion/identity_fixture.sql");
  const source = "supabase/migration_sources/academic_export";
  await database.exec("BEGIN");
  for (const name of ["tables", "constraints", "indexes", "permissions"])
    await run(`${source}/${name}.sql`);
  await run(
    "supabase/migration_sources/academic_foundations/authorization.sql",
  );
  for (const name of [
    "tenant",
    "validation",
    "parent_guards",
    "write",
    "security",
  ])
    await run(`${source}/${name}.sql`);
  await database.exec("COMMIT");
  await run(
    "supabase/migrations/20261027000000_academic_workspace_integration.sql",
  );
  await run("supabase/migrations/20261030000000_semester_registration.sql");
  await run(
    "supabase/migrations/20261030010000_unused_department_deletion.sql",
  );
  await run("supabase/migrations/20261030020000_unused_program_deletion.sql");
  await run(
    "supabase/migrations/20261030030000_unused_calendar_section_deletion.sql",
  );
  await run(
    "supabase/migrations/20261031000000_academic_curriculum_subject_snapshots.sql",
  );
  await run("scripts/validation/academic_workspace/seed.sql");
  await database.exec("BEGIN");
  await run("backend/tests/academics/workspace/contracts.sql");
  await database.exec("ROLLBACK");
  const accountsBefore = await database.query(
    "SELECT to_jsonb(u) AS row FROM public.users u ORDER BY id",
  );
  await run("backend/tests/academics/deletion/contracts.sql");
  await run("backend/tests/academics/deletion/program_contracts.sql");
  await run("backend/tests/academics/deletion/program_integrity.sql");
  await run("backend/tests/academics/deletion/calendar_contracts.sql");
  await run("backend/tests/academics/deletion/section_contracts.sql");
  await run("backend/tests/academics/deletion/calendar_section_integrity.sql");
  const accountsAfter = await database.query(
    "SELECT to_jsonb(u) AS row FROM public.users u ORDER BY id",
  );
  if (
    JSON.stringify(accountsBefore.rows) !== JSON.stringify(accountsAfter.rows)
  )
    throw new Error("Academic deletion modified account identities");
  console.log(
    "PASS: real PostgreSQL department, program, year, semester and section deletion with history, current-period, authority and audit protection",
  );
  console.log(
    "LIMIT: isolated relevant-schema fixture; not a full migration replay or a concurrent-session test",
  );
} finally {
  await database.close();
}
