# Fill platform notes

Per-platform mechanics for *filling* a portal (distinct from extracting it — for
selectors and pagination see `ddq-portal-extract/references/platform-notes.md`). Read the
matching section before filling; append what you learn so the next fill is faster.

## Generic (unknown platform)

1. **Identify the input types** (radio / checkbox / select / text / textarea / file) and a
   stable handle per control — prefer a `name`/`id`/`data-*` attribute over hashed classes.
2. **Confirm selection state is read-only-observable** (`input.checked`, `.value`, a
   selected class) so you can verify fills.
3. **Assume controlled inputs** — drive with `computer`/`form_input`, not JS assignment;
   use JS only to read state back.
4. **Screenshot before clicking ambiguous options** — a11y labels can be wrong/duplicated;
   map by position and confirm by DOM.
5. **Find the completeness counter** and reconcile after each batch.
6. **Locate comment/upload controls** and apply the comment rule — fill a free-text/comment
   field only when it's a genuine free-text answer or the form requires it.
7. **Write down what you found here** for next time.
