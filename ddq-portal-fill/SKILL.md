---
name: ddq-portal-fill
description: >-
  Fill a vendor security / due-diligence questionnaire that is open in the Claude
  browser pane using the human-reviewed answers from a proposed-answers workbook,
  then hand back for attachments and submission. Use this as the LAST step of the DDQ
  chain, after ddq-portal-extract pulled the questions and ddq-propose-answers produced
  the color-coded workbook the human then reviewed/edited — e.g. "fill the portal",
  "enter our answers into the portal", "the responses are approved, fill them in",
  "complete the questionnaire from the reviewed sheet". Reconciles from the reviewed
  sheet open in the pane (not the pre-review local file), fills radios / checkboxes /
  free-text / upload picks, verifies every fill by reading form state back, and closes
  by naming the attachments the human must upload and offering a final saved extract.
  It never submits — the human clicks submit.
author: Deborah Beckett | deborahbeckett99@gmail.com
---

# Fill a DDQ portal from the reviewed answers

## What this does and why

`ddq-propose-answers` produces a color-coded workbook; the human then reviews it —
resolving pink rows, correcting answers, picking frames — and that reviewed sheet, not
the draft Claude generated, is what actually gets submitted. This skill takes those
**human-approved** answers and enters them into the live portal, then stops so the human
can attach files and submit.

Two ideas make this safe rather than a blunt auto-filler:

1. **The reviewed sheet is the source of truth — and it's open in the browser pane.**
   The person uploaded the proposed-answers workbook into a Drive tab and edited it right
   there (that's the whole point of putting it in the pane). So read the answers *from the
   pane*, not from the local `*_PROPOSED_*.xlsx` the propose step wrote — that local file
   is pre-review and stale the moment the human touches a cell.
2. **Fill only what the form asks for.** A questionnaire answer is a *selection* plus,
   sometimes, a *comment*. Over-filling comment/free-text fields with rationale is the main
   way a fill step leaks internal or wrong-scoped text to a customer. The comment rule
   below is the guardrail.

**This skill never submits.** Filling is the human's authorized ask; clicking *Submit /
Complete questionnaire* is always the human's action, in the portal. Stop before it.

## Where this sits in the chain

1. `ddq-portal-extract` — pull questions + options from the portal.
2. `ddq-propose-answers` — match to the Answer Bank → color-coded review workbook.
3. **`ddq-portal-fill` (this skill)** — reconcile from the reviewed sheet in the pane, fill
   the portal, verify, hand back for attachments.
4. `ddq-portal-extract` again — capture the *completed* portal (answers + attachments) as
   the final saved record. Then the human submits.

## Inputs

1. **The portal**, open and signed-in in the browser pane (same tab the extract used).
2. **The reviewed proposed-answers workbook**, open in a Drive/Sheets tab in the *same*
   pane. Read the **Proposed Answers** sheet. Its columns (from `build_proposed_xlsx.py`):
   `Section | Q # | Hangs off | Question | Type | Response Options | Proposed Answer (G) |
   Proposed Comment / Rationale (H) | Source (I) | Confidence / Action (J) | Proposed
   Attachment (K)`.
   - **Column G is the answer** (the radio pick, the checkbox selection text, or a
     `(free-text — see rationale)` marker meaning "the answer is in H").
   - **Column H** is the customer-facing text — used *only* for genuine free-text fields
     (see the comment rule).
   - **Column K** names the file to attach, when the question is an upload ask.

## Reading the reviewed sheet from the pane

Google Sheets renders the grid on a **canvas**, so `get_page_text` returns only the
selected cell and `read_page` won't give you the grid. Read it visually:

1. `tabs_context` to find the Sheets tab; `tabs_select` it.
2. `screenshot` and scroll through the **Proposed Answers** sheet top to bottom, reading
   columns G / H / K per row. Widen or zoom if cells are clipped; click a cell to read its
   full value in the formula bar when a long H is truncated.
3. Build your fill plan as `{Q#, type, G-answer, H-text, K-attachment}` per question.

**Do not** re-download the workbook from Drive to read it — the human edited it in the
pane, and (because an `.xlsx` opened in Sheets autosaves in Office-editing mode) the pane
*is* current. Round-tripping through the Drive connector is the exact step the pane was set
up to avoid.

If the sheet isn't open in the pane, ask the human to open it there rather than pulling it.

## The comment rule (the core guardrail)

**Never proactively fill a comment / free-text field from column H.** Fill H into a field
only when **one** of these holds:

- **It's a genuine free-text question and H *is* the answer** (the extract typed it
  `longAnswer` / `shortAnswer` / free-text; G reads `(free-text — see rationale)`). Then
  the field's value is H.
- **Free text beyond the column-G selection is required by the form mechanics** — e.g. a
  radio/checkbox whose option is "Other (please specify)", or a portal that hard-requires a
  justification comment before it will accept the row.

Outside those two cases, a radio/checkbox answer is **the selection alone** — enter the
pick and move on. H is reviewer/rationale context; it is not a comment to paste. Many
portals don't even expose a comment box on radio questions (confirm in the DOM); when they
do, still leave it empty unless one of the two conditions applies.

**Shape H to the field.** When H carries answer-framing that doesn't fit the input — a
"Yes. " preamble in front of a URL destined for a URL box — enter the value the field wants
(the URL), not the conversational wrapper. Note any such trimming in your report.

**Don't fill an unresolved row.** If a reviewed row is still a "pick a reading" note rather
than an answer (an unresolved AMBIGUOUS FRAME), leave the field blank and flag it — don't
dump the enumeration into the portal. (In practice the human resolves these during review;
if one slips through, stop and ask.)

## Filling — mechanics that actually work

Portals are usually SPAs with **React (or similar) controlled inputs**, so setting
`.value` / `.checked` in JS **won't register** — the framework overwrites it on next
render and the change never reaches state. Drive the real controls:

- **Radios / checkboxes:** `computer left_click` on the option (by `ref` from `read_page`,
  or by screenshot coordinate). Checkboxes are a toggle — only click ones that should end
  up ticked; re-clicking an already-ticked box clears it.
- **Free-text / textarea / URL:** `form_input` with the field's `ref` — it dispatches the
  events the framework listens for. (Raw JS assignment does not.)
- **Upload picks:** if the answer is "Upload file", select that radio; the actual file is
  the human's to attach (see below). Selecting "Upload file" with no file attached is the
  correct half-state — it usually leaves the question *incomplete*, which is expected.

**a11y-label caveat.** `read_page` can mislabel option controls. A file-upload pair whose
real labels were "Upload file" / "I don't have this file" surfaced as `radio "Yes"` /
`radio "No"`. Don't trust the label alone; anchor by **document order + a screenshot**, and
confirm each control by the DOM `name`/position, not the printed label.

**Verify every fill by reading state back.** After each action (or each small batch), run a
read-only JS check of the underlying inputs (`input.checked`, `textarea.value.length`, the
"N of M answered" progress counter) to confirm it registered before moving on. This is how
you catch a mis-mapped ref immediately instead of at the end. Reading state is fine; it's
*writing* state in JS that doesn't work.

**Map refs carefully across scroll.** `read_page` windows to what's rendered, and refs
renumber as you scroll. Re-`read_page` after each scroll and re-confirm which ref is which
question (a quick `form_input` on a known free-text field, then read its `name` back, pins
the mapping) before clicking radios you can't easily tell apart.

## Guardrails

- **Read-only-safe actions:** reading the DOM, screenshots, expanding sections, reading
  state back. **Write actions** are limited to entering the reviewed answers. Never click
  Submit / Complete / Finish / Send.
- **Fill from the reviewed sheet, not the local draft.** If in doubt which is which, the
  reviewed one is open in the pane and may differ from the generated file; the pane wins.
- The customer-facing accuracy rules still apply to anything you type — but the reviewed
  sheet has already been through them, so you're transcribing approved text, not composing.
  If a reviewed answer looks actively wrong (over-claims Type II, names a colleague, pastes
  an internal handling note), **stop and flag it** rather than entering it.

## Closing — hand back for attachments, then the final extract

When the fillable answers are in, don't declare victory — walk the human through what's
left, in two beats:

**1. Attachments (right after filling).** Count the questions that ask for an upload and
name the recommended file for each from column K. Say plainly that you can't upload and
that the file is named in the sheet's final column. Template:

> There are **N questions requiring you to upload an attachment** (Qx, Qy). I can't upload
> these for you, but I've recommended the file to attach in the final column (**Proposed
> Attachment**) of the Proposed Answers sheet — Qx: `<file>` (NDA-gated), Qy: `<file>`
> (NDA-gated). Let me know when you've uploaded those attachments, and I'll do a final pass
> to extract a final version of everything we're submitting to the customer.

(If there are zero upload asks, skip straight to the offer of a final extract.)

**2. Final extract (after the human confirms the files are on).** When the human says the
attachments are uploaded:

> I'll extract all our responses so we have a saved final version of exactly what's going
> to the customer — attachments included. I'll let you know when it's done, then you submit.

Then run **`ddq-portal-extract`** once more against the now-complete portal (its attachment
sweep will pick up the uploaded filenames) to produce the final saved record next to the
other per-customer extracts. Report where it landed and reconcile the count — then it's the
human's to click Submit.

## Log it on the Linear tracking issue

Once the final record exists, close the loop back to the DDQ's Linear issue — the sub-issue
under **`<your DDQ tracking project>`** that the request came in on. **Suggest the
comment, then post it only on the operator's explicit approval.** The operator's standing rule
is "I publish myself"; they have authorized posting *this wrap-up comment* specifically, after
a clear yes. So show them the drafted text, ask, and on a yes `save_comment` to the issue. On
anything short of a yes — or if you don't have Linear write access — leave it as a draft for
them to post themselves.

The comment carries two things the operator asked for: **a link to the final saved answers**
and **a time estimate**. Match whatever house format your prior DDQ closeouts use — the shape
below is a compact bullet list, not prose:

> * **Duration: `<X>` hours** (`<optional context — e.g. portal friction, research-heavy questions>`)
> * Questions: `<N>` (`<context, e.g. "total across 3 questionnaires", if relevant>`)
> * Responses:
>   * [`<descriptive sheet title>`](<`<Drive/Sheets link to the saved final record>`>)

Notes on the format: duration is in **hours** (decimal, e.g. `5.41 hours`), bold; the
optional parenthetical is where honest context goes ("some of this was fighting with the
portal"). The Responses bullet links each saved answer sheet, one per line — and Linear link
syntax wraps the URL in angle brackets: `[title](<url>)`. If a run spanned multiple
questionnaires, list one Responses sub-bullet per sheet and note the combined question count.

Two specifics that keep the comment honest:

- **The link.** The final workbook is written locally; a Linear link needs it in Drive
  first. Have the operator drag the `*_FINAL_*.xlsx` into their **`<your DDQ folder>`**
  folder (opening it with Google Sheets is fine), then link that Drive file. Don't paste a local path — it isn't clickable for anyone else.
- **Duration is an estimate, not a tracked duration.** Claude Code does not clock billable
  time. Reconstruct a *rough* figure in hours from artifact timestamps (workbook
  build/modified times, Drive created/modified times) and **exclude** the operator's async
  review/attach gaps and any one-time tooling work. Give a round figure (`~0.5 hours`), not a
  false-precise one, and put the basis in the parenthetical. If the operator tracked the time
  themselves, theirs wins — offer the estimate, let them overwrite it.

## What this skill is not

It does not *extract* the questions (`ddq-portal-extract`) or *draft/match* the answers
(`ddq-propose-answers`) — it transcribes already-reviewed answers into the portal. It does
not submit, and it does not attach files. It does not edit the Answer Bank.
