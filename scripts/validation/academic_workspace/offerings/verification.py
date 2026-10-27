"""Validate retained offering relationships and real API mutations/rejections."""

from collections import Counter
from uuid import uuid4

from api import BASE_URL, STRUCTURE_URL
from catalogue import PROGRAMS
from writer import identity, primary_key


def verify(database, api, user, baseline, plan, writer):
    checks = []

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    records = {}
    for url in (BASE_URL, STRUCTURE_URL):
        response = api.get(url)
        check(f"Real GET {url} returns 200", response.status_code == 200)
        body = response.json()
        check(f"GET {url} retains institution scope", body["institution_id"] == writer.tenant)
        records.update(body["records"])
    by_id = {entity: {row[primary_key(entity)]: row for row in rows} for entity, rows in records.items()}
    check("Both catalogues return all fourteen academic entities", len(records) == 14)
    check("All API records retain the selected institution", all(
        row["institution_id"] == writer.tenant for rows in records.values() for row in rows))
    check("All 264 planned subject offerings persisted", len(plan) == 264 and all(
        item["offering_id"] in by_id["academic_offerings"] for item in plan))
    for entity, rows in records.items():
        check(f"No duplicate natural keys in {entity}", len({identity(entity, row) for row in rows}) == len(rows))
    for code, _, _, _, intake, subjects in PROGRAMS:
        items = [item for item in plan if item["program_code"] == code]
        stages = len(subjects)
        program_id = items[0]["program_id"]
        check(f"{code}: complete offering matrix", len(items) == stages * 2 * 2 * 3)
        check(f"{code}: two batches", len({item["cohort_id"] for item in items}) == 2)
        check(f"{code}: all study semesters", {item["stage_number"] for item in items} == set(range(1, stages + 1)))
        check(f"{code}: every section has exactly three subjects", set(Counter(item["section_id"] for item in items).values()) == {3})
        check(f"{code}: sections split expected intake", all(item["capacity"] == intake // 2 for item in items))
        course_ids = {item["course_id"] for item in items}
        check(f"{code}: curriculum credits match program total", sum(
            by_id["courses"][identifier]["credits"] for identifier in course_ids
        ) == by_id["programs"][program_id]["total_credits"])
        section_groups = {}
        for item in items:
            section_groups.setdefault((item["cohort_id"], item["stage_number"]), {})[
                item["section_id"]] = item["capacity"]
        check(f"{code}: each batch semester has two sections totaling its expected intake", all(
            len(group) == 2 and sum(group.values()) == intake for group in section_groups.values()))
        check(f"{code}: legacy course offerings retained", sum(
            row["program_id"] == program_id for row in records["course_offerings"]) == stages * 2 * 3)
    for item in plan:
        offering = by_id["academic_offerings"][item["offering_id"]]
        section = by_id["academic_sections"][item["section_id"]]
        cohort = by_id["admission_cohorts"][item["cohort_id"]]
        mapping = by_id["curriculum_subjects"][item["mapping_id"]]
        version = by_id["curriculum_versions"][item["version_id"]]
        stage = by_id["program_semesters"][section["program_semester_id"]]
        term = by_id["semesters"][item["term_id"]]
        year = by_id["academic_years"][term["academic_year_id"]]
        check(f"Offering {item['offering_id']}: complete, active and correctly linked",
              offering["academic_section_id"] == item["section_id"]
              and offering["curriculum_subject_id"] == item["mapping_id"]
              and offering["capacity"] == item["capacity"] and offering["is_active"]
              and section["admission_cohort_id"] == item["cohort_id"]
              and section["semester_id"] == item["term_id"] and section["is_active"]
              and mapping["curriculum_version_id"] == cohort["curriculum_version_id"] == item["version_id"]
              and mapping["program_semester_id"] == section["program_semester_id"]
              and mapping["course_id"] == item["course_id"]
              and stage["program_id"] == cohort["program_id"] == version["program_id"] == item["program_id"]
              and stage["semester_number"] == item["stage_number"]
              and int(year["start_date"][:4]) == item["admission_year"] + (item["stage_number"] - 1) // 2
              and term["semester_number"] == (item["stage_number"] - 1) % 2 + 1
              and version["status"] == "published" and version["published_at"] is not None
              and year["start_date"] <= term["start_date"] < term["end_date"] <= year["end_date"])
    preserved = 0
    for entity, rows in baseline.items():
        for row in rows:
            identifier = row[primary_key(entity)]
            if identifier not in writer.touched:
                check(f"Pre-existing {entity} {identifier} preserved", by_id[entity].get(identifier) == row)
                preserved += 1
    first = plan[0]
    other_stage = next(item for item in plan if item["program_id"] == first["program_id"]
                       and item["stage_number"] != first["stage_number"])
    other_version = next(item for item in plan if item["program_id"] == first["program_id"]
                         and item["stage_number"] == first["stage_number"]
                         and item["admission_year"] != first["admission_year"])
    other_program = next(item for item in plan if item["program_id"] != first["program_id"])
    payload = {"academic_section_id": first["section_id"], "curriculum_subject_id": first["mapping_id"]}
    rejection_cases = [
        ("Duplicate offering", "post", f"{STRUCTURE_URL}/academic_offerings", payload, 409),
        ("Wrong progression semester", "post", f"{STRUCTURE_URL}/academic_offerings",
         {**payload, "curriculum_subject_id": other_stage["mapping_id"]}, 422),
        ("Wrong curriculum version", "post", f"{STRUCTURE_URL}/academic_offerings",
         {**payload, "curriculum_subject_id": other_version["mapping_id"]}, 422),
        ("Wrong program", "post", f"{STRUCTURE_URL}/academic_offerings",
         {**payload, "curriculum_subject_id": other_program["mapping_id"]}, 422),
        ("Missing parent", "post", f"{STRUCTURE_URL}/academic_offerings",
         {**payload, "academic_section_id": str(uuid4())}, 404),
        ("Forged tenant", "post", f"{STRUCTURE_URL}/academic_offerings",
         {**payload, "institution_id": str(uuid4())}, 422),
        ("Missing required fields", "post", f"{STRUCTURE_URL}/academic_offerings", {}, 422),
        ("Unknown entity", "post", f"{STRUCTURE_URL}/unknown", {}, 422),
        ("Negative capacity", "patch", f"{STRUCTURE_URL}/academic_offerings/{first['offering_id']}", {"capacity": -1}, 422),
        ("Immutable offering ancestry", "patch", f"{STRUCTURE_URL}/academic_offerings/{first['offering_id']}",
         {"curriculum_subject_id": other_stage["mapping_id"]}, 422),
        ("Published curriculum edit", "patch", f"{STRUCTURE_URL}/curriculum_versions/{first['version_id']}", {"name": "Invalid edit"}, 422),
        ("Published mapping edit", "patch", f"{STRUCTURE_URL}/curriculum_subjects/{first['mapping_id']}", {"is_required": False}, 422),
        ("Active offering blocks section deactivation", "patch", f"{STRUCTURE_URL}/academic_sections/{first['section_id']}", {"is_active": False}, 422),
        ("Active section blocks cohort completion", "patch", f"{STRUCTURE_URL}/admission_cohorts/{first['cohort_id']}", {"status": "completed"}, 422),
    ]
    audit_before = audit_count(database, writer.tenant)
    for label, method, url, body, status in rejection_cases:
        response = getattr(api, method)(url, json=body)
        check(f"API rejects {label}", response.status_code == status)
    check("Rejected API mutations leave audit history unchanged", audit_count(database, writer.tenant) == audit_before)
    total = database.table("academic_offerings").select("academic_offering_id", count="exact").eq(
        "institution_id", writer.tenant).limit(1).execute().count
    check("Rejected API mutations leave offering count unchanged", total == len(records["academic_offerings"]))
    verify_updates(database, api, first, check)
    print(f"PASS: {len(checks)} retained-data/API assertions; {preserved} unrelated pre-existing records preserved", flush=True)
    print(f"PASS: {len(plan)} academic offerings remain available for manual testing", flush=True)


def audit_count(database, tenant):
    return database.table("admin_audit_log").select("audit_id", count="exact").eq(
        "institution_id", tenant).limit(1).execute().count


def verify_updates(database, api, first, check):
    url = f"{STRUCTURE_URL}/academic_offerings/{first['offering_id']}"
    try:
        for value in (first["capacity"] - 1, 0, None):
            response = api.patch(url, json={"capacity": value})
            check(f"API accepts offering capacity {value}", response.status_code == 200 and response.json()["capacity"] == value)
            row = database.table("academic_offerings").select("capacity").eq(
                "academic_offering_id", first["offering_id"]).single().execute().data
            check(f"Capacity {value} persisted in database", row["capacity"] == value)
        for value in (False, True):
            response = api.patch(url, json={"is_active": value})
            check(f"API sets offering active={value}", response.status_code == 200 and response.json()["is_active"] == value)
    finally:
        response = api.patch(url, json={"capacity": first["capacity"], "is_active": True})
        if response.status_code != 200:
            raise RuntimeError("Could not restore the test offering's intended capacity and active state")
    check("Test offering restored for manual testing", response.json()["capacity"] == first["capacity"])
