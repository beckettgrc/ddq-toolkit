# Sandbox questionnaire

A fictional vendor security questionnaire for trying the toolkit without a live
customer. Pair it with `Stark Industries - Answer Bank.xlsx` — the ten questions
below are chosen to exercise every path in `ddq-propose-answers`, so a full run
should produce all four shades in the review workbook rather than a wall of white.

Two ways to use it:

- **Spreadsheet path** — paste the questions into a sheet and run the chain from
  `ddq-propose-answers`. No portal, no browser, works immediately.
- **Portal path** — run against the [live demo form](https://docs.google.com/forms/d/e/1FAIpQLScTRmgNn-8FRmsNe4EzonBC2SSwYvUUN0oUnZzoTLD41V-dsg/viewform) to exercise
  `ddq-portal-extract` and `ddq-portal-fill` end to end. Stop before submitting; responses go
  to the form owner. This file is here so you can rebuild your own — keep it to three pages so
  the extractor has pagination to walk.

Keep the three sections — they make the form paginate, which is what the extractor
has to walk. The annotations say what each question is *for*; strip them before
loading.

---

## Section 1 — Security controls

1. Is multi-factor authentication required for all employees and contractors
   accessing production systems? *(Yes / No)*
   *→ Verbatim from the bank. Expect white.*

2. Do you encrypt data in transit and at rest? *(Yes / No)*
   *→ Verbatim. White.*

3. Do you have a documented incident response plan? *(Yes / No)*
   *→ Verbatim. White.*

## Section 2 — Data handling

4. **Do any of your personnel have access to our data?** *(Yes / No + comment)*
   *→ The judgment question. "No" is the tempting answer and is almost always false;
   the honest answer is a small number of staff, least-privilege, logged, for support
   and incident response. Neither the question nor its neighbors pin down which
   personnel or under what circumstances. Expect pink, with both readings presented
   rather than a guess.*

5. Do you support customer-managed encryption keys (BYOK)? *(Yes / No)*
   *→ An honest **No**, and it lives on the Tier 2 sheet — so expect yellow. A demo where
   every answer is "Yes" proves nothing about whether the tool will decline.*

6. How long is customer data retained after contract termination? *(Free text)*
   *→ No direct bank entry. Backups are covered, retention windows are not. Expect a
   synthesized answer at reduced confidence — gray.*

## Section 3 — Assurance and governance

7. Do you maintain an ISO 27001 certified ISMS? *(Yes / No)*
   *→ Tier 2 sheet. Expect yellow.*

8. Please attach your most recent SOC 2 Type II report. *(File upload)*
   *→ An attachment ask, not an answerable question. Should resolve against the
   `Artifacts` tab and surface as a document for the human to upload — the toolkit
   names the file but cannot attach it.*

9. Describe your governance of AI and machine learning systems, including whether
   customer data is used to train models. *(Free text)*
   *→ Genuine gap — the bank has nothing on AI. Expect pink with a note that a human
   must draft it. Realistic: this is on most 2026 questionnaires and most answer banks
   haven't caught up.*

10. Describe your anti-money-laundering and counter-terrorist-financing program,
    including KYC procedures and sanctions screening. *(Free text)*
    *→ Should come back a confident **"Not applicable — Stark Industries is a software
    provider, not a financial institution."** Gray, not pink. Tests that the tool
    recognizes a clean N/A instead of flagging it as uncertainty.*

---

## What a good run looks like

- **White** — questions 1, 2, 3 straight from the bank, plus question 8's high-confidence
  cover line; skim only
- **Gray** — questions 6 and 10: a reduced-confidence synthesis and a confident N/A
- **Yellow** — questions 5 and 7, Tier 2 material worth a human's eyes
- **Pink** — questions 4 and 9
- **Attachment named, not attached** — question 8

`sample-review-workbook.xlsx` in this folder is a real run of `ddq-propose-answers` over
these ten questions, if you want to see the output without running anything.

If a run comes back all white, the bank is being matched too loosely — that is the
failure mode this questionnaire exists to catch. If questions 4 and 9 come back
answered with confidence, the guardrails in
`ddq-propose-answers/references/guardrails.md` are not firing.
