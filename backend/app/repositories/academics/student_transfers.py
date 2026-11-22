"""Atomic, audited student transfer RPCs.

Every function passes only the authenticated actor and tenant; the database
re-derives the student, reviewer scope and placement before reading or writing.
"""


def own_transfers(client, actor_id, tenant):
    return client.rpc("read_student_transfers", {
        "p_actor": actor_id, "p_tenant": tenant,
    }).execute().data


def submit(client, actor_id, tenant, to_section_id, reason):
    return client.rpc("submit_student_transfer", {
        "p_actor": actor_id, "p_tenant": tenant,
        "p_to_section": to_section_id, "p_reason": reason,
    }).execute().data


def cancel(client, actor_id, tenant, request_id):
    return client.rpc("cancel_student_transfer", {
        "p_actor": actor_id, "p_tenant": tenant, "p_request": request_id,
    }).execute().data


def reviews(client, actor_id, tenant, open_only):
    return client.rpc("read_transfer_reviews", {
        "p_actor": actor_id, "p_tenant": tenant, "p_open_only": open_only,
    }).execute().data


def decide(client, actor_id, tenant, request_id, action, comment):
    return client.rpc("decide_student_transfer", {
        "p_actor": actor_id, "p_tenant": tenant, "p_request": request_id,
        "p_action": action, "p_comment": comment,
    }).execute().data


def direct_students(client, actor_id, tenant):
    return client.rpc("read_direct_transfer_students", {
        "p_actor": actor_id, "p_tenant": tenant,
    }).execute().data


def direct_options(client, actor_id, tenant, student_id):
    return client.rpc("read_direct_transfer_options", {
        "p_actor": actor_id, "p_tenant": tenant, "p_student": student_id,
    }).execute().data


def direct_transfer(client, actor_id, tenant, student_id, to_section_id, reason, allow_other_semester):
    return client.rpc("direct_transfer_student", {
        "p_actor": actor_id, "p_tenant": tenant, "p_student": student_id,
        "p_to_section": to_section_id, "p_reason": reason,
        "p_allow_other_semester": allow_other_semester,
    }).execute().data


def department_heads(client, actor_id, tenant):
    return client.rpc("read_department_heads", {
        "p_actor": actor_id, "p_tenant": tenant,
    }).execute().data


def assign_department_head(client, actor_id, tenant, department_id, faculty_user_id):
    return client.rpc("assign_department_head", {
        "p_actor": actor_id, "p_tenant": tenant,
        "p_department": department_id, "p_faculty": faculty_user_id,
    }).execute().data


def add_department_head(
    client, actor_id, tenant, department_id, faculty_user_id, starts_on=None, planned_end_on=None,
):
    return client.rpc("add_department_head", {
        "p_actor": actor_id, "p_tenant": tenant,
        "p_department": department_id, "p_faculty": faculty_user_id,
        "p_starts_on": starts_on, "p_planned_end_on": planned_end_on,
    }).execute().data


def set_department_head_term(client, actor_id, tenant, department_id, faculty_user_id, starts_on, planned_end_on):
    return client.rpc("set_department_head_term", {
        "p_actor": actor_id, "p_tenant": tenant,
        "p_department": department_id, "p_faculty": faculty_user_id,
        "p_starts_on": starts_on, "p_planned_end_on": planned_end_on,
    }).execute().data


def set_department_head_policy(client, actor_id, tenant, allow):
    return client.rpc("set_department_head_policy", {
        "p_actor": actor_id, "p_tenant": tenant, "p_allow": allow,
    }).execute().data


def end_department_head(client, actor_id, tenant, department_id, faculty_user_id):
    return client.rpc("end_department_head", {
        "p_actor": actor_id, "p_tenant": tenant,
        "p_department": department_id, "p_faculty": faculty_user_id,
    }).execute().data
