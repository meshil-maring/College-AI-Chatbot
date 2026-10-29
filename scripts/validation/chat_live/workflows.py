"""Actual HTTP workflows with run-owned resources and server-issued tokens."""

from uuid import uuid4
import time

from runtime import accepted


def login(api, credentials):
    headers = {}
    for role, account in credentials.items():
        session = accepted(api.post("/api/v1/auth/login", json={
            "email": account["email"], "password": account["password"],
        }))
        headers[role] = {"Authorization": "Bearer " + session["access_token"]}
        identity = accepted(api.get("/api/v1/auth/me", headers=headers[role]))
        if role != identity.get("role"):
            raise AssertionError(f"Server identity lacks expected {role} role")
    print("PASS: normal password login, JWT verification and role resolution for all four roles", flush=True)
    return headers


def decision(api, headers, revision, action, expected=200):
    response = api.post(f"/api/v1/knowledge/revisions/{revision['revision_id']}/{action}", headers=headers, json={
        "expected_version": revision["revision_version"], "expected_policy": revision["policy_version"],
    })
    return accepted(response, expected)


def publication(api, headers, evidence, save):
    revision = accepted(api.post("/api/v1/knowledge/resources", headers=headers["staff"], json={
        "title": "Chat acceptance " + evidence["run"], "source_type": "handbook",
        "description": "Fictional, run-owned service acceptance fixture; not college policy.",
        "audience": {"mode": "roles", "roles": ["staff"]},
    }), 201)
    evidence["resource"] = revision
    save()
    text = ("Fictional Chat Acceptance Handbook\n\n"
            "This document is a test fixture, not real college policy.\n\n"
            f"The test reference is {evidence['run']}.\n"
            "For the fictional staff workshop, the meeting room is Cedar Room 42. "
            "Participants should bring a blue notebook. These details are for testing only.\n")
    revision = accepted(api.post(f"/api/v1/knowledge/revisions/{revision['revision_id']}/documents",
        headers=headers["staff"], data={"expected_version": revision["revision_version"]},
        files={"file": ("chat-acceptance.txt", text.encode(), "text/plain")}), 201)
    evidence["resource"] = revision
    save()
    assert revision["documents"] and all(item["indexing_status"] == "indexed" for item in revision["documents"])
    revision = decision(api, headers["staff"], revision, "submit")
    decision(api, headers["staff"], revision, "publish", expected=403)
    decision(api, headers["faculty"], revision, "approve", expected=403)
    for action in ("approve", "publish"):
        revision = decision(api, headers["admin"], revision, action)
    evidence["resource"] = revision
    save()
    print("PASS: R2 upload, extraction, embeddings, staff submission and admin-only publication", flush=True)
    return revision


def audience(api, headers, resource_id, allowed):
    for role, authorization in headers.items():
        rows = accepted(api.get("/api/v1/knowledge/resources?limit=100", headers=authorization))["items"]
        visible = any(row["knowledge_source_id"] == resource_id for row in rows)
        assert visible == (role in allowed), f"Incorrect resource visibility for {role}"
        status = 200 if role in allowed else 404
        accepted(api.get(f"/api/v1/knowledge/resources/{resource_id}/chat-context", headers=authorization), status)
    print("PASS: resource library and Ask AI enforce audience for all four roles", flush=True)


def chat(api, authorization, tenant, source, question, evidence, role, save):
    payload = {"institution_id": tenant, "session_id": str(uuid4()), "turn_id": str(uuid4()),
               "resource_id": source, "user_query": question}
    # Register identifiers before sending, so ambiguous failures remain inspectable.
    evidence.setdefault("turns", []).append({"role": role, **payload})
    save()
    result = api.post("/api/v1/generation/chat", headers=authorization, json=payload)
    for attempt in range(2):
        if result.status_code != 500 or result.json().get("error", {}).get("code") not in {
            "EMBEDDING_FAILED", "GENERATION_FAILED",
        }:
            break
        status = accepted(api.get(f"/api/v1/generation/turns/{payload['turn_id']}", headers=authorization))
        assert status["state"] == "failed" and status["retryable"], "Unsafe retry state"
        evidence["turns"][-1].setdefault("explicit_recovery", []).append(result.json()["error"]["code"])
        save()
        print(f"CHECK: {role} confirmed failed provider work; explicitly retrying the same turn ({attempt + 1}/2)", flush=True)
        time.sleep(5)
        result = api.post("/api/v1/generation/chat", headers=authorization, json=payload)
    response = accepted(result)
    assert response["status"] == "success" and response["sources"], f"Missing cited {role} answer"
    assert "[Retrieved chunk" not in response["answer"]
    conversation = response["conversation_id"]
    replay = accepted(api.post("/api/v1/generation/chat", headers=authorization, json=payload))
    assert replay == response, "Completed request did not replay exactly"
    status = accepted(api.get(f"/api/v1/generation/turns/{payload['turn_id']}", headers=authorization))
    assert status["state"] == "completed"
    history = accepted(api.get(f"/api/v1/conversations/{conversation}/messages", headers=authorization))
    assert len(history) == 2, "Replay duplicated a saved message"
    assistant = next(item for item in history if item["message_type"] == "assistant")
    assert assistant["content_text"] == response["answer"]
    assert assistant["sources"] == response["sources"], "Restored citations differ from live answer"
    evidence["turns"][-1].update(conversation_id=conversation, source_count=len(response["sources"]), verified=True)
    save()
    print(f"PASS: {role} live retrieval/generation, exact replay and restored source cards", flush=True)
    return conversation


def change_audience(api, headers, revision, evidence, save):
    updated = accepted(api.post(f"/api/v1/knowledge/resources/{revision['knowledge_source_id']}/revisions",
        headers=headers["admin"], json={"audience": {"mode": "roles", "roles": ["student"]}}), 201)
    evidence["resource"] = updated
    save()
    for action in ("submit", "approve", "publish"):
        updated = decision(api, headers["admin"], updated, action)
    evidence["resource"] = updated
    save()
    return updated


def unpublish(api, headers, evidence, save):
    if "resource" not in evidence:
        return
    # A request can commit even if its response fails. Resolve the current source
    # revision from the authoritative review reader before cleanup.
    source = evidence["resource"]["knowledge_source_id"]
    revisions = accepted(api.get("/api/v1/knowledge/revisions?view=review&limit=100", headers=headers["admin"]))["items"]
    published = [row for row in revisions if row["knowledge_source_id"] == source and row["lifecycle_status"] == "published"]
    for revision in published:
        decision(api, headers["admin"], revision, "unpublish")
    evidence["resource_unpublished"] = True
    save()
    print("PASS: run-owned test resource is unpublished", flush=True)
