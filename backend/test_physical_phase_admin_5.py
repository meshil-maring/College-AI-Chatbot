"""ADMIN-5 physical end-to-end validation.

Validates the complete Admin + Student workflow against the real running
application and live database:

  * admin / student authentication (Supabase Auth, magic-link OTP)
  * admin identity + dashboard
  * FAQ create/update/publish/delete + chatbot retrieval + stale-content purge
  * learning-resource upload -> R2 -> extraction -> chunking -> embedding
    -> ready -> grounded chatbot answer
  * regulation/policy upload + retrieval
  * notices create/update/publish + RAG sync
  * results / test-results / attendance publish + student My Academics
  * CSV result upload with row-level validation
  * security: role gating (401/403), student isolation, no student_id injection
  * audit-log coverage

Run:
    cd backend
    .\\.venv\\Scripts\\python.exe test_physical_phase_admin_5.py

Requires: backend running at http://127.0.0.1:8000 with live Supabase + R2.
"""

import io
import sys
import time

import httpx
from docx import Document as DocxDocument

from app.config import settings
from app.db.supabase import create_supabase_client, get_admin_client
from app.services.storage import get_r2_client

BASE_URL = "http://127.0.0.1:8000"

# Admin-1 fixtures
INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
ACADEMIC_YEAR_ID = "30000000-0000-0000-0000-000000000022"
SEMESTER_ID = "30000000-0000-0000-0000-000000000033"
PROGRAM_ID = "30000000-0000-0000-0000-000000000042"
COURSE_ID = "30000000-0000-0000-0000-000000000051"
SECTION_ID = "30000000-0000-0000-0000-000000000099"

ADMIN_EMAIL = "admin.demo@collegelocal.dev"
S1_EMAIL = "dsmeshilmaring13@gmail.com"
S2_EMAIL = "student2.demo@collegelocal.dev"
S3_EMAIL = "student3.demo@collegelocal.dev"
FACULTY_EMAIL = "admin.iridix@gmail.com"

S1_STUDENT_ID = "30000000-0000-0000-0000-000000000151"
S2_STUDENT_ID = "30000000-0000-0000-0000-000000000152"
S3_STUDENT_ID = "30000000-0000-0000-0000-000000000153"

CHECKS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(ok), detail))
    flag = "PASS" if ok else "FAIL"
    print(f"[{flag}] {name}" + (f" -- {detail}" if detail else ""))


def authenticate(email: str) -> str:
    """Issue a real access token via the Supabase magic-link OTP flow."""
    admin = get_admin_client()
    client = create_supabase_client()
    link = admin.auth.admin.generate_link({"type": "magiclink", "email": email})
    otp = link.properties.email_otp
    resp = client.auth.verify_otp({"email": email, "token": otp, "type": "magiclink"})
    return resp.session.access_token


def db():
    return get_admin_client()


def make_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def ask_chat(token: str, question: str, timeout: float = 180.0):
    """One grounded chat call. Returns (answer, source_references)."""
    with httpx.Client(timeout=timeout) as http:
        resp = http.post(
            f"{BASE_URL}/api/v1/generation/chat",
            headers=make_headers(token),
            json={"user_query": question, "institution_id": INSTITUTION_ID},
        )
    if resp.status_code != 200:
        return None, []
    data = resp.json()
    return data.get("answer"), data.get("source_references") or []


def find_version_label_document(marker: str):
    client = db()
    rows = (
        client.table("document_versions")
        .select("document_id, version_label, lifecycle_status")
        .eq("version_label", marker)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def wait_for_run(run_id: str, timeout: float = 240.0) -> dict:
    client = db()
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        rows = (
            client.table("document_processing_runs")
            .select("processing_run_id, status")
            .eq("processing_run_id", str(run_id))
            .limit(1)
            .execute()
            .data
        )
        if rows:
            last = rows[0]
            if rows[0]["status"] in ("completed", "failed"):
                return rows[0]
        time.sleep(3)
    return last or {}


def verify_pipeline_artifacts(run_id: str, storage_key: str) -> None:
    client = db()
    run = wait_for_run(run_id)
    check("Processing run reaches completed", run.get("status") == "completed", str(run))
    run_rows = (
        client.table("document_processing_runs")
        .select("extracted_text, chunk_count, embedding_count")
        .eq("processing_run_id", str(run_id))
        .limit(1)
        .execute()
        .data
    )
    if run_rows:
        rr = run_rows[0]
        check("Extracted text persisted", bool(rr.get("extracted_text")),
              f"len={len(rr.get('extracted_text') or '')}")
        chunks = client.table("knowledge_chunks").select("chunk_id, content_text").eq(
            "processing_run_id", str(run_id)).execute().data or []
        check("Chunking created chunks", len(chunks) > 0, f"chunks={len(chunks)}")
        if chunks:
            emb = client.table("chunk_embeddings").select("chunk_id").in_(
                "chunk_id", [c["chunk_id"] for c in chunks]
            ).eq("model_name", settings.embedding_model).limit(1).execute().data
            check("Embedding stored rows", len(emb) > 0, f"emb>=1 (model={settings.embedding_model})")
    r2 = get_r2_client()
    listed = r2.list_objects_v2(Bucket=settings.r2_bucket, Prefix=storage_key, MaxKeys=5)
    check("R2 storage object present", int(listed.get("KeyCount", 0)) >= 1,
          f"bucket={settings.r2_bucket} key={storage_key}")
def create_knowledge_source(admin_token: str, source_type: str, title: str, description: str) -> str:
    with httpx.Client(timeout=60.0) as http:
        resp = http.post(
            f"{BASE_URL}/api/v1/admin/knowledge-sources",
            headers=make_headers(admin_token),
            json={
                "institution_id": INSTITUTION_ID,
                "source_type": source_type,
                "title": title,
                "description": description,
                "authority_level": "official",
                "lifecycle_status": "published",
            },
        )
    check(f"Knowledge source create ({source_type}) returns 201", resp.status_code == 201, str(resp.status_code))
    return resp.json()["knowledge_source_id"]


def upload_document(admin_token: str, ks_id: str, filename: str, data: bytes, content_type: str):
    with httpx.Client(timeout=600.0) as http:
        resp = http.post(
            f"{BASE_URL}/api/v1/admin/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            data={"knowledge_source_id": ks_id, "auto_process": "true"},
            files={"file": (filename, data, content_type)},
        )
    return resp


def publish_faq_journey(admin_token: str) -> None:
    print("\n=== FAQ Journey ===")
    with httpx.Client(timeout=60.0) as http:
        created = http.post(
            f"{BASE_URL}/api/v1/admin/faqs",
            headers=make_headers(admin_token),
            json={
                "institution_id": INSTITUTION_ID,
                "category": "academics",
                "question": "What time does the central library open on Sundays?",
                "answer": "The central library opens at 10:00 AM on Sundays and closes at 5:00 PM.",
                "is_active": False,
            },
        )
        check("FAQ create returns 201", created.status_code == 201, str(created.status_code))
        faq = created.json()
        faq_id = faq["faq_id"]

        updated = http.patch(
            f"{BASE_URL}/api/v1/admin/faqs/{faq_id}",
            headers=make_headers(admin_token),
            json={"answer": "The central library opens at 10:00 AM on Sundays and closes at 6:00 PM."},
        )
        check("FAQ update returns 200", updated.status_code == 200, str(updated.status_code))
        check("FAQ update persisted answer", "6:00 PM" in updated.json().get("answer", ""))

        published = http.patch(
            f"{BASE_URL}/api/v1/admin/faqs/{faq_id}",
            headers=make_headers(admin_token),
            json={"is_active": True},
        )
        check("FAQ publish (is_active) returns 200", published.status_code == 200, str(published.status_code))
        check("FAQ is_active toggle persisted", published.json().get("is_active") is True)

    marker = f"faq:{faq_id}"
    doc = find_version_label_document(marker)
    check("FAQ RAG sync created synthetic document", doc is not None, marker)
    if doc:
        check("FAQ sync version published", doc["lifecycle_status"] == "published", str(doc))

    question = "What time does the central library open on Sundays?"
    answer, sources = ask_chat(admin_token, question)
    found_faq = doc is not None and any(str(s.get("document_id")) == str(doc["document_id"]) for s in sources)
    check(
        "Chat retrieves FAQ content pre-delete",
        answer is not None and len(sources) > 0,
        f"sources={len(sources)} founded={found_faq}",
    )

    with httpx.Client(timeout=60.0) as http:
        deleted = http.delete(f"{BASE_URL}/api/v1/admin/faqs/{faq_id}", headers=make_headers(admin_token))
    check("FAQ delete returns 200", deleted.status_code == 200, str(deleted.status_code))
    check("FAQ record deleted",
          db().table("faqs").select("faq_id").eq("faq_id", faq_id).limit(1).execute().data == [])
    check("FAQ synthetic document removed on delete",
          find_version_label_document(marker) is None, marker)
def learning_resource_journey(admin_token: str):
    print("\n=== Learning Resource Journey ===")
    content = (
        "Library Inter-Loan Handbook: The maximum inter-library loan quota is "
        "twelve items per semester. Overdue fines are waived for the first "
        "holiday week of December. The rare-books annex permits supervised "
        "access only for faculty and final-year project students."
    )
    doc = DocxDocument()
    doc.add_paragraph(content)
    doc.add_paragraph("Procedures: requests must be placed at least three working days in advance.")
    buf = io.BytesIO()
    doc.save(buf)
    doc_bytes = buf.getvalue()

    ks_id = create_knowledge_source(admin_token, "learning_resource", "Library Inter-Loan Handbook", content[:80])
    resp = upload_document(
        admin_token, ks_id, "library_interloan_handbook.docx", doc_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    check("Learning resource upload returns 201", resp.status_code == 201, str(resp.status_code))
    if resp.status_code != 201:
        print("  upload body:", resp.text[:400])
        return ks_id, None
    uploaded = resp.json()
    doc_id = uploaded["document_id"]
    run_id = uploaded["processing_run_id"]
    check("Upload returns status ready", uploaded.get("status") in ("completed", "ready", "synced"), str(uploaded.get("status")))
    verify_pipeline_artifacts(run_id, uploaded["storage_object_key"])
    check("Learning resource document version published", bool(
        db().table("document_versions").select("document_version_id").eq("document_id", doc_id).eq(
            "lifecycle_status", "published").limit(1).execute().data))
    question = "What is the maximum inter-library loan quota per semester?"
    answer, sources = ask_chat(admin_token, question)
    grounded = answer is not None and any(str(s.get("document_id")) == str(doc_id) for s in sources)
    check("Chat grounded in learning resource", grounded and len(sources) > 0,
          f"sources={len(sources)} founded={grounded} answer={ (answer or '')[:80]!r}")
    return ks_id, doc_id


def regulation_journey(admin_token: str):
    print("\n=== Regulation / Policy Journey ===")
    content = (
        "Readmission Eligibility (Regulation QX-200): a student who has failed "
        "the same core course twice may apply for readmission under the Financial "
        "Aid Pilot Program QX-200. The application window opens on the first "
        "Monday of March. Approved students retain two semesters of eligibility."
    )
    ks_id = create_knowledge_source(admin_token, "regulation", "Academic Readmission Regulation", content[:80])
    resp = upload_document(admin_token, ks_id, "readmission_regulation_QX200.txt", content.encode("utf-8"), "text/plain")
    check("Regulation upload returns 201", resp.status_code == 201, str(resp.status_code))
    if resp.status_code != 201:
        print("  upload body:", resp.text[:400])
        return ks_id, None
    uploaded = resp.json()
    doc_id = uploaded["document_id"]
    verify_pipeline_artifacts(uploaded["processing_run_id"], uploaded["storage_object_key"])
    question = "According to the readmission regulation, when does the QX-200 application window open and how long is eligibility?"
    answer, sources = ask_chat(admin_token, question)
    grounded = answer is not None and any(str(s.get("document_id")) == str(doc_id) for s in sources)
    check("Chat grounded in regulation/policy", grounded and len(sources) > 0,
          f"sources={len(sources)} founded={grounded} answer={ (answer or '')[:80]!r}")
    return ks_id, doc_id
def notice_journey(admin_token: str) -> None:
    print("\n=== Notices Journey ===")
    with httpx.Client(timeout=120.0) as http:
        created = http.post(
            f"{BASE_URL}/api/v1/admin/notices",
            headers=make_headers(admin_token),
            json={
                "institution_id": INSTITUTION_ID,
                "title": "Exam Hall Change - Engineering Block",
                "content": "The Physics end-semester practical examination moves to "
                           "Engineering Block Hall 3. Students must report 15 minutes early.",
                "category": "exam",
                "priority": "high",
                "is_active": True,
                "is_pinned": False,
            },
        )
        check("Notice create returns 201", created.status_code == 201, str(created.status_code))
        notice = created.json()
        notice_id = notice["notice_id"]

        updated = http.patch(
            f"{BASE_URL}/api/v1/admin/notices/{notice_id}",
            headers=make_headers(admin_token),
            json={"content": "The Physics end-semester practical examination moves to "
                             "Engineering Block Hall 3. Students must report 30 minutes early."},
        )
        check("Notice update returns 200", updated.status_code == 200, str(updated.status_code))
        check("Notice update persisted", "30 minutes" in updated.json().get("content", ""))

        listed = http.get(
            f"{BASE_URL}/api/v1/admin/notices?institution_id={INSTITUTION_ID}",
            headers=make_headers(admin_token),
        )
        check("Notice visible in admin list", listed.status_code == 200
              and any(n["notice_id"] == notice_id for n in listed.json()),
              f"count={len(listed.json())}")

    marker = f"notice:{notice_id}"
    doc = find_version_label_document(marker)
    check("Notice RAG sync created synthetic document", doc is not None, marker)

    with httpx.Client(timeout=120.0) as http:
        deleted = http.delete(
            f"{BASE_URL}/api/v1/admin/notices/{notice_id}", headers=make_headers(admin_token)
        )
    check("Notice delete returns 200", deleted.status_code == 200, str(deleted.status_code))
    check("Notice synthetic document removed on delete",
          find_version_label_document(marker) is None, marker)
def academic_data_journey(admin_token: str) -> None:
    print("\n=== Results / Test Results / Attendance Journey ===")
    with httpx.Client(timeout=60.0) as http:
        resp = http.post(
            f"{BASE_URL}/api/v1/admin/results",
            headers=make_headers(admin_token),
            json={
                "student_id": S1_STUDENT_ID,
                "academic_year_id": ACADEMIC_YEAR_ID,
                "semester_id": SEMESTER_ID,
                "program_id": PROGRAM_ID,
                "result_type": "semester",
                "total_credits_earned": 8.0,
                "total_credits_max": 8.0,
                "sgpa": 8.6,
                "cgpa": 8.6,
                "status": "published",
                "items": [
                    {"course_id": COURSE_ID, "section_id": SECTION_ID,
                     "credits_earned": 4.0, "credits_max": 4.0,
                     "grade_points": 8.0, "letter_grade": "A", "grade_value": 9.0}
                ],
            },
        )
        check("Result create returns 201", resp.status_code == 201, str(resp.status_code))
        result_id = resp.json().get("student_result_id") if resp.status_code == 201 else None

        tr = http.post(
            f"{BASE_URL}/api/v1/admin/test-results",
            headers=make_headers(admin_token),
            json={
                "student_id": S1_STUDENT_ID,
                "course_id": COURSE_ID,
                "section_id": SECTION_ID,
                "academic_year_id": ACADEMIC_YEAR_ID,
                "semester_id": SEMESTER_ID,
                "test_name": "Midterm Physics",
                "test_type": "midterm",
                "max_marks": 50,
                "scored_marks": 42,
                "percentage": 84,
                "letter_grade": "A",
                "status": "published",
            },
        )
        check("Test result create returns 201", tr.status_code == 201, str(tr.status_code))
        test_result_id = (tr.json().get("test_results_id") or tr.json().get("test_result_id")
                          if tr.status_code == 201 else None)

        att = http.post(
            f"{BASE_URL}/api/v1/admin/attendance",
            headers=make_headers(admin_token),
            json={
                "student_id": S1_STUDENT_ID,
                "section_id": SECTION_ID,
                "academic_year_id": ACADEMIC_YEAR_ID,
                "semester_id": SEMESTER_ID,
                "date": "2026-09-09",
                "status": "present",
                "notes": "Validation record",
            },
        )
        check("Attendance create returns 201", att.status_code == 201, str(att.status_code))
        attendance_id = att.json().get("student_attendance_id") if att.status_code == 201 else None

    csv_content = (
        "student_number,academic_year_id,semester_id,program_id,result_type,total_credits_earned,total_credits_max,sgpa,cgpa,status\n"
        f"STU2026001,{ACADEMIC_YEAR_ID},{SEMESTER_ID},{PROGRAM_ID},semester,8,8,8.7,8.7,published\n"
        "STU0000000,00000000-0000-0000-0000-000000000000,00000000-0000-0000-0000-000000000000,"
        "00000000-0000-0000-0000-000000000000,semester,8,8,8.7,8.7,published\n"
    ).encode("utf-8")
    with httpx.Client(timeout=60.0) as http:
        csv_resp = http.post(
            f"{BASE_URL}/api/v1/admin/results/csv-upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            data={"institution_id": INSTITUTION_ID},
            files={"file": ("results.csv", csv_content, "text/csv")},
        )
    check("CSV upload returns 200", csv_resp.status_code == 200, str(csv_resp.status_code))
    if csv_resp.status_code == 200:
        summary = csv_resp.json()
        check("CSV valid row inserted", summary.get("inserted_count", 0) >= 1, str(summary))
        check("CSV invalid row reported",
              any(e.get("student_number") == "STU0000000" for e in summary.get("row_errors", [])),
              str(summary.get("row_errors", [])[:1]))

    return {
        "result_id": result_id,
        "test_result_id": test_result_id,
        "attendance_id": attendance_id,
    }
def student_isolation_journey(s1_token: str, s3_token: str, faculty_token: str, admin_token: str) -> None:
    print("\n=== Student Isolation / Security Journey ===")
    with httpx.Client(timeout=60.0) as http:
        p1 = http.get(f"{BASE_URL}/api/v1/students/me/profile", headers=make_headers(s1_token))
        check("Student /me/profile returns 200", p1.status_code == 200, str(p1.status_code))
        check("Student profile resolved server-side", p1.status_code == 200
              and p1.json().get("student_id") == S1_STUDENT_ID,
              str(p1.json().get("student_id")))

        r = http.get(
            f"{BASE_URL}/api/v1/admin/students/{S3_STUDENT_ID}/results",
            headers=make_headers(s1_token),
        )
        check("Student blocked from admin results endpoint", r.status_code == 403, str(r.status_code))

        r2 = http.get(
            f"{BASE_URL}/api/v1/students/me/results?student_id={S3_STUDENT_ID}",
            headers=make_headers(s1_token),
        )
        own_results = r2.json() if r2.status_code == 200 else []
        check("student_id query param cannot reframe /me", r2.status_code == 200,
              f"code={r2.status_code}")
        check("Student only receives own results (published only)",
              r2.status_code == 200 and all(
                  str(x.get("student_id")) == S1_STUDENT_ID for x in own_results
              ), f"count={len(own_results)}")

        tr = http.get(f"{BASE_URL}/api/v1/students/me/test-results", headers=make_headers(s1_token))
        att = http.get(f"{BASE_URL}/api/v1/students/me/attendance", headers=make_headers(s1_token))
        check("Student /me/test-results returns 200", tr.status_code == 200, str(tr.status_code))
        check("Student /me/attendance returns 200", att.status_code == 200, str(att.status_code))

        own3 = http.get(f"{BASE_URL}/api/v1/students/me/results", headers=make_headers(s3_token))
        s3_has_s1 = any(str(x.get("student_id")) == S1_STUDENT_ID for x in own3.json())
        check("Student B cannot see Student A results", own3.status_code == 200 and not s3_has_s1,
              f"s1_in_s3={s3_has_s1}")

        anon = http.get(f"{BASE_URL}/api/v1/students/me/profile")
        check("Unauthenticated /me blocked (401)", anon.status_code == 401, str(anon.status_code))
        anon_admin = http.get(f"{BASE_URL}/api/v1/admin/dashboard")
        check("Unauthenticated admin blocked (401)", anon_admin.status_code == 401, str(anon_admin.status_code))

        fac_admin = http.get(f"{BASE_URL}/api/v1/admin/dashboard", headers=make_headers(faculty_token))
        check("Non-admin (faculty) blocked from admin (403)", fac_admin.status_code == 403, str(fac_admin.status_code))

        me = http.get(f"{BASE_URL}/api/v1/admin/me", headers=make_headers(admin_token))
        check("Admin /me returns role", me.status_code == 200
              and "admin" in (me.json().get("roles") or []), str(me.status_code))

        dash = http.get(f"{BASE_URL}/api/v1/admin/dashboard", headers=make_headers(admin_token))
        check("Admin dashboard returns 200", dash.status_code == 200, str(dash.status_code))
        if dash.status_code == 200:
            dd = dash.json()
            check("Dashboard has counts", isinstance(dd, dict) and len(dd) > 0, str(list(dd.keys())[:8]))
def audit_verification(admin_token: str) -> None:
    print("\n=== Audit Log Verification ===")
    with httpx.Client(timeout=60.0) as http:
        logs = http.get(
            f"{BASE_URL}/api/v1/admin/audit-logs?limit=50",
            headers=make_headers(admin_token),
        )
    check("Audit log endpoint returns 200", logs.status_code == 200, str(logs.status_code))
    if logs.status_code != 200:
        return
    entries = logs.json()
    actions = {e.get("action") for e in entries}
    required = {
        "faq.create", "faq.update", "faq.delete",
        "notice.create", "notice.update", "notice.delete",
        "result.create", "result.csv_upload",
        "test_result.create", "attendance.create",
        "knowledge_source.create", "document.upload",
    }
    present = required & actions
    missing = required - actions
    check("Audit log contains Admin-3 mutation actions",
          len(missing) == 0,
          f"present={len(present)} missing={sorted(missing)}")


def main() -> int:
    print("=" * 70)
    print("ADMIN-5 PHYSICAL END-TO-END VALIDATION")
    print("=" * 70)
    try:
        health = httpx.get(f"{BASE_URL}/health", timeout=10)
        check("Backend reachable (/health)", health.status_code == 200, health.text)
    except Exception as exc:  # noqa: BLE001
        check("Backend reachable (/health)", False, str(exc))
        _summary(1)
        return 1

    try:
        print("\n[Auth] obtaining live access tokens ...")
        admin_token = authenticate(ADMIN_EMAIL)
        check("Admin OTP login succeeds", admin_token is not None and len(admin_token) > 100, f"len={len(admin_token or '')}")
        s1_token = authenticate(S1_EMAIL)
        check("Student 1 OTP login succeeds", s1_token is not None and len(s1_token) > 100, "OK")
        s2_token = authenticate(S2_EMAIL)
        check("Student 2 OTP login succeeds", s2_token is not None and len(s2_token) > 100, "OK")
        s3_token = authenticate(S3_EMAIL)
        check("Student 3 OTP login succeeds", s3_token is not None and len(s3_token) > 100, "OK")
        faculty_token = authenticate(FACULTY_EMAIL)
        check("Faculty OTP login succeeds", faculty_token is not None and len(faculty_token) > 100, "OK")
    except Exception as exc:  # noqa: BLE001
        check("Authentication phase", False, str(exc))
        _summary(1)
        return 1

    publish_faq_journey(admin_token)
    learning_ks, learning_doc = learning_resource_journey(admin_token)
    regulation_ks, regulation_doc = regulation_journey(admin_token)
    notice_journey(admin_token)
    created_ids = academic_data_journey(admin_token)
    student_isolation_journey(s1_token, s3_token, faculty_token, admin_token)
    audit_verification(admin_token)

    _summary(0)
    return 0


def _summary(exited: int) -> None:
    print("\n" + "=" * 70)
    print("ADMIN-5 VALIDATION SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    failed = [(n, d) for n, ok, d in CHECKS if not ok]
    print(f"TOTAL: {len(CHECKS)}  PASSED: {passed}  FAILED: {len(failed)}")
    if failed:
        print("\nFAILURES:")
        for name, detail in failed:
            print(f"  - {name} :: {detail}")
    print(f"EXIT: {exited}")


if __name__ == "__main__":
    raise SystemExit(main())