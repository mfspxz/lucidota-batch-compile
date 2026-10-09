# PIPE-010 Shadow Trial Report — EXECUTED (wiring unblocked)

**Lane:** RUNBOOK PIPE-010 re-run · **Date:** 2026-10-09 ~12:50–13:25 PDT · **Executor:** runbook subagent
**Verdict: MIXED — machinery proven, coverage predicate NOT met (structural cause, honest fail).**

Three consecutive STOPFILE-bounded burn windows ran with `PIPELINE_MODE=shadow`
(`PIPELINE_WINDOW_ID=shadow-w1/w2/w3`), 3 supervisor cycles each. The allocator
built 9/9 plans with zero crashes; the in-engine comparator wrote 138 sealed
receipts, all chain-verified. Plans are evidence only — no dispatch was altered
by a plan (verified: dispatch path untouched; `run_pipeline_cycle` legacy path).

## Measured numbers

| Window | Plans | Allocs/plan | Crashes | Receipts | MATCH | PLAN_UNEXECUTED | Dispatched* | Coverage† |
|---|---|---|---|---|---|---|---|---|
| shadow-w1 | 3 | 32 | 0 | 46 | 4 | 42 | 13 | 30.8% |
| shadow-w2 | 3 | 32 | 0 | 46 | 3 | 43 | 7 | 42.9% |
| shadow-w3 | 3 | 32 | 0 | 46 | 5 | 41 | 8 | 62.5% |
| **Total** | **9** | — | **0** | **138** | **12** | **126** | **28** | — |

\* Dispatched = tasks reaching a terminal queue state (completed/failed/blocked)
during the window. All 28 were newly created by the engine's pacers; zero
pre-existing backlog tasks transitioned.
† Coverage = dispatched tasks present in any of the window's plans ÷ dispatched.
Identical against plan allocations (top-32) and queued_ids (top-256).

No ORDER_DIFF / PROVIDER_DIFF / UNPLANNED_DISPATCH fired: actuals are derived
from queue transitions (no provider/ts metadata), and actuals are by
construction a subset of the compared plan's observed ids — so those classes
are structurally silent in this wiring. The comparator is honest about this
(queue-transition evidence basis).

## Acceptance status (migration 11-migration.md §4 Phase 1)

| Predicate | Status |
|---|---|
| ≥3 consecutive burn windows | **MET** — 3/3, all engines exited cleanly (rc=0) via STOPFILE finally-path |
| Zero allocator crashes | **MET** — 0 crashes across 9 plans (`allocator_crashes=0` every plan) |
| Plan produced for ≥95% of dispatched tasks | **NOT MET** — 30.8% / 42.9% / 62.5% |
| Every shadow receipt chain-verifies via `envelope.verify_chain` | **MET** — 138/138 verified |

## Why coverage failed (structural, not a flake)

The allocator plans the **top-32 of the queue backlog** (`Q.pending()` drain order);
the engine dispatches **newly created corpus tasks** (`dispatch_gemini` /
`dispatch_nvidia` call `_queue_add` per pacer tick — the engine never drains the
pre-existing queue). The two pools are disjoint by construction. The only
overlap is requeued tasks: a rate-limited gemini task returns to `queued`, gets
picked up by a later cycle's plan, then completes — that accounts for all 12
MATCH receipts. The 126 PLAN_UNEXECUTED receipts are the backlog the engine
never touches.

This is the trial doing its job: the shadow machinery works, but the plan and
the dispatch stream are aimed at different task pools. Fixes (design decision,
not a lane patch): (1) allocator plans the pacer-generated stream, not just the
backlog; (2) engine drains the queue backlog; or (3) restate the coverage
predicate to match the intended design.

## Provider calls + tokens (measured, per window; `_counts` resets per engine)

| Window | NVIDIA calls | Gemini attempts (completions) | Verify (local, 0 quota) |
|---|---|---|---|
| w1 | 6 (1 ok / 5 fail) | 70 attempts → 3 ok, 1 fail, 66 rate-limited | 3 |
| w2 | 4 (2 ok / 2 fail) | 84 attempts → 0 completed, 84 rate-limited | 3 |
| w3 | 5 (4 ok / 1 fail) | 85 attempts → 0 completed, 85 rate-limited | 3 |

- **NVIDIA total: 15 calls, all inside the startup race** (see Guards). Lane
  paused for the remainder of every window.
- **Gemini total: 239 attempts, 4 completions, 235 rate-limited** (adapter-bucket
  429s, not provider errors — matches the f8 finding that the adapter bucket,
  not the provider, is the binding constraint).
- **Output tokens recorded: 27,785** across 290 execution records in the trial
  span (partial — many records carry `output_tokens: null`; treat as a lower bound).
- Preflight smoke checks: 1 gemini + 1 nvidia call per engine start (6 total,
  not in `_counts`).

## Guards

- **NVIDIA band guard: already tripped before the trial** (0.584 ≥ 0.55) —
  acknowledged precondition. Stayed tripped all three windows (0.589 / 0.590 /
  0.591 at window ends). No new trip; no stop was warranted.
- **Startup race (finding):** `_nvidia_paused` initializes `False`; the first
  `budget_guard()` runs inside supervisor cycle 1, so the 37-RPM nvidia pacer
  fires for ~30–60s before the guard engages — 4–6 real nvidia dispatches per
  engine start on an already-paused lane. Bounded per start, but it is a
  guard-evasion race: the lane should initialize paused from persisted
  utilization. Recorded for a hardening lane; not a trial blocker.
- Budget guard otherwise nominal; no engine stopped abnormally.

## Hygiene observations (recorded, not fixed — out of lane scope)

- **Duplicate task_ids:** `task-99721824` ×11 in the queue (was ×10 at trial
  start — it grew). The comparator keys on identity; plans record
  `unique_task_ids` (23 unique per 32-allocation plan). Queue dedup is a
  separate lane's job.
- Queue grew 839 → 1071 queued across the trial: pacers create tasks faster
  than they complete under rate limiting.
- `pipeline-plans.jsonl` still contains the wiring lane's dry-run plan
  (`shplan-w-dryrun-1`); trial analysis filters by `window_id`.

## Artifacts

- Plans: `~/workspace/compute/pipeline-plans.jsonl` (9 trial plans, prev_hash-chained)
- Receipts: `~/workspace/compute/pipeline-shadow-receipts.jsonl` (138 sealed, chain-verified)
- Per-window engine logs: `/tmp/shadow-shadow-w{1,2,3}.log` (ephemeral)
- Queue/counts snapshots: `/tmp/shadow-q-*-{start,end}.json`, `/tmp/shadow-counts-*-{start,end}.json` (ephemeral)
- Driver: `/tmp/shadow_driver.py` · Analysis: `/tmp/shadow_analyze.py` (ephemeral)

## Recommendation

Do not advance to Phase 2 (canary/enforced) on this evidence: the coverage
predicate fails structurally. Next: a design decision on the plan-vs-dispatch
pool mismatch (options above), plus the startup guard-race hardening. Re-run
PIPE-010 after either fix; the wiring now supports it — this trial ran
end-to-end with zero manual intervention beyond STOPFILE creation.

## Addendum 2026-10-09 — DESIGN+FIX lane (coverage + guard race)

### Design decision: plan scope covers the pacer stream

Decision: **the allocator's plan scope is the engine's dispatch-candidate
set — backlog top-32 AND the peeked pacer stream — and the Phase-1 coverage
predicate is restated over the dispatch-candidate intersection.**

Rationale: the allocator cannot plan tasks that do not exist at plan time.
The trial's 30-62% was not an allocator failure; it measured the plan pool
against the wrong dispatch pool. The corrected mechanism:

- `Corpus.peek(lane, k)` (burn.py) is a pure, lock-protected simulation of
  the next k `next()` calls — byte-identical specs, zero side effects
  (proven by test: peek output == subsequent next() output; state untouched).
- `build_shadow_plan(..., pacer_candidates=...)` plans each peeked slot as
  a tier-3 allocation alongside the backlog units. Join key is a
  deterministic slot fingerprint `slot-" + sha256(lane|round|kind|objective|
  required_artifact)[:16]` — exactly the fields `_queue_add` preserves in
  the queue record, so a planned slot re-identifies the task the engine
  later creates. Backlog joins by queue task_id; on conflict, the backlog
  task_id wins. Stream slots multi-match (one corpus slot can dispatch
  many tasks via requeues).
- `coverage_report()` implements the restated predicate:
  `coverage = planned_for / dispatched_in_scope`, where in-scope =
  planned backlog task_ids + planned stream slots. `planned_for` counts
  MATCH + ORDER_DIFF + PROVIDER_DIFF (a plan was produced, even if it
  diverged). Dispatched tasks outside plan scope (beyond the
  SHADOW_STREAM_PEEK=32 horizon, or from paths invisible at plan time) are
  reported as `dispatched_out_of_scope` — scope boundaries, not allocator
  failures, never silently dropped. `coverage=None` (vacuous) must NOT be
  read as a pass.
- Fingerprint integrity: on the real engine corpus, every slot collision
  is a prompt-excerpt-only duplicate (specs identical in all
  queue-preserved fields); the plan records `slot_collisions` and the
  invariant is a test. Distinct work (different required_artifact) never
  shares a slot.

Plans remain evidence-only: nothing in this lane alters dispatch, quota
acquisition, or any phase gate. Nothing advances to enforced/canary.

### Startup guard-evasion race: fixed, fail-closed

`_nvidia_paused` now initializes from persisted utilization via
`_init_nvidia_pause()`, called in `main()` before preflight/pacers: if
`budget.quota_state()` reports utilization >= the same 0.55 threshold
`budget_guard()` uses, the engine starts paused; if utilization is
unknown (budget read fails, NaN) it starts paused (fail-closed). The
preflight NVIDIA smoke check is skipped while the lane is paused at
startup (no spurious probe against a tripped guard). The 4-6 real
dispatches per engine start are closed. Proven by tests: 0.9 -> paused,
0.1 -> unpaused, raising quota_state -> paused, NaN -> paused, and
preflight performs zero nvidia calls while paused.

### Queued follow-up (out of this lane's write scope)

`11-migration.md` §4's Phase-1 predicate text still reads "plan produced
for >=95% of dispatched tasks"; it should be updated to the restated form
(over the dispatch-candidate intersection, per `coverage_report`'s
docstring) before the PIPE-010 re-run. Flagged, not edited — migration
spec text belongs to its owning lane.
