import assert from "node:assert/strict";
import path from "node:path";
import { checkLayout } from "./journey.mjs";

export async function recoveryJourney(page, role, logDir, backend) {
  assert(["127.0.0.1", "localhost"].includes(backend.hostname));
  await page.setViewportSize({ width: 1440, height: 1000 });
  const lostQuestion = `Recover a lost reply for ${role}`;
  let lostRequest;
  let saved;
  const loseResponse = async (route) => {
    lostRequest = route.request().postDataJSON();
    const response = await route.fetch({
      url: new URL("/api/v1/generation/chat", backend).href,
      timeout: 60000,
      maxRedirects: 0,
    });
    assert.equal(response.status(), 200);
    saved = await response.json();
    await route.abort("connectionreset");
  };
  await page.route("**/api/v1/generation/chat", loseResponse);
  await page
    .getByRole("textbox", { name: "Ask a question" })
    .fill(lostQuestion);
  await page.getByRole("button", { name: "Send message" }).click();
  const recovery = page.getByRole("region", { name: "Reply recovery" });
  await recovery.waitFor();
  await page.unroute("**/api/v1/generation/chat", loseResponse);
  await recovery.getByRole("button", { name: "Check reply" }).click();
  await recovery.waitFor({ state: "detached" });
  assert.equal(await page.getByText(lostQuestion, { exact: true }).count(), 1);
  const replay = await page.request.post(
    new URL("/api/v1/generation/chat", backend).href,
    {
      headers: { Authorization: `Bearer fixture-${role}` },
      data: lostRequest,
    },
  );
  assert.equal(replay.status(), 200);
  assert.equal((await replay.json()).message_id, saved.message_id);

  const failedQuestion = `Fictional retry test for ${role}`;
  const submitted = [];
  const observe = (request) => {
    if (
      new URL(request.url()).pathname === "/api/v1/generation/chat" &&
      request.method() === "POST"
    ) {
      const data = request.postDataJSON();
      if (data.user_query === failedQuestion) submitted.push(data);
    }
  };
  page.on("request", observe);
  await page
    .getByRole("textbox", { name: "Ask a question" })
    .fill(failedQuestion);
  await page.getByRole("button", { name: "Send message" }).click();
  await recovery.waitFor();
  await page.reload();
  await page.getByRole("button", { name: "AI Assistant", exact: true }).click();
  await page.getByRole("button", { name: /Reply needs attention/ }).click();
  const retry = recovery.getByRole("button", { name: "Retry reply" });
  await retry.waitFor();
  await page.setViewportSize({ width: 320, height: 800 });
  await checkLayout(page);
  await page.screenshot({
    path: path.join(logDir, `${role}-reply-recovery-320.png`),
  });
  await retry.click();
  await recovery.waitFor({ state: "detached" });
  await page
    .getByText(/^Fictional resource answer:/)
    .nth(4)
    .waitFor();
  await page
    .getByText("Reply needs attention", { exact: true })
    .waitFor({ state: "detached" });
  page.off("request", observe);
  assert.equal(submitted.length, 2);
  assert.equal(submitted[0].turn_id, submitted[1].turn_id);
  assert.equal(
    await page.getByText(failedQuestion, { exact: true }).count(),
    1,
  );
  const history = await page.request.get(
    new URL(`/api/v1/conversations/${saved.conversation_id}/messages`, backend)
      .href,
    {
      headers: { Authorization: `Bearer fixture-${role}` },
    },
  );
  assert.equal(history.status(), 200);
  const messages = await history.json();
  assert.equal(
    messages.filter(
      (message) =>
        message.message_type === "user" &&
        message.content_text === lostQuestion,
    ).length,
    1,
  );
  assert.equal(
    messages.filter(
      (message) =>
        message.message_type === "user" &&
        message.content_text === failedQuestion,
    ).length,
    1,
  );
  assert.equal(
    messages.length,
    10,
    "Five questions have exactly five saved replies",
  );
  console.log(
    `PASS ${role}: lost response replay, retry after reload, stable turn ID and no duplicate saved messages`,
  );
}
