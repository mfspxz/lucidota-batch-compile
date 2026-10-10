# PIPE-011 — Enforced Canary (Phase 2, single scope)

**Lane:** 2026-10-09 ~17:09–17:25 PDT · **Spec:** `SPEC/11-migration.md` §4 Phase 2
**Trials 1–5 (PIPE-010) untouched.** 0 real provider calls throughout
(synthetic harness only). All burn guards apply.

## Design

New module `pipeline/dispatch.py` (canary gate + kill handling +
`reconcile()`), plus four additive flag-guarded hunks in `burn.py`.
No existing symbol's behavior changes unless `PIPELINE_MODE=enforced`
AND `PIPELINE_CANARY_SCOPE` is set.

**Canary scope** (`PIPELINE_CANARY_SCOPE=synthetic:stream`): the
synthetic harness's stream-slot dispatches (`source ==
"synthetic-dispatch"`, non-empty `slot_id`). Exactly one narrow scope;
everything else is observe-only (Phase-1 behavior). Scope parsing is
opt-in: unknown/missing scope → no enforcement anywhere.

**The gate** (`dispatch.check()`): in-scope dispatch requires a live
plan. Keying mirrors `compare_shadow`'s two-keyed matching (stream
slots by fingerprint, backlog by task id). Miss → seal a
`REFUSED_UNPLANNED` receipt (envelope, prev_hash-chained) *then* raise
`UnplannedDispatchRefused` — a refusal can never escape unrecorded. No
live plan → `NoPlanRefused` (fail closed). Malformed requests →
`DispatchError` (caller bug, no receipt).

**Kill** (`PIPELINE_KILL=1`): read at call time via `flags.killed()`.
`burn.py`'s `_pacer` now checks the kill every tick and halts the pacer
thread on observation (kill-switch = immediate off-semantics, per the
flags contract; supervisor continues on the legacy path). In-flight
attempts fold to the named terminal state `aborted_by_kill`; the kill
is sealed as `KILL_OBSERVED` naming every aborted key.

**`dispatch.reconcile()`**: every fold record must carry a terminal
state from the closed vocabulary
`{completed, refused_unplanned, aborted_by_kill, failed}` — anything
else (missing, `"started"`, unknown) is a lost/zombie task. Checks
exactly-once per key, refused-vs-completed contradictions, and (with a
plan) that every enforced completion was planned. Seals a
`dispatch-reconcile/1` artifact (status `established`, prev_hash-chained,
chain-verified on read-back) binding the fold digest, counts, and the
gate-receipt count.

## Acceptance

### Item 1 — one enforced canary scope (seeded fixture)

| Case | Result |
|---|---|
| Planned stream slot, in scope | allowed, `mode=enforced`, executes |
| Unplanned stream slot, in scope | **refused**: `UnplannedDispatchRefused` (`UNPLANNED_DISPATCH`) + sealed `REFUSED_UNPLANNED` receipt, chain-verifies |
| Out-of-scope dispatch (other source / no slot) | allowed, `mode=observe`, seals nothing |
| No `PIPELINE_CANARY_SCOPE` set | gate inert, `mode=observe` |
| In scope, no live plan | `NoPlanRefused` (`NO_PLAN`), sealed, fail closed |
| Malformed request | `DispatchError`, no receipt |

Burn wiring proven: with `PIPELINE_MODE=enforced` + scope + seeded plan,
`dispatch_synthetic` refuses an unplanned slot *before* `_queue_add`
(`synthetic_refused` bumped, early return); a planned slot proceeds to
queue + fake-provider completion; with no scope the gate is inert.

### Item 2 — `PIPELINE_KILL=1` mid-cycle rollback drill

Deterministic seeded drill (`run_kill_drill`): 5 requests, kill fires
(event-driven) after the 4th dispatch STARTs; the 4th task sleeps
0.15 s mid-execution so the kill genuinely lands mid-flight.

Measured:

| Metric | Value |
|---|---|
| Kill signal → last dispatch terminal (halt latency) | **0.1501 s** (in-flight drain; no new dispatch after observation) |
| Dispatches STARTed after kill observed | **0** |
| Terminals | completed 3, refused_unplanned 1, aborted_by_kill 1 |
| In-flight at kill | folded to `aborted_by_kill` — no zombies |
| Kill sealed | `KILL_OBSERVED` receipt naming the aborted key; gate receipts chain-verify (2/2) |
| Env hygiene | drill restores `PIPELINE_KILL`/`PIPELINE_MODE`/`PIPELINE_CANARY_SCOPE` on exit |

The out-of-scope request dispatched as `observe` (Phase-1 behavior
inside the drill); the unplanned in-scope request was refused before
the kill. The burn `_pacer` kill hunk is proven separately: with
`PIPELINE_KILL=1` the pacer thread exits without calling the dispatch
fn once.

### Item 3 — `dispatch.reconcile()` proves zero lost tasks

On the drill fold: **ok=True, lost=[], double=[], unenforced=[]**
(counts: 5 total, 3 completed, 1 refused, 1 aborted). Sealed artifact
`dispatch-reconcile/1` (`established`, seal `8465e2d0e45761c6…`,
chain-verified on read-back, binds fold digest + gate-receipt count).

Tamper battery (proves the check is real, not vacuous):
- terminal flipped to `"started"` → 1 lost, ok=False
- completed record duplicated → 1 double-count, ok=False
- enforced completion outside the plan → 1 unenforced, ok=False

## Tests

`pipeline/dispatch_test.py`: **18/18 green** (scope, gate, drill,
reconcile incl. tamper battery, burn hunks). All receipts to tmp paths.

## Pre-existing failures (recorded, not fixed — out of scope)

Full suite: **1137 passed, 3 skipped, 11 failed**. The 11 failures are
PRE-EXISTING relative to this lane and untouched by it:

- Failing: `driver_test.py::test_live_cli_with_fake_adapter`,
  `redteam_cycle2_test.py` (8 adapter tests),
  `redteam_cycle4a_test.py::test_rt4a_cli_live_e2e_ok`,
  `redteam_cycle18_test.py::test_c18d_huge_claim_field`.
- Structural cause: trial 5's engine wrote 2,599 synthetic dispatch-fold
  actuals (no `dispatch_id`) into `compute/dispatches.jsonl`
  (23:20–00:07 UTC), the same file the supervision protocol
  (`compute/dispatch.py`, another lane's RT-C7 module) reads as its
  event log. Its `_fold_state()` does `ev["dispatch_id"]` → `KeyError`
  on the synthetic records. Last synthetic record 00:07:20 UTC; this
  lane started 00:09:17 UTC. Suite was green at dogfood-2 (20:11 UTC),
  before the pollution. None of this lane's files appear in those
  tracebacks; this lane's tests stub `_append_dispatch_fold` and never
  wrote to that file.
- Not fixed: `compute/dispatch.py` belongs to another active lane, and
  the records are append-only evidence (deletion forbidden). Flagged
  for the parent: the burn dispatch fold and the supervision event log
  need separate files.

## Verdict

**Items 1–3 demonstrated with sealed evidence: PASS.** The
full-suite-green criterion is **BLOCKED** by the pre-existing
cross-lane collision above — not declared met, not this lane's to fix.
Phase 2 canary mechanics are proven; **Phase 3 stays with the parent.**

## Artifacts

- `~/workspace/compute/pipeline/dispatch.py` (new)
- `~/workspace/compute/pipeline/dispatch_test.py` (new, 18 tests)
- `~/workspace/compute/burn.py` (4 additive hunks: import, pacer kill
  check, synthetic gate, `_maybe_shadow_plan` also runs in enforced)
- Sealed evidence pattern: `pipeline-dispatch-gate.jsonl` /
  `pipeline-reconcile.jsonl` (envelope, prev_hash-chained); drill
  artifacts in tests are tmp-scoped.

## Commits

- compute: PIPE-011 lane (dispatch.py, dispatch_test.py, burn.py hunks)
- batch-compile: this file
