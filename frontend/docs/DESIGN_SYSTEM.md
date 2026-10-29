# College AI Chatbot design system

Version 1.0 · 27 October 2026

Use this guide for new screens and visual updates across public entry, authentication,
administrator, staff, faculty, student and AI chat experiences. The visual direction
is the existing Academic Setup interface: dark neutral surfaces, warm yellow actions,
readable typography and compact, orderly layouts.

This document defines the standard implemented by the shared theme and active screens.
See the [adoption record](DESIGN_ADOPTION.md) for coverage and implementation ownership.
Apply these rules when implementing or updating a screen, preserving its behavior,
permissions and institution boundaries. The [Academic Setup guide](ACADEMIC_SETUP_DESIGN.md)
continues to define that workflow's data and integration rules.

## 1. Visual principles

- Give every page one clear title and one primary action per action group.
- Use neutral surfaces for structure; reserve yellow for actions, selection and focus.
- Use consistent spacing and alignment before adding decoration.
- Keep ordinary content readable; handle crowded layouts through reflow and grouping.
- Use the same component sizes and state meanings across roles and workflows.

## 2. Colors

The names below are the canonical CSS custom properties installed in
[`src/styles/tokens.css`](../src/styles/tokens.css) and exposed to Tailwind utilities.

| Token                 | Value              | Purpose                                          |
| --------------------- | ------------------ | ------------------------------------------------ |
| `--ui-bg`             | `#0d0d0d`          | Page canvas                                      |
| `--ui-shell`          | `#101214`          | Sidebar and top bar                              |
| `--ui-surface`        | `#131619`          | Cards, panels and drawer body                    |
| `--ui-surface-raised` | `#1b1e21`          | Menus, secondary buttons and table headers       |
| `--ui-surface-hover`  | `#202326`          | Hovered neutral controls and rows                |
| `--ui-border`         | `#292d32`          | Decorative card borders and dividers             |
| `--ui-border-control` | `#6b7280`          | Input boundaries and meaningful control outlines |
| `--ui-text`           | `#f5f7fa`          | Headings, body text and entered values           |
| `--ui-text-muted`     | `#adb6c3`          | Supporting text, metadata and placeholders       |
| `--ui-accent`         | `#ffca28`          | Primary actions, selected navigation and focus   |
| `--ui-accent-hover`   | `#ffda6b`          | Hovered primary actions                          |
| `--ui-accent-pressed` | `#e6b622`          | Pressed primary actions                          |
| `--ui-on-accent`      | `#17130a`          | Text and icons on yellow surfaces                |
| `--ui-overlay`        | `rgb(0 0 0 / 48%)` | Modal and mobile navigation backdrop             |

Use flat fills for standard controls and panels. Existing gradients are migration
items. Use dark text on yellow buttons. Use the accent for links with an underline
in prose. Keep muted text fully opaque; fading a container also fades its text.

Status tokens use `--ui-{status}` for foreground and `--ui-{status}-bg` for background.

| Status    | Foreground | Background | Examples                               |
| --------- | ---------- | ---------- | -------------------------------------- |
| `success` | `#32db87`  | `#09251c`  | Active, saved, published               |
| `warning` | `#ffca28`  | `#211f15`  | Pending, needs attention               |
| `danger`  | `#ffb2b2`  | `#211719`  | Validation failure, destructive action |
| `info`    | `#6eafff`  | `#111f32`  | Informational message                  |
| `neutral` | `#adb6c3`  | `#1b222b`  | Draft, inactive, archived              |

Every badge includes a written status. Status colors describe meaning and must not
become alternate brand accents. Use the danger foreground as the border of a danger
button; use the matching status background as its fill. Destructive hover/press
states retain that pair and add an underline/inset outline respectively.

## 3. Typography

Use one sans-serif stack throughout the product, including form controls and dialogs:

```css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  'Segoe UI',
  sans-serif;
```

The existing admin CSS names Inter, but the app does not currently bundle or load it.
Use the system fallback until Inter is supplied locally with its license and
`font-display: swap`. Keep the existing content security policy when adding fonts.
Use weights 400 (body), 500 (labels), 600 (components) and 700 (page titles).

Sizes below are CSS-pixel equivalents at a 16px root. Implement type sizes in `rem`,
preserve the browser's root size and use unitless line heights.

| Role / token        | Size            | Line height | Weight | Use                                            |
| ------------------- | --------------- | ----------- | ------ | ---------------------------------------------- |
| `--ui-type-title`   | 30px / 1.875rem | 1.25        | 700    | Page h1; 24px / 1.5rem on mobile               |
| `--ui-type-section` | 20px / 1.25rem  | 1.3         | 600    | Major section and drawer title                 |
| `--ui-type-card`    | 16px / 1rem     | 1.5         | 600    | Card and subsection heading                    |
| `--ui-type-body`    | 14px / 0.875rem | 1.5         | 400    | Default body, labels, inputs and buttons       |
| `--ui-type-small`   | 12px / 0.75rem  | 1.5         | 400    | Helper text, metadata, badges and breadcrumbs  |
| `--ui-type-metric`  | 28px / 1.75rem  | 1.2         | 700    | Summary values                                 |
| `--ui-type-reading` | 16px / 1rem     | 1.6         | 400    | Chat answers, notices and long reading content |

Buttons use body size at weight 600; labels use body size at weight 500.
Table cells use body size; a deliberately compact table may use 12px throughout.
Keep essential text at least 12px. Editable controls on mobile use 16px.
Use sentence case, one h1 per page and sequential heading levels. Use normal letter
spacing for body text and -0.02em for page titles. Use tabular numerals for metrics;
reserve monospace for code and technical identifiers. Keep prose within 70ch.

## 4. Spacing and shape

Use a 4px spacing scale, expressed in `rem`. The token naming is `--ui-space-N`,
where N is the number of 4px units.

| Token           | Value          | Typical use                                      |
| --------------- | -------------- | ------------------------------------------------ |
| `--ui-space-1`  | 4px / 0.25rem  | Label to helper or closely related metadata      |
| `--ui-space-2`  | 8px / 0.5rem   | Icon to label; label to input; button group gap  |
| `--ui-space-3`  | 12px / 0.75rem | Compact panel padding; related field gap         |
| `--ui-space-4`  | 16px / 1rem    | Card padding; form field gap; mobile page gutter |
| `--ui-space-5`  | 20px / 1.25rem | Drawer padding; tablet page gutter               |
| `--ui-space-6`  | 24px / 1.5rem  | Desktop page gutter; panel and section gap       |
| `--ui-space-8`  | 32px / 2rem    | Separation between major content groups          |
| `--ui-space-12` | 48px / 3rem    | Empty-state vertical padding                     |
| `--ui-space-16` | 64px / 4rem    | Spacious entry-page section padding              |

Use `gap` for sibling layout. Align headings, filters and tables to the same page
gutter. Avoid negative margins for page alignment. Keep borders at 1px and focus
outlines at 2px; these are intentional exceptions to the spacing scale.

| Token                 | Value                          | Use                                     |
| --------------------- | ------------------------------ | --------------------------------------- |
| `--ui-radius-sm`      | 6px                            | Badges and small inset elements         |
| `--ui-radius-md`      | 8px                            | Buttons, inputs, menus and table panels |
| `--ui-radius-lg`      | 12px                           | Cards, dialogs and chat bubbles         |
| `--ui-radius-pill`    | 999px                          | Avatars and pill-shaped indicators      |
| `--ui-shadow-overlay` | `0 16px 48px rgb(0 0 0 / 32%)` | Floating menus and dialogs              |

Separate ordinary cards with borders. Apply shadows only to floating surfaces.

## 5. Page layout and responsive behavior

Standard management-page order: breadcrumbs → title, description and primary action
→ optional summary cards → search and filters → records → pagination.
Omit optional groups when they do not help the task.

| Viewport width | Page gutter | Navigation                 | Content behavior                            |
| -------------- | ----------- | -------------------------- | ------------------------------------------- |
| Up to 760px    | 16px        | Overlay sidebar            | Stacked header/actions; full-screen drawers |
| 761–1150px     | 20px        | 230px sidebar, collapsible | Wrap filters; reduce grid columns           |
| Above 1150px   | 24px        | 264px sidebar, collapsible | Full management layout                      |

Keep the top bar at a minimum of 68px and the content container at a maximum of
1760px, centered within the remaining workspace. Authentication panels use a
448px maximum width; chat reading columns use a 768px maximum width.
At mobile sizes, sidebar width is `min(280px, calc(100vw - 48px))`.

Prefer container queries for feature grids: above 1050px use up to four summary
columns, 521–1050px use two, and up to 520px use one. Below 840px of available
content width, convert management records to labeled cards, preserving sorting and
actions. If a comparison requires a table, place horizontal scrolling inside its
own labeled region. Never require horizontal scrolling for the whole page.
Wrap long names and identifiers; make any truncated value available on focus or
through an accessible detail view. Allow control and row heights to grow with text.

## 6. Component rules

| Component             | Standard                                                                                |
| --------------------- | --------------------------------------------------------------------------------------- |
| Primary button        | Accent fill, on-accent text, 40px minimum height, 16px horizontal padding, 8px icon gap |
| Secondary button      | Raised surface, text foreground, control border; hover uses hover surface               |
| Tertiary action       | Text or icon with transparent fill; hover uses hover surface                            |
| Input, select, search | 40px minimum height, 12px horizontal padding, surface fill, control border              |
| Textarea              | Input styling, 96px minimum height, vertical resize                                     |
| Checkbox/radio        | 20px visual indicator, accent checked state with dark check/dot; label is clickable     |
| Icon button           | 40px square target, 18px icon, accessible name and visible hover/focus feedback         |
| Badge                 | Small type at weight 500, 4px vertical / 8px horizontal padding, status colors          |
| Card                  | Surface fill, decorative border, large radius, 16px padding, 12px internal gap          |
| Table                 | 48px minimum header/row height, 12px vertical / 16px horizontal cell padding            |
| Drawer                | 400px width capped at viewport, 20px padding, scrollable body, pinned action footer     |
| Confirmation dialog   | 448px maximum width, 24px padding, explicit action and cancel labels                    |

Use 44px minimum control targets on mobile and coarse pointers. Keep inputs at
a minimum of 40px on desktop in compact forms. Give buttons default, hover, pressed,
focus, disabled and loading states. Primary hover/press use the corresponding
accent tokens; neutral pressed controls use surface fill with an inset control outline.
Use 50% opacity only for disabled controls, retain their labels and explain any
non-obvious restriction nearby. Loading actions retain width, say “Saving…” or
“Sending…”, expose busy state and block duplicate submissions.

Table headers are left-aligned except numeric columns and trailing actions.
Right-align numeric values and use tabular numerals. Show sort direction visually
and with `aria-sort`. Show row actions on keyboard focus as well as hover.
Forms have persistent labels, visible required indicators, associated helper/error
text and `aria-invalid` on invalid fields. Place errors beside fields and retain drafts.

Drawers and dialogs show a title, close control, body and footer. Use the existing
academic dialog lifecycle where applicable: contain focus, prevent background
interaction and restore focus to the opener. Escape and close follow the same
unsaved-change confirmation. Mobile drawers occupy `100dvh`; pinned controls allow
for safe-area insets. Modal content remains modal even with a transparent backdrop.

Chat uses reading-size text, 16px bubble padding and 16px between messages.
Distinguish user/assistant messages with written speaker labels and alignment;
use raised neutral and surface fills respectively. Keep sources beside the answer,
allow long content to wrap and keep the composer reachable above the keyboard.

## 7. States, icons, motion and accessibility

Loading uses layout-shaped skeletons and a readable busy label. Empty states explain
what is missing and offer a permitted next action. A failed request shows an error
and Retry; retained stale data is labeled. Unavailable metrics say “Unavailable”;
zero means a successful, empty result. Success messages use a polite live region;
urgent errors use an alert. Preserve existing permission and stale-data safeguards.

Use Lucide icons consistently: 16px inline, 20px navigation, 24px card headings,
with stroke width 2. Decorative icons are hidden from assistive technology.
Use 150ms ease-out for color/opacity changes and 200ms for drawer movement.
Honor `prefers-reduced-motion` by removing movement and pulsing animation.
Layer order: content 0, sticky headers 20, sidebar 30, menus 40, mobile scrim 50,
mobile sidebar 60. Modal dialogs use the browser top layer with their own backdrop.

Use a 2px accent focus outline with 3px offset. When the surrounding surface is yellow,
use the on-accent color. Keep focus visible and unobscured on every interactive control.
Target 4.5:1 text contrast throughout, including helper text and placeholders;
meaningful control boundaries and state indicators need at least 3:1 against
adjacent colors. Decorative borders may be subtler. These targets follow W3C's
[text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
and [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) guidance.
Support keyboard operation, 200% text enlargement and content reflow at 320 CSS
pixels; verify narrow layouts and 400% zoom following the
[reflow guidance](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html).

## 8. Implementation and review

Shared tokens, base rules and component styles are imported by `src/index.css`.
Keep feature layout styles with their feature. Existing `--admin-*` and academic
feature variables map to canonical tokens; new components use `var(--ui-*)`.
Tailwind utilities resolve to the same values. Keep portal dialogs in the theme
scope. Document any new reusable
variant here with its purpose and consumers before introducing different values.

Current references: [shared workspace](../src/features/workspace/WorkspaceFrame.tsx),
[Academic Setup navigation](../src/features/admin/academic-setup/styles/overview-theme.css),
[page layout](../src/features/admin/academic-setup/styles/overview-layout.css) and
[dialog lifecycle](../src/features/workspace/useWorkspaceDialog.ts).
These establish the starting point; the target values in this guide take precedence
over inconsistent existing visual values during a scoped design update.

Before completing a visual change, check the palette, type scale, spacing and
component states against this guide; inspect desktop, tablet and mobile layouts;
verify keyboard focus, contrast, zoom, loading, empty, error and long-content states.
Run the checks required by [frontend instructions](../AGENTS.md), and keep evidence
in repository-level `logs/frontend/`. Record which screens were migrated so the
documented target is never confused with completed application-wide adoption.
