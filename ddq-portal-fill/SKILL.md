---
name: ddq-portal-fill
description: >-
  Fill a vendor security / due-diligence questionnaire that is open in the Claude
  browser pane using the human-reviewed answers from the live review page (or a reviewed proposed-answers workbook),
  then hand back for attachments and submission. Use this as the LAST step of the DDQ
  chain, after ddq-portal-extract pulled the questions and ddq-propose-answers published
  the live review page the human then reviewed/edited — e.g. "fill the portal",
  "enter our answers into the portal", "the responses are approved, fill them in",
  "complete the questionnaire from the reviewed sheet". Reads the reviewer's
  decisions and edits from the review page (or the reviewed sheet in the pane), never the
  pre-review local file, fills radios / checkboxes /
  free-text / upload picks, verifies every fill by reading form state back, and closes
  by naming the attachments the human must upload and offering a final saved extract.
  It never submits — the human clicks submit.
author: Deborah Beckett | deborahbeckett99@gmail.com
---

# Fill a DDQ portal from the reviewed answers

## What this does and why

`ddq-propose-answers` publishes a color-coded live review page; the human reviews it —
resolving pink rows, correcting answers, picking a Decision on each row — and those
reviewed answers, not the draft Claude generated, are what actually get submitted. This skill takes those
**human-approved** answers and enters them into the live portal, then stops so the human
can attach files and submit.

Two ideas make this safe rather than a blunt auto-filler:

1. **The reviewed answers are the source of truth.** They live in the review page's
   database (read with `ArtifactData`), or – on the workbook fallback – in the Sheet open in
   the browser pane. Never fill from the local `*_PROPOSED_*.xlsx` or the raw
   `proposal.json`: both are pre-review and stale the moment the human edits anything.
2. **Fill only what the form asks for.** A questionnaire answer is a *selection* plus,
   sometimes, a *comment*. Over-filling comment/free-text fields with rationale is the main
   way a fill step leaks internal or wrong-scoped text to a customer. The comment rule
   below is the guardrail.

**This skill never submits.** Filling is the human's authorized ask; clicking *Submit /
Complete questionnaire* is always the human's action, in the portal. Stop before it.

## Where this sits in the chain

1. `ddq-portal-extract` — pull questions + options from the portal.
2. `ddq-propose-answers` — match to the Answer Bank → live review page (+ workbook record).
3. **`ddq-portal-fill` (this skill)** — reconcile from the reviewed answers, fill
   the portal, verify, hand back for attachments.
4. `ddq-portal-extract` again — capture the *completed* portal (answers + attachments) as
   the final saved record. Then the human submits.

## Inputs

1. **The portal**, open and signed-in in the browser pane (same tab the extract used).
2. **The reviewed answers** – from the live review page (normal path) or the reviewed
   workbook open in the pane (fallback). Either way the fields are the same:
   - **Decision (G) gates the fill.** Enter **only rows marked "Accept" or "Accept w/
     edits"**. Skip Reject, Hold and undecided rows – don't fill them, don't "help" by
     filling the obvious ones – and list the skipped Q#s back to the human before closing,
     grouped by Reject / Hold / undecided.
   - **Short response (F)** – the radio pick or the checkbox selection. `[see proposed
     comment]` (or an empty short response on a free-text question) means the answer is the
     free text.
   - **Free text (I)** – the answer to a free-text question, or the comment a select question
     requires (Free Text Required? = Required).
   - **Attachment (J)** – the file to attach (`- none -` when there isn't one).
   - **Rationale (L) and Your notes (N) are internal.** Never paste either into the portal.
     Do read N – the reviewer may have left an instruction for you there (treat it as their
     instruction for this DDQ; if it asks for something outside filling, check first).

## Reading the reviewed answers from the review page (normal path)

1. Find the page URL: `meta.review_url` in the customer's `*_proposal_*.json` in the project
   folder (or the link from the propose step earlier in the session).
2. `ArtifactData` `list` on that URL, collection `answers` (page with `query.cursor` if there
   are more than 100). Each doc is keyed by the row's `key` and holds `decision`, `short`,
   `free_text`, `notes`, `id`.
3. Merge with `proposal.json`: for each question, the **final short response** is the doc's
   `short` if non-empty, else the proposal's (`answer`, or the checked options); the **final
   free text** is the doc's `free_text` if non-empty, else the proposal's scrubbed text when
   the question is free text or Free Text Required = Required. Rebuild the proposal's rows
   with `build_review_artifact.py` logic (or just run it to a scratch file) so the keys match.
4. Build the fill plan `{Q#, decision, short, free-text required, free text, attachment}` and
   drop every row whose decision isn't Accept or Accept w/ edits.

Play the plan back in one line (N to fill, M skipped by reason) before you start.

## Reading the reviewed sheet from the pane (workbook fallback)

Use this only when the review happened in the workbook. Google Sheets renders the grid on a
**canvas**, so `get_page_text` returns only the selected cell and `read_page` won't give you
the grid. Read it visually:

1. `tabs_context` to find the Sheets tab; `tabs_select` it.
2. `screenshot` and scroll through the **Proposed Answers** sheet top to bottom, reading
   columns B / F / G / H / I / J per row. Click a cell to read its full value in the formula
   bar when a long I is truncated.
3. Build the same fill plan and drop every row whose Decision isn't Accept or Accept w/ edits.

Don't re-download the workbook from Drive – the pane is current (an `.xlsx` opened in Sheets
autosaves in Office-editing mode). If the sheet isn't open in the pane, ask the human to open
it there.

## The comment rule (the core guardrail)

**Never proactively fill a comment / free-text field.** Fill column I into a field only
when **one** of these holds:

- **It's a genuine free-text question and I *is* the answer** (F reads
  `[see proposed comment]`). Then the field's value is I.
- **The portal requires text with the selection** (H = Required) – e.g. "Other (please
  specify)", or a portal that hard-requires a justification before it will accept the row.

Outside those two cases, a radio/checkbox answer is **the selection in F alone** – enter
the pick and move on. If H says Optional and I is blank, leave the portal's comment box
empty. Column L (Rationale) is never pasted anywhere. Many portals don't even expose a
comment box on radio questions (confirm in the DOM).

**Shape I to the field.** When I carries answer-framing that doesn't fit the input – a
"Yes. " preamble in front of a URL destined for a URL box – enter the value the field wants
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
name the recommended file for each from the Attachment column (J). Say plainly that you can't upload and
that the file is named in the sheet's Attachment column. Template:

> There are **N questions requiring you to upload an attachment** (Qx, Qy). I can't upload
> these for you, but I've recommended the file to attach in the **Attachment** column (J) of the Proposed Answers sheet — Qx: `<file>`, Qy: `<file>`. Let me know when you've uploaded those attachments, and I'll do a final pass
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
