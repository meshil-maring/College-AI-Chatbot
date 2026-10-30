"""Tenant-filtered registration reads and atomic, audited SQL commands."""

from app.repositories.shared.query_pages import read_all


def choices(client, actor_id, tenant):
    return client.rpc("read_curriculum_choices", {
        "p_actor": actor_id, "p_tenant": tenant,
    }).execute().data


def students(client, tenant):
    return read_all(client.table("students").select(
        "student_id,student_number,email,institution_id"
    ).eq("institution_id", tenant).eq("approval_status", "approved")
        .eq("status", "active").eq("is_active", True).order("student_id"))


def assignments(client, tenant):
    return read_all(client.table("student_semester_registrations").select(
        "semester_registration_id,institution_id,student_id,academic_section_id,"
        "semester_id,status,selected_option_ids,assigned_at,registered_at"
    ).eq("institution_id", tenant).order("semester_registration_id"))


def save_choices(client, actor_id, tenant, body, group_id=None, delete=False):
    return client.rpc("manage_curriculum_choice_group", {
        "p_actor": actor_id, "p_tenant": tenant, "p_group": group_id,
        "p_payload": body, "p_delete": delete,
    }).execute().data


def assign(client, actor_id, tenant, body):
    return client.rpc("assign_student_semester", {
        "p_actor": actor_id, "p_tenant": tenant,
        "p_student": body["student_id"], "p_section": body["academic_section_id"],
    }).execute().data


def own_semesters(client, actor_id, tenant):
    return client.rpc("read_student_semesters", {
        "p_actor": actor_id, "p_tenant": tenant,
    }).execute().data


def complete(client, actor_id, tenant, registration_id, options):
    return client.rpc("complete_student_semester", {
        "p_actor": actor_id, "p_tenant": tenant,
        "p_registration": registration_id, "p_options": options,
    }).execute().data
