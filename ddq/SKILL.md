---
name: ddq
description: >-
  End-to-end runner for a `<your-org>` customer DDQ / security questionnaire, ideally
  starting from its Linear issue. Use this as the ENTRYPOINT when the operator hands over a
  DDQ to work — e.g. "let's work on this DDQ: `<URL>`", "run this DDQ", "take this
  questionnaire end to end", or just a link to the tracked request (in Linear, GitHub, etc.). It reads the issue for context (or asks for it when Linear isn't
  available), then orchestrates the three step-skills in order — ddq-portal-extract →
  ddq-propose-answers → (human review) → ddq-portal-fill → final capture — pausing at each
  human handoff, and closes by suggesting a label fix and a wrap-up comment on the issue,
  publishing each only on the operator's explicit approval. It never submits the
  questionnaire and never sends anything customer-facing.
author: Deborah Beckett | deborahbeckett99@gmail.com | 2026-07-22
---

# Run a DDQ end to end from its Linear issue

## What this is

The single entrypoint that turns "here's a DDQ" into a guided run. The operator drops a
Linear issue link (or just names the customer and portal); you drive the whole pipeline,
prompting them at each handoff instead of making them name skills. The three step-skills
stay the source of truth for *how* each phase works — this skill's job is to **sequence**
them, carry context between them, and bookend the run with intake and closeout.

```
Linear issue ──▶ [intake] ──▶ ddq-portal-extract ──▶ ddq-propose-answers ──▶ (human reviews
in the pane) ──▶ ddq-portal-fill ──▶ (attachments, human) ──▶ final ddq-portal-extract
──▶ [closeout: label fix + wrap-up comment] ──▶ human submits
```

Because a run spans many turns and several human handoffs, **state where you are** at each
step ("Extract done — 35 questions. Proposing answers next.") so a resumed session can pick
up cleanly.

## Connectors are ideal, not required — degrade gracefully

The Linear and Google Drive connectors make this run *efficient*; they are not *hard
dependencies*. You can complete a DDQ without either — you just gather by hand what the
connector would have handed you. Never dead-end because a connector is missing; fall back:

- **No Linear (or no access to this issue).** You don't need to see the issue to start — you
  only need the same facts. Ask the operator: *what's the customer name? can you share the
  link to their portal/questionnaire? what format is it? did they ask for any specific
  documents (SOC 2, ISO, pen-test)?* That's the whole of intake. At closeout, without Linear
  **write** access, the label fix and wrap-up comment simply become **draft-only** — you hand
  the operator the label suggestion and the comment text, and they apply/post them (which is
  also the correct behavior any time the operator hasn't authorized you to write to Linear).
- **No Google Drive connector.** The Answer Bank read in `ddq-propose-answers` has a
  pane-based fallback (open the bank in the browser and read it there); delivery of the review
  workbook is already a human drag-and-drop, so it doesn't need the connector at all. See that
  skill's Answer Bank section.

So the connector-rich path is: Linear issue in, label + comment posted for you on approval.
The degraded path is: a few intake questions in, drafts out for the operator to apply. Same
pipeline, same output quality — only the last-mile efficiency changes.

## Guardrails that hold for the whole run

- **Never submit the questionnaire, and never send anything customer-facing.** Submission,
  customer replies, portal "Complete" — all the operator's. You fill and prepare; they send.
- **Two Linear write-actions are allowed, on explicit approval only:** adding/fixing a label
  and posting the wrap-up comment. The operator's standing rule is "I publish myself"; they
  have authorized *these two internal Linear actions specifically, each after they say yes.*
  Suggest → get a clear yes → then execute. Everything else stays draft-only. Do not extend
  this to any customer-facing send. If you don't have Linear write access, these stay
  draft-only regardless.
- All the customer-facing accuracy rules (assurance limits, subprocessor≠subcontractor, no
  naming colleagues, voice) apply throughout — they live in
  `ddq-propose-answers/references/guardrails.md`.

## Step 1 — Intake

**With Linear**, read the issue before touching anything:

- `get_issue` for title, description, state, labels, assignee,
  team/project, attachments.
- `list_comments` for the request thread — the customer's original ask, the portal link,
  access/credential notes, what documents they requested, any deadline, who's coordinating.

**Without Linear**, ask the operator for the same facts (customer, portal link, format,
requested documents) — see the degradation note above.

Either way, establish and play back to the operator:

- **Customer** and what's being assessed.
- **Where the DDQ lives and its format** — portal (which platform), spreadsheet, or email
  questions. The portal URL is usually in the description or an early comment.
- **What's explicitly requested**, including named documents (ISO cert, SOC 2, pen-test) —
  these become attachment expectations later.
- **Current labels / focus area** — note the focus-area label (e.g. `infosec`, `ESG`); you'll
  re-check it against actual question content at closeout. (Only when you have the issue.)
- **Access reality.** If the portal needs a login the operator must do (most do), say so now
  and point them at `ddq-portal-extract/references/operator-guide.md`. You don't sign in.

Confirm the plan in one line and proceed once they're ready and the portal is open/signed-in.

## Step 2 — Extract  (invoke `ddq-portal-extract`)

Run the extract skill against the open portal to capture every question, option, current
answer, upload ask, and attachment into the per-customer extract xlsx. Report the count,
reconciled against the portal's own completion numbers. Keep the extracted question set in
hand — the label-vs-content check at closeout uses it.

(If the DDQ is a spreadsheet or email rather than a portal, you already have the questions;
skip the portal mechanics and go straight to proposing, per that skill's "any question list
works" input.)

## Step 3 — Propose  (invoke `ddq-propose-answers`)

Match the extracted questions against the live Answer Bank and produce the color-coded review
workbook, then land the operator in the DDQ Drive folder to import and review it. Follow that
skill's delivery + reporting rules exactly (two moves: drag the file in; review the flagged
rows — pink first). **Then stop and wait** — they review in the pane and edit G/H. Do not
proceed to fill until they say the answers are reviewed/approved.

## Step 4 — Fill  (invoke `ddq-portal-fill`)

Once they signal the review is done, run the fill skill: reconcile from the **reviewed sheet
open in the pane** (not the pre-review local file), fill the portal, verify each fill by
reading state back, then do its two-beat closing — name the attachments they must upload,
wait for their "attached," and run the final `ddq-portal-extract` pass to save the record of
exactly what's being submitted. That skill owns these mechanics; don't re-derive them here.

At the end of Step 4 the portal is filled, attachments are on, and the `*_FINAL_*.xlsx`
record exists — but nothing is submitted.

## Step 5 — Closeout on the Linear issue

Two suggestions, each published **only on the operator's explicit yes** (and only if you have
Linear write access — otherwise hand them the drafts to apply).

### 5a. Label-vs-content check

You have the full question set from the extract and the issue's labels from intake. If the
body doesn't match the focus-area label, say so concretely and offer the fix:

> This DDQ is labeled `infosec`, but section 4 was 12 sustainability/ESG questions. Want me
> to add `Topic: ESG`?

Only raise it when there's a real, sizable mismatch (a whole section on another topic, a
questionnaire labeled one thing that's mostly another) — not for one stray question.
Over-labeling is noise. On a clear **yes**: `list_issue_labels` to resolve the exact label id
(use the existing label; don't mint a near-duplicate — if the right label truly doesn't
exist, ask before creating one), then `save_issue` to add it to the issue's label set
(add to the existing labels, don't replace them). Confirm what you changed. (No issue in
hand → just name the label you'd suggest, for the operator to add.)

### 5b. Wrap-up comment

Draft the closeout comment in the house format (see `ddq-portal-fill/SKILL.md` →
"Log it on the Linear tracking issue" for the exact shape and the honesty rules):

> * **Duration: `<X>` hours** (`<optional honest context>`)
> * Questions: `<N>`
> * Responses:
>   * [`<sheet title>`](<`<Drive link to the FINAL record>`>)

- **Duration** is an estimate from artifact timestamps (workbook build/modified, Drive
  created/modified), excluding the operator's async review/attach gaps; round it, put the
  basis in the parenthetical, and let them overwrite with a tracked figure if they have one.
- **The responses link** needs the `*_FINAL_*.xlsx` in the DDQ Drive folder first — prompt
  the operator to drag it in, then use that file's Drive link (a local path isn't clickable).

Show them the drafted comment and ask approval to post. On a clear **yes**: `save_comment` to
the issue. On anything short of yes (or no write access), leave it as a draft for them to post
themselves.

Then hand back: the portal is filled and ready, the record is saved, the issue is updated —
**the operator clicks Submit** in the portal.

## What this skill is not

It doesn't replace the step-skills — it calls them. It doesn't extract/propose/fill by hand;
each phase defers to its skill. It never submits the questionnaire and never sends
customer-facing communication. The only writes it performs are the two approved internal
Linear actions in Step 5.
