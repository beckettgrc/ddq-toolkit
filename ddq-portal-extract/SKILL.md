---
name: ddq-portal-extract
description: >-
  Extract every question, answer option, selected response, comment/rationale,
  upload instruction, and attachment out of a vendor security, due-diligence, or
  sanctions/trade questionnaire that is open in the Claude browser pane, and save
  it to an xlsx record. Use this whenever someone says they want to "pull",
  "extract", "capture", "grab", or "get a record of" the questions and our
  responses from a DDQ / VRA / security- or sanctions-questionnaire portal (SAFE
  ONE, Fusion/FFQ on Salesforce, Onspring, OneTrust, UpGuard, Venminder,
  Securimate, ProcessUnity, and lookalikes) — including when they just say
  "the portal is open, extract it" without naming a format. Also
  triggers on requests to reconstruct which answer options were available so we
  can see where a "least-worst-fit" answer was chosen, or to note which questions
  asked us to attach a file.
author: Deborah Beckett | deborahbeckett99@gmail.com
---

# DDQ / VRA portal extraction

## What this does and why

Vendor questionnaire portals let you *submit* answers but almost never let you
*export* them. Once submitted, the record lives only in the customer's portal.
When you want a durable copy — for the answer library, for the next renewal,
or to review where we were forced into a thin answer — someone has to walk the
portal and capture it by hand. This skill does that capture reliably and puts it
in a consistent xlsx.

Two things make portal capture harder than it looks, and this skill exists to
handle both:

1. **The submitted answer, the rationale, and the full option list are often not
   in the visible text.** Radio inputs are `disabled` in the read-only view but
   still carry `.checked`. Rationales can live in a hidden `<textarea>.value`.
   Innerhtml/CSV scrapes of the rendered page miss all of this. You have to read
   the DOM, not the screenshot.
2. **Portals paginate.** They load one section (or ~10 rows) at a time. If you
   extract what's on screen you silently get a fraction of the questionnaire. You
   must load every section/row first — and on some platforms that means the human
   scrolls, because programmatic scroll stalls.

Capture more than the selected answer. The record must keep **every option
the portal offered**, because a bare "Yes" hides the cases where the
real answer was "none of these fit, we picked the least-worst one." That signal
is only visible when you keep the full option set.

## The output

One xlsx with two sheets, built by `scripts/build_extract_xlsx.py`:

- **Summary** — customer, assessment, portal platform, record id, respondent,
  completion state, section list, question count, how many questions asked for a
  file upload, and how many files were actually attached.
- **Q&A** — one row per question: `Section | Q # | Hangs off | Question | Our
  Answer | Response Options Available | Comment / Rationale | Instruction (portal
  ask) | Attachment / File`.
  - **Response Options Available** lists *every* option with `[X]` on the selected
    one — the "least-worst-fit" reconstruction column.
  - **Hangs off** preserves conditional nesting (sub-questions that only appear
    because a parent was answered a certain way).
  - **Attachment / File** always renders explicitly (`- none -` when empty) and
    notes what the file appears to be when one is present.

Don't hand-roll the workbook. Produce a `capture.json` (schema in
`references/capture-schema.md`) and run the script:

```bash
python3 .claude/skills/ddq-portal-extract/scripts/build_extract_xlsx.py capture.json "<Customer>_<Portal>_extract_<YYYY-MM-DD>.xlsx"
```

Follow the house filename convention (e.g.
`Customer_FFQ_VRA_extract_2026-07-14.xlsx`) and save into the project
folder alongside the other per-customer extracts.

## Workflow

### 1. Orient before touching anything

The portal is already open in the browser pane and the human has signed in (see
the operator guide, `references/operator-guide.md`). Confirm what you're looking
at:

- `mcp__Claude_Browser__tabs_context` to get the tab id and origin.
- One `screenshot` to see the layout — sections, question shape (radio / checkbox
  / dropdown / free-text), comment fields, any upload controls.
- `read_page` (filter `all`) to get the section navigation and confirm how many
  questions/sections exist. Note the per-section counts (e.g. "7/7", "16/16") —
  that's your completeness checklist.

Identify the platform. If it matches one in `references/platform-notes.md`
(Fusion/FFQ, SAFE ONE, Onspring, OneTrust, UpGuard, Venminder, Gartner
BuySmart), read that section — it tells you the exact
question-card selector, where the hidden values live, and how pagination behaves.
If it's a platform not yet documented, use the generic discovery steps below and
**add what you learn to `references/platform-notes.md`** so the next extraction is
faster.

### 2. Find the reliable extraction handle (DOM, not screenshot)

The accessibility tree truncates question text and hides option/comment values
inside empty form nodes, so go to `mcp__Claude_Browser__javascript_tool` and
inspect the real DOM. Dump the `outerHTML` of one question card to learn its
structure, then figure out:

- the **question-card selector** (a repeating element wrapping each question),
- how to read the **full question text**,
- the **option elements** and how to tell which is selected (`input.checked` even
  when `disabled`; a checkmark SVG; an `aria-checked`),
- where the **comment / rationale** lives (visible `<textarea>.value`, a hidden
  textarea, or a read-only output span),
- whether there's an **upload/attachment** control or a "please provide/upload…"
  instruction, and any filename shown.

**Scope every card to itself.** Questionnaires nest sub-questions inside parents.
When you collect options/comments for a card, filter to elements whose
`.closest(cardSelector) === card`, or you'll pull a child's radios into the
parent and double-count. Record the parent id in the `parent` field.

### 3. Load the whole questionnaire, then extract

Portals rarely have everything in the DOM at once:

- **Section-paginated** (Fusion/FFQ): click each section in the left nav, let it
  render, extract, move to the next. Reconcile against the per-section counts.
- **Infinite-scroll / virtualized** (SAFE ONE): only *real* human scroll reliably
  triggers page fetches; programmatic scroll stalls and can corrupt the height
  estimate. Ask the human to scroll top-to-bottom while you extract, or arm a
  fetch/XHR response interceptor before they scroll (see platform notes).

Run one extraction function per loaded view that returns structured JSON per card
(question, options+checked, selected, comment, instruction, attachment). Wrap DOM
JS in an IIFE — `const` at eval top-level leaks and the next call throws
"already declared."

### 4. Sweep for attachments explicitly

The record must note which questions asked for a file and what it was. Even if no
card showed an upload widget, do one global pass for file anchors
(`sfc/servlet`, `ContentDocument`, `download`, `*.pdf/docx/xlsx…`), file-upload
components, and question text containing "upload / attach / please provide /
evidence / screenshot". Record findings in the `instruction` and `attachment`
fields. **"No attachments anywhere" is itself a finding worth stating** — say so
rather than leaving it silent.

### 5. Build and report

Assemble `capture.json`, run the build script, then tell the human:

- where the file landed,
- counts (total questions, per section) reconciled against the portal's own
  completion numbers,
- anything notable: N/A or comment-only answers, thin "least-worst-fit" picks
  surfaced by the options column, conflicts between an answer and its comment,
  and the attachment situation.

## Guardrails

- **Read-only by default.** This skill captures; it does not change or submit
  answers. Don't click answer options, edit fields, or submit. If the human wants
  to *update* the portal, that's a separate task they drive.
- **Never submit on the operator's behalf.** Submission is always the human's to
  do in the portal.
- The extract is an internal record. Apply the usual DDQ voice/assurance rules
  only if you go on to draft customer-facing answers from it — pure extraction
  copies what's there verbatim, including any answer you'd later want to revisit.

## Reference files

- `references/platform-notes.md` — per-platform selectors, hidden-value
  locations, and pagination behavior — seven platforms plus a generic
  discovery procedure.
  Read the matching section before extracting; append new platforms you learn.
- `references/capture-schema.md` — the exact `capture.json` shape the build script
  consumes.
- `references/operator-guide.md` — the short, non-technical instructions for the
  person opening the portal (open Claude Code, browser icon, sign in, hand off).
