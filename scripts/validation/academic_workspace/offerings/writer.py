"""Idempotent, schema-validated writes through the existing academic RPCs."""

from collections import Counter
from threading import Lock
from uuid import NAMESPACE_URL, uuid5

from app.schemas.academics.academic_setup import CREATE_MODELS as BASE_MODELS
from app.schemas.academics.academic_structure import CREATE_MODELS as STRUCTURE_MODELS


MODELS = {str(key): model for key, model in {**BASE_MODELS, **STRUCTURE_MODELS}.items()}
STRUCTURE = {str(key) for key in STRUCTURE_MODELS}
KEYS = {
    "departments": ("code",), "programs": ("department_id", "code"),
    "academic_years": ("start_date", "end_date"),
    "semesters": ("academic_year_id", "semester_number"),
    "courses": ("department_id", "code"), "program_courses": ("program_id", "course_id"),
    "course_offerings": ("course_id", "program_id", "academic_year_id", "semester_id"),
    "sections": ("course_offering_id", "code"),
    "program_semesters": ("program_id", "semester_number"),
    "curriculum_versions": ("program_id", "version"),
    "curriculum_subjects": ("curriculum_version_id", "program_semester_id", "course_id"),
    "admission_cohorts": ("code",), "academic_sections": ("code",),
    "academic_offerings": ("academic_section_id", "curriculum_subject_id"),
}


def primary_key(entity):
    return entity.removesuffix("s") + "_id"


def identity(entity, row):
    return tuple(str(row.get(field)).strip().lower() for field in KEYS[entity])


class Writer:
    def __init__(self, client, actor, tenant, records, *, apply=False, http_create=None):
        self.client, self.actor, self.tenant = client, actor, tenant
        self.apply, self.http_create = apply, http_create
        self.lock, self.http_claimed = Lock(), False
        self.created, self.reused = Counter(), Counter()
        self.touched, self.operations = {}, []
        self.records = {
            entity: {identity(entity, row): dict(row) for row in records.get(entity, [])}
            for entity in MODELS
        }

    def save(self, entity, payload):
        model = MODELS[entity].model_validate(payload)
        body = model.model_dump(mode="json", exclude_unset=True)
        key = identity(entity, body)
        with self.lock:
            existing = self.records[entity].get(key)
            if existing:
                if existing.get("is_active") is not True:
                    raise RuntimeError(f"Existing {entity} is inactive; choose a fresh dataset prefix")
                if entity not in {"academic_years", "semesters"}:
                    differences = [field for field, value in body.items() if existing.get(field) != value]
                    if differences:
                        raise RuntimeError(f"Existing {entity} differs in {differences}; refusing to overwrite")
                self.reused[entity] += 1
                identifier = str(existing[primary_key(entity)])
                self.touched[identifier] = entity
                return identifier
            use_http = self.apply and entity == "academic_offerings" and self.http_create and not self.http_claimed
            if use_http:
                self.http_claimed = True
        if self.apply:
            row = self.http_create(body) if use_http else self._rpc(entity, body)
        else:
            identifier = str(uuid5(NAMESPACE_URL, f"{self.tenant}/{entity}/{key}"))
            row = {**model.model_dump(mode="json"), primary_key(entity): identifier}
            if entity == "curriculum_versions":
                row["status"] = "draft"
            if entity == "admission_cohorts":
                row["is_active"] = row["status"] == "active"
        identifier = str(row[primary_key(entity)])
        with self.lock:
            self.records[entity][key] = {**row, "institution_id": self.tenant}
            self.created[entity] += 1
            self.touched[identifier] = entity
            self.operations.append({"entity": entity, "record_id": identifier, "payload": body})
        return identifier

    def _rpc(self, entity, body, record_id=None):
        function = "manage_academic_structure_record" if entity in STRUCTURE else "manage_academic_master_record"
        return self.client.rpc(function, {
            "p_actor_user_id": self.actor, "p_institution_id": self.tenant,
            "p_entity": entity, "p_record_id": record_id, "p_payload": body,
        }).execute().data

    def publish(self, identifier):
        row = next(row for row in self.records["curriculum_versions"].values()
                   if row["curriculum_version_id"] == identifier)
        if row["status"] == "published":
            return
        if row["status"] != "draft":
            raise RuntimeError("Existing curriculum is archived; choose a fresh dataset prefix")
        if self.apply:
            result = self._rpc("curriculum_versions", {"status": "published"}, identifier)
            row.update(result)
        else:
            row["status"] = "published"

    def summary(self):
        return {"created": dict(self.created), "reused": dict(self.reused),
                "touched_records": len(self.touched), "http_creation_used": bool(self.http_claimed)}
