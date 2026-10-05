#!/usr/bin/env python3
"""Render a color-coded DDQ proposed-answers workbook from a proposal.json.

The JUDGMENT (matching each question to the Answer Bank, choosing tier /
confidence, writing the answer) is done by Claude and captured in proposal.json.
This script is the deterministic part: it scrubs internal handling instructions
out of the customer-facing text, applies the shading convention, and writes a
Proposed Answers + Summary workbook that a human can review quickly.

Layout: one row per question, whole-row shading, a Decision pick-list for the reviewer.

Usage:
    python3 build_proposed_xlsx.py proposal.json "Customer_DDQ_PROPOSED_YYYY-MM-DD.xlsx"

proposal.json schema:
{
  "meta": {
    "customer": "Acme Corp",
    "assessment": "Vendor Security Assessment 2026",
    "portal": "ExamplePortal (portal.example.com)",          # or "Spreadsheet", "Email", ...
    "due": "October 5, 2026",
    "answer_bank": "<Your Answer Bank> (live Drive copy, modified YYYY-MM-DD)",
    "drafted": "YYYY-MM-DD",
    "notes": [["Conditional questions", "..."], ["Bank fixes spotted", "..."]]
        # each note is [label, text]; a bare string is shown under the label "Note"
  },
  "questions": [
    {
      "section":    "1.0 Business Information",
      "id":         "1.9",
      "parent":     "",                 # the id this hangs off, "" if top-level
      "question":   "Are backups stored inside or outside the US?",
      "type":       "single-select" | "multi-select" | "free-text",
                    # legacy "radio" = single-select (multi-select if any option is checked:true)
      "options":    [{"label":"Inside","checked":true}, ...],   # [] for free-text
      "answer":     "Yes",              # single-select pick; "" for free-text / multi-select
      "free_text":  "Customer-facing text (verbatim from the bank, or synthesized).",
                    # legacy key "rationale" is accepted
      "free_text_required": "Required" | "Optional" | "N/A",
                    # Required = the portal compels free text with this answer (a No / N/A
                    # justification, "Other – specify", an explanation field it won't skip).
                    # Optional = the portal offers a comment box but doesn't need it.
                    # N/A = no comment box. Free-text questions are always N/A here, because
                    # the free text IS the answer. Legacy key "comment_need" is accepted;
                    # "Recommended" is treated as Required.
      "tier":       "1" | "2-3" | "synth",
      "confidence": 88,                 # int 0-100; REQUIRED for "synth", optional for "2-3",
                                        # never shown for tier "1"
      "source":     "1. General #7",    # bank tab + row; "Synthesized" for synth rows
      "note":       "short internal note (why this shade, what to verify, the gap)",
      "attachment": "SOC 2 Type II Report 2026.pdf"   # or ""
    }
  ]
}

Column G (Decision) is a pick-list – Accept / Accept w/ edits / Reject / Hold – left blank
for the reviewer. ddq-portal-fill enters only Accept and Accept w/ edits rows.

Column I (customer-facing free text) is filled only when the question is free text or
free_text_required is "Required". Otherwise the bank text is kept for reference in the
internal Rationale column, so the reviewer can add it as a comment if they want.

Shading (applied across the whole row):
  tier "1"     -> no fill        (primary verbatim match; a glance is enough)
  tier "2-3"   -> LIGHT YELLOW   (secondary source; validate)
  tier "synth" -> by confidence: >90 no fill, 80-90 LIGHT GRAY, <80 LIGHT PINK
"""
import json, re, sys
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

# --- scrub: internal handling instructions must never reach the customer ---
# These live in the Answer Bank comment fields on purpose (internal guidance);
# strip them from the customer-facing text, and report what was removed so
# nothing is cut silently. Keep legitimate answer language like "assessed on a
# case-by-case basis" — the tell is a routing/handling instruction aimed at us.
SCRUB_MARKERS = [
    "please escalate", "escalate to legal", "escalate to finance", "escalate to grc",
    "escalate to sales engineering", "handles approval", "approves case-by-case", "approved internally",
    "internal approval", "may be superseded", "trust package", "do not publish",
    "do not cite", "hold —", "blocked —", "needs input",
]
# Inline parentheticals that carry a routing/handling instruction (e.g.
# "(escalate to Legal)", "(approved internally, case-by-case)") — name-agnostic:
# match any (...) containing a handling verb, so notes get stripped regardless of
# who is named. Legitimate answer language like "(assessed on a case-by-case basis)"
# has no handling verb and is kept.
INLINE_HANDLING = re.compile(
    r"\s*\([^)]*\b(?:escalat|approv|handle[sd]?|internal|do not (?:publish|cite)"
    r"|superseded|hold|blocked|needs input)[^)]*\)", re.I)
def scrub(text):
    if not text:
        return text, []
    t = INLINE_HANDLING.sub("", text)
    parts = re.split(r"(?<=[.!?])\s+", t)
    kept, removed = [], []
    for p in parts:
        if any(m in p.lower() for m in SCRUB_MARKERS):
            removed.append(p.strip())
        else:
            kept.append(p)
    if t != text and not removed:
        removed.append("(inline internal-handling note in parentheses)")
    return " ".join(kept).strip(), removed

HEADERS = [  # (header, width) — matches the model worksheet
    ("Section", 15), ("#", 6), ("Hangs Off", 7), ("Question", 41),
    ("Short Response Options", 15), ("Proposed Short Response", 35), ("Decision", 16),
    ("Free Text Required?", 13), ("Proposed Free Text Response (Use Only When Required)", 54),
    ("Attachment", 20), ("Confidence", 13), ("Rationale (Internal Use Only)", 50),
    ("Source (Answer Bank)", 26),
]
FILLS = {
    "yellow": PatternFill("solid", fgColor="FFF2CC"),
    "gray":   PatternFill("solid", fgColor="E0E0E0"),
    "pink":   PatternFill("solid", fgColor="F8D7DA"),
}

def band(q):
    tier = q.get("tier", "synth")
    if tier == "1":
        return "white"
    if tier == "2-3":
        return "yellow"
    c = int(q.get("confidence") or 0)
    return "white" if c > 90 else ("gray" if c >= 80 else "pink")

def qtype(q):
    t = (q.get("type") or "").lower()
    opts = q.get("options", [])
    if t in ("free-text", "free text", "freetext", "text") or (not opts and t != "radio"):
        return "free-text"
    if t == "multi-select" or (t != "single-select" and sum(1 for o in opts if o.get("checked")) > 0
                               and not q.get("answer")):
        return "multi-select"
    return "single-select"

def ftr(q, kind):
    if kind == "free-text":
        return "N/A"
    v = str(q.get("free_text_required") or q.get("comment_need") or "").strip().lower()
    if v.startswith("req") or v.startswith("rec"):
        return "Required"
    if v.startswith("opt"):
        return "Optional"
    return "N/A"

def main(proposal_path, out_path):
    data = json.load(open(proposal_path))
    meta = data.get("meta", {})
    qs = data["questions"]

    wb = openpyxl.Workbook()
    thin = Side(style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(wrap_text=True, vertical="top")

    # ---- Proposed Answers sheet (first, so it opens on the work) ----
    pa = wb.active
    pa.title = "Proposed Answers"
    for j, (h, w) in enumerate(HEADERS, 1):
        c = pa.cell(1, j, h)
        c.fill = PatternFill("solid", fgColor="1F3864")
        c.font = Font(bold=True, color="FFFFFF")
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = border
        pa.column_dimensions[openpyxl.utils.get_column_letter(j)].width = w
    pa.freeze_panes = "A2"

    counts = {"white": 0, "yellow": 0, "gray": 0, "pink": 0}
    scrub_log = []
    for r, q in enumerate(qs, 2):
        kind = qtype(q)
        opts = q.get("options", [])
        need = ftr(q, kind)
        text, removed = scrub(q.get("free_text", q.get("rationale", "")) or "")
        if removed:
            scrub_log.append((q["id"], removed))

        if kind == "free-text":
            options_txt = "Free text"
            short = "[see proposed comment]"
        elif kind == "multi-select":
            options_txt = "Multi-select:\n" + "\n".join(f"• {o['label']}" for o in opts)
            picks = [o["label"] for o in opts if o.get("checked")]
            short = "\n".join(f"• {p}" for p in picks) or "(no selection – see rationale)"
        else:
            options_txt = "Single-select:\n" + "\n".join(f"[ ] {o['label']}" for o in opts)
            short = q.get("answer") or "(no selection – see rationale)"

        use_text = kind == "free-text" or need == "Required"
        rationale = q.get("note", "") or ""
        if text and not use_text:
            rationale = (rationale + "\n\n" if rationale else "") + f"Bank text (if you want a comment): {text}"

        tier = q.get("tier", "synth")
        conf = q.get("confidence") if tier != "1" else None
        source = q.get("source") or ("Synthesized" if tier == "synth" else "")

        vals = [q.get("section", ""), q["id"], q.get("parent", ""), q["question"],
                options_txt, short, None, need, text if use_text else "",
                q.get("attachment") or "- none -",
                int(conf) if conf not in (None, "") else None, rationale, source]
        b = band(q)
        counts[b] += 1
        for j, v in enumerate(vals, 1):
            c = pa.cell(r, j, v)
            c.alignment = wrap
            c.border = border
            if b != "white":
                c.fill = FILLS[b]

    # Decision pick-list on column G. The reviewer picks per row; ddq-portal-fill enters
    # only "Accept" and "Accept w/ edits" rows.
    if qs:
        dv = DataValidation(type="list", formula1='"Accept,Accept w/ edits,Reject,Hold"',
                            allow_blank=True)
        dv.error = "Pick Accept, Accept w/ edits, Reject or Hold."
        pa.add_data_validation(dv)
        dv.add(f"G2:G{len(qs) + 1}")

    # ---- Summary sheet ----
    sm = wb.create_sheet("Summary")
    sections = len({q.get("section", "") for q in qs if q.get("section")})
    qcount = f"{len(qs)} across {sections} sections" if sections else str(len(qs))
    rows = [
        ("Customer", meta.get("customer", "")),
        ("Assessment", meta.get("assessment", "")),
        ("Portal", meta.get("portal", "")),
        ("Due", meta.get("due", "")),
        ("Questions", qcount),
        ("Answer Bank", meta.get("answer_bank", "")),
        ("Prepared", f"{meta.get('drafted', '')} (DRAFT, for internal review; not customer-ready)"),
        (None, None),
        ("Shading key", None),
        ("White", "Tier 1 bank answer used verbatim, or synthesized with >90 confidence. A glance is enough."),
        ("Yellow", "From a secondary bank tab (2./3.). Validate."),
        ("Gray", "Synthesized, 80–90 confidence. Verify."),
        ("Pink", "Synthesized, <80 confidence, ambiguous, or placeholder. Needs your judgment."),
        (None, None),
        ("Counts", None),
        ("White", counts["white"]), ("Yellow", counts["yellow"]),
        ("Gray", counts["gray"]), ("Pink", counts["pink"]),
        ("Attachments proposed", sum(1 for q in qs if q.get("attachment"))),
    ]
    notes = meta.get("notes", [])
    if notes:
        rows += [(None, None), ("Notes", None)]
        for n in notes:
            rows.append(tuple(n) if isinstance(n, (list, tuple)) else ("Note", n))
    for i, (a, b_) in enumerate(rows, 1):
        ca = sm.cell(i, 1, a); cb = sm.cell(i, 2, b_)
        ca.alignment = wrap; cb.alignment = wrap
        if a and b_ is None:
            ca.font = Font(bold=True)
        if a in FILLS or a == "White":
            key = a.lower()
            if key in FILLS:
                ca.fill = FILLS[key]
    sm.column_dimensions["A"].width = 26
    sm.column_dimensions["B"].width = 110

    wb.save(out_path)
    print(f"wrote {out_path}")
    print(f"questions: {len(qs)} | white {counts['white']} | yellow {counts['yellow']} | "
          f"gray {counts['gray']} | pink {counts['pink']} | "
          f"attachments: {sum(1 for q in qs if q.get('attachment'))}")
    if scrub_log:
        print(f"\nSCRUBBED internal-only text from {len(scrub_log)} customer-facing answer(s):")
        for qid, rem in scrub_log:
            for frag in rem:
                print(f"   {qid}: removed -> {frag[:110]}")
    else:
        print("no internal-instruction text needed scrubbing")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_proposed_xlsx.py <proposal.json> <output.xlsx>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
