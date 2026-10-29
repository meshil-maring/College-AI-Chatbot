# Learning Resources and AI Assistant: UI and UX

The shared library, draft/upload, review and resource-scoped Ask AI UI are
implemented. File-delivery interactions below remain planned.
See the [baseline and scope](README.md) and [implemented API](API.md) for current behavior.
Apply the existing [design system](../../../frontend/docs/DESIGN_SYSTEM.md).

## Shared resource workspace

All three role shells mount the same `LearningResourcesPage`. Shells supply
navigation and identity; they do not implement resource lists, dialogs or forms.
The page owns its title to avoid duplicate workspace headings.

```text
Learning Resources                       [Add resource]*
Institution documents and reference material for your AI assistant.

[Library] [My uploads]* [Review queue]*
[Search resources................] [Type v] [Status v]* [Clear]

Title                  Audience          Publication     AI availability
Student handbook       Public            Published       Available
  Institution guide                 [View details] [Ask AI]* [...]*
Library guidelines     Students only     Draft*          Still processing*
  Reference material                [View details]          [...]*

[Previous]                 Page / result information                 [Next]
```

`*` denotes a capability-dependent control or authorized management detail.
Readers see only eligible records and safe status information. Managers can see
drafts and processing failures when granted access. A role name alone never
unlocks a control. No dummy rows or fabricated counts appear in production.
Library applies reader audience rules. My uploads shows permitted own drafts;
Review queue uses explicit admin management access. All views reuse the list,
details and form. The same audience badge appears throughout the workflow.

Keep the common label **Learning Resources** in admin, faculty and staff
navigation. During migration, admin Documents can open this same component;
remove duplicate navigation once the old workflow is covered. Keep the existing
FAQ editor until shared adapters preserve its canonical publication behavior.

## Resource list and details

- One row represents a knowledge source. Its detail view lists its documents and
  versions; a source ID is never treated as a document ID.
- Search matches resource title/description. Type and status filters, sorting and
  pagination must operate over the authorized server result set. Until the API
  supports them, omit those controls or explicitly label a current-page search.
- Use title, description, source type, audience and authorized publication/readiness labels.
  Show document counts or update times only when returned by the API.
- Open details in the same accessible drawer in every role. Show source metadata,
  permitted document/version information and an explanation of AI availability.
- Put supported actions in a consistent order: View details, Ask AI, then a menu
  for authorized edit/version/retry/publication/archive actions.
- Expose file open/download only after a separate authorized delivery contract
  exists. Citation metadata and storage identifiers are not download links.

The add/edit form has persistent labels for title, description, existing upload
source type and requested audience: Public, All signed-in institution members,
or Selected roles. Roles include Students, Staff, Faculty/teachers and Admins;
allow combinations. New drafts are private until an admin publishes them.
Faculty/staff can propose an audience and submit for review; admin capabilities
add review and live publication actions. Use the exact shared form and audience
matrix in the [upload plan](AUDIENCE_UPLOAD.md).

Upload accepts only server-supported file types and size limits. Retain a failed
draft and give a specific retry action. File inputs explain when reselection is
needed. Show reviewer feedback beside the draft and keep proposed audience
separate from the currently published audience. A replacement never changes live
answers before admin approval of its version and audience.

## Component ownership

Proposed implementation locations; these files are not created by this draft:

| Owner                                       | Modules and responsibility                                        |
| ------------------------------------------- | ----------------------------------------------------------------- |
| `frontend/src/features/learning-resources/` | Shared page, resource rows/list, filters and view model           |
| `learning-resources/details/`               | Source detail drawer and document/version presentation            |
| `learning-resources/editor/`                | Metadata/upload form, validation and action controls              |
| `learning-resources/data/`                  | Query options/keys, capability mapping and guarded mutation hooks |
| `learning-resources/styles/`, `__tests__/`  | Scoped layout and adjacent workflow coverage                      |
| `frontend/src/features/chat/`               | Existing chat shell, composer, messages and source cards          |

Extract components by responsibility as they become necessary. Do not create
empty scaffolding or separate admin/faculty/staff resource implementations. Keep
every maintained folder within 15 files and each code file within 250 lines.

## Chat experience

Retain one AI Assistant entry and the shared `ChatShell` for authenticated roles.
Use a conversation list, readable answer column, source cards and a persistent
composer. Suggested prompts can differ by context while using the same component.

From an eligible resource, **Ask AI** opens a new resource-scoped conversation
after the backend supports that contract. Display a named resource context chip
above the composer and in restored history. Never inject source text in the
browser or attach a filter to an unrelated existing conversation. Changing scope
starts a new conversation and preserves the previous conversation in history.

An institution-wide conversation is clearly labeled as using institution
knowledge. A source-scoped conversation explains that its answers are limited
to that resource. Missing relevant evidence produces an insufficient-information
message and supported next steps; it does not silently broaden the search.

Render server-returned citations below the relevant answer, with source title
and version/section when available. Source cards use the same resource-detail
interaction as the library once that API exists. Unavailable or revoked sources
show an explanation; never reconstruct a storage URL in the client.

Display only progress the server actually reports. A single request/response
endpoint uses **Sending...** and **Preparing answer...**; fine-grained searching,
generation stages, streaming and Stop require explicit backend support.

## State behavior

| State                              | Required behavior across roles                                                           |
| ---------------------------------- | ---------------------------------------------------------------------------------------- |
| Identity or institution unresolved | Explain the prerequisite before mounting private data hooks.                             |
| First load                         | Layout-shaped skeleton with an accessible loading label.                                 |
| Authorized empty library           | Explain that no resources are available; offer Add resource when allowed.                |
| No search matches                  | Preserve filters and offer Clear filters.                                                |
| Initial error                      | Section error and Retry; do not display an empty-success state.                          |
| Background refresh/error           | Retain authorized rows; show Updating or a stale warning and Retry.                      |
| Action pending                     | Keep button width, show the operation, block duplicate submissions.                      |
| Write saved but refresh failed     | Say Saved with a refresh warning; Retry refresh does not repeat the write.               |
| Access/session replaced            | Hide protected rows immediately, cancel retired reads and discard late callbacks.        |
| Processing failure                 | Explain that AI indexing failed; offer an authorized retry without claiming publication. |
| No AI evidence                     | Explain the limitation beside the answer; preserve the question and conversation.        |

## Visual and accessibility rules

Use existing dark surfaces, warm yellow primary actions, shared typography and
status colors. Reuse workspace headers and base controls before adding variants.
Use 40px desktop controls and at least 44px targets on mobile/coarse pointers.
Below 840px available content width, render labeled resource cards with the same
content and actions. Filters wrap, long titles reflow and the page never scrolls
horizontally. Mobile detail drawers occupy the available viewport.

All actions work by keyboard, drawers contain and restore focus, fields associate
errors with labels, statuses include text and async updates use appropriate live
regions. Follow the design system's contrast, reduced-motion, zoom and reflow
checks. No role-specific palette, spacing or action vocabulary is introduced.
