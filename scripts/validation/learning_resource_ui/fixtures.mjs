import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { createChatFixture } from "./chat_fixture.mjs";

export function createFixture(role) {
  const actor = randomUUID();
  const tenant = randomUUID();
  const state = { revisions: [], resources: [], writes: [], errors: [] };
  const file = () => ({
    document_id: randomUUID(),
    document_version_id: randomUUID(),
    original_filename: "guide.txt",
    file_type: "txt",
    version_number: 1,
    file_size_bytes: 1280,
    indexing_status: "indexed",
  });
  const initial = {
    knowledge_source_id: randomUUID(),
    title: "Student support handbook",
    description:
      "Library access, campus services and study support for institution members.",
    source_type: "handbook",
    visibility: "public",
    audience_roles: [],
    policy_version: 1,
    effective_from: null,
    effective_until: null,
    documents: [file()],
  };
  state.resources.push(initial);
  const reply = (route, data, status = 200) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(data),
    });
  const chat = createChatFixture(initial, tenant, reply);
  function apply(row, fields) {
    const { audience, ...metadata } = fields;
    Object.assign(row, metadata);
    if (audience) {
      row.visibility = {
        public: "public",
        institution: "authenticated",
        roles: "restricted",
      }[audience.mode];
      row.audience_roles = audience.roles;
    }
  }
  async function handle(route) {
    const request = route.request();
    const url = new URL(request.url());
    const endpoint = url.pathname;
    const method = request.method();
    if (await chat(route)) return;
    if (endpoint === "/api/v1/auth/me")
      return reply(route, {
        authenticated: true,
        user_id: actor,
        auth_user_id: actor,
        email: `${role}@fixture.invalid`,
        role,
        institution_id: tenant,
        institution_code: "FIXTURE",
        effective_permissions: ["*"],
      });
    const base = "/api/v1/knowledge";
    if (!endpoint.startsWith(base))
      throw new Error(`Unexpected fixture API: ${endpoint}`);
    const suffix = endpoint.slice(base.length);
    if (
      method === "GET" &&
      (suffix === "/resources" || suffix === "/revisions")
    ) {
      const rows = suffix === "/resources" ? state.resources : state.revisions;
      const offset = Number(url.searchParams.get("offset") || 0);
      return reply(route, {
        items: rows.slice(offset, offset + 20),
        total: rows.length,
      });
    }
    if (method === "GET") {
      const id = suffix.split("/").at(-1);
      const row = suffix.startsWith("/resources/")
        ? state.resources.find((item) => item.knowledge_source_id === id)
        : state.revisions.find((item) => item.revision_id === id);
      assert(row, "Requested fixture resource exists");
      return reply(route, row);
    }
    const revisionId = suffix.split("/")[2];
    const row = state.revisions.find((item) => item.revision_id === revisionId);
    state.writes.push({ method, suffix });
    if (method === "POST" && suffix === "/resources") {
      const fields = request.postDataJSON();
      assert(
        !("institution_id" in fields),
        "Client does not supply tenant identity",
      );
      const created = {
        ...initial,
        knowledge_source_id: randomUUID(),
        documents: [],
        policy_version: 0,
        revision_id: randomUUID(),
        institution_id: tenant,
        revision_number: 1,
        revision_version: 1,
        lifecycle_status: "draft",
        created_by_user_id: actor,
        reviewed_by_user_id: null,
        approved_by_user_id: null,
        review_notes: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      apply(created, fields);
      state.revisions.push(created);
      return reply(route, created, 201);
    }
    assert(row, "A staged revision is selected");
    if (suffix.endsWith("/documents")) {
      const body = request.postData();
      const expected = body.match(
        /name="expected_version"\r?\n\r?\n(\d+)/,
      )?.[1];
      assert.equal(
        Number(expected),
        row.revision_version,
        "Upload uses the latest revision token",
      );
      row.documents = [file()];
      row.revision_version += 2;
      return reply(route, row, 201);
    }
    const command = request.postDataJSON();
    assert.equal(
      command.expected_version,
      row.revision_version,
      "Decision uses the latest revision token",
    );
    const action = suffix.split("/").at(-1);
    if (action !== "submit")
      assert.equal(role, "admin", "Only admin reviews or publishes");
    if (action === "publish" || action === "unpublish")
      assert.equal(command.expected_policy, row.policy_version);
    row.lifecycle_status = {
      submit: "under_review",
      approve: "approved",
      publish: "published",
      unpublish: "archived",
    }[action];
    assert(row.lifecycle_status, "Only supported decisions are issued");
    row.revision_version += 1;
    if (action === "publish") {
      row.policy_version += 1;
      state.resources.push(
        Object.fromEntries(Object.keys(initial).map((key) => [key, row[key]])),
      );
    }
    if (action === "unpublish") {
      row.policy_version += 1;
      state.resources = state.resources.filter(
        (item) => item.knowledge_source_id !== row.knowledge_source_id,
      );
    }
    return reply(route, row);
  }
  return {
    state,
    async handle(route) {
      try {
        await handle(route);
      } catch (error) {
        state.errors.push(error.message);
        await reply(
          route,
          {
            error: {
              code: "FIXTURE_ERROR",
              message: "Fixture contract failed",
            },
          },
          500,
        );
      }
    },
  };
}
