"""Future 45+4 replay orchestration; every SQL call stays in its own psql session."""
import re

from .inputs import LEGACY_FIXTURE, safe_sql
from .policy import HarnessError, require
from .concurrency import run_concurrency


def replay(session, migrations):
    """No BEGIN/COMMIT rewriting, concatenation, retry, -1 or sequence transaction."""
    for migration in migrations:
        session.sql(safe_sql(migration.text))


def snapshot_sql(plan):
    text = plan.sql("snapshot")
    for marker, name in (("__CATALOG_CAPTURE_SQL__", "catalog"),
                         ("__RETAINED_CAPTURE_SQL__", "retained"),
                         ("__RETAINED_FIXTURES_SQL__", "fixtures")):
        require(text.count(marker) == 1, "Missing catalog capture module")
        text = text.replace(marker, plan.sql("snapshots/" + name))
    for marker, values in (("__RETIRED_TABLE_VALUES__", plan.retired_tables),
                           ("__RETIRED_FUNCTION_VALUES__", plan.retired_functions)):
        require(text.count(marker) == 1 and all(re.fullmatch(r"[a-z][a-z0-9_]*", item) for item in values),
                "Invalid snapshot inventory")
        text = text.replace(marker, ",".join(f"('{item}')" for item in values))
    return text


def late_failure(text, *, control=""):
    """A disposable negative variant; the original file and transaction stay intact."""
    newline = "\r\n" if text.endswith("COMMIT;\r\n") else "\n"
    ending = "COMMIT;" + newline
    # A real optional CR supports both LF and CRLF; literal backslash-r is invalid.
    require(text.endswith(ending) and len(re.findall(r"(?m)^COMMIT;\r?$", text)) == 1,
            "Unexpected decommission transaction boundary")
    failure = "DO $$ BEGIN RAISE EXCEPTION USING ERRCODE='P4001'; END $$;" + newline
    return text.removesuffix(ending) + control + failure + ending


def execute_plan(session, plan):
    """Not called by the preparation CLI. Live transport remains disabled."""
    try:
        session.create()
        session.start()
        session.ready()
        session.sql(plan.sql("runtime_probe"))
        session.sql(plan.sql("bootstrap"))
        replay(session, plan.migrations[:45])
        session.sql(plan.inputs[LEGACY_FIXTURE].text)
        session.sql(snapshot_sql(plan))
        session.sql(plan.sql("probes/snapshot_differences"))
        decommission = plan.migrations[45]
        session.sql(plan.sql("prerequisite_violation"))
        session.sql(decommission.text, expected_sqlstate="P0001", expected_message=
                    "Unexpected preserved-table foreign key into academic domain; removal refused")
        session.sql(plan.sql("rollback_verify"))
        session.sql(plan.sql("prerequisite_restore"))
        # Exercise preserved-object changes after the original destructive DDL,
        # against the original baseline, then roll back the entire variant.
        controls = plan.sql("probes/decommission_retention") + plan.sql("probes/catalog_properties")
        session.sql(late_failure(decommission.text, control=controls), expected_sqlstate="P4001")
        session.sql(plan.sql("rollback_verify"))
        # Fail after destructive DDL and internal preservation checks, just before
        # COMMIT. The disconnected failed session must roll back all its changes.
        session.sql(late_failure(decommission.text), expected_sqlstate="P4001")
        session.sql(plan.sql("rollback_verify"))
        replay(session, (decommission,))
        session.sql(plan.sql("retained_verify"))
        # Capture the retained state again after the sanctioned decommission.
        session.sql("UPDATE academic_setup_check.snapshots "
                    "SET value=academic_setup_check.capture(name='post_decommission_catalog') "
                    "WHERE name IN ('post_decommission','post_decommission_catalog');")
        replay(session, plan.migrations[46:])
        session.sql(plan.sql("academic_probes"))
        session.sql(plan.sql("security_probes"))
        session.sql(plan.sql("probes/helpers"))
        session.sql(plan.sql("probes/object_inventory"))
        session.sql(plan.sql("probes/catalog_retention"))
        session.sql(plan.sql("probes/privilege_roles"))
        for name in ("tenancy_authority", "lifecycle", "audit_atomicity"):
            session.sql(plan.sql("probes/" + name))
        run_concurrency(session, plan)
        session.sql("SELECT academic_setup_check.verify_post_academic();")
    except HarnessError:
        try:
            session.cleanup()
        except HarnessError:
            raise HarnessError("Verification failed; cleanup unverified; manual review required") from None
        raise
    else:
        session.cleanup()
