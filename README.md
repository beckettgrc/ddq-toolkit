# DDQ toolkit

A set of four Claude skills for running a customer security questionnaire from link to filled
portal.

## The problem

Many enterprise customers now send their security due-diligence questionnaire through a
third-party portal — OneTrust, UpGuard, Venminder, Onspring, SAFE ONE, and others. Those portals 
are built for the customer's assessment workflow, not the vendor's.
They let you submit answers. Many do not support exporting the questions, or your responses.

The time-intensive part of a DDQ isn't answering it. Roughly 80% of any questionnaire is ground
the organization has already covered — MFA, encryption at rest, incident response, backup
retention — with a validated answer sitting in an answer bank somewhere. The cost is in the
mechanics around that: someone reads several hundred questions off a screen, matches them to previous 
questionnaire responses, and then modifies and/or pastes the answers back into the portal one
field at a time. Then the record of what was submitted lives only in the customer's system, so
the next questionnaire starts over.

Worse, the volume buries the 20% that actually needs judgment — the question with no bank
match, the one whose scope is ambiguous, the checkbox list where none of the options fit and
you have to pick the least-bad one. Those are the answers that carry risk, and they get the
same attention as the ninety questions that didn't need any.

This toolkit automates the mechanical part and puts the review time where it belongs. It can also be
used to populate spreadsheet-based questionnaires -- it's not limited to the portal workflow.

## What it does

Four skills that hand off to each other:

- **`ddq`** — the orchestrator. You start here and it sequences the rest, pausing at each
  human handoff.
- **`ddq-portal-extract`** — reads the questions out of the portal. Works from the DOM rather
  than the rendered page, because submitted answers, rationales, and the full option list are
  routinely hidden in disabled inputs and empty textareas that a screenshot or an HTML scrape
  will miss. Captures every option the portal offered, not just the one selected — that's what
  makes a thin "least-worst-fit" answer visible later.
- **`ddq-propose-answers`** — matches each question to your answer bank and produces a review
  workbook whose **shading says where to spend attention**: unshaded for verbatim bank
  answers, yellow for secondary-source material, gray for confident synthesis, pink for the
  rows that need a human. You review the pink.
- **`ddq-portal-fill`** — enters your reviewed answers back into the portal and verifies each
  one by reading the form state back, then stops.

It never submits, and it never sends anything to the customer. Both of those stay yours.

## Scope

**It does:** extract questions from a portal, draft answers from a bank you control, flag what
needs judgment, fill the portal, and save a durable record of exactly what was submitted.

**It does not:** submit the questionnaire, upload attachments, write to your answer bank, or
send anything customer-facing. It also doesn't sign in — portal credentials and 2FA are always
the operator's.

The judgment rules live in `ddq-propose-answers/references/guardrails.md`, and they're the part
worth reading even if you never run the toolkit. They cover the failure modes that matter:
answering the right topic at the wrong scope, over-claiming security practices, or letting internal 
handling notes reach a customer.

## Prerequisites

Claude Code with browser access. The Linear and Google Drive connectors make a run more
efficient but aren't required — every step degrades to asking you for what a connector would
have supplied.

You also need your own answer bank. **Every file here is a template.** The `<your-org>` and
`<…>` placeholders are deliberate; fill them in with your own details and treat your answer
bank, not anything in this repo, as the source of truth for assurance posture, subprocessors,
and infrastructure facts.

## Install

Copy the four skill folders into your `.claude/skills/` directory — project-level to share them
with a team, or `~/.claude/skills/` to have them everywhere. Start a fresh Claude Code session
and type `/ddq` to confirm they loaded.

## Try it on synthetic data

`demo/` contains a ten-question fictional questionnaire, and `Stark Industries - Answer
Bank.xlsx` is a matching synthetic bank. Paste the questions into a spreadsheet and run
`ddq-propose-answers` against them — no portal or browser needed.

To exercise the browser path as well, run the full chain against the [live demo
form](https://docs.google.com/forms/d/e/1FAIpQLScTRmgNn-8FRmsNe4EzonBC2SSwYvUUN0oUnZzoTLD41V-dsg/viewform). Extraction and fill both work against it; don't click submit at the end
— the toolkit stops short of that anyway, and submissions land in the form owner's responses.
If you'd rather have your own, rebuild it from the questions below.

The ten questions are chosen to exercise every path, so a correct run produces all four shades
rather than a wall of unshaded rows:

| Question | Expected | Why |
|---|---|---|
| 1, 2, 3 | unshaded | Clean verbatim bank matches |
| 8 | unshaded + attachment named | The toolkit names the file from the Artifacts registry; it can't attach it |
| 5, 7 | yellow | Tier 2 material, worth a human's eyes |
| 6, 10 | gray | A reduced-confidence synthesis, and a confident "not applicable" — AML/KYC doesn't map to a software provider |
| 4 | **pink** | "Do any of your personnel have access to our data?" — "No" is tempting and almost always false |
| 9 | **pink** | AI governance. A genuine gap; most answer banks haven't caught up |

If a run comes back entirely unshaded, the bank is being matched too loosely — which is the
failure mode the demo exists to catch. If questions 4 and 9 come back answered confidently,
the guardrails aren't firing.

`demo/sample-review-workbook.xlsx` is the output of an actual run over these ten questions,
if you'd rather just look at the shading than reproduce it.

## Analysis

I wrote up what building this taught me about where questionnaire work actually goes:
*(link to come)*

## License

Copyright © 2026 Deborah Beckett. GPLv3 — see [LICENSE](LICENSE).

Use it in your own work, change it, build a practice on it. The one condition is the copyleft
bargain: if you distribute a modified version, it stays open under the same license. Nobody
gets to take it closed and sell it as their own. No warranty.

---

*Deborah Beckett — deborahbeckett99@gmail.com*
