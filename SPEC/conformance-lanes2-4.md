# Cross-lane conformance — lanes 2–4 vs lane-1 parser surface (wave 4, lane C)

Lane-1 canonical surface (READ-ONLY, never modified): `~/workspace/compute/pipeline/workorder.py`
— `validate_parsed` (workorder.py:404-417), `TIER_VALIDATORS = {"tier3_eligible", "validate_tiering"}` (workorder.py:563-566),
`SCHEMA_NOTES` (workorder.py:93-102), `REQUIRED_FIELDS`/`ALLOWED_FIELDS` (workorder.py:104-120).

Spec refs: `~/workspace/batch-compile/SPEC/03-schemas.md` (§§18/20/21), `~/workspace/batch-compile/SPEC/12-implementation-backlog.md` (§13).
Demo evidence: `~/workspace/compute/pipeline/demo_e2e_test.py` (147/147 green, 0 provider calls).

## Module verdicts

### partition.py — CONFORMS (with documented notes)

- `can_standalone` (partition.py:236-257) implements the batch-brief pin
  ("Tier 3 ONLY if can_standalone (Depends-On empty ∧ context_refs resolve ∧ no Group)",
  backlog §13 lines 476-479). Against the lane-1 validator `tier3_eligible`
  (workorder.py:529-542): NOT a contradiction — `tier3_eligible` is a structural
  pre-check (no depends_on, no group); `can_standalone` is the conservative
  binding partitioning rule (adds context_ref resolution). A goal with
  unresolvable context_refs passes `tier3_eligible` but fails `can_standalone`
  → Tier 2. Brief-pinned; conformant.
- `_resolve_goal_type` (partition.py:169-182) reads `manifest.goal_type_registry`
  entries `{goal_type, subdivision_permitted}` — matches the §18 manifest profile.
  OBSERVATION (not a deviation): `parse_workorder` never emits a `manifest` key
  (pinned §13 typed-work-order profile has no manifest), so this path resolves
  manifest → module registry (`goaltypes.get`) → atomic-fail-closed. The
  fail-closed atomic default matches §18 ("undeclared type → not subdivided").
- `_t3_assignment` (partition.py:260-297) and `_t2_bundle` (partition.py:303-354):
  unit/bundle ids (`t3-<12hex>`, `t2-<12hex>`), content-derived, deterministic;
  match the §13 pinned T2/T3 assignment profiles (backlog §13 lines 418-425).
  `partition_hash` (partition.py:369-383): stable determinism pin.
- Key-name note: `_t2_bundle` emits `t3_result_refs` / `shared_context_refs`
  (partition.py:350-351) — §13-pinned shorthand, not §21 canonical names (see (d)).

### allocate.py — CONFORMS

- `assemble_t1_kit` (allocate.py:462-500): `context_scope` carries canonical
  §21 tier-1 keys `tier2_result_refs` (allocate.py:498) and `evidence_refs`
  (allocate.py:499). ✓
- `schedule_order` (allocate.py:652-686): reads canonical §21 keys —
  `scope.get("tier3_result_refs")` (allocate.py:674) for tier 2,
  `scope.get("tier2_result_refs")` / `scope.get("evidence_refs")` (allocate.py:679-680)
  for tier 1. Comments (allocate.py:671-672, 678) record the canonical contract
  explicitly. ✓
- Quota refusal codes: `REASON_CODES` (allocate.py:155-167) verbatim from
  `governor.py` REASON_CODES (canon §0.5). Reservation minted by the coordinator
  only; worker minter → `AUTHORITY_VIOLATION` (allocate.py:380-384) — matches §5.
- OBSERVATION (adapter-layer, feeds (e)): `schedule_order` reads
  `tier3_result_refs` from the envelope's `context_scope`, but
  `partition.py::_t2_bundle` emits refs top-level as `t3_result_refs` with no
  `context_scope` — so the T3 gate is inert on raw partition envelopes. The
  demo's `_envelope` adapter (demo_e2e_test.py:61-73, 144-151) bridges the two
  shapes; with the raw envelope the gate never fires.

### checks.py — CONFORMS to §13 pin; DEVIATES from §20 base table (recorded, resolved by addendum)

- `OPS` (checks.py:54-64): closed 9-op vocabulary, exact-case lowercase —
  matches the §13 pinned check-result profile (backlog §13 lines 434-436) exactly.
- `CheckResult` (checks.py:99-165): tri-state `passed: True|False|None`
  (pass|fail|unknown); serializes as `pass` + `evidence_refs` (checks.py:136-145)
  — the §13 pin's field names. INV-02 enforced: unmeasurable → unknown
  (checks.py:201-207, 261-262), forged bare-True evidence → fail, never pass
  (checks.py:459-475). `passed=True` requires ≥1 evidence ref (checks.py:129-130).
- Module docstring (checks.py:1-35) already records the §20 delta; the base
  §20 table (03-schemas.md:671-686) pins only 3 capitalized ops and
  `outcome: pass|fail`. Gap is real — resolved additively under (a).

### goaltypes.py — CONFORMS

- Seeded `generic`, `subdivisible=false` (goaltypes.py:34-38): the parser's
  `_check_type_id` default (workorder.py:229-245) treats absent/unknown types as
  generic/atomic — consistent.
- Unknown-type lookup → `KeyError("…register it first")` (goaltypes.py:57-62);
  parser's unknown-type error is `"goal {n}: unknown type … (register it first)"`
  (workorder.py:240) — same fail-closed contract, verbatim phrasing.

## Open items

### (a) §20 check-result vs §13 pin + checks.py tri-state — GAP CONFIRMED, additively documented

- §20 base table (03-schemas.md:681): `op` closed exact-case `Compare | Calculate | Compare-against-policy`;
  (03-schemas.md:684): `outcome` closed exact-case `pass | fail`; (03-schemas.md:685): field `evidence`.
- §13 pinned batch profile (backlog §13:434-436): 9 lowercase ops
  `compare|compare-policy|calculate|route|track|stop|t3-completion|t2-consistency|t1-coherence`,
  field `pass: bool`, field `evidence_refs`.
- `checks.py` codes the §13 profile and extends it with the tri-state
  `passed` (True|False|None = pass|fail|unknown) required by INV-02.
- RESOLUTION: an ADDITIVE subsection "§20 ADDENDUM — batch-1 concrete
  check-result profile" was appended to 03-schemas.md after the §20
  Compatibility line. No existing §20 text was modified or rewritten
  (diff shows additions only — verified below).

### (b) §18-vs-§13 divergence — VERDICT: §13 pinned layout is normative

- The §13 doc itself declares "Pinned schemas are normative" (backlog §13:366).
- `workorder.py` module docstring (workorder.py:24-27): "Field layout follows the
  BATCH-1 pinned interface (12-implementation-backlog.md section 13), which is
  normative for this batch."
- `SCHEMA_NOTES` (workorder.py:93-102) records the two known divergences:
  (1) `development_rules` is a list of strings in the pin vs a single string in
  the §18 table; (2) the pin carries `source_sha256`/`created_by`/`created_at`
  and omits the §18 `run_id`/`author`/`raw_text`/`manifest`/`state`/`prompt_id` fields.
- VERDICT: §13 is normative for the batch; §18 is the divergent reference.
  No code or spec change made (verdict only).

### (c) `context_refs` — VERDICT: lane-2-local (partitioner-tolerated, parser-absent)

- The parser does NOT emit it: `ParsedGoal.to_dict` (workorder.py:219-229)
  carries only `n, type, title, body, depends_on, group, done_when`; the
  manifest merge allows only `depends_on/group/done_when` per goal
  (workorder.py:190, 268-324); `validate_goal` rejects unknown fields
  (workorder.py:456-461). A goal dict carrying `context_refs` FAILS
  `validate_parsed` — proven by the unknown-field rejection path.
- `partition.py` reads `goal.get("context_refs")` in `can_standalone`
  (partition.py:251) and `_t3_assignment` (partition.py:278); the docstring
  (partition.py:27-30) marks it optional. It is tolerated-never-required,
  resolution-checked against work-order-supplied context
  (partition.py:237-243).
- VERDICT: documented as lane-2-local — partitioner-tolerated, parser-absent.
  The parser was NOT changed (lane 1 is canonical).

### (d) Canonical §21 key names — VERDICT: allocate.py and checks.py conform; one shorthand remains

- `allocate.py::assemble_t1_kit`: `tier2_result_refs` (allocate.py:498),
  `evidence_refs` (allocate.py:499) — canonical. ✓
- `allocate.py::schedule_order`: `tier3_result_refs` (allocate.py:674),
  `tier2_result_refs` + `evidence_refs` (allocate.py:679-680) — canonical. ✓
  (Prose in comments uses the shorthand `t3_result_refs` (allocate.py:658-660)
  — documentation only.)
- `checks.py::CheckResult`: `evidence_refs` (checks.py:91-165) — matches the
  §13 check profile and the §21 tier-1 scope key.
- REMAINING SHORTHAND: `partition.py::_t2_bundle` emits top-level
  `t3_result_refs` (partition.py:350) and `shared_context_refs`
  (partition.py:351) — the §13-pinned form, not the §21 canonical
  `tier3_result_refs` / `shared_context`. This matches the brief it was
  written against (§13 pin, backlog:425) and is recorded here, not fixed
  (pipeline code is read-only in this lane).

### (e) Inter-bundle depends_on gap — VERDICT: BACKLOG TASK (not spec-blessed)

- Evidence (demo_e2e_test.py:173-183 NOTE): the `{3,4}`-group bundle and the
  goal-5 bundle declare `depends_on` edges to NON-standalone goals (2, and 3/4),
  which resolve to no T3 result refs — `schedule_order(allocs, {})` treats them
  as immediately schedulable (sched0 = [2,2,3], i.e. two T2 bundles + the T3 unit).
  Only the goal-2 bundle (dep on standalone goal 1) actually waits on the T3 gate.
- Why (i) spec-blessed fails: `depends_on` is a validated, resolved ordering
  edge (parser: workorder.py:353-357; `validate_parsed` depends-on resolution),
  and §18's validation rules give `enables`-class edges scheduling semantics.
  Goal 5 ("Test concurrent execution, rate limits, retries and recovery")
  depends on goals 3 and 4 — real ordering, not group-context-advisory.
- Why it can't be fixed inside the scheduler alone: §21 pins the tier-2
  `context_scope` to `{item_ids, tier3_result_refs, shared_context}` and
  rejects out-of-scope fields (over-contextualization is a violation); there
  is no field for inter-bundle (T2→T2) result refs, and
  `schedule_order`'s T2 rule only reads `tier3_result_refs`. Wiring an
  inter-bundle gate is a schema decision; the additive-only path (§0.1) exists
  for exactly this (new optional field in a v1.x §21 profile or a follow-up
  batch's concrete pin).
- VERDICT: backlog task for a follow-up batch (T2→T2 gating field +
  scheduler gate on it). No code changed. Also in that batch's scope: the
  `_t2_bundle` top-level `t3_result_refs` vs `schedule_order`'s
  `context_scope.tier3_result_refs` read-shape mismatch (see allocate.py note).

## Suite + diff verification

- Full pipeline suite: `cd ~/workspace/compute/pipeline && python3 -m pytest -q`
  → **156 passed** (2026-10-09). Suite stays green; no pipeline code was
  modified (read-only lane).
- §20 edit: verified additive — the base §20 table (03-schemas.md:671-686)
  and the §20 Compatibility line are byte-identical to before the edit; the
  new "§20 ADDENDUM — batch-1 concrete check-result profile (ADDITIVE)"
  subsection was inserted after the Compatibility line, before "## 21.".
  No existing §20 text was modified, rewritten, or removed.
- Commit: `~/workspace/batch-compile` was not previously a git repo; a repo
  was initialized there and `SPEC/03-schemas.md` + `SPEC/conformance-lanes2-4.md`
  committed selectively (commit `94090b2`). No other files staged; no git
  history exists outside this repo. No forbidden git ops were used.
