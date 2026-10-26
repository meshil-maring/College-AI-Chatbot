"""Future synchronized SQL sessions; never invoked by the review-only CLI."""
from concurrent.futures import ThreadPoolExecutor
import secrets


def mutation(entity, payload, *, world="a", record="NULL"):
    # All fragments are harness constants, never user input or connection strings.
    return ("SELECT academic_setup_check.mutate(value,'" + entity + "','" + payload
            + "'," + record + ") FROM academic_setup_check.race_worlds WHERE name='" + world + "';")


def pair_scripts(lane, token):
    holder = f"academic_{token}_{lane}_holder"
    waiter = f"academic_{token}_{lane}_waiter"
    prefix = "BEGIN; SET LOCAL request.jwt.claim.role='service_role'; SET LOCAL statement_timeout='20s'; "
    left = prefix + f"SET LOCAL application_name='{holder}'; "
    right = prefix + f"SET LOCAL application_name='{waiter}'; "
    right += f"SELECT academic_setup_check.race_wait('holder','{holder}'); "
    if lane == "parent":
        left += mutation("departments", '{"is_active":false}', record="(value->>'race_parent')::uuid")
        child = ("SELECT academic_setup_check.mutate(value,'subjects',jsonb_build_object("
                 "'department_id',value->'race_parent','name','Race child','code','RACE_CHILD','credits',3)) "
                 "FROM academic_setup_check.race_worlds WHERE name='a'")
        right += "SELECT academic_setup_check.expect_error($race$" + child + "$race$,'23514','Active academic parents required');"
    else:
        code = {"duplicate": "RACE_DUP", "rollback": "RACE_ROLLBACK", "independent": "RACE_TENANT"}[lane]
        payload = '{"name":"Race","code":"' + code + '"}'
        left += mutation("departments", payload)
        write = mutation("departments", payload, world="b" if lane == "independent" else "a")
        right += ("SELECT academic_setup_check.expect_error($race$" + write + "$race$,'23505');"
                  if lane == "duplicate" else write)
    condition = "independent" if lane == "independent" else "blocked"
    left += f"SELECT academic_setup_check.race_wait('{condition}','{waiter}'); "
    left += "ROLLBACK;" if lane == "rollback" else "COMMIT;"
    right += "COMMIT;"
    return left, right


def run_concurrency(session, plan):
    session.sql(plan.sql("concurrency/setup"))
    session.sql(plan.sql("concurrency/synchronization"))
    for lane in ("duplicate", "parent", "independent", "rollback"):
        scripts = pair_scripts(lane, secrets.token_hex(6))
        # Both sessions are joined before cleanup or any later lane. SQL-side
        # deadlines also cover absent peers, wrong locks and unexpectedly fast writes.
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(session.sql, script) for script in scripts]
            for future in futures:
                future.result()
    session.sql(plan.sql("concurrency/verify"))
    session.sql(plan.sql("concurrency/teardown"))
