# Answer-crafting guardrails

These are the judgment rules that keep proposed DDQ answers accurate and safe.
They exist because a wrong or over-claimed answer goes to an enterprise customer
under contract — the cost of a bad answer is far higher than the cost of leaving
a row pink for human review. When in doubt, lower the confidence and flag it.

> **This is a template.** The *patterns* below are reusable, but every fact is
> org-specific. Replace `<your-org>` and every `<…>` placeholder with your own
> details, and treat your Answer Bank — not this file — as the source of truth for
> assurance posture, subprocessors, registration IDs, and data-center facts. Do not
> ship this file with another company's specifics pasted in.

## Frame ambiguity — when the answer depends on what the customer *means*

Most infosec DDQ questions are secretly of the form "at trust boundary **B**, is
control **C** enforced for actor **A**?" The sentence usually pins down C (MFA,
encryption, logging, spoofing protection) but leaves **A** (whose people) and **B**
(whose systems) floating — and the true answer changes with them. A keyword match can
find a bank entry on the same *topic* that answers the wrong *frame*, and shading it
white/yellow launders a wrong-scope answer into something that looks reviewed. That's
the failure to guard against.

Two worked examples:

- **"How do you protect against email spoofing (SPF/DKIM/DMARC)?"** Your bank's only
  email entries may be about **your corporate** email (staff inboxes). But in a vendor
  DDQ this is often asking about the **service delivered to the customer** — email sent
  from the site/domain you host for them — where the honest answer can be the opposite
  ("`<your-org>` is a `<what you are>`, not an email provider for your domain; SPF/DKIM/DMARC
  are DNS records you configure at your own provider"). Same topic, opposite scope.
- **"Is MFA required?"** has at least four readings: your staff → your internal systems;
  your staff → the customer's environment; the customer's staff → the hosted service;
  the customer's end-users → their site. Four different controls, four different true
  answers.

How to handle it:

1. **Read the neighborhood, not just the question.** A questionnaire is a list of the
   customer's *worries*, and a section is often one worry asked several ways. The adjacent
   questions usually pin the frame (5–6 spoofing/phishing questions in a row = they mean
   "protect *us* from phishing through your service"). Use the extract's full question list,
   not the single row.
2. **If the frame is resolved by context, just answer it** — don't flag. Over-flagging is a
   real cost; it makes review slow enough that people stop trusting the shading.
3. **Flag (→ pink) only when all three hold:** the answer *materially* changes across
   readings, **and** neither the question nor its neighbors resolve which is meant, **and** a
   wrong pick would visibly reflect back on you (the "why did you say xyz?" a customer circles
   back on). Below that bar, answer normally.
4. **When you do flag, present the readings, not a guess.** Put the candidate frames in the
   rationale — "(a) if this means *our* systems → …; (b) if it means *your* hosted
   environment → …" — and make the reader's job "pick the reading," which is fast, rather
   than re-deriving it. Lead the `note` with `AMBIGUOUS FRAME:`.

The cost model here is deliberately not "prevent catastrophe" — a mis-framed answer usually
just draws a clarifying reply. It's that these ship under a named owner; the bar is avoiding
the *avoidable, traceable* embarrassment, not chasing every theoretical nuance.

## Assurance — never over-claim

Your assurance posture is specific and easy to over-state. Encode *your* exact posture
as placeholders and hold the line on them:

- State only the certifications/reports you **actually hold today**. If a report is in
  progress, the only correct forward framing is "anticipated `<date>`" — never present an
  in-progress or planned attestation as issued.
- Distinguish the **product/subsidiary** from the **parent company**: a report scoped to one
  may not cover the other. Never attribute a parent-company attestation to the product (or
  vice-versa) if it doesn't apply.
- A certification held by an **upstream provider** (e.g. your data-center or cloud provider's
  ISO 27001) is *theirs*, not yours — say so precisely rather than implying it's your own.
- If you are **not** certified against a standard (PCI DSS, etc.), say so plainly rather than
  implying coverage.
- Put a **review-by date** on this section. If assurance status changes (a report issues, a
  window closes), stale guidance here becomes a source of over-claims — flag rather than
  assume.

## Subprocessor ≠ subcontractor

These terms are routinely conflated and the distinction matters for accuracy. Your
**subprocessors** are the third parties that process customer data on your behalf (publish
the authoritative list at `<your-subprocessor-URL>`). "Subcontractor" is often used loosely
by customers to mean something else — sometimes personnel who deliver the service, sometimes
fourth-party vendors. Default to the customer's own term in your answer, but if you actually
mean subprocessors, say so — mismatched terminology causes count discrepancies across a
customer's assessments (a real, recurring audit-trail problem). Read the section's other
questions to tell which sense ("people" vs "vendors") is meant, and answer in that sense.

## Honor the Answer Bank's own hold flags

Your Answer Bank comment fields may carry status flags. Treat these as blocking:
- **HOLD / "do not publish as a standalone row yet"** — don't publish that text; if the
  real ask is to attach a report, propose the attachment instead.
- **BLOCKED / "do not publish yet"** — do not use the figures (e.g., remediation-SLA numbers
  pending a final policy). State that the *program exists* without the specific numbers, and
  leave it lower-confidence.
- **NEEDS INPUT / "confirm before citing"** — surface it to the human; don't guess.
- Any **escalation / secondary-source** tab is follow-up / compensating-controls material.
  Do NOT pull it into a first-pass answer — it's for when a customer pushes back after the
  simpler answer. Keep first-pass answers to the minimal sufficient response.

## Strip internal handling notes from customer-facing text

Answer Bank comments often mix the customer answer with internal instructions
("escalate to Legal/Finance", "approved internally, case-by-case", roadmap asides). These are
intentional internal guidance and stay in the bank — but they must never reach the
customer. The `build_proposed_xlsx.py` script scrubs them from the proposed answer and
prints what it removed. Legitimate answer language like "assessed on a case-by-case
basis" is NOT an internal instruction — the tell is a routing/handling instruction
aimed at your team.

## DDQ voice and framing

- **Don't use "available on request" / "through your account team" as a friction layer.**
  If the deliverable can be provided, frame it as provided/attached. Reserve
  "available under NDA" for genuinely NDA-gated docs (audit reports, pen-test summary,
  policies) — that gating is real and correct.
- **"Where are services delivered / locations"** → answer with the actual origin
  **data centers / regions** you run in, plus your workforce model (e.g. distributed /
  remote-first with no central office, if true). Don't lead with a registered HQ address if
  nobody works from it.
- **Incident / breach notification timeline** → for international / GDPR-oriented customers,
  give your specific commitment (e.g. "without undue delay, target within 72 hours, aligned
  with GDPR breach-notification expectations"). Don't retreat to a bare "without undue delay."
  Any short *internal* reporting window is internal, not the customer-notification timeline.
- **Financial-institution-shaped questions** that don't map to your service — AML/CFT policy
  & training, KYC, PEPs, sanctions screening, fraud metrics, three-lines-of-defense — are
  usually a clean, confident **"Not applicable — `<your-org>` is a `<what you are>`, not a
  financial institution."** These are gray (confident N/A), not pink.
- **Financials:** if you're privately held and don't disclose audited statements, say so; note
  any compensating control (e.g. a CPA attestation letter) but keep the *approval* step
  internal — don't put it in the customer answer.
- **Don't conflate differently-scoped questions.** "Major cybersecurity incident affecting us"
  and "any data breach or loss" are different thresholds; a narrow "No" alongside a broad
  disclosure is consistent, not contradictory. Answer each to its own scope.
- **Never name a colleague in a customer-facing answer** in a way that characterizes their
  behavior or judgment. Naming execs when the question asks for management contacts is fine.

## Org-specific facts to fill in (from YOUR answer bank, which is source of truth)

Replace these placeholders with your own details before using the toolkit; do not carry over
another organization's values:

- Legal entity / registration: `<legal entity name>`, `<tax ID>`, `<registration number>`,
  `<DUNS>`; ultimate parent `<parent, jurisdiction>`; founded `<year>`.
- Subprocessors: `<list>` (published at `<your-subprocessor-URL>`).
- Infrastructure: `<data-center / cloud providers>`; origin regions `<regions>`; backups
  `<how/where>`.
- Assurance: `<what you hold today>`; in progress `<what, anticipated when>`.
