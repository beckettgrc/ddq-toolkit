---
name: ddq-propose-answers
description: >-
  Propose customer-facing answers for a `<your-org>` DDQ / security questionnaire
  by matching each extracted question against the validated Answer Bank, then produce
  a color-coded review workbook that flags which answers are verbatim-from-the-bank
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
3. **Optional, for attachments** — the Answer Bank's `Artifacts` registry tab names
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

1. **Find the file id.** `search_files` with
   `title contains '<Your Answer Bank>' and mimeType = 'application/vnd.google-apps.spreadsheet'`,
   and pick the one in your DDQ folder (parent
   `<YOUR_DRIVE_FOLDER_ID>`). If the team shares one canonical bank, its id is
   stable across users; searching by title each run is the robust default.
2. **Export it to xlsx.** Call `download_file_content` with that `fileId` and
   `exportMimeType = application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`. The
   result is too big to inline, so it lands at a path the tool response prints
   (`.../tool-results/…download_file_content-*.txt`), shaped `{content: [base64], id, mimeType,
   title}`.
3. **Decode to a real workbook** (no blob through the model):

   ```bash
   jq -r '.content' "<that tool-results path>" | base64 -d > /tmp/answer_bank_live.xlsx
   ```

4. **Parse `/tmp/answer_bank_live.xlsx` with openpyxl** exactly as before — every tab and
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

Delivery of the finished review workbook is already a human drag-and-drop into your DDQ folder,
so **that** step never needed the connector — only the bank read did, and this covers it.

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

## Radio questions

For Yes/No/N-A questions, set `answer` to the pick and keep the customer comment empty
unless the portal actually requires one — a bare, correct radio selection is usually the
right answer, and it avoids re-stating the obvious. Take the pick from the bank entry's
answer field, or infer it from the matched comment's plain meaning; where it's genuinely
ambiguous (a compound question, or the bank is silent), leave `answer` empty and make it
pink so the human decides.

**Multi-select (checkbox) questions** — a single `answer` string can't express several
ticks, so set `checked: true` on each selected entry in the `options` array instead
(leave `answer` empty). The renderer marks `[X]` on every checked option and lists the
joined picks in the Proposed Answer column. Checkbox picks are frequently a **judgment
call** — provider/vendor inventories (cloud, CDN, DNS, MDM), region lists where the
portal's buckets don't line up with the regions you actually run in, or the assurance list,
which is the classic trap: tick only what you hold **today**, never a report type you
haven't been issued, and never an upstream provider's certification as your own (see
`references/guardrails.md` → *Assurance*). When the selection is uncertain, make the row
pink and say which ticks to confirm.

## Attachments

Some questions ask for a document ("please provide/attach evidence/copy of X"). Propose
the file in the `attachment` field **by name**, taking the name from the Answer Bank's
`Artifacts` registry tab. The evidence files live in Drive; you only
name the file so the human attaches it — you don't read or upload it.

Mark NDA-gated docs as such (SOC 2 report, pen-test summary, policies). Claude can't
upload — the human attaches — so the attachment field is a flag for them.

## Producing the output

Assemble a `proposal.json` (schema and shading rules are documented at the top of
`scripts/build_proposed_xlsx.py`) with one entry per question — including the scrubbed
customer-facing `rationale`, the `tier`/`confidence`, a short internal `note` (why this
tier, what to verify, or the gap), the `source` label (which bank tab/row), and any
`attachment`. Then run:

```bash
python3 .claude/skills/ddq-propose-answers/scripts/build_proposed_xlsx.py \
    proposal.json "<Customer>_<Portal>_PROPOSED_<YYYY-MM-DD>.xlsx"
```

The script scrubs internal handling notes from the customer-facing text (and prints what
it removed — nothing is cut silently), applies the shading, and writes a **Summary** sheet
(counts + the shading key + your notes) and a **Proposed Answers** sheet. Save it into the
project folder next to the other per-customer files.

## Delivering the workbook to Drive

The workbook lives in Google Drive under your **`<your DDQ folder>`**
folder:

```
https://drive.google.com/drive/folders/<YOUR_DRIVE_FOLDER_ID>
```

**Do not try to upload it programmatically.** The only wired-up Drive auth is the MCP
connector, which accepts the file only *inline* — that forces the whole workbook, base64-
encoded, through the model's token stream. It's unreliable (it fails outright by
announcing-without-emitting) and degrades as the file grows. The robust path is a **human
import**: the person running the skill is already signed into Drive, so hand the last step
to them.

So, at delivery:

1. **Open the folder in a new browser tab** — `mcp__Claude_Browser__tabs_create`, then
   `navigate` that tab to the folder URL above. If a Drive tab is already open on that
   folder, just use it.
2. **Prompt the human to move the workbook into the folder and review/approve it.** Give
   them the workbook as a **clickable markdown link to its local path** (so they can
   right-click → locate the file to drag it in — a bold plain filename isn't clickable) and
   tell them to drag it into the folder window (or **New → File upload**). Uploading a native
   `.xlsx` keeps the shading exactly; "Open with Google Sheets" preserves the cell fills.
   These are drafts — the human reviews and approves before anything is customer-ready,
   working the shading in order (pink → gray → a glance at white). You never submit.
3. **Don't click the import for them** — the file picker is an OS dialog outside the
   browser pane, and delivery/import is the human's action to take. Your job is to land
   them in the right folder with the right filename in hand.

## Reporting back

**The workbook is the report. The shading already says which rows need attention — do not
re-explain the pink/gray rows in prose.** Re-narrating every flagged answer in chat is the
verbose failure mode this section exists to prevent; it duplicates the workbook and buries
the one instruction the human actually needs.

Keep the final message to **two moves**, tight:

1. **Drag the file into your DDQ folder.** Reference the workbook as a **clickable markdown
   link to its local path** (e.g. `[Acme_VendorHub_PROPOSED_2026-07-20.xlsx](./Acme_VendorHub_PROPOSED_2026-07-20.xlsx)`),
   not bold plain text — the human needs to right-click → locate the file to drag it in, and
   only a real link is clickable. The Drive folder is already open in a browser tab.
2. **Review the flagged rows** (pink first, then gray; white is a glance). One line — the
   count is enough; the shading names them.

Add a line **only** for something the shading cannot carry: an Answer Bank entry that looked
stale or mis-framed and is worth fixing at source, or a HOLD/BLOCKED entry you honored that
the human should know about. If there's nothing like that, don't manufacture a summary.

## What this skill is not

It does not *fill* the portal (that's the fill step) and it does not *extract* the
questions (that's `ddq-portal-extract`). It also does not write new answers back into the
Answer Bank — surfacing gaps to the human is the correct move; the human decides what
gets promoted into the validated bank.
