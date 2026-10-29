import assert from "node:assert/strict";
import http from "node:http";

/** Fictional public API on loopback; no configuration, credentials or providers. */
export async function startFixture(origin) {
  const requests = [];
  const waiting = new Map();
  const hanging = new Set();
  const server = http.createServer((request, response) => {
    response.setHeader("Access-Control-Allow-Origin", origin.origin);
    response.setHeader("Access-Control-Allow-Headers", "content-type");
    response.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
    response.setHeader("Content-Type", "application/json");
    if (request.method === "OPTIONS") return response.end();
    if (request.url !== "/api/v1/chat/public" || request.method !== "POST") {
      response.writeHead(404);
      return response.end("{}");
    }
    let raw = "";
    request.on("data", (part) => {
      raw += part;
    });
    request.on("end", () => {
      const body = JSON.parse(raw);
      assert.deepEqual(Object.keys(body).sort(), [
        "institution_code",
        "message",
      ]);
      assert.equal(body.institution_code, "PUBLIC-TEST");
      assert.equal(request.headers.authorization, undefined);
      assert.equal(request.headers.cookie, undefined);
      requests.push(body);
      waiting.get(body.message)?.();
      waiting.delete(body.message);
      const attempt = requests.filter(
        (item) => item.message === body.message,
      ).length;
      if (
        attempt === 1 &&
        ["Slow body question", "Stopped question"].includes(body.message)
      ) {
        hanging.add(response);
        response.on("close", () => hanging.delete(response));
        response.writeHead(200);
        response.flushHeaders();
        response.write('{"answer":');
        return;
      }
      if (attempt === 1 && body.message === "Busy question") {
        response.writeHead(429, { "Retry-After": "3" });
        return response.end(
          JSON.stringify({
            error: { message: "Private quota/provider details" },
          }),
        );
      }
      response.end(
        JSON.stringify({
          status: "success",
          answer: `Public reply: ${body.message}`,
          sources: [
            {
              title: "Fictional public handbook",
              section: "Library",
              quote: "Published fictional evidence.",
            },
          ],
        }),
      );
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return {
    url: new URL(`http://127.0.0.1:${server.address().port}`),
    requests,
    waitForQuestion(question) {
      if (requests.some((item) => item.message === question))
        return Promise.resolve();
      return new Promise((resolve, reject) => {
        const timer = setTimeout(
          () => reject(new Error("Expected public question was not received")),
          10000,
        );
        waiting.set(question, () => {
          clearTimeout(timer);
          resolve();
        });
      });
    },
    async close() {
      for (const response of hanging) response.destroy();
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    },
  };
}
