# Chat answer formatting

Start the frontend on loopback port 5180 and save a successful real public-chat
response as `logs/backend/answer-formatting/live-response.json` with the shape
`{ "http_status": 200, "response": { "answer": "...", "status": "success", "sources": [] } }`.
The response must contain Markdown line breaks. Then run from the repository root:

```powershell
node scripts/validation/chat_answers/verify.mjs http://127.0.0.1:5180
```

The runner launches headless Edge, blocks non-loopback requests, seeds fictional
local history and replays the captured API response. It checks formatting of old
collapsed answers, fresh replies and reloaded history at desktop and 320px widths.
Screenshots stay in `logs/frontend/answer-formatting/browser/`. It creates no
server accounts, resources or conversations. Component tests also cover HTML,
links, remote images, code indentation and tables for both chat entry points.
