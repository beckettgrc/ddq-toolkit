# Platform notes

Per-platform mechanics for portal extraction. Read the section matching the
portal you're on before extracting. When you work a platform not listed here,
add a section — the whole point is that the second extraction of a platform is
faster than the first.

## Table of contents

- [Fusion Framework (FFQ) on Salesforce Experience Cloud](#fusion-framework-ffq-on-salesforce-experience-cloud)
- [SAFE ONE (SAFE TPRM)](#safe-one-safe-tprm)
- [Onspring](#onspring)
- [OneTrust (Assessment Automation / Trust Intelligence)](#onetrust-assessment-automation--trust-intelligence)
- [UpGuard (Trust Exchange / Cyber Risk)](#upguard-trust-exchange--cyber-risk)
- [Venminder (Vendor questionnaire-response portal)](#venminder-vendor-questionnaire-response-portal)
- [Gartner BuySmart (vendor evaluation questionnaire)](#gartner-buysmart-vendor-evaluation-questionnaire)
- [Generic discovery (unknown platform)](#generic-discovery-unknown-platform)

---

## Fusion Framework (FFQ) on Salesforce Experience Cloud

Seen on: a vendor service risk assessment. Salesforce Experience Cloud community
site, Lightning Web Components.

**Question card:** `article.FFQResponseUI_QuestionResponse`.
- Question text: `.slds-card__header h2 span.slds-text-heading_small`.
- Options: `lightning-radio-group input[type=radio]`; the label text is the
  sibling `span[part=label]` (or `.slds-form-element__label`) inside the enclosing
  `.slds-radio`. Inputs are `disabled` in the read-only view but `.checked` still
  marks the submitted answer.
- Comment: a `<textarea>` inside the card — its `.value` holds the comment
  (visible ones, but read `.value` not innerText).
- Some questions are **free-text only** (no radio group) — options come back empty
  and the answer is the comment/textarea value.

**Nesting:** parent questions contain their conditional sub-questions as nested
`article.FFQResponseUI_QuestionResponse` elements. Scope every collection with
`el.closest('article.FFQResponseUI_QuestionResponse') === card`, and derive the
parent id from `card.parentElement.closest('article.FFQResponseUI_QuestionResponse')`.
Without scoping, a parent double-counts all its children's radios.

**Pagination:** section-based. The left nav (`navigation[aria-label="Sections"]`)
lists sections with completion counts like `7/7`. Only the selected section's
cards are in the DOM. Click each section link, screenshot/confirm it rendered,
run the extractor, then move on. Reconcile your row count per section against the
`N/N` counts.

**Attachments:** this instance had none — pure radio + comment, no upload
fields. Confirm per instance with the global attachment sweep; don't assume.

**Extractor (per loaded section), proven shape:**

```js
(function(){
  function tc(s){return (s||'').replace(/\s+/g,' ').trim();}
  const SEL='article.FFQResponseUI_QuestionResponse';
  const owned=(el,card)=>el.closest(SEL)===card;
  const cards=[...document.querySelectorAll(SEL)];
  return JSON.stringify(cards.map(card=>{
    const h=card.querySelector('.slds-card__header h2 span.slds-text-heading_small')||card.querySelector('.slds-card__header h2');
    const radios=[...card.querySelectorAll('lightning-radio-group input[type=radio]')].filter(r=>owned(r,card));
    const options=radios.map(r=>{
      const l=r.closest('.slds-radio')?.querySelector('span[part=label], .slds-form-element__label');
      return {label:tc(l&&l.textContent), checked:r.checked};
    });
    const comments=[...card.querySelectorAll('textarea')].filter(t=>owned(t,card)).map(t=>tc(t.value)).filter(Boolean);
    const parent=card.parentElement.closest(SEL);
    const parentQ=parent?tc((parent.querySelector('.slds-card__header h2 span.slds-text-heading_small')||{}).textContent):'';
    return {
      question:tc(h&&h.textContent),
      isSub:!!parent, parentQ:parentQ.slice(0,55),
      options, selected:options.filter(o=>o.checked).map(o=>o.label),
      comment:comments[0]||''
    };
  }),null,1);
})();
```

---

## SAFE ONE (SAFE TPRM)

Seen on: a vendor DDQ. This platform is why the
"read the DOM, not the screenshot" and "human scrolls" rules exist.

- **Rationale is a hidden `<textarea>`** (id pattern `SB CCQ NNN-rationale`); the
  text is in `.value`, invisible to innerText/CSV scrapes. This defeated an
  earlier Claude-in-Chrome attempt.
- **The `/assessment?…` API is AWS SigV4-signed** — a plain `fetch` returns 403 and
  can't be replayed. Capture responses by installing a `fetch`/`XHR` **response
  interceptor before the app fetches**, keyed by `controlId`.
- **Virtualized infinite-scroll (pagelen≈10).** Only *real* human scroll reliably
  triggers page fetches; programmatic scroll stalls (~row 130) and can corrupt the
  height estimate. Do **not** enlarge the viewport — it broke the scroll/screenshot
  pipeline. Have the human scroll top-to-bottom.
- **Stable key is `controlId`** (`SB CCQ NNN`), not the SAFE ONE display number,
  which re-sorts on every page load.
- **Working extraction:** arm the interceptor → human scrolls top-to-bottom →
  merge interceptor data (answer/rationale) with DOM extraction; instructions come
  from the "Per guidelines…" span (case-insensitive), associated by DOM order;
  build a CSV Blob in-page and trigger a download for byte-exact fidelity.
- Each question card carries `id="SB CCQ NNN"`; options are No / Yes / Not
  Applicable (selected one has an SVG checkmark).


---

## Onspring

Seen on: an enterprise customer's "Corporate
Sustainability Questionnaire", third party `<your-org>`. Host
Per-tenant subdomain. jQuery + Kendo UI +
Onspring's own `onx-selector` widgets. The page title reads "Onspring - Edit
Content".

**Landing layout.** The record opens on a tab with the questionnaire. Questions
live in **read-only report grids** (one grid per section — e.g. "Questions" and
"Additional Information"). The grid columns are `Number | Question | Help Text |
Previous Answer Provided | Answer | Comment | Attachment`. Crucially, in the grid
view the **Answer/Comment/Attachment cells are empty and the answer OPTIONS are
not shown** — the read-only grid only ever shows a *submitted* answer's text, never
the option set. To get options you must open each question's editor.

**Question + help text are fully available without opening editors** — grab them
from `get_page_text` or the grid. Only the option list requires the editor.

**Per-question editor = jQuery UI dialog (`.ui-dialog`, NOT a Kendo window).**
Each grid row has a pencil button `button.quick-edit`; `.click()` opens the
dialog. The dialog has `Previous | Next | Save | Cancel`. **`Next` navigates
without saving** (Save is a separate button), so walking with Next is read-only —
but the re-render is **async**, so read on the *following* call, not the same one.
`Next` is disabled on the last question of a section (use that as the end signal).
Close with the `Cancel` button. `Save and Next` is the answer-and-advance control —
don't use it for extraction.

**Reading options (the whole point).** Two widget shapes seen:
- **Single-select** — a Kendo DropDownList (`kendoReferenceDropDownList`). Options
  are in the widget's `dataSource`, not the DOM until opened. Read them without
  opening: walk the visible dialog's elements, find the one whose jQuery `.data()`
  has a `kendo*` key with a `.dataSource` + `.value()` function, and map
  `dataSource.data().map(x => x.text)`.
- **Multi-select** — an `onx-selector` wrapping a real `<select
  data-field-type="selectorList">`. The Kendo scan does **not** find this one; read
  `select.options` directly (`{text, value, selected}`). `data-options` JSON holds
  `filteredValues` (the value ids).

Option labels can carry a **scoring suffix** the respondent actually sees, e.g.
`"Yes - 10"`, `"No - 0"`. Capture it — the weighting varies by question and is real
signal.

**Free-text questions** present as a single-option dropdown whose only option is a
placeholder pointing the respondent at the comment field; the real answer goes in
the Comment `<textarea>`.

**Attachments.** Every editor exposes a generic drag-and-drop upload zone
regardless of whether a file is wanted; "No files have been attached" text means
empty. The genuine "please upload X" asks live in the **Help Text**, so treat Help
Text as the `instruction` field — but note not every instruction is a file ask
(some say "name them" or are multi-selects). The build script counts any non-empty
`instruction` as a "file upload" ask, so if you want that Summary counter to mean
*uploads only*, reserve `instruction` for true upload asks and state the real
breakdown in the meta notes.

**Proven read (run with a dialog open; reads current question's options):**

```js
(function(){
  const jq=window.jQuery, win=jq('.ui-dialog:visible').last();
  if(!win.length) return {err:'no dialog'};
  let answer=null;
  win.find('*').each(function(){                       // single-select (Kendo)
    const d=jq(this).data(); if(!d) return;
    for(const k in d){ const w=d[k];
      if(/^kendo/i.test(k)&&w&&w.dataSource&&typeof w.value==='function'){
        let o=[]; try{o=Array.from(w.dataSource.data()).map(x=>x.text).filter(x=>typeof x==='string');}catch(e){}
        if(o.length&&o.length<=25&&o.every(t=>t.length<80)) answer={type:'dropdown',options:o,selected:String(w.value())};
      }}});
  if(!answer){                                         // multi-select (onx-selector)
    const sel=win.find('select[data-field-type="selectorList"]')[0];
    if(sel) answer={type:'multiselect',options:Array.from(sel.options).map(o=>o.text.trim()),
                    selected:Array.from(sel.options).filter(o=>o.selected).map(o=>o.text.trim())};
  }
  const tas=win.find('textarea').map((i,e)=>e.value).get();
  return {title:win.find('.ui-dialog-title').first().text().trim(),
          answer, comment:tas, attach:/No files have been attached/i.test(win.text())?'- none -':'FILE PRESENT'};
})();
```

Walk pattern: read current → click `Next` → (next call) read → … until `Next`
disabled; `Cancel` to close; repeat for each section grid. The multi-select
"Additional Information" section is a separate grid with its own `quick-edit`.

**Addendum — a tiered cyber-security questionnaire on the same tenant.** Different
assessment, same platform. Things the Sustainability
notes above don't cover:

- **Tier scoping.** This questionnaire was scoped to a low tier. The DOM holds ~35
  section grids (access control, network security, encryption, HR security, …) but
  most show `0 of N Questions Complete` with **0 questions** — they're template
  sections not activated for this vendor/tier. Only the preliminary section and the
  tier's security section were populated, matching the header count. Orient by the
  per-grid completion counters; don't extract the empty template grids.
- **The Kendo `.data()` scan can come up empty.** On these `quick-edit` dialogs the
  `jq(el).data()` kendo-key walk found no dropdown widget (returned `[]`). The
  reliable fallback was the **DOM listbox**: each dialog's List Answer dropdown has
  an input with `aria-owns="Field-XXXX_listbox"`, and the `<ul id="…_listbox">` is
  populated on dialog open. Read `ul li` text.
- **Duplicate-id trap (important).** Re-opening dialogs leaves **orphan `<ul>`
  elements all sharing the same `id`**, so `document.getElementById(id)` returns the
  *stale first* one → wrong options for the question. Fix: before opening each
  dialog, purge orphans — `document.querySelectorAll('ul[id$="_listbox"]').forEach(u=>(u.closest('.k-animation-container')||u).remove())`
  and Cancel any open dialog — then read the single remaining listbox (or just take
  the **last** matching `ul`). Cleaner than the Next-walk here: purge → open row →
  (next call) read the lone listbox → repeat. Key questions by the row/`recordId` order, which increments contiguously, so you
  don't need to parse dialog text.
- **Lazy / empty picklists.** Some single-selects (Onspring "reference dropdown")
  don't populate the listbox `ul` until the dropdown is clicked open. And a **truly
  empty** picklist (only "Select a value") = free-text question answered in
  Respondent Comments.
- **No scoring suffix** on this assessment (options were plain `Yes` / `No` / `N/A`,
  no `- 10`). The scoring suffix is questionnaire-specific, not a tenant constant.
- **Help-text vs. dropdown mismatch** happens — help text can enumerate more values
  than the dropdown actually offers. Trust the dropdown for `options`; keep the help
  text as context.

**Addendum — a conditionally triggered section.** Answering the
preliminary AI/ML question `PRE-1` "Yes" (e.g. `a) Artificial Intelligence
(AI)`) **spawns a whole new "Artificial Intelligence Security"
section** and bumps the header total. So a section's very existence can
depend on a prior answer — **re-`get_page_text` after any answer that could
branch**, and reconcile the per-section completion counters again. On this
section the **Kendo `dataSource` scan worked** (unlike the earlier dialogs where
it came up empty), so try Kendo first, listbox fallback second. Free-text
questions present as an empty picklist + a required Respondent Comments rich-text
box; several questions worded "choose all that apply" / "list all ways (a-e)" are
actually **single-select** dropdowns (same trap as `PRE-1` and DLP). recordIds increment
contiguously with the preceding block.

**Addendum — a risk-and-compliance questionnaire in a different app on the same
tenant.** Different answer widget. The Answer field is a
**lazy Onspring "reference" dropdown**: the backing `<select>` (`Field-NNNN`)
stays empty (`.options == []`), the jQuery `.data()` keys are
`onxGridForReferencesHelper` + `val` (no readable `.dataSource`), and **no
`ul[id$="_listbox"]` is created until the dropdown is opened**. Programmatic
clicks on the `span.option-label` did **not** open it. Reliable method: open each
dialog, **click the Answer field with the computer tool, then screenshot** the
options (they render as `Select Answer / No / Yes` rows; DOM reads of the popup
returned nothing). Options were `No/Yes` for narrative questions and
`N/A/No/Yes` for insurance, with **per-question customised N/A text** rather than a
bare "N/A" — capture it verbatim, the wording is real signal. Same pencil→`quick-edit`→jQuery-dialog + Cancel-to-close mechanics;
the dialog title / recordId is the PQ Question ID prefix (e.g. "Insurance"). The
Comment field here is a single-line text input, not a rich-text textarea.

---

## OneTrust (Assessment Automation / Trust Intelligence)

Seen on: an enterprise customer's vendor intake assessment (cybersecurity TPRM +
privacy), third party `<your-org>`. Angular app; all the
assessment components are prefixed `aa-` (assessment automation). The vendor
answers in a read/write portal (respondent view), so submitted answers, options,
comments, and attachments are all live in the DOM once a section is expanded.

**Layout = section accordion + detail pane.** The left side is an accordion of
sections (`.aa-section-list__staged-delivery--section`, each wrapping an
`ot-collapse`). Section header buttons are `button.ot-collapse__header-btn`; the
active one carries `.ot-collapse__header--active`. **Only the expanded section's
questions are rendered** (in a separate `aa-detail` pane) — this is
section-paginated, so expand each section, extract, move on. The first "section"
(Welcome) is intro text with **0 questions**; don't count it. Header shows overall
progress like `34/35` / `97%`.

**Question card:** `aa-assessment-detail-question` (one per question).
- Number: `.aa-question__number-text` (e.g. `3.1`, `4.2`, `5.11` — display numbers
  skip, that's normal, they're stable enough to use as `id`).
- Question text: `.aa-question__name` (full, untruncated).
- Extra description / instruction block: `.aa-question__description` (the
  "If you select yes… provide documentation", option enumerations, and the
  boilerplate "Assessments with blank fields will not be processed").
- Required marker: `.aa-question__required`.

**Answer widgets (three shapes, all captured by one extractor):**
- **Multi-select** — `aa-multichoice-buttons`; each option is a
  `button.vt-button.full-width`. **Selected = class `vt-button--primary`**
  (green); unselected = `vt-button--secondary`. Multichoice selected buttons also
  carry `aria-checked="true"`, but `vt-button--primary` is the universal rule.
- **Single-select (Yes/No etc.)** — same `button.vt-button.full-width` but NOT
  inside `aa-multichoice-buttons`, and `aria-checked` is null; rely on
  `vt-button--primary` for selection. A blank single-select (no button primary) =
  **unanswered** (this is how the 1 missing answer in 34/35 showed up).
- **Free-text** — `aa-rich-text-editor .ql-editor`; read `.innerText`. Some
  free-text questions also expose a lone `Not applicable` option button alongside
  the editor (an N/A escape) — keep it in `options` for the least-worst signal, but
  the real answer is the editor text.

Scope option/comment/attachment reads to the card. The footer config buttons
(attachment/comment) are also `vt-button` but lack `full-width`, so filtering on
`button.vt-button.full-width` cleanly excludes them.

**Counts + full question text for free** — the per-question footer has two buttons
whose `aria-label` reads `"Attachment for [full question text]. N attachments
available…"` and `"Comments for [full question text]. N Comments available…"`.
Regex `(\d+)\s+attachments? available` / `(\d+)\s+Comments? available` gives exact
per-question counts without opening anything.

**Comments.** The header comment badge (`3`) counts commented *questions*, not
messages (one question's thread had 2 messages → 4 messages but badge said 3).
Click any question's Comments footer button to open the drawer; the **right panel
lists every thread across the assessment** (question #, author, date, text), which
is the fastest way to read them all. Customer-side assessor names appear here
(e.g. `<assessor name>`); our side shows as the `@<your-org>.com` email. The DOM
splits author/date/text across nodes, so a screenshot of the drawer is often the
cleanest capture.

**Attachments.** Header paperclip button (`"9 attachments available"`) opens an
Attachments drawer listing **all files with `Question N.N`, timestamp, and full
filename** — grab filenames from anchor text or the `Download Attachment <name>` /
`Delete Attachment <name>` aria-labels (strip the `Download/Delete Attachment`
prefix). Far faster than per-card. Map back to questions by the `Question N.N`
label.

**Nesting.** No DOM nesting — sub-questions are siblings. Infer `parent` from the
question wording: "Other - (please describe):" free-texts hang off the immediately
preceding multi where "Other" was checked; "If yes, …" questions hang off the
preceding Yes/No.

**Navigation is read-only-safe.** Expanding sections (`.ot-collapse__header-btn`
`.click()`) and opening comment/attachment drawers don't touch answers. Don't
click the option buttons or Submit.

**Extractor (per expanded section):**

```js
(function(){
  function tc(s){return (s||'').replace(/\s+/g,' ').trim();}
  const cards=[...document.querySelectorAll('aa-assessment-detail-question')];
  return JSON.stringify(cards.map(card=>{
    const num=tc((card.querySelector('.aa-question__number-text')||{}).textContent);
    const question=tc((card.querySelector('.aa-question__name')||{}).textContent);
    const optBtns=[...card.querySelectorAll('button.vt-button.full-width')];
    const options=optBtns.map(b=>({label:tc(b.textContent), checked:b.classList.contains('vt-button--primary')}));
    const rte=card.querySelector('aa-rich-text-editor .ql-editor');
    const freetext=rte?tc(rte.innerText):'';
    const desc=[...card.querySelectorAll('.aa-question__description')].map(d=>tc(d.innerText)).filter(Boolean).join(' | ');
    let att=0, com=0;
    card.querySelectorAll('button').forEach(b=>{const a=b.getAttribute('aria-label')||'';let m;
      if((m=a.match(/(\d+)\s+attachments? available/i)))att=+m[1];
      if((m=a.match(/(\d+)\s+Comments? available/i)))com=+m[1];});
    const type=options.length?(card.querySelector('aa-multichoice-buttons')?'multi':'single'):(rte?'freetext':'other');
    return {num,question,type,options,selected:options.filter(o=>o.checked).map(o=>o.label),freetext,desc,attCount:att,comCount:com};
  }),null,1);
})();
```

Expand section (`btns=[...document.querySelectorAll('button.ot-collapse__header-btn')]; btns.find(b=>tc(b.textContent).includes('<Section name>')).click();`),
screenshot to confirm render (async), then run the extractor. Reconcile row count
per section against the header `N/N`.

---

## UpGuard (Trust Exchange / Cyber Risk)

Seen on: an enterprise customer's TPRM "CIS Critical Security Controls v8.1 - Implementation
Group 3", third party `<your-org>`. React SPA. This is the *vendor answering* view (read/write), so all submitted
answers, options, uploads, and risk narratives are live in the DOM.

**Landing gate.** The questionnaire opens on an intro screen ("`<Customer>` has
invited you to answer a questionnaire") with a "Get AI-generated answers" button -
**do not click that** (it would generate/modify answers). Enter the questionnaire
body by scrolling the main pane down (the "Continue answering without extra help"
link just scrolls) or clicking a question in the left nav. The header shows overall
progress ("231 of 231 answered", a completion %), and the Overview tab (reachable
via the app's questionnaire list) shows metadata: status (e.g. "Submitted / In
remediation"), sent-by, due date, sent-to recipients - grab meta there.

**Whole questionnaire renders at once - no pagination/virtualization.** All nodes
are in the DOM after entering; you extract in one pass. (231-question instance had
all cards present.) Left nav is a tree of `.sidebar-item[data-node-id]` (sections +
questions, `.answered` class on each) - a useful completeness index, but the main
pane is where answers/options live.

**Question card:** `.question-answer-node[data-node-id]` in `#main-content-area-inner`.
Four node-type classes (read the class to branch):
- `section-node` - a CIS control header (icon `cr-icon-q-builder-flag`). `.display-id`
  = control number, `.node-name` = control name. **Not a question** - use it to set
  the current section; skip it.
- `select-node` - a radio/checkbox question (icon `cr-icon-q-builder-radio` single /
  `cr-icon-q-builder-checkbox` multi). Options are `.answer-option` (`.id` = letter
  a/b/c, `.text` = label). **Selected = the `.answer-option` has class `selected`**
  (also an inner `.color-checkbox-inner.checked` with `aria-checked="true"`). A
  select-node with no `.selected` = unanswered.
- `upload-node` - a "please upload X" question (icon `cr-icon-q-builder-attachment`).
  Files in `.current-files-uploaded .file-answer .filename` (can be multiple per
  question). "No file" = empty.
- `risk-node` - an inline free-text follow-up UpGuard injects when a risky answer is
  given. `.display-id` reads literally "Risk"; `.node-name` = the risk statement;
  `.risk-response .desc` = the standard prompt ("If you have compensating controls...
  please provide a detailed explanation"); **our answer = the `<textarea>.value`**.
  These are the compensating-control / risk-acceptance narratives and are the most
  valuable output.

Common shape: numbering nests up to 4 levels (`1.1.1.1`); the `.display-id` skips
numbers - that's normal (CIS safeguard numbering), and it's stable enough to use as
`id`.

**Reconciling counts.** `.sidebar-item` count = sections + leaf questions (e.g. 249
= sections + leaf questions). The header "N of N answered" counts leaf questions
only. `risk-node`s are **not** counted as questions and are **not** sidebar
items - they're inline addenda. So: question rows = select + upload nodes; risk
rows are extra.

**Risk parent = DOM order.** A risk-node's own `data-node-id` (e.g. `Q_CIS_003_risk`)
does *not* match its triggering question's id (`Q_3200`), so link by document order:
iterate `.question-answer-node` in order, remember the last non-risk question's
`.display-id`, and set that as the risk's `parent`.

**Comments.** Every question shows a `cr-icon-chat-messages` button (add-comment) -
its presence is **not** an indicator of an actual comment. The header comment badge
(e.g. "1") is usually the *customer's questionnaire-level invite message*, not a
per-question thread. Don't infer per-question comments from the icon; check for a
real count badge / open a thread if you need to confirm.

**Extraction is a single in-page pass** (all nodes rendered). Because a full
questionnaire can be ~150KB of JSON, the reliable bridge to disk is: build the whole
`{meta, questions}` object in-page, `JSON.stringify` it, create a Blob, and trigger
a download (`a.download='..._capture.json'; a.click()`). **It lands in the host's
`~/Downloads/`** (there can be a few seconds' delay before the file appears - if a
`find ~/Downloads` misses it, wait and retry rather than paging the bytes through
context). Then `cp` it in and run the build script. Do **not** try to relay 150KB by
hand via base64 chunks - the download is the clean path.

**Extractor (run once after entering the questionnaire body):**

```js
(function(){
  function tc(s){return (s||'').replace(/\s+/g,' ').trim();}
  const nodes=[...document.querySelectorAll('.question-answer-node[data-node-id]')];
  const rows=[]; let curSection='', lastQ=null;
  nodes.forEach(n=>{
    const cls=n.className.toString();
    const displayId=tc((n.querySelector('.display-id')||{}).textContent);
    const name=tc((n.querySelector('.node-name')||{}).textContent);
    if(cls.includes('section-node')){ curSection=(displayId?displayId+' ':'')+name; return; }
    if(cls.includes('select-node')){
      const options=[...n.querySelectorAll('.answer-option')].map(o=>({label:tc((o.querySelector('.text')||{}).textContent), checked:o.classList.contains('selected')}));
      rows.push({section:curSection,id:displayId,parent:'',question:name,answer:options.filter(o=>o.checked).map(o=>o.label).join('; '),options,comment:'',instruction:'',attachment:''});
      lastQ=displayId; return;
    }
    if(cls.includes('upload-node')){
      const files=[...n.querySelectorAll('.current-files-uploaded .filename, .file-answer .filename')].map(f=>tc(f.textContent)).filter(Boolean);
      rows.push({section:curSection,id:displayId,parent:'',question:name,answer:files.length?('Uploaded: '+files.join(' | ')):'(no file)',options:[],comment:'',instruction:'Please upload the requested document(s).',attachment:files.join(' | ')});
      lastQ=displayId; return;
    }
    if(cls.includes('risk-node')){
      const val=tc((n.querySelector('textarea')||{}).value||'');
      rows.push({section:curSection,id:(lastQ?lastQ+' – Risk':'Risk'),parent:lastQ||'',question:'[Flagged risk] '+name,answer:val,options:[],comment:'Portal prompt: compensating-controls / risk-explanation field (triggered by the flagged answer above).',instruction:'',attachment:''});
    }
  });
  window.__CAP=rows; return JSON.stringify({rows:rows.length});
})();
```

Then build `{meta:{...},questions:window.__CAP}` in-page, download it, `cp` in, run
the build script.

---

## Venminder (Vendor questionnaire-response portal)

Seen on: a financial-services customer's due-diligence questionnaire for a
critical service provider, vendor `<your-org>`. **Aurelia** app (`au-target`, `.bind`, `click.delegate`
attributes everywhere) — not Salesforce/Angular/React. This is the vendor's own
read/write response view, reached from the **Client Requests → Questionnaires**
tab. Sign in first; the logged-in vendor user shows in the top-right account menu.

**Landing / picking a questionnaire.** `…/vendor/questionnaires/questionnaire-request`
lists all questionnaires in a table (Request by | Questionnaire | Primary Contact |
Received | Deadline | Status with a completion %). The questionnaire links are
`a[href^="/user/questionnaire-response/<uuid>"]` — but **clicking the link in the
grid just scrolls** (Aurelia intercept); `navigate` straight to the
`/user/questionnaire-response/<uuid>` URL instead. A `0% In Progress` questionnaire
has no answers yet → a questions-only capture (all "Our Answer" blank); `100%
Completed` ones carry submitted answers.

**Section pagination.** One section in the DOM at a time. Section picker is a
custom `button.vm-dropdown` whose current label is `span.vm-dropdown--text`; the
full section list is the set of `button.vm-dropdown-item--content` (dedupe — each
appears twice for top/bottom navs). Two nav buttons `button.nav-btn` labelled
`Previous` / `Next` drive `previousSection()` / `nextSection()`; **`.click()` on
Next is read-only-safe** (navigation only, doesn't touch answers). `Next` becomes
`disabled` on the last section — use that as the end signal. The per-section header
also shows `Total Number of Questions in Section: N | Unanswered or Returned
Questions: N` — reconcile against it.

**Question card:** `div.row.m-t-md` that contains a `span.question`. Within it:
- Number: the leading `<strong>` (e.g. `1.1`); question text: `span.question`
  (read `.textContent` — the value is bound via `formattedQuestion | sanitizeHTML`).
- **Free-text** questions: a real `textarea.form-control` (there's also a
  `textarea.hidden` used only for validation — exclude `.hidden`). Answer = its
  `.value`. `options` is `[]`.
- **Single-select** questions: `input[type=radio]` with a sibling `label[for=id]`;
  options seen were `N/A / Yes / No` (a few are just `Yes / No`). Inputs are
  disabled in read-only but `.checked` marks the answer.
- **Exclude the `vm-toggle` checkbox** ("Tag question as complete") and its
  `input.vm-toggle--input` — it's a status control, not an answer option.
- "Requirements" column: a `<label>Requirements</label>` + `ul.text-teal`; every
  question here read `* Answer is required`. Status pill = `.vm-label` ("Awaiting
  Response").

**Attachments.** Every question exposes the **same generic optional paperclip**
(`.fa-paperclip`, `attachFiles(question)`), so its presence is *not* a per-question
upload ask — treat like Onspring's generic zone. Genuine "please provide/upload"
asks would show up in the Requirements list or question wording; none did here.
No file anchors on the page.

**Extractor (run per loaded section; accumulate keyed by section name):**

```js
(function(){
  function tc(s){return (s||'').replace(/\s+/g,' ').trim();}
  const secBtn=document.querySelector('button.vm-dropdown .vm-dropdown--text')||document.querySelector('span.vm-dropdown--text');
  const section=tc(secBtn&&secBtn.textContent);
  const cards=[...document.querySelectorAll('div.row.m-t-md')].filter(c=>c.querySelector('span.question'));
  const rows=cards.map(card=>{
    const num=tc((card.querySelector('.form-group strong')||{}).textContent);
    const question=tc((card.querySelector('span.question')||{}).textContent);
    const tas=[...card.querySelectorAll('textarea')].filter(t=>!t.classList.contains('hidden'));
    const opts=[...card.querySelectorAll('input[type=radio],input[type=checkbox]')].filter(i=>!i.classList.contains('vm-toggle--input'));
    const options=opts.map(i=>{let l='';if(i.id){const e=card.querySelector('label[for="'+i.id+'"]');if(e)l=tc(e.textContent);}if(!l){const p=i.closest('label')||i.parentElement;l=tc(p&&p.textContent);}return {label:l,checked:i.checked};});
    return {num,question,answer:tas.map(t=>tc(t.value)).filter(Boolean).join(' '),options};
  });
  return JSON.stringify({section,count:rows.length,rows});
})();
```

Walk: extract current → click `Next` → (next call) extract → … until `Next`
disabled.


---

## Gartner BuySmart (vendor evaluation questionnaire)

Seen on: a public-sector customer's product evaluation, with `<your-org>` as one of
the scored vendors. React 17 + single-spa micro-frontends (the responses UI is
the `survey-responses-app`). Sign-in is the Gartner.com account (email + password,
the operator does it). URL shape:
`/s/tasks/<taskId>/questionnaire/<questionnaireId>/product/<productId>/responses`.

**This is an RFP-style capability-scoring questionnaire, NOT a Yes/No security
DDQ.** Every "question" is a required capability (name + a Gartner-authored
description). The respondent rates fit on **one uniform 4-point scale for the whole
survey**: `Fully meets / Partially meets / Does not meet / Not applicable`. Each
question also has an optional free-text "view text response" box and a discussion
thread. No file uploads anywhere (`hasRequestedDocuments=false` on the header).

**Skip the DOM — hit the API.** Walking the DOM is a trap here: the list is
**virtualized** (only ~20 `li.gx-survey-responses-list-item` render at once), the
class names are obfuscated CSS-module hashes, and the scoring options live in a
custom `gx-survey-responses-scoring-popover` that only renders its menu on open. All
of that is unnecessary because one authenticated JSON endpoint returns the entire
questionnaire, including the option scale, in order:

```
GET /api/v2/initiatives/<taskId>/survey/recipients/<questionnaireId>/<productId>/responses
```

Response `data` shape:
- `data.categories[]` = sections, each `{name, id, comment, items[]}`.
- `items[]` = questions, each `{id, name, description, comment, responseOptionId,
  hasComments, discussionId}`. `responseOptionId` is `""` when unanswered, else it
  maps into...
- `data.options[]` = the shared scale `[{id, name}]` (Fully meets / Partially meets
  / Does not meet / Not applicable). Join `item.responseOptionId → option.name` for
  the selected answer.
- `data.isSubmitted`, `data.surveyState` ("OPEN"), `data.initState` ("ACTIVE").

Header metadata (customer, requester, dates) is a second endpoint:
`.../<productId>/overview/header` → `requestedByCompanyName`, `requestedByUserName`,
`requestedByEmail`, `requestedOnDate`, `hasRequestedDocuments`, `status`.

A same-origin `fetch(url,{credentials:'include'})` in `javascript_tool` works once
the operator is signed in (cookie-authed, no SigV4 games like SAFE ONE). Build the
`{meta,questions}` capture straight from the JSON. Notes:
- Some `description` values contain rich-text HTML (`<p class="rte-paragraph">…`).
  **Strip tags** (set `div.innerHTML`, read `textContent`) — seen on ~4 questions
  (identity/access mgmt, compliance certs, readability, A/B testing).
- Options are identical on every question, so set `options` to the 4 `data.options`
  names with `checked = (option.id === item.responseOptionId)`.
- The in-page `a.download` blob **did not reach the local `~/Downloads`** here (the
  browser pane is sandboxed) — just return the stringified capture from
  `javascript_tool` and Write it to disk directly. Don't rely on the download path
  the UpGuard notes describe.
- Q-id scheme: no stable portal numbers, so a per-section `FR-/TR-/SR-/SS-/VH-/PC-`
  index works fine (order is stable from the API).

Sections seen: functional, technical, security, support and services, vendor health,
and pricing. A 0-answered questionnaire is a normal case — a questions-and-options
capture to prep responses, rather than a record of submitted answers.


---

## Generic discovery (unknown platform)

When the portal isn't one of the above:

1. **Screenshot + `read_page`** to see sections, question shape, and navigation.
2. **Dump one question's `outerHTML`** via `javascript_tool` to find the repeating
   question-card selector and how text/options/comments are marked up.
3. **Determine selection state.** Try, in order: `input.checked` (works even when
   `disabled`), `aria-checked="true"`, a selected/active class, a checkmark SVG,
   or a `<select>`'s `.value`.
4. **Find hidden values.** Comments/rationales are frequently in a `<textarea>.value`
   or a read-only span rather than visible text. Read `.value`, not innerText.
5. **Determine pagination.** Is everything in the DOM, or does it load by section
   (click through) or by scroll (human scrolls; consider a response interceptor if
   the data arrives via `fetch`/XHR)? Reconcile against any completion counters.
6. **Scope to each card** so nested sub-questions don't bleed into their parents.
7. **Wrap DOM JS in an IIFE** to avoid `const` redeclaration errors between calls.
8. **Global attachment sweep** for file anchors, upload widgets, and
   "upload/attach/provide/evidence" wording.
9. **Write down what you found here** for next time.
