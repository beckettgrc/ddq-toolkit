#!/usr/bin/env python3
"""Render the live review page (an Artifact) from the same proposal.json that
build_proposed_xlsx.py uses.

The page is a spreadsheet-style grid with the workbook's columns. The reviewer picks a
Decision per row and edits the short response and free text in place; each change saves
to the artifact's database (collection "answers", one doc per question). ddq-portal-fill
reads those docs back with ArtifactData – no workbook round trip.

Usage:
    python3 build_review_artifact.py proposal.json "<Customer>_DDQ_REVIEW_<YYYY-MM-DD>.html"

It also writes each question's db key into proposal.json as `review_key`.

Then publish the HTML with the Artifact tool, declaring capabilities {"db": {}, "user": {}}
on the first publish, and record the returned URL in proposal.json as meta.review_url.

The scrub, shading and short/free-text rules are shared with build_proposed_xlsx.py, so
the page and the workbook always agree.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_proposed_xlsx import scrub, band, qtype, ftr  # noqa: E402

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_template.html")


def doc_key(qid, seen):
    """A stable, db-safe document id for a question id like '1.9' or 'Q22 (a)'."""
    k = re.sub(r"[^A-Za-z0-9_.\-]", "_", str(qid)).strip("._") or "q"
    base, n = k, 2
    while k in seen:
        k = f"{base}_{n}"; n += 1
    seen.add(k)
    return k


def main(proposal_path, out_path):
    data = json.load(open(proposal_path))
    meta = data.get("meta", {})
    rows, seen, scrub_log = [], set(), []
    for q in data["questions"]:
        kind = qtype(q)
        opts = [o["label"] for o in q.get("options", [])]
        need = ftr(q, kind)
        text, removed = scrub(q.get("free_text", q.get("rationale", "")) or "")
        if removed:
            scrub_log.append((q["id"], removed))
        if kind == "free-text":
            options_txt, short = "Free text", ""
        elif kind == "multi-select":
            options_txt = "Multi-select:\n" + "\n".join(f"• {o}" for o in opts)
            short = "\n".join(o["label"] for o in q.get("options", []) if o.get("checked"))
        else:
            options_txt = "Single-select:\n" + "\n".join(f"[ ] {o}" for o in opts)
            short = q.get("answer") or ""
        use_text = kind == "free-text" or need == "Required"
        rationale = q.get("note", "") or ""
        if text and not use_text:
            rationale = (rationale + "\n\n" if rationale else "") + f"Bank text (if you want a comment): {text}"
        tier = q.get("tier", "synth")
        rows.append({
            "key": doc_key(q["id"], seen), "id": str(q["id"]), "section": q.get("section", ""),
            "parent": q.get("parent", ""), "question": q["question"], "kind": kind,
            "options": opts, "options_txt": options_txt, "short": short, "need": need,
            "use_text": use_text, "free_text": text if use_text else "",
            "attachment": q.get("attachment") or "- none -",
            "confidence": q.get("confidence") if tier != "1" else "",
            "rationale": rationale,
            "source": q.get("source") or ("Synthesized" if tier == "synth" else ""),
            "band": band(q),
        })
    # Write each row's db key back into proposal.json so ddq-portal-fill can join the saved
    # decisions to questions without recomputing anything.
    for q, r in zip(data["questions"], rows):
        q["review_key"] = r["key"]
    json.dump(data, open(proposal_path, "w"), indent=1, ensure_ascii=False)
    payload = {"meta": {k: meta.get(k, "") for k in ("customer", "assessment", "portal", "due", "drafted")},
               "rows": rows}
    payload["meta"]["notes"] = [list(n) if isinstance(n, (list, tuple)) else ["Note", n]
                                for n in meta.get("notes", [])]
    title = f"{meta.get('customer', 'DDQ')} DDQ Review"
    html = open(TEMPLATE).read()
    html = html.replace("__TITLE__", title.replace("<", "&lt;"))
    html = html.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    open(out_path, "w").write(html)
    counts = {b: sum(1 for r in rows if r["band"] == b) for b in ("white", "yellow", "gray", "pink")}
    print(f"wrote {out_path}  ({len(rows)} questions | " +
          " | ".join(f"{b} {n}" for b, n in counts.items()) + ")")
    for qid, rem in scrub_log:
        for frag in rem:
            print(f"   SCRUBBED {qid}: {frag[:110]}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_review_artifact.py <proposal.json> <output.html>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
