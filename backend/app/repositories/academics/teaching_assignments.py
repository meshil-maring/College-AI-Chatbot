"""Atomic, audited teaching assignment RPCs.

Only the authenticated actor and tenant are passed with the request values; the
database re-derives administrator or Head of Department authority every time.
"""


def overview(client, actor_id, tenant):
    return client.rpc("read_teaching_assignments", {"p_actor": actor_id, "p_tenant": tenant}).execute().data


def options(client, actor_id, tenant):
    return client.rpc("read_teaching_options", {"p_actor": actor_id, "p_tenant": tenant}).execute().data


def request(client, actor_id, tenant, offering_id, faculty_user_id, starts_on, planned_end_on):
    return client.rpc("request_teaching_assignment", {
        "p_actor": actor_id, "p_tenant": tenant, "p_offering": offering_id,
        "p_faculty": faculty_user_id, "p_starts_on": starts_on, "p_planned_end_on": planned_end_on,
    }).execute().data


def decide(client, actor_id, tenant, assignment_id, approve, note):
    return client.rpc("decide_teaching_assignment", {
        "p_actor": actor_id, "p_tenant": tenant, "p_assignment": assignment_id,
        "p_approve": approve, "p_note": note,
    }).execute().data


def end(client, actor_id, tenant, assignment_id):
    return client.rpc("end_teaching_assignment", {
        "p_actor": actor_id, "p_tenant": tenant, "p_assignment": assignment_id,
    }).execute().data
