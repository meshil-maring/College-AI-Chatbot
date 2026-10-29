# Public college chat

`PublicChatPage` remains outside authentication and uses only an institution code.
Routes key the page by college so drafts, request feedback and late callbacks
cannot move into another college's conversation. `usePublicChat` owns guarded
manual sends and retries; `state/messages.ts` owns browser message construction.
`PublicChatMessages` reuses the shared assistant Markdown renderer.

The public transport sends only `institution_code` and `message`, omits browser
credentials and projects only public answer/source fields. Its 35-second deadline
covers fetch, response-body loading and validation. It reuses the shared deadline
helper; public errors remain independent of signed-in recovery status.

`recovery/PublicRequestFeedback` renders timeout/failure feedback, **Stop waiting**
and **Retry**. Stopping aborts browser waiting and retains the unanswered question.
Retry uses that existing message, without appending a duplicate question. Stale
responses and failures are ignored after stop, retry, unmount or college changes.
There is no automatic POST retry, including when the retry timer expires.

`recovery/useRetryDelay` unlocks the manual Retry control after a valid server
`Retry-After` value on 429/503. Seconds and HTTP dates are accepted, bounded to one
hour. The countdown is in memory; server rate/concurrency controls remain
authoritative after reload or a new conversation.

History is browser-local, bounded and scoped by college. An unanswered stored
question restores as interrupted after reload and offers explicit retry. Existing
storage validation, safe projection and per-college clearing remain in `storage/`.
No pending-request IDs, server conversation records or authenticated turn RPCs
are added to the public endpoint. Each retry is a new anonymous generation call;
stopping browser waiting does not guarantee that server model work has stopped.

Colocated tests cover the transport deadline, response-body cancellation,
retry delay, question retention, route changes and late callbacks. The loopback
streaming browser runner is documented in
[`scripts/validation/public_chat`](../../../../scripts/validation/public_chat/README.md).
The [configured-service acceptance runner](../../../../scripts/validation/chat_live/README.md)
checks actual authentication, storage and AI providers, public citations, history
reload and mobile layout. It uses run-owned accounts and disables them afterward.
