# Public chat recovery browser checks

Start the frontend on loopback, then run from the repository root:

```powershell
node scripts/validation/public_chat/verify.mjs http://127.0.0.1:5180
```

Uses installed `playwright-core` and headless Microsoft Edge. The owned local
HTTP fixture sends response headers and a partial JSON body, then deliberately
stalls. The browser must abort body loading after the actual 35-second deadline.
It reloads the saved question and retries it, then exercises a 429 retry countdown
and Stop waiting, checking request counts and duplicate-free question display.

The harness checks mobile layout at 320 pixels and desktop controls, requires
the narrow anonymous body, rejects cookies/authorization, blocks external traffic
and flags authentication API calls. It reads no application credentials and
contacts no configured backend, project database or AI provider. Its server and
browser close after completion or failure. Logs and screenshots belong under
repository-level `logs/frontend/public-chat-recovery/`.
