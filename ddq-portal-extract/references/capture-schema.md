# capture.json schema

The extraction step assembles this JSON; `scripts/build_extract_xlsx.py` turns it
into the workbook. Keep field names exactly as below.

```json
{
  "meta": {
    "customer":    "<Customer>",
    "assessment":  "Vendor Service Risk Assessment v1.3",
    "record":      "<record-id>",
    "platform":    "Fusion Framework (FFQ) on Salesforce Experience Cloud",
    "portal_url":  "<portal URL>",
    "respondent":  "<name of the person who completed it>",
    "completion":  "100% (Business Resilience 7/7, Disaster Recovery 16/16)",
    "extracted":   "2026-07-14",
    "notes": [
      "Free-form strings; each becomes a bullet on the Summary sheet.",
      "Good things to note: attachment situation, comment-only questions, thin answers."
    ]
  },
  "questions": [
    {
      "section":     "Disaster Recovery",
      "id":          "DR-14",
      "parent":      "DR-1",
      "question":    "Are your production and backup environments geographically distinct...?",
      "answer":      "Yes",
      "options": [
        {"label": "Yes", "checked": true},
        {"label": "No",  "checked": false}
      ],
      "comment":     "Provided through our hosting provider, on <region> located servers...",
      "instruction": "",
      "attachment":  ""
    }
  ]
}
```

## Field notes

| field | meaning |
|---|---|
| `id` | Portal question number **or** stable control id. Prefer whichever is stable across page loads. If the display number re-sorts (e.g. SAFE ONE), use the control id. Otherwise a `SEC-N` scheme (`BR-1`, `DR-14`) is fine. |
| `parent` | The `id` this question hangs off, `""` if top-level. Preserves conditional nesting. |
| `answer` | The selected option's label. For free-text questions, put the typed value here. |
| `options` | Every option the portal offered, each `{label, checked}`. **Empty list `[]`** means a free-text question — the builder renders "(free-text response - no options)". Always include the full set even when only one is checked; that's the least-worst-fit signal. |
| `comment` | Comment / rationale field value. Read `.value`, not innerText. `""` if none. |
| `instruction` | The portal's own "please upload / provide X" text, `""` if none. Rows with an instruction but no attachment get flagged red in the workbook. |
| `attachment` | What was attached **and what it appears to be** (e.g. "COI_2026.pdf (certificate of insurance)"), `""` if none. The builder renders "- none -" when empty. |

The builder derives the Summary counters (upload asks, files attached, section
list, totals) from the questions array — you don't supply them.
