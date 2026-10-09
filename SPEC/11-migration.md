# SPEC §12.11 — Migration Plan: Minimal Pipeline, Additive-Only

**Status:** DRAFT specification (no code changed, nothing deployed).
**Re-scoped 2026-10-09 per OWNER DIRECTIVE — ARCHITECTURE SIMPLIFICATION,**
as amended by the **TIER MODEL UPDATE** (same day; numbering INVERTED —
Tier 1 is the TOP; tiers defined by context/responsibility scope, N=3 fixed).
The migration target is the MINIMAL pipeline:

**Prompts → Typed work order (checklist) → Partition / Group → tiered Assign →
Schedule → tiered Workers (T3 → T2 → T1) → Ledger → fixed retry rules → repeat**,
with deterministic check ops (Compare/Calculate, Compare-against-policy,
Calculate, Route/Track/Stop).

Tier model: **Tier 3** = single-check workers (ONE checklist item +
inputs/context + output + completion condition) · **Tier 2** = check-group
workers (GROUP of related items + Tier 3 results + shared context; local deps,
bounded in-group inconsistencies) · **Tier 1** = full-context developer (entire
checklist + objective + specs/constraints + Tier 2 results + evidence; owns
coherence + final integration). Scheduler ops: **Partition, Group, Assign,
Schedule, Record, Repeat**. Structural partitioning rule: Tier 3 ONLY if
performable with supplied context alone; related/dependent checks stay at
Tier 2. Prompts are developer-defined/supplied; the scheduler distributes,
never authors/judges. No fourth tier.

**Cut from the target:** semantic-judge LLM, hierarchy of validators,
LLM-debates-LLM layers, autonomous reinterpretation of the human's objective,
Tier-2 LLM glue with merge authority, LLM conflict resolution.

**Hard rules (unchanged):** additive-only; archive-don't-delete absolute; no
destructive git ops (`reset`, `stash`, `clean -f`, `checkout --force`,
`push --force`, history rewrite) anywhere; exact discovered symbols only —
never a second governor / router / ledger / scheduler / validator; measured
numbers only; Cap'n Maps BLOCKED.

**Reconciliation note:** `~/workspace/batch-compile/SPEC/` was empty when the
first draft was written (~11:50 PDT); this re-scoped draft supersedes it.
Reconcile against sibling deliverables before implementation.

---

## 1. Migration principles (minimal)

1. **The pipeline is new narrow modules beside existing ones.** New package
   `~/workspace/compute/pipeline/` with one module per stage:
   `prompts.py`, `workorder.py`, `partition.py`, `allocate.py`, `worker.py`,
   `checks.py`, `retry.py`. No existing file is rewritten.
2. **Existing components are reused by call, not by copy.** The five anchor
   components keep their contracts; the pipeline calls them (see §2 verdicts).
3. **Elaborate implementations get adapter-or-deprecate, never expansion.**
   Anything already built that the minimal pipeline does not need
   (semantic judges, validator hierarchies, debate layers, LLM glue) is marked
   DEPRECATION CANDIDATE in 14-traceability.md: it stays in the tree (archive,
   don't delete), it is not wired into the pipeline, and no new work extends it.
4. **Shadow before enforcement.** The allocator first *plans* while the existing
   `burn.py` engine *executes*; plans vs actuals are compared as receipts.
5. **State ownership unchanged.** Pipeline proposes; governor disposes; ledger records.
6. **Rollback = flag flip + archive**, never delete, never history rewrite.

---

## 2. Component-mapping verdicts (the reconciliation — authoritative)

Verdict vocabulary: **KEEP** = use as-is, zero changes · **EXTEND** = additive
change to the component itself (new function, flag-guarded, default-off) ·
**DEPRECATE** = not used by the minimal pipeline; stays in the tree, no new work
extends it · **NEW** = new narrow module beside existing ones.

### 2a. Anchor components (the five)

| Component (exact file/symbol targets) | Verdict | Minimal-pipeline role |
|---|---|---|
| `~/workspace/compute/queue.py` — `queue.add` (l39), `queue.mark` (l114), `queue.drain` (l125), `QUEUE_STATUSES` (l35–36) | **KEEP** | Route/Track: partitioned tasks are queued, marked, drained via the existing lifecycle. No new queue. |
| `~/workspace/compute/dispatch.py` — `_fold_state` (l112–156), `create_dispatch`, `mark_executing`, `complete_dispatch`, `fail_dispatch`, `supervised_execute`, `reconcile` (l164–269) | **KEEP** | Track: worker runtime records execution through the existing fold. `pipeline/worker.py` calls it; never re-implements it. |
| `~/workspace/compute/envelope.py` — `wrap` (l144), `verify` (l169), `verify_chain` (l200); `proof-ledger/rs/src/envelope.rs` | **KEEP** | Ledger contracts: every pipeline receipt sealed with the existing v1 envelope. No second envelope. |
| `~/workspace/compute/ledger.py` — `record()` (l122), `verify_envelopes()` (l155), `request_hash_for()` (l42) | **KEEP** | Ledger: append-only execution records. Pipeline emits via `record()`; never writes the jsonl directly. |
| `~/workspace/compute/governor.py` — `govern()` | **KEEP** | Compare-against-policy: allocator proposes, `govern()` disposes allocation. `MUSE_PROPOSES_GOVERNOR_DISPOSES` holds end to end. |

### 2b. Supporting components (reused by call)

| Component | Verdict | Role |
|---|---|---|
| `~/workspace/compute/router.py` — `route()`, `_route_impl()`, `route_with_receipt()` | **KEEP** | Allocator consumes routing decisions; never re-routes. |
| `~/workspace/compute/budget.py`, `nvidia_rpm.py` (`acquire()`), `adapters/gemini_rpm.py` | **KEEP** | Allocator quota-math inputs; buckets stay the hard enforcement. |
| `~/workspace/compute/court.py` — `derive_status` (l94), `file_claim` (l82) | **KEEP** | Compare-against-policy for acceptance: deterministic check op, not an LLM judge. |
| `~/workspace/compute/adapters/nvidia.py` (`execute`), `adapters/gemini.py` (`execute`) | **KEEP** | Worker runtime execution backends. |
| `~/workspace/compute/burn.py` — engine, `budget_guard()` (l90), pacers | **EXTEND** | One additive, flag-guarded entry `run_pipeline_cycle()` hosting the minimal loop (Prompts→…→repeat). Default off = byte-identical current behavior. This avoids a second driver loop. |
| CANON (`~/workspace/canon/`, `Canon::open`, `canon snapshot`) | **KEEP** | Read-only normative basis for check ops. |
| `~/workspace/exchange/worker.js` v0.6.14 | **KEEP — no touch** | Out of the minimal pipeline's scope entirely. |
| LiteBox / `liteboxd` | **KEEP — optional** | Not required by the minimal pipeline. Cooperative-witnessing role only (f7); never a gate. |
| `~/workspace/bin/devgraph.py` (`ready`, `enables` semantics) | **KEEP** | Partitioner may read dev-graph conventions; not a dependency. |

### 2c. New narrow modules (the minimal pipeline itself)

| Module | Stage | Verdict |
|---|---|---|
| `~/workspace/compute/pipeline/prompts.py` | Prompts | **NEW** — versioned typed prompt registry (`register`, `get(prompt_id, version)`, `pin`) |
| `~/workspace/compute/pipeline/workorder.py` | Typed work order | **NEW** — `WorkOrder/1` schema + `validate_workorder()` |
| `~/workspace/compute/pipeline/partition.py` | Partition + Group ops | **NEW** — Partition: checklist → typed Tier 3 units; Group: related/dependent items → Tier 2 bundles; structural rule (`can_standalone`) |
| `~/workspace/compute/pipeline/allocate.py` | tiered Assign + Schedule | **NEW** — tiered Assign (T3 units / T2 bundles / T1 kit), Schedule ordering T3→T2→T1, quota math + reservation ledger + `govern()` consult |
| `~/workspace/compute/pipeline/worker.py` | tiered Workers | **NEW** — tier-scoped envelopes (`t3_envelope` / `t2_envelope` / `t1_envelope`, progressively broader context), thin wrapper over `dispatch.py` + adapters |
| `~/workspace/compute/pipeline/checks.py` | Deterministic check ops | **NEW** — compare/calculate, compare-against-policy, calculate, route/track/stop |
| `~/workspace/compute/pipeline/retry.py` | Fixed retry rules | **NEW** — deterministic failure-class → action table |

### 2d. Deprecation candidates (elaborate — adapter-or-deprecate, never expand)

These exist in the tree and stay there (archive-don't-delete). They are NOT
wired into the minimal pipeline, and no backlog task extends them. Full
justifications in 14-traceability.md.

| Candidate | Treatment |
|---|---|
| Semantic-judge LLM (any LLM-as-judge of artifact quality) | **DEPRECATE** — replaced by `checks.py` compare/calculate against typed acceptance criteria |
| Hierarchy of validators as a runtime layer (per-task `independent_verifier` 11-gate / `pl_canon_verifier` 17-gate runs) | **DEPRECATE from pipeline** — kept as offline periodic audit tooling; pipeline acceptance is `court.derive_status` + deterministic checks |
| LLM-debates-LLM decision layers | **DEPRECATE** — single deterministic allocator; no debate machinery |
| Autonomous reinterpretation of the human's objective | **DEPRECATE** — work-order objective is human-immutable; partitioner applies explicit rules only |
| Tier-2 LLM glue with merge authority / LLM conflict resolution | **DEPRECATE** — integration is typed work orders producing patch artifacts; merge is deterministic checks + authorized scope |
| 9-stage exchange pipeline as the scheduler's lifecycle | **DEPRECATE from pipeline scope** — minimal lifecycle is work-order → tasks → terminal; exchange worker untouched |
| PROVENANCE-ENFORCEMENT v2 as a pipeline dependency | **DEPRECATE as requirement** — pipeline provenance rests on v1 envelopes (existing & verified); v2 extends later, never blocks |

**What is explicitly NOT created:** no second queue, dispatch, router, governor,
ledger, envelope, verifier, prompter, partitioner, or allocator.

---

## 3. Feature flags (exact contract)

```
PIPELINE_MODE=off        # default; burn.py ignores the pipeline entirely
PIPELINE_MODE=shadow     # allocator builds plans for every burn cycle;
                         # burn.py executes as today; plans vs actuals compared as receipts
PIPELINE_MODE=enforced   # burn.py runs run_pipeline_cycle(): the minimal loop;
                         # governor/router/buckets still authorize every dispatch
PIPELINE_KILL=1          # overrides any mode to off-semantics immediately
```

- Flag read: `~/workspace/compute/pipeline/flags.py::mode()` — env read at call
  time, never cached across cycles, so a kill takes effect on the next cycle.
- `run_pipeline_cycle()` MUST be a no-op returning the legacy path when mode is
  `off` or kill is set.
- Flag state recorded in every cycle receipt (mode value + source).

---

## 4. Rollout: shadow / observe-first (4 phases)

### Phase 0 — Scaffolding (no behavior change)
- Create `~/workspace/compute/pipeline/` with `flags.py` + `workorder.py` only.
- `burn.py` gains `run_pipeline_cycle()` stub returning the legacy path; flag defaults `off`.
- Acceptance: reference burn dry-run reproduces pre-change `burn.STATUS.json`
  counter shape with flags unset.

### Phase 1 — Shadow (observe-first)
- Allocator (`allocate.py`) builds per-cycle allocation plans from queue state +
  quota state + `govern()` decisions; `burn.py` executes as today; comparator
  (in `checks.py`) writes `pipeline-shadow-receipts.jsonl` with divergence classes
  (`MATCH`, `ORDER_DIFF`, `PROVIDER_DIFF`, `UNPLANNED_DISPATCH`, `PLAN_UNEXECUTED`).
- **No dispatch is altered by a plan in this phase.** Plans are evidence only.
- Shadow acceptance (gate to Phase 2): ≥3 consecutive burn windows with
  (a) zero allocator crashes,
  (b) coverage = planned_for / dispatched_in_scope ≥ 95%, where in-scope =
      planned backlog task_ids + planned pacer-stream slots (per the restated
      predicate; out-of-scope dispatches reported separately as scope
      boundaries, never silently dropped; coverage=None is vacuous, not a pass),
  (c) every shadow receipt chain-verifies via `envelope.verify_chain`.
  (Restated 2026-10-09: the allocator plans the engine's dispatch-candidate set
  — backlog top-32 plus peeked pacer-stream slots — so the predicate measures
  the planned fraction of what was actually dispatched.)

### Phase 2 — Canary enforced (single scope)
- `PIPELINE_MODE=enforced` on ONE campaign/scope only. Governor/router/buckets
  unchanged — enforced allocations still pass `govern()` and the RPM buckets.
- Rollback drill required: `PIPELINE_KILL=1` mid-cycle; verify `burn.py`
  completes on the legacy path with zero lost tasks (`dispatch.reconcile()`:
  every dispatch reaches a terminal fold state).

### Phase 3 — Full enforcement
- `PIPELINE_MODE=enforced` globally. Shadow comparator keeps running as a
  permanent drift detector.

---

## 5. Per-component rollback procedures

| Component | Rollback trigger | Procedure (no deletions, no history rewrite) |
|---|---|---|
| `pipeline/` package | Any phase | `PIPELINE_KILL=1` (immediate) → `PIPELINE_MODE=off` (durable). Superseded versions archived to `~/workspace/archive/batch-compile/pipeline-<date>/`. Existing stores untouched. |
| `burn.py` `run_pipeline_cycle()` | Regression | Flag off ⇒ never called; additive and inert. Removal, if ever needed, is a normal forward commit removing the hunk — never reset/revert surgery. |
| Shadow receipts (`pipeline-shadow-receipts.jsonl`) | Corruption | Append-only; corrupt tail repaired by PL `repair()` semantics (amputate tail, record the repair as a new entry). Never rewrite history. |
| Reservation ledger (`pipeline-reservations.jsonl`) | Crash mid-cycle | Startup replay; TTL-expired reservations released; in-flight past `lease_expiry` → `EXPIRED` + replan (mirrors worker.js claim-expiry semantics). |
| `exchange/worker.js`, CANON, PL, governor, router, court, queue, dispatch, envelope, ledger | N/A — untouched or keep-verdict | No rollback needed; no migration writes to their stores. |
| Flag misconfiguration | Flag stuck | `flags.mode()` reads env at call time; fixing the env fixes the next cycle. |

**Rollback acceptance:** post-rollback reference burn dry-run reproduces the
pre-migration `burn.STATUS.json` counter shape.

---

## 6. Branch / worktree strategy

1. **Isolated worktrees:** one `git worktree` per lane under
   `~/workspace/worktrees/pipe-<task-id>/`, branched from mainline. Lanes never
   share a working tree.
2. **Forbidden in every lane brief** (brief-lint gate
   `~/workspace/full-send/brief-lint.sh <brief>` passes before dispatch):
   `git reset` (any mode), `git stash`, `git clean -f`, `checkout`/`switch --force`,
   `push --force`, `rebase`/`amend`/`filter-branch`/`filter-repo`/BFG.
3. **Selective staging** for mixed trees; fixes committed same-turn;
   falsification entries committed with the fix they record.
4. **Merge gates:** a lane merges only when (a) acceptance tests green in the
   worktree, (b) no destructive git op in its history, (c) compatible
   (no existing symbol's contract altered — additive only), (d) authorized
   (dispatch-gate scope ALLOW).
5. **Archive-don't-delete:** superseded branches/worktrees archived, never deleted.

---

## 7. Data migration (new files only)

| New file | Writer | Lifecycle |
|---|---|---|
| `~/workspace/compute/pipeline-plans.jsonl` | `allocate.py` | append-only; `prev_hash`-chained like the dispatch fold |
| `~/workspace/compute/pipeline-shadow-receipts.jsonl` | `checks.py` comparator | append-only; sealed via existing `ledger.record()` envelope path |
| `~/workspace/compute/pipeline-reservations.jsonl` | `allocate.py` | append-only reservation ledger with TTL + expiry sweep |
| `~/workspace/compute/pipeline-workorders/` | `workorder.py` | versioned work-order snapshots, content-addressed by sha256 |
| `~/workspace/compute/pipeline-prompts/` | `prompts.py` | versioned prompt registry entries, content-addressed |

**No existing file format changes.** `queue.jsonl`, `dispatches.jsonl`,
`executions.jsonl`, `envelopes.jsonl`, `claims.jsonl`, PL `ledger.jsonl`,
CANON stores: schemas untouched.

---

## 8. Migration acceptance (whole-plan)

1. Phase 0: reference burn dry-run counters unchanged with flags unset.
2. Phase 1: shadow predicates met (§4) over ≥3 burn windows.
3. Phase 2: canary completes; kill drill recovers with zero lost tasks
   (`dispatch.reconcile()` — every dispatch terminal).
4. Phase 3: enforced mode runs a full campaign; `court.derive_status`
   ESTABLISHED for the migration claim with PL-bound receipts.
5. Every phase: brief-lint clean on all lane briefs; no destructive git op in
   any lane history.

---

## Provider use

None — direct synthesis from evidence bundle f1–f8 (no NVIDIA NIM generation,
no Gemini critique), to preserve exact symbol grounding. Fallback per task
authorization ("record `direct` fallback in receipts").
