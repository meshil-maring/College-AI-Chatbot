import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";

export function createChatFixture(resource, tenant, reply) {
  const context = {
    knowledge_source_id: resource.knowledge_source_id,
    title: resource.title,
    available: true,
  };
  const conversations = [];
  const messages = new Map();
  const sources = [
    {
      chunk_id: randomUUID(),
      quote: "Fictional campus library support evidence.",
      source_title: resource.title,
      section: null,
      relevance_score: 0.9,
    },
  ];
  return async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/chat-context")) {
      assert(path.includes(resource.knowledge_source_id));
      await reply(route, context);
      return true;
    }
    if (path === "/api/v1/conversations") {
      await reply(route, conversations);
      return true;
    }
    if (
      path.startsWith("/api/v1/conversations/") &&
      path.endsWith("/messages")
    ) {
      const id = path.split("/").at(-2);
      assert(messages.has(id));
      await reply(route, messages.get(id));
      return true;
    }
    if (path !== "/api/v1/generation/chat") return false;
    const command = request.postDataJSON();
    assert.equal(
      command.resource_id,
      resource.knowledge_source_id,
      "Every question keeps its selected resource",
    );
    assert.equal(command.institution_id, tenant);
    let conversation = conversations.find(
      (row) => row.conversation_id === command.conversation_id,
    );
    if (!conversation) {
      assert(!command.conversation_id, "Only owned conversations may continue");
      conversation = {
        conversation_id: randomUUID(),
        title: command.user_query,
        status: "active",
        resource_context: context,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      conversations.push(conversation);
      messages.set(conversation.conversation_id, []);
    }
    const rows = messages.get(conversation.conversation_id);
    const answer =
      "Fictional resource answer: Campus library support is available.";
    for (const [type, content] of [
      ["user", command.user_query],
      ["assistant", answer],
    ]) {
      rows.push({
        message_id: randomUUID(),
        conversation_id: conversation.conversation_id,
        message_sequence: rows.length + 1,
        message_type: type,
        content_text: content,
        sources: type === "assistant" ? sources : [],
        created_at: new Date().toISOString(),
      });
    }
    await reply(route, {
      ...conversation,
      session_id: randomUUID(),
      message_id: rows.at(-1).message_id,
      answer,
      status: "success",
      model_used: null,
      metadata: {},
      sources,
      source_references: [],
      usage: null,
    });
    return true;
  };
}
