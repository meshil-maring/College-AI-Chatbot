"""Service-only RPC transport for complete academic package operations."""


def catalogue(db, actor: str, institution: str):
    return db.rpc("academic_package_catalogue", {
        "p_actor_user_id": actor, "p_institution_id": institution,
    }).execute().data


def command(db, actor: str, institution: str, operation: str, payload: dict):
    return db.rpc("academic_package_command", {
        "p_actor_user_id": actor, "p_institution_id": institution,
        "p_operation": operation, "p_payload": payload,
    }).execute().data


def assign_legacy_subject(db, actor: str, institution: str, section: str,
                          registration: str, permission: str):
    return db.rpc("assign_student_subject", {
        "p_actor_user_id": actor, "p_institution_id": institution,
        "p_section_id": section, "p_registration_id": registration,
        "p_permission": permission,
    }).execute().data


def delete_legacy_roster(db, actor: str, institution: str, roster: str):
    return db.rpc("delete_academic_roster", {
        "p_actor_user_id": actor, "p_institution_id": institution,
        "p_roster_id": roster,
    }).execute().data


def roster_context(db, institution: str, roster_ids: list[str]):
    return db.rpc("academic_package_roster_context", {
        "p_tenant": institution, "p_roster_ids": roster_ids,
    }).execute().data


def offering_eligibility(db, actor: str, institution: str):
    return db.rpc("academic_package_offering_eligibility", {
        "p_actor_user_id": actor, "p_institution_id": institution,
    }).execute().data
