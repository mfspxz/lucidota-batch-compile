# WAVE-4 LANE C — Cross-lane conformance (lanes 2–4 vs lane 1 parser surface)

## Task
Verify the lane 2–4 modules against lane 1's parser surface, and adjudicate the
recorded open items. Verification + verdicts only — do NOT redesign anything.

## Inputs
- Lane 1 surface (canonical, do not modify): `~/workspace/compute/pipeline/workorder.py`
  — `validate_parsed`, `TIER_VALIDATORS = {"tier3_eligible", "validate_tiering"}`,
  `SCHEMA_NOTES`, `REQUIRED_FIELDS`/`ALLOWED_FIELDS`.
- Lanes 2–4 modules: `partition.py`, `allocate.py`, `checks.py`, `goaltypes.py`.
- Spec: `~/workspace/batch-compile/SPEC/03-schemas.md` (§§18/20/21),
  `~/workspace/batch-compile/SPEC/12-implementation-backlog.md` (§13 pinned layouts).
- Demo evidence: `~/workspace/compute/pipeline/demo_e2e_test.py` (147/147 green).

## Deliverables
1. `~/workspace/batch-compile/SPEC/conformance-lanes2-4.md` — per-module
   verdict (CONFORMS / DEVIATES with exact symbol + line), and a verdict for
   each open item below.
2. Additive §20 edit to `03-schemas.md` ONLY if item (a) finds a gap
   (append a subsection; never rewrite existing text).

## Open items to resolve
(a) §20 check-result table vs the pinned §13 layout: the batch layout lists 9 ops
    (`compare|compare-policy|calculate|route|track|stop|t3-completion|t2-consistency|t1-coherence`)
    and `checks.py` uses tri-state `passed` (True/False/None). If §20 lacks either,
    append an ADDITIVE subsection documenting them. Never rewrite §20's existing text.
(b) §18-vs-§13 layout divergence: `workorder.py` SCHEMA_NOTES already records it.
    Confirm in the report that the §13 pinned layout is normative and §18 is the
    divergent reference. Verdict only.
(c) `context_refs`: `partition.py::_t3_assignment` reads `goal.get("context_refs")`
    but `workorder.py` goal ALLOWED_FIELDS does not list it. Determine whether
    `parse_workorder` emits it. If not: document as lane-2-local
    (partitioner-tolerated, parser-absent) — do NOT change the parser; lane 1 is canonical.
(d) Brief-vs-§21 key names: `allocate.py::schedule_order` already codes to canonical
    §21 keys (`tier3_result_refs`, `tier2_result_refs`, `evidence_refs`). Confirm every
    lane-2–4 module uses the canonical keys; list any remaining shorthand.
(e) Inter-bundle depends_on gap (found in the §13 demo): T2 bundles whose
    `depends_on` resolve only to non-standalone goals get empty `t3_result_refs`,
    so `schedule_order` treats them as immediately schedulable — no ordering gate
    between T2 bundles. Adjudicate: either (i) spec-blessed — T2 bundles are
    order-independent within a wave and workers see deps via group context —
    record the verdict; or (ii) a backlog task for a follow-up batch. Do NOT change code.

## Acceptance
- Report exists, every verdict cites exact file + symbol + line.
- Full pipeline suite still green: `cd ~/workspace/compute/pipeline && python3 -m pytest -q`.
- Any §20 edit is purely additive (diff shows only additions).

## Constraints
- 0 provider calls. Local reads + pytest only.
- Write scope: `~/workspace/batch-compile/SPEC/` only. Pipeline code is READ-ONLY.
- Commit same-turn (spec dir). Consult `~/ledger` via grep for context; don't dump it.
- Production naming; no "sketch"/"prototype" labels. No deletions — archive safely only.

## FORBIDDEN GIT OPS
NEVER run `git reset` (any mode) — destroys uncommitted work tree-wide.
NEVER run `git stash` — parks work where concurrent lanes can lose it.
NEVER run `git clean -f` — deletes untracked fixtures/evidence.
NEVER run `checkout`/`switch --force` (or `-f`) — overwrites without asking.
NEVER run `push --force` (or `-f`) — rewrites shared history.
NEVER rewrite history (`rebase`, `commit --amend`, `filter-branch`, `filter-repo`, BFG).
Stage selectively; commit new files with `git add <paths>` + `git commit`. If in doubt, stop and report.
