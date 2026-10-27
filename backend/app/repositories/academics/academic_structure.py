"""Tenant-filtered storage for the additive academic structure."""

from app.repositories.shared.query_pages import read_all, read_one
from app.schemas.academics.academic_structure import StructureEntity


PRIMARY_KEYS = {entity: entity.value.removesuffix("s") + "_id" for entity in StructureEntity}
FIELDS = {
    StructureEntity.program_semesters: "program_id,name,code,semester_number,is_active",
    StructureEntity.curriculum_versions: "program_id,academic_year_id,name,version,total_semesters,description,status,is_active,published_at",
    StructureEntity.curriculum_subjects: "curriculum_version_id,program_semester_id,course_id,course_type,is_required,is_active",
    StructureEntity.admission_cohorts: "program_id,curriculum_version_id,academic_year_id,name,code,start_year,end_year,expected_count,description,status,is_active",
    StructureEntity.academic_sections: "admission_cohort_id,program_semester_id,semester_id,name,code,capacity,description,is_active",
    StructureEntity.academic_offerings: "academic_section_id,curriculum_subject_id,capacity,is_active",
}


def _query(client, institution_id, entity):
    columns = f"{PRIMARY_KEYS[entity]},institution_id,{FIELDS[entity]},created_at,updated_at"
    return client.table(entity.value).select(columns).eq("institution_id", institution_id)


def list_records(client, institution_id, entity):
    return read_all(_query(client, institution_id, entity).order(PRIMARY_KEYS[entity]))


def get_record(client, institution_id, entity, record_id):
    return read_one(_query(client, institution_id, entity)
                    .eq(PRIMARY_KEYS[entity], record_id).maybe_single())


def manage_record(client, actor_id, institution_id, entity, record_id, payload):
    return client.rpc("manage_academic_structure_record", {
        "p_actor_user_id": actor_id, "p_institution_id": institution_id,
        "p_entity": entity.value, "p_record_id": record_id, "p_payload": payload,
    }).execute().data


def activities(client, institution_id, entities):
    if not entities:
        return []
    response = client.table("admin_audit_log").select(
        "audit_id,action,table_name,record_id,performed_at,record_data"
    ).eq("institution_id", institution_id).in_("table_name", entities).eq(
        "status", "success"
    ).order("performed_at", desc=True).order("audit_id", desc=True).limit(20).execute()
    return [{
        "id": row["audit_id"], "entity": row["table_name"],
        "record_id": row["record_id"], "action": row["action"],
        "performed_at": row["performed_at"],
        "name": ((row.get("record_data") or {}).get("after") or {}).get("name"),
    } for row in response.data or []]
