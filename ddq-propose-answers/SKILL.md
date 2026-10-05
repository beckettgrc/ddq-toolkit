---
name: ddq-propose-answers
description: >-
  Propose customer-facing answers for a `<your-org>` DDQ / security questionnaire
  by matching each extracted question against the validated Answer Bank, then produce
  a color-coded live review page (plus a workbook record) that flags which answers are verbatim-from-the-bank
  versus synthesized, so a human can focus review on the low-confidence rows. Use this
  whenever you have a list/spreadsheet of DDQ questions and need draft responses — e.g.
  "propose answers for this DDQ", "draft responses from the Answer Bank", "fill out the
  answers column", "which of these can we answer from the bank", or the middle step after
  ddq-portal-extract has pulled the questions. Also triggers on requests to compare a
  questionnaire to the Answer Bank, or to identify which questions have no bank coverage
  and need a human to draft.
author: Deborah Beckett | deborahbeckett99@gmail.com
---

# Propose DDQ answers from the Answer Bank

## What this does and why

Given a set of DDQ questions (usually the output of `ddq-portal-extract`), this
skill drafts a proposed answer for each one and packages them into a workbook whose
**shading tells the reviewer where to spend attention**. The insight is that ~80% of
DDQ questions have a crafted, validated answer sitting in the Answer Bank — those
should go in **verbatim** and need only a glance. The remaining ~20% are the ones that
eat time: no bank match, a partial match, or a judgment call. The color-coding surfaces
exactly those, so the human reviews the 20% instead of re-reading the 80%.

The Answer Bank is **the floor and the ceiling** for the high-confidence answers: use
its crafted entries verbatim, don't expand or "improve" them. Where the bank has no
match, synthesizing a draft is allowed *for review* — but say so honestly (via low
confidence) rather than passing a guess off as bank-backed. Read
`references/guardrails.md` before drafting — it carries the accuracy rules (assurance
limits, subprocessor≠subcontractor, HOLD/BLOCKED flags, voice) that keep answers safe.

## Inputs

1. **The questions.** Normally the `ddq-portal-extract` output xlsx (Q&A sheet: Section,
   Q #, Hangs off, Question, options, etc.), but any question list works.
2. **The Answer Bank — for real runs, read it live from Google Drive, not a local file.**
   (The synthetic bank in `demo/` is the exception — a local file is fine there.) It is a native
   Google Sheet, **`<Your Answer Bank>`**, in your DDQ folder. It is **tiered by tab-name prefix** (see below), and it
   changes often (evergreen URLs, new stock answers) — so always pull the current copy. See
   *Loading the Answer Bank from Drive* below. For a real bank, do **not** rely on an `.xlsx`
   sitting in a local folder; other operators won't have it and it goes stale the moment
   someone edits the Drive copy.
3. **The customer's tier / package**, if your answers vary by it (e.g. recovery objectives
   by support level). The `ddq` runner reads it from the request ticket; without the runner,
   ask. See *tier-conditional rows* below.
4. **Optional, for attachments** — the Answer Bank's `Artifacts` registry tab names
   the available evidence files; the files themselves live in Drive. You only *name* the
   attachment for the human to attach (you don't upload it), so the registry tabs are enough —
   you don't need to read the PDFs.

## Loading the Answer Bank from Drive

The read has to work for whoever runs the skill against *their own* connected Drive, so it
goes through the Drive connector — never a local path. Two gotchas decided the method:

- `read_file_content` returns the sheet as text but **flattens every tab into one stream with
  no tab names** — that destroys the tiering (you can't tell `1. Customer Questions` from
  `2. Refine` from `3. Escalation`). Don't use it for the bank.
- `download_file_content` exporting to `.xlsx` **keeps the sheet names**, and because the file
  is large the connector **spills the result to a local file** instead of returning it inline
  — so the bytes never round-trip through the model. That's the path.

Steps:

1. **Use the canonical file id.** Pin your bank's id here – `<YOUR_ANSWER_BANK_FILE_ID>` – so
   every run reads the one validated copy. Only if that id fails (moved, or the operator can't
   access it) fall back to `search_files` with
   `title contains '<Your Answer Bank>' and mimeType = 'application/vnd.google-apps.spreadsheet'`,
   pick the one in your DDQ folder (parent `<YOUR_DRIVE_FOLDER_ID>`), and tell the operator the
   id changed. Staged updates (review pages, sweep workbooks) aren't validated until they land
   in the bank itself.
2. **Export it to xlsx.** Call `download_file_content` with that `fileId` and
   `exportMimeType = application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`. The
   result is too big to inline, so it lands at a path the tool response prints
   (`.../tool-results/…download_file_content-*.txt`), shaped `{content: [base64], id, mimeType,
   title}`.
3. **Decode to a real workbook** (no blob through the model):

   ```bash
   jq -r '.content' "<that tool-results path>" | base64 -d > /tmp/answer_bank_live.xlsx
   ```

4. **Parse `/tmp/answer_bank_live.xlsx` with openpyxl** (if the default `python3` lacks
   openpyxl, macOS's `/usr/bin/python3` usually has it) exactly as before — every tab and
   its name is intact, so the tier logic works unchanged.

Everything downstream (matching, verbatim pulls, tiering) reads that decoded file.

### Fallback when there's no Drive connector

The Drive connector makes this efficient; it isn't required. If the operator hasn't connected
Drive (or the connector can't see the bank), read it from the **browser pane** instead — the
same way the fill step reads the reviewed sheet:

1. Have the operator open the **`<Your Answer Bank>`** sheet in a browser-pane tab (they're
   signed into Google in the pane; you are not — don't sign in for them).
2. Read it visually: `screenshot` and scroll each tier-1 tab, keying on the **tab name prefix**
   for tiering (`1.` primary, `2./3.` secondary) — Google Sheets renders on canvas, so
   `get_page_text` gives only the selected cell; use screenshots and click a cell to read a long
   value in the formula bar.
3. Match as usual. It's slower and you'll want to scope reads to the tabs a given questionnaire
   actually touches, but the tiering, verbatim rule, and guardrails are unchanged.

Review happens on the live review page, so **that** step never needed the connector — only the
bank read did, and this covers it.

## The ranking — match each question in this order

The tab-name prefix encodes the trust tier. Prefer the highest tier that genuinely fits.

1. **Tier 1 — primary, verbatim.** Tabs whose name starts with **"1"** (e.g.
   `1. General`, `1. Common Questions - Verbatim`, and whatever topic tabs you keep).
   If a question closely matches an entry here, use that entry's answer **verbatim**.
   → shade: **none** (`tier: "1"`).

2. **Tier 2/3 — secondary.** Tabs starting with **"2"** or **"3"** (`2. Prior Responses - Synthesis`). Use these only when Tier 1 has no strong match.

   *(Excel caps sheet names at 31 characters — keep any new tab name at or under that, and
   note that only the leading digit is what actually selects the tier.)*
   → shade: **light yellow** (`tier: "2-3"`). 

3. **Synthesize — last resort.** No usable bank match. Draft from general known facts (and,
   if needed, the evidence registry in the `Artifacts` tab) and set a
   **confidence** that reflects how solid it is.
   → shade by confidence: **>90 none, 80–90 light gray, <80 light pink** (`tier: "synth"`).

A useful confidence calibration for synthesized answers:
- **≥90 (white):** essentially certain (a documented fact just not in a crafted buffer).
- **80–90 (gray):** sound and defensible — a partial bank match used verbatim but only
  answering part of the ask, an assembly of identity facts, or a confident "Not applicable"
  (e.g. financial-institution questions that don't map to `<your-org>`'s service).
- **<80 (pink):** needs the human's judgment — a real gap, a radio pick the bank doesn't
  settle, missing data, or a bracketed placeholder. Leave these clearly incomplete rather
  than inventing specifics.

## Variants, review dates and tier-conditional rows

**Pick the variant that matches the phrasing.** Keep one bank row per common phrasing of a
question – "in the last 12 months" vs "in the last 24–36 months"; "what are your timeframes?"
vs "do you remediate within [X] days?" vs "is it documented?". Match the customer's phrasing
to the closest variant and use that row verbatim; don't reshape the base row to fit a variant
that already exists.

**Simple questions get simple answers.** Bank rows follow the CAIQ shape: a short answer
(`answer` – Yes / No / N/A, sometimes empty) and a description (`comment`). For a yes/no
question, propose the **short answer** and leave the free text blank unless the portal
requires a comment or the question also asks how/what/describe – don't volunteer the
description. On a free-text field that asks a yes/no question, answer "Yes." or "No." and at
most one sentence drawn from the description. Use the full description for "describe your X"
questions.

**Honor `nextReviewDate`.** Give every bank row a `nextReviewDate`. Time-boxed rows (incident
history "in the last 12 months", the latest pen test or DR test, an audit period) have answers
that go stale on that date. If today is past a row's `nextReviewDate`, don't use it as a
verbatim match: make the row **pink**, note "bank row past its review date (YYYY-MM-DD) –
confirm the answer still holds", and add it to the Summary's "Bank fixes spotted".

**Fill tier-conditional rows from the customer's tier.** Some answers depend on the customer's
support tier or package. Store those rows as templates, e.g.:

> RTO and RPO are based on the customer's support tier. As a {{Tier}} customer, your
> Recovery Time Objective (RTO) is {{RTO}} and your Recovery Point Objective (RPO) is {{RPO}}.

| Tier | RTO | RPO |
|---|---|---|
| `<Top tier>` | `<x hours>` | `<y minutes>` |
| `<Middle tier>` | `<x hours>` | `<y minutes>` |
| `<Base tier>` | `<x hours>` | `<y hours>` |

(Fill the table from your continuity plan. If the bank row's figures differ, trust the bank
row and flag the mismatch.) Fill the placeholders and treat the result as **verbatim**
(tier 1). No tier known (a prospect) → use an all-tiers row. A tier name not in the table →
pink, and ask.

## Frame ambiguity — a wrong *scope* is worse than a gap

A bank match on the same **topic** can still answer the wrong **frame** — and shading that
white or yellow is worse than a blank, because a reviewer skimming for colour lets it
through. So before you trust *any* match (even a clean verbatim one), check whose people and
whose systems the question is really about. See `references/guardrails.md` → *Frame
ambiguity* for the full rule and the email-spoofing / MFA worked examples. In short:

- Read the **surrounding questions** (the extract gives you the whole list) — a section is
  usually one customer worry asked several ways, and the neighbours pin the frame.
- If context resolves it, **answer normally — do not flag.** Over-flagging makes review slow
  enough that the shading stops being trusted; that's a real cost.
- **Force the row to pink** only when the answer *materially* changes across readings, the
  question **and** its neighbours leave it unresolved, **and** a wrong pick would visibly
  trace back to us. Then, in the `rationale`, **lay out the readings** — "(a) if *our*
  systems → …; (b) if *your* hosted environment → …" — so the reviewer's job is "pick the
  reading," and lead the `note` with `AMBIGUOUS FRAME:`. (No new colour or field — this is
  just a pink `synth` row whose rationale enumerates the frames.)

## Short responses and free text

Every row has a **short response** (column F) and, when it's needed, a **free-text
response** (column I). Keep them separate:

- **Free-text questions** (the portal field *is* a text box): set `type: "free-text"` and
  put the answer in `free_text`. The renderer writes `[see proposed comment]` in F, `N/A` in
  *Free Text Required?*, and your text in I.
- **Single-select (Yes/No/N-A, radio)**: set `answer` to the pick. Take it from the bank
  entry's answer field, or infer it from the matched comment's plain meaning; where it's
  genuinely ambiguous (a compound question, or the bank is silent), leave `answer` empty and
  make it pink so the human decides.
- **Multi-select (checkbox)**: set `checked: true` on each selected option (leave `answer`
  empty). The renderer lists the picks as bullets in F. Checkbox picks are frequently a
  **judgment call** – provider/vendor inventories (cloud, CDN, DNS, MDM), region lists where
  the portal's buckets don't line up with the regions you actually run in, or the assurance
  list, which is the classic trap: tick only what you hold **today**, never a report type you
  haven't been issued, and never an upstream provider's certification as your own (see
  `references/guardrails.md` → *Assurance*). When the selection is uncertain, make the row
  pink and say which ticks to confirm.

For select questions, set `free_text_required` from what the **portal** does:

- **Required** – the portal compels text with this answer (a No/N/A justification, "Other –
  please specify", an explanation box it won't let you skip). Write the text in `free_text`;
  it lands in column I.
- **Optional** – a comment box exists but isn't needed. **Leave column I blank.** A bare,
  correct selection is usually the right answer and avoids restating the obvious. If you
  matched bank text, still pass it as `free_text` – the renderer moves it into the internal
  Rationale column as reference, so the reviewer can add it if they choose.
- **N/A** – no comment box.

The `note` goes to **Rationale (Internal Use Only)** – why this shade, what to verify, the
gap, or the frame readings for an ambiguous row. It never reaches the customer.

## Attachments

Some questions ask for a document ("please provide/attach evidence/copy of X"). Propose
the file in the `attachment` field **by name**, taking the name from the Answer Bank's
`Artifacts` registry tab. The evidence files live in Drive; you only
name the file so the human attaches it — you don't read or upload it.

Claude can't upload — the human attaches — so the attachment field is a flag for them.
Don't add "under NDA" or "on request" to the answer or the attachment name: customers filling
a questionnaire are typically already under NDA, and the questionnaire is the request.

## Producing the output

Assemble a `proposal.json` (schema and shading rules are documented at the top of
`scripts/build_proposed_xlsx.py`) with one entry per question – the short response
(`answer` or checked `options`), the customer-facing `free_text`, `free_text_required`, the
`tier`/`confidence`, a short internal `note`, the `source` label (bank tab + row, or
"Synthesized"), and any `attachment`. Fill in `meta.portal` and `meta.due`, and pass
`meta.notes` as `[label, text]` pairs (e.g. `["Conditional questions", "…"]`,
`["Bank fixes spotted", "…"]`). Save `proposal.json` in the project folder as
`<Customer>_<Portal>_proposal_<YYYY-MM-DD>.json` – the fill step reads it back.

The review happens on a **live review page** (an Artifact), not in a workbook. The reviewer
picks a Decision on each row and edits answers in place; every change saves automatically,
and the fill step reads the decisions straight from the page.

**1. Build the page:**

```bash
python3 .claude/skills/ddq-propose-answers/scripts/build_review_artifact.py \
    proposal.json "<scratchpad>/<Customer>_DDQ_REVIEW_<YYYY-MM-DD>.html"
```

It scrubs internal handling notes from customer-facing text (and prints what it removed),
shades each **whole row** by band, and lays out the same columns as the workbook:
`A Section | B # | C Hangs Off | D Question | E Short Response Options | F Proposed Short
Response | G Decision | H Free Text Required? | I Proposed Free Text Response | J Attachment
| K Confidence | L Rationale (Internal Use Only) | M Source (Answer Bank) | N Your notes`.
F (a dropdown for single-select, a text box otherwise), G (Accept / Accept w/ edits / Reject
/ Hold), I and N are editable. The shading key and `meta.notes` sit in a collapsible panel
above the grid; filters cover Undecided / Decided / Pink / Gray / Yellow / Attachments.

**2. Publish it** with the Artifact tool: `file_path` = the HTML, `icon: "table"`,
`capabilities: {"db": {}, "user": {}}` (first publish only), and a one-line `description`
("Proposed answers for <Customer>'s <assessment> – review and approve in place."). Load the
`artifact-design` skill first if this session hasn't already – the template already follows
its page contract, so this is a formality, not a redesign. Republishing the same file path
(e.g. after re-proposing a few rows) keeps the URL and the saved decisions.

**3. Record the URL.** Write the returned artifact URL into `proposal.json` as
`meta.review_url`. Decisions live in the artifact's database, collection `answers`, one doc
per question keyed by the row's `key` (the question id made db-safe): fields `decision`,
`short` and `free_text` (filled only when the reviewer changed the proposal), `notes`, `id`,
`row`, `updatedAt`.

**4. Also write the workbook, as the record.** Run
`build_proposed_xlsx.py proposal.json "<Customer>_<Portal>_PROPOSED_<YYYY-MM-DD>.xlsx"` and
save it in the project folder. It's the archive copy and the fallback if the reviewer can't
use the page (no claude.ai sign-in); it isn't the review surface, so don't ask the human to
import it unless they want it in Drive.

## Delivering the review

Give the human the review page link. That's the whole handoff – no Drive import, no
download. They work the page (pink first, then gray, a glance at white) and tell you when
they're done.

If they want the workbook in Drive as well, your DDQ folder is
`https://drive.google.com/drive/folders/<YOUR_DRIVE_FOLDER_ID>`. **Don't upload
it programmatically** – the Drive connector only takes the file inline, which pushes the
whole workbook through the token stream and fails. Open the folder in a browser tab and let
them drag the file in from a clickable markdown link to its local path.

**Falling back to the workbook.** If the page can't save (the reviewer isn't signed in to
claude.ai, or the Artifact tool isn't available), deliver the workbook the old way: open your
DDQ folder in a browser tab, hand them the clickable local link to drag in, and they review
in Sheets using column G.

## Reporting back

**The page is the report. The shading already says which rows need attention — do not
re-explain the pink/gray rows in prose.** Re-narrating every flagged answer in chat duplicates
the page and buries the one instruction the human needs.

Keep the final message to **two moves**, tight:

1. **The review page link**, with one line on what to do: pick a Decision on each row, edit
   F/I in place, say "done" when finished.
2. **The counts** – pink / gray / yellow – in one line; the shading names the rows.

Add a line **only** for something the shading cannot carry: an Answer Bank entry that looked
stale or mis-framed, a bank row past its review date, or a HOLD/BLOCKED entry you honored.
Mention the workbook record with a clickable local link in a short closing clause, not as a
step.

## What this skill is not

It does not *fill* the portal (that's the fill step) and it does not *extract* the
questions (that's `ddq-portal-extract`). It also does not write new answers back into the
Answer Bank — surfacing gaps to the human is the correct move; the human decides what
gets promoted into the validated bank.
