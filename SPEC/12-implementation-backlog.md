# SPEC §12.12 — Dependency-Ordered Implementation Backlog (Minimal Pipeline + 3-Tier Model)

**Status:** DRAFT specification. No code written by this file.
**Re-scoped 2026-10-09 per OWNER DIRECTIVE — ARCHITECTURE SIMPLIFICATION,**
as amended by the **TIER MODEL UPDATE** (same day).

Tier model (numbering INVERTED — Tier 1 is the TOP; tiers defined by
context/responsibility scope, NOT model capability; N=3, fixed; no fourth tier):
- **Tier 3:** single-check workers — ONE numbered goal + inputs/context +
  output + completion condition.
- **Tier 2:** check-group workers — GROUP of related goals + Tier 3 results +
  shared context; local deps; bounded in-group inconsistencies.
- **Tier 1:** full-context developer — the entire work order (all goals) +
  objective + specs/constraints + Tier 2 results + evidence; owns coherence +
  final integration.

Scheduler ops: **Partition, Group, Assign, Schedule, Record, Repeat**.
Structural partitioning rule: **Tier 3 ONLY if performable with supplied context
alone; related/dependent checks stay at Tier 2.**
Prompts are developer-defined/supplied; the scheduler distributes, never
authors/judges.

**WORK-ORDER INPUT SPEC (owner delta, same day): the work order is THE
interface** — a plain-text prompt with Objective, Development rules, and
individually numbered Goals (human-written or any-LLM-written, both equally
valid). Governing line: *the work order defines the requested work; the
scheduler defines its allocation and execution.* Scheduler behavior is
deterministic ONLY:
(a) explicit goal boundaries + registered goal types construct the work graph;
(b) dependencies/metadata inline or in a simple accompanying manifest;
(c) each numbered goal is the DEFAULT unit of work — the partitioner may split
a goal ONLY when its type explicitly permits subdivision (encoded partitioner rule);
(d) related goals may be grouped for Tier 2; Tier 1 receives the entire work order;
(e) the scheduler NEVER uses an LLM to author, normalize, or semantically
validate the work order — structural parsing + deterministic ops only;
(f) malformed structure is reported plainly as an error; ambiguous intent is
NEVER silently reinterpreted by a judge model.

Data flow: T3 units run first (max parallelism) → T2 bundles consume T3 results
where referenced → T1 kit consumes all T2 results + evidence → deterministic
check ops gate each tier boundary → ledger records everything → fixed retry
rules → repeat until terminal.

Cut from scope: semantic-judge LLM, validator hierarchies, LLM-debates-LLM,
autonomous objective reinterpretation, Tier-2 LLM glue / LLM merge authority.

**Conventions:** task IDs `PIPE-001…`; estimates S = ~1 lane-wave, M = 2–3,
L = 4+. Every task carries an **extend-vs-new verdict** on the five anchor
components (`queue.py`, `dispatch.py`, `envelope.py`, `ledger.py`, `governor.py`)
from the reconciliation in 11-migration.md §2a (all five = **KEEP**; pipeline
modules are **NEW** beside them; `burn.py` = **EXTEND** flag-guarded).
All new code under `~/workspace/compute/pipeline/`. Existing files are read or
called, never rewritten.

---

## Phase A — Types & registries

### PIPE-001 — Prompts registry (distribute, never author)
- **Depends on:** none.
- **Targets:** NEW `~/workspace/compute/pipeline/prompts.py` —
  `PROMPTS_VERSION="prompts/1"`, `register(prompt_id, version, text, sha256)`,
  `get(prompt_id, version) -> str`, `pin(prompt_id) -> (version, sha256)`.
  NEW `~/workspace/compute/pipeline-prompts/` (content-addressed entries).
- **Rules:** prompts are developer-defined/supplied, versioned, immutable once
  registered; the scheduler **distributes** pinned `(prompt_id, version, sha256)`
  to tier envelopes — it never authors, rewrites, judges, or selects prompt
  text (test asserts no code path generates prompt content); re-register of the
  same id+version with different text → rejected.
- **Extend-vs-new:** queue.py KEEP · dispatch.py KEEP · envelope.py KEEP ·
  ledger.py KEEP · governor.py KEEP · this module NEW.
- **Acceptance:** (1) register→get roundtrip byte-identical; (2) text change
  under same id+version → rejected; (3) `pin()` resolves latest; (4) static
  check: no prompt-text generation in the module (grep for model-call imports → empty).
- **Test:** `cd ~/workspace/compute/pipeline && python3 -m pytest prompts_test.py -q`.
- **Estimate:** S.

### PIPE-002 — Work-order structural parser (plain-text; no LLM, no reinterpretation)
- **Depends on:** none.
- **Targets:** NEW `~/workspace/compute/pipeline/workorder.py` —
  `parse_workorder(text) -> (TypedWorkOrder | None, errors: list[str])`,
  `validate_parsed(pw) -> (bool, [str])`, `WORKORDER_TEXT_SPEC` (the grammar,
  documented in-module). Emits `lucidota-sched/1#typed-work-order` (03 §18; concrete field layout in the §13 batch spec below).
- **The work-order format (normative, minimal, structural):**
  ```
  Objective: <one or more lines, until the next section header>

  Development rules:
  - <rule line>
  - <rule line>

  Goal 1 [<type-id>]: <title>
  <free body lines>
  Depends-On: 2, 3
  Group: <group-id>
  Done-When: <shell command>

  Goal 2 [<type-id>]: <title>
  ...
  ```
  Header grammar: `Objective:`, `Development rules:`, `Goal <N> [<type-id>]: <title>`
  (`[<type-id>]` optional → defaults to registered type `generic`). Trailer lines
  (`Depends-On:`, `Group:`, `Done-When:`) are the only recognized metadata keys.
  Dependencies/metadata may instead live in a simple sidecar manifest
  `<workorder>.manifest.json`; inline and manifest conflicting → plain error
  (deterministic: conflict is an error, never silent precedence).
- **Rules:** structural parsing + deterministic ops ONLY. The scheduler NEVER uses
  an LLM to author, normalize, or semantically validate the work order — the module
  has no model-call imports (static check in test). Malformed structure →
  plain error strings (`goal 3: <problem>` / `workorder: <problem>`); ambiguous
  intent → error, NEVER silently reinterpreted (there is no reinterpretation path
  to test — the test asserts ambiguous fixtures produce errors, not guesses).
  Plain errors include: numbering not starting at 1 / non-contiguous / duplicate;
  unknown goal type (names the type + "register it first"); Depends-On pointing
  at an unknown goal; empty Objective; zero goals; unknown trailer key.
- **Extend-vs-new:** five anchors KEEP · this module NEW.
- **Acceptance:** (1) valid work order → parsed representation byte-stable;
  (2) each malformed fixture → the expected plain error, no exception leak;
  (3) ambiguous-intent fixture → error, not a guessed parse;
  (4) static check: no model-call imports in the module.
- **Test:** `python3 -m pytest workorder_test.py -q` (≥20 cases: valid shapes,
  every error class, ambiguity fixtures).
- **Estimate:** M (was S — parsing + error taxonomy is real work).

### PIPE-003 — Goal-type registry + Partition/Group + subdivision rule
- **Depends on:** PIPE-002 (consumes `lucidota-sched/1#typed-work-order`; codes against the
  pinned schema).
- **Targets:**
  - NEW `~/workspace/compute/pipeline/goaltypes.py` — the **goal-type registry**:
    `register_type(type_id, subdivisible: bool, description)`,
    `get(type_id) -> GoalType`, `types() -> list`. Seeded with `generic`
    (`subdivisible=false`). Developer-populated; the scheduler reads it, never
    infers types.
  - NEW `~/workspace/compute/pipeline/partition.py` —
    - `maybe_subdivide(goal, gtype, constraints) -> list[goal]` — the
      **subdivision-permission rule**: a goal is split ONLY if
      `gtype.subdivisible` is true. Split is deterministic: when the goal body
      exceeds `max_input_tokens`, split on paragraph boundaries into numbered
      sub-goals `N.a, N.b, …` (stable order, hash-pinned). Non-subdivisible
      oversized goal → stays ONE unit; the oversize is reported in the receipt,
      never silently truncated.
    - `can_standalone(goal, pw) -> bool` — the **structural partitioning rule**:
      TRUE iff `depends_on` empty AND every `context_ref` resolves from
      work-order-supplied context AND `group` empty. No LLM judgment.
    - `partition_checklist(pw) -> list[T3Assignment]` — **Partition op**: every
      standalone (sub-)goal becomes a Tier 3 unit
      (`lucidota-sched/1#worker-assignment-envelope` (tier 3): one goal + inputs/context + output + completion condition).
      Each numbered goal is the DEFAULT unit of work — subdivision is the only
      exception, and only by type permission.
    - `group_related(pw, t3_units) -> list[T2Assignment]` — **Group op**: goals
      sharing a `group` id → one Tier 2 bundle; non-standalone ungrouped goals →
      singleton Tier 2 bundles; bundles record `t3_result_refs` + `shared_context_refs`.
    - `partition_hash(units, bundles) -> str` — determinism pin.
- **Rules:** Partition and Group are deterministic (same parsed work order →
  same units/bundles); the subdivision rule is the ONLY way a goal splits;
  related/dependent goals stay at Tier 2, never forced to Tier 3.
- **Extend-vs-new:** five anchors KEEP · both modules NEW.
- **Acceptance:** (1) determinism: 3 runs, identical hash; (2) non-subdivisible
  oversized goal → one unit + oversize reported; (3) subdivisible oversized goal →
  deterministic sub-units; (4) dependent goal → Tier 2, never Tier 3;
  (5) grouped goals → single bundle; (6) cycle in Depends-On → refused naming
  the cycle (surfaced from parser errors).
- **Test:** `python3 -m pytest partition_test.py -q` + `goaltypes_test.py -q`
  (registry: duplicate registration rejected; unknown type lookup → plain error).
- **Estimate:** M.

## Phase B — Allocation & execution (tiered)

### PIPE-004 — Allocator: tiered Assign + Schedule + quota math
- **Depends on:** PIPE-002, PIPE-003.
- **Targets:** NEW `~/workspace/compute/pipeline/allocate.py` —
  - `assign_tiered(t3_units, t2_bundles, t1_kit | None, quota_snapshot) -> list[Allocation]` —
    **Assign op**: T3 single checks → T3 workers; T2 groups → T2 workers;
    T1 complete kit → T1 worker. the allocation record (`lucidota-sched/1#quota-reservation` join) carries `tier: 1|2|3` + `unit_ref`.
  - `schedule_order(assignments, terminal_results) -> list[Allocation]` —
    **Schedule op**: T3 units schedulable immediately (max parallelism); T2
    bundles schedulable when their `t3_result_refs` are terminal; T1 kit
    schedulable when ALL T2 bundles are terminal (+ evidence refs present).
    Tier ordering T3→T2→T1 is structural, not heuristic.
  - `reserve(pool_id, req) -> Reservation | Refusal`, `release(id)`,
    `reconcile(id, actual)`, `sweep_expired()` — quota math.
  NEW `~/workspace/compute/pipeline-reservations.jsonl` (append-only).
- **Rules:** pools seeded from MEASURED values only (f8): NVIDIA `rpm_ceiling=39`
  (`nvidia_rpm.py::DEFAULT_RPM`), Gemini `rpm_ceiling=10` (`gemini_rpm.py`);
  TPM/concurrency = symbolic `UNMEASURED` (UF-007); ai-router caps `DECLARED_ONLY`
  (UF-009); reservation atomic, TTL 120s; **every allocation consults
  `governor.govern()`** (allocator proposes, governor disposes); refusal carries
  a `governor.REASON_CODES` code; T1 kit is assembled by the allocator (entire
  checklist + objective + specs/constraints + T2 results + evidence), never by a worker.
- **Extend-vs-new:** queue.py KEEP (reads queue state) · dispatch.py KEEP ·
  envelope.py KEEP · ledger.py KEEP · governor.py KEEP (called, not copied) ·
  this module NEW.
- **Acceptance:** (1) no double-spend under 32 concurrent reservers;
  (2) every allocation cites a governor receipt; (3) T2 bundle with pending T3
  ref → not scheduled until the ref is terminal; (4) T1 kit scheduled only after
  all T2 terminal; (5) expired reservations swept.
- **Test:** `python3 -m pytest allocate_test.py -q` (simulated clock, concurrent
  property test, kill-and-replay; `govern_fn` injectable stub; 0 provider calls).
- **Estimate:** M.

### PIPE-005 — Worker runtime: tier-scoped envelopes (progressively broader context)
- **Depends on:** PIPE-001, PIPE-002.
- **Targets:** NEW `~/workspace/compute/pipeline/worker.py` —
  - `t3_envelope(unit, prompt_text) -> dict` — ONE numbered goal + its
    inputs/context + output spec + completion condition + pinned prompt ref.
    MUST contain no refs outside the unit's allowlist (test-enforced).
  - `t2_envelope(bundle, t3_results, prompt_text) -> dict` — group items +
    T3 results + shared context. Broader than T3.
  - `t1_envelope(kit, prompt_text) -> dict` — the entire work order (all goals) + objective +
    specs/constraints + Tier 2 results + evidence. Broadest.
  - `run_unit(envelope, allocation) -> AttemptRecord` — thin wrapper: envelope →
    `dispatch.create_dispatch` → adapter `execute()` (or
    `dispatch.supervised_execute`) → artifact + receipt →
    `dispatch.complete_dispatch` / `fail_dispatch`. Tier recorded on the attempt.
- **Rules:** context breadth monotonic T3 < T2 < T1 (asserted in test);
  a worker response can never self-accept, raise its own budget, authorize a
  tool, or change policy (named violations, mirroring
  `indy-reads/src/governor.rs` `AiProposal::sanitize`); deterministic timeout
  from the work order; prompts distributed from the registry, never authored here.
- **Extend-vs-new:** queue.py KEEP · dispatch.py KEEP (fold is the execution
  record) · envelope.py KEEP · ledger.py KEEP (receipts via `record()`) ·
  governor.py KEEP · this module NEW.
- **Acceptance:** (1) T3 envelope for a unit contains zero out-of-allowlist refs;
  (2) ref-count monotonic across tiers on fixtures; (3) 10 adversarial responses →
  rejected with named violation; (4) timeout → `fail_dispatch`, attempt recorded;
  (5) every attempt emits an envelope-sealed receipt.
- **Test:** `python3 -m pytest worker_test.py -q` (fake adapters; 0 provider calls).
- **Estimate:** M.

### PIPE-006 — burn.py minimal pipeline mode (EXTEND, flag-guarded)
- **Depends on:** PIPE-004, PIPE-005.
- **Targets:** EXTEND `~/workspace/compute/burn.py` — additive function
  `run_pipeline_cycle(workorder_path)` implementing the loop
  Partition → Group → tiered Assign → Schedule → tiered Workers → Record →
  checks → retry → Repeat, called ONLY when `PIPELINE_MODE=enforced`
  (see 11-migration.md §3). NEW `~/workspace/compute/pipeline/flags.py` —
  `mode()`, `killed()` (env read at call time, never cached).
- **Rules:** additive hunk only; no existing burn symbol's signature changes;
  mode `off`/unset/kill ⇒ legacy path, reference dry-run reproduces pre-change
  `burn.STATUS.json` counter shape; avoids a second driver loop (hard rule).
- **Extend-vs-new:** burn.py EXTEND (flag-guarded additive) · five anchors KEEP ·
  `flags.py` NEW.
- **Acceptance:** flag matrix (off/shadow/enforced × kill) → correct path each;
  `git diff` shows only the additive hunk + import.
- **Test:** `python3 -m pytest pipeline_mode_test.py -q` (in `pipeline/`).
- **Estimate:** M.

## Phase C — Checks, ledger, retry (tier-aware)

### PIPE-007 — Deterministic check ops (per-tier completion)
- **Depends on:** PIPE-002, PIPE-005.
- **Targets:** NEW `~/workspace/compute/pipeline/checks.py` —
  - `compare_calculate(artifact, acceptance) -> CheckResult` — run the work
    order's acceptance commands, compute pass/fail, hash artifacts. Pure calculation.
  - `check_t3_completion(unit, artifact) -> CheckResult` — the unit's completion
    condition executed deterministically (ONE numbered goal ⇒ one verdict).
  - `check_t2_consistency(bundle, artifacts) -> CheckResult` — bounded in-group
    inconsistency check: deterministic cross-item comparisons declared in the
    bundle (e.g., schema agreement, non-contradiction of measured values);
    inconsistencies beyond the bound → fail, never "resolved" by judgment.
  - `check_t1_coherence(kit, integrated_artifact) -> CheckResult` — work-order
    acceptance checks over the integrated artifact (T1 owns coherence; the check
    verifies it deterministically).
  - `compare_against_policy(task, decision) -> CheckResult` — `governor.govern()`
    for allocation; `court.derive_status()` for claim acceptance. Policy oracle, not judge.
  - `calculate(reservation, actual) -> CheckResult` — quota reconciliation arithmetic.
  - `route_track_stop(task, action) -> CheckResult` — `queue.mark`, dispatch fold
    transitions, kill-switch. State mechanics only.
  `CheckResult = {task_id, tier, op, pass, evidence_refs, measured}`.
- **Rules:** no generative model consulted by any check op; unmeasurable →
  `unknown`, never inferred-pass (INV-02); tier boundary gates: T3 results feed
  T2 only through `check_t3_completion` pass; T2 results feed T1 only through
  `check_t2_consistency` pass.
- **Extend-vs-new:** five anchors KEEP (governor.py + court.py called) ·
  this module NEW.
- **Acceptance:** (1) forged bare-True evidence → `compare_against_policy`
  fail/unknown, never pass (mirrors `canon_court_e2e.py` case 2);
  (2) T2 bundle with contradictory item outputs beyond bound → fail;
  (3) all ops green on synthetic fixtures with zero provider calls.
- **Test:** `python3 -m pytest checks_test.py -q`.
- **Estimate:** M.

### PIPE-008 — Ledger contract pin + conformance test
- **Depends on:** none (tests existing code).
- **Targets:** NEW `~/workspace/compute/pipeline/ledger_contract_test.py` —
  pins the pipeline's ledger contract: every pipeline action recorded via
  `ledger.record()`; every receipt sealed with `envelope.wrap` / verified by
  `envelope.verify_chain`; tier + unit/bundle/kit refs carried on attempt
  records; corrections are new entries (never edits).
  NEW `~/workspace/compute/pipeline/LEDGER-CONTRACT.md` (one page: symbols,
  fields, guarantees).
- **Rules:** no code changes to `ledger.py`/`envelope.py` (KEEP verified by the
  test passing against the current tree); test failure blocks the pipeline —
  the contract is not "fixed" by the pipeline.
- **Extend-vs-new:** ledger.py KEEP · envelope.py KEEP · others KEEP ·
  test + doc NEW.
- **Acceptance:** `python3 -m pytest ledger_contract_test.py -q` → green against
  the unmodified tree; tamper fixture → `verify_chain` raises.
- **Test:** as above. **Estimate:** S.

### PIPE-009 — Fixed retry rules
- **Depends on:** PIPE-007.
- **Targets:** NEW `~/workspace/compute/pipeline/retry.py` —
  `FAILURE_CLASSES` (maps to worker.js taxonomy:
  RETRYABLE/PERMANENT/POLICY/AUTH/QUOTA/CAPABILITY/PROVIDER/VERIFICATION_FAILURE),
  `next_action(class, attempt, tier) -> retry_at_tail | dead_letter | blocked | failed`,
  `MAX_ATTEMPTS=5`, per-class backoff table (deterministic).
  Tier note: T1-kit failure → `blocked` (never silently re-run the full-context
  developer; a failed integration is a human-visible event), T3/T2 follow the
  standard table. NEW `~/workspace/compute/pipeline-dead-letter.jsonl`.
- **Rules:** retries to the queue tail, never head-of-line; dependency-blocked
  stays blocked; every task terminates in
  `done | failed | blocked | dead_letter | explicitly_unresolved` — liveness by
  bounded attempts.
- **Extend-vs-new:** five anchors KEEP · this module NEW.
- **Acceptance:** fault-injection — 200 synthetic tasks × 8 failure classes ×
  3 tiers → 100% terminal, 0 lost, 0 exceeding MAX_ATTEMPTS; T1 failure →
  `blocked`, never auto-retried.
- **Test:** `python3 -m pytest retry_test.py -q` (simulated clock; 0 provider calls).
- **Estimate:** M.

## Phase D — Rollout

### PIPE-010 — Shadow trial + acceptance report
- **Depends on:** PIPE-004, PIPE-006, PIPE-007.
- **Targets:** runbook execution (no new modules): 3 consecutive burn windows in
  `PIPELINE_MODE=shadow`; comparator in `checks.py` writes
  `pipeline-shadow-receipts.jsonl`; report at
  `~/workspace/batch-compile/SPEC/shadow-trial-report.md`.
- **Acceptance:** migration 11-migration.md §4 Phase-1 predicates (zero allocator
  crashes, ≥95% plan coverage, receipts chain-verify).
- **Estimate:** M (wall-clock bound by burn windows).

### PIPE-011 — Canary enforced + rollback drill
- **Depends on:** PIPE-010, PIPE-009.
- **Targets:** runbook execution: one scope in `PIPELINE_MODE=enforced`;
  mid-cycle `PIPELINE_KILL=1` drill; `dispatch.reconcile()` verifies zero lost tasks.
- **Acceptance:** canary completes; kill drill recovers on the legacy path.
- **Estimate:** M.

---

## Dependency graph (condensed)

```
PIPE-001 ─┐
PIPE-002 ─┼─→ PIPE-003 ─→ PIPE-004 ─→ PIPE-006 ─→ PIPE-010 ─→ PIPE-011
PIPE-008 ─┘         │            │──→ (tier boundary gates in PIPE-007)
PIPE-001 ─→ PIPE-005 ─→ PIPE-007 ─→ PIPE-009 ─→ PIPE-011
                    (tier envelopes)  (tier completion / consistency / coherence)
```

---

## §13 COMPLETION-CRITERION DELIVERABLE — First independently-dispatchable implementation batch

**Goal:** the minimal pipeline's **first working slice INCLUDING the 3-tier flow**
— after this batch, a driver can run work-order(numbered goals) → Partition (T3 units)
→ Group (T2 bundles) → tiered Assign → Schedule (T3→T2→T1) → tier completion
checks on synthetic input with zero provider calls.

**How independence is achieved:** the four lanes depend only on the **pinned
schema text in this brief** — not on each other's completion. PIPE-002
implements the schemas; the other three code against the brief text.
Post-batch, a conformance task (next batch) verifies all four against the
implemented validators. Pinned schemas are normative; a lane that finds a schema
defect records it in its receipt and codes to the brief — no freelanced schemas.

### Pinned interface (normative for this batch)

**The work order is THE interface** — plain-text. Governing line: *the work
order defines the requested work; the scheduler defines its allocation and
execution.* Human-written or any-LLM-written, both equally valid. The scheduler
NEVER uses an LLM to author, normalize, or semantically validate it.

**Plain-text work-order format (normative, minimal):**
```
Objective: <one or more lines, until the next section header>

Development rules:
- <rule line>
- <rule line>

Goal 1 [<type-id>]: <title>
<free body lines>
Depends-On: 2, 3
Group: <group-id>
Done-When: <shell command>

Goal 2 [<type-id>]: <title>
...
```
- `Goal <N> [<type-id>]: <title>` — `[<type-id>]` optional → `generic`.
  Numbering: starts at 1, contiguous, unique (else plain error).
- Trailer keys: `Depends-On:`, `Group:`, `Done-When:` only (unknown key → plain error).
- Dependencies/metadata may instead live in sidecar `<workorder>.manifest.json`;
  inline↔manifest conflict → plain error (never silent precedence).
- Malformed → plain error strings; ambiguous intent → error, never reinterpreted.

**Parsed representation** (what `parse_workorder` emits; lanes 2–4 code against this):

> **Identifier note (shared-identifiers rule):** every schema below is the canonical `lucidota-sched/1#<contract>` identifier from 03-schemas.md (§§18/21/20/6/5). Each emitted record carries `"schema": "lucidota-sched/1#<contract>"`; the field layouts here are the batch's concrete tier-scoped profiles of those contracts. T3/T2/T1 assignments are all `lucidota-sched/1#worker-assignment-envelope` (§21) with `tier` ∈ {3,2,1}.

**Typed work order** (`lucidota-sched/1#typed-work-order` — 03 §18):
```json
{
  "schema": "lucidota-sched/1#typed-work-order",
  "work_order_id": "wo-<12 hex chars>",
  "objective": "verbatim, immutable",
  "development_rules": ["<rule>"],
  "goals": [
    {"n": 1, "type": "<type-id>", "title": "<title>", "body": "<verbatim body>",
     "depends_on": [2], "group": "<id|null>", "done_when": "<cmd|null>"}
  ],
  "source_sha256": "<hex of the source text>",
  "created_by": "<actor>", "created_at": "<rfc3339>"
}
```

**T3 assignment** (`lucidota-sched/1#worker-assignment-envelope`, tier=3 — 03 §21): `{"schema": "lucidota-sched/1#worker-assignment-envelope", unit_id: "t3-<12hex>", tier: 3,
work_order_id, goal_n: 1, goal_ref: "1|1.a", inputs, output, completion, prompt_ref}` —
ONE goal (or sub-goal) + inputs/context + output + completion condition. No other goal's refs.

**T2 assignment** (`lucidota-sched/1#worker-assignment-envelope`, tier=2 — 03 §21): `{"schema": "lucidota-sched/1#worker-assignment-envelope", bundle_id: "t2-<12hex>", tier: 2,
work_order_id, group_id, goal_ns: [], t3_result_refs: [], shared_context_refs: [],
completion}` — GROUP of related goals + T3 results + shared context.

**T1 assignment** (`lucidota-sched/1#worker-assignment-envelope`, tier=1 — 03 §21): `{"schema": "lucidota-sched/1#worker-assignment-envelope", kit_id: "t1-<12hex>", tier: 1, work_order_id,
typed_work_order_ref, objective, specs_refs: [], constraints, t2_result_refs: [],
evidence_refs: []}` — **the entire work order** + Tier 2 results + evidence.

**Allocation record** (allocator join of `lucidota-sched/1#worker-assignment-envelope` §21 + `lucidota-sched/1#quota-reservation` §5): `{task_id, tier: 1|2|3, unit_ref,
provider, model, reservation_id, quota_snapshot, governor_receipt_ref, decided_at}`

**Check result** (`lucidota-sched/1#check-result` — 03 §20): `{task_id, tier,
op: "compare|compare-policy|calculate|route|track|stop|t3-completion|t2-consistency|t1-coherence",
pass: bool, evidence_refs: [], measured: {}}`

**Attempt record** (`lucidota-sched/1#attempt-record` — 03 §6): `{task_id, tier, attempt, allocation_ref,
artifact_ref, check_result_ref, terminal_state}`

Integer fields: i64 range (XIMPL-2 guard). Unknown fields: rejected.
`tier` outside {1,2,3}: rejected (no fourth tier).

### Shared driver preconditions (all four lanes)

- Worktree: `git worktree add ~/workspace/worktrees/pipe-<TASK> -b pipe/<task>-<date>`
  from mainline (verify `git rev-parse` at dispatch; else work in place under
  `~/workspace/compute/pipeline/`).
- Brief-lint: `~/workspace/full-send/brief-lint.sh <brief>` passes before start.
- Provider budget: **0 provider calls** — local-only.
- Permitted write scope per lane: `~/workspace/compute/pipeline/` ONLY
  (+ the lane's own test ledger path, cleaned up by tests).
- Commit same-turn; falsification entries (if any) committed with the fix.

### BATCH-1 TASK 1 — PIPE-002: Work-order structural parser (plain-text; no LLM)

- **Inputs:** the plain-text work-order format spec + `lucidota-sched/1#typed-work-order` schema
  text above; evidence f5 §3 (i64 contract).
- **Deliverables:** `pipeline/__init__.py`, `pipeline/workorder.py`
  (`parse_workorder`, `validate_parsed`, `WORKORDER_TEXT_SPEC`,
  `REQUIRED_FIELDS`, `ALLOWED_FIELDS`, tier validators),
  `pipeline/workorder_test.py` (≥20 cases).
- **Acceptance tests:** `cd ~/workspace/compute/pipeline && python3 -m pytest workorder_test.py -q`
  → green; demo: valid plain-text work order → stable parsed representation;
  every malformed fixture → the expected plain error; ambiguous-intent fixture →
  error, not a guessed parse; static check: no model-call imports in the module.
- **Dependency declarations:** NONE on other batch lanes (implements the pinned interface).
- **Permitted write scope:** `~/workspace/compute/pipeline/` only.
- **Resource budget:** 0 provider calls; local pytest; est. M.

### BATCH-1 TASK 2 — PIPE-003: Goal-type registry + Partition/Group + subdivision rule

- **Inputs:** `lucidota-sched/1#typed-work-order`, `lucidota-sched/1#worker-assignment-envelope` (tier 3), `lucidota-sched/1#worker-assignment-envelope` (tier 2) schema text above;
  rules: each numbered goal = DEFAULT unit of work; split ONLY if the goal's
  registered type has `subdivisible=true`; Tier 3 ONLY if `can_standalone`
  (Depends-On empty ∧ context_refs resolve from work-order context ∧ no Group).
- **Deliverables:** `pipeline/goaltypes.py` (`register_type`, `get`, `types`,
  seeded `generic`), `pipeline/partition.py` (`maybe_subdivide`,
  `can_standalone`, `partition_checklist`, `group_related`, `partition_hash`),
  `pipeline/goaltypes_test.py`, `pipeline/partition_test.py`.
- **Acceptance tests:** `python3 -m pytest goaltypes_test.py partition_test.py -q` → green;
  demo on a synthetic 6-goal work order (3 standalone, 2 grouped+dependent,
  1 singleton dependent, 1 oversized non-subdivisible): exactly 3 T3 units +
  2 T2 bundles; oversized goal stays one unit with oversize reported;
  dependent goal never lands in T3; determinism hash stable.
- **Dependency declarations:** NONE on other batch lanes (codes against pinned
  schema text; conformance to lane 1's parser verified post-batch).
- **Permitted write scope:** `~/workspace/compute/pipeline/` only.
- **Resource budget:** 0 provider calls; local pytest; est. M.

### BATCH-1 TASK 3 — PIPE-004: Allocator — tiered Assign + Schedule + quota math

- **Inputs:** pinned `lucidota-sched/1#worker-assignment-envelope` (tier 3), `lucidota-sched/1#worker-assignment-envelope` (tier 2), `lucidota-sched/1#worker-assignment-envelope` (tier 1), the allocation record (`lucidota-sched/1#quota-reservation` join) text above;
  measured seeds (f8): NVIDIA `rpm_ceiling=39`, Gemini `rpm_ceiling=10`;
  TPM/concurrency = `UNMEASURED`; ai-router caps `DECLARED_ONLY`. `govern_fn`
  injectable (stub at lane time; production `governor.govern` later).
- **Deliverables:** `pipeline/allocate.py` (`assign_tiered`, `schedule_order`,
  `reserve`, `release`, `reconcile`, `sweep_expired`, `UNMEASURED`,
  `assemble_t1_kit`), `pipeline/allocate_test.py`, `pipeline/QUOTA-SEEDS.md`.
- **Acceptance tests:** `python3 -m pytest allocate_test.py -q` → green; demo:
  tiered assignment of 3 T3 + 2 T2 + 1 T1 kit; `schedule_order` holds the T2
  bundle until its T3 ref is terminal and holds T1 until all T2 terminal;
  double-spend refused; every allocation carries `tier` + `governor_receipt_ref`.
- **Dependency declarations:** NONE on other batch lanes.
- **Permitted write scope:** `~/workspace/compute/pipeline/` only (+ test-local ledger).
- **Resource budget:** 0 provider calls; local pytest; est. M.

### BATCH-1 TASK 4 — PIPE-007: Deterministic check ops (per-tier completion)

- **Inputs:** pinned `lucidota-sched/1#check-result` + `lucidota-sched/1#worker-assignment-envelope` (tier 3) + `lucidota-sched/1#worker-assignment-envelope` (tier 2) + `lucidota-sched/1#worker-assignment-envelope` (tier 1) text above;
  ops: `compare_calculate`, `check_t3_completion`, `check_t2_consistency`,
  `check_t1_coherence`, `compare_against_policy` (injectable stub at lane time),
  `calculate`, `route_track_stop` (injectable stub).
- **Deliverables:** `pipeline/checks.py` (seven ops + `CheckResult`),
  `pipeline/checks_test.py`.
- **Acceptance tests:** `python3 -m pytest checks_test.py -q` → green; demo:
  T3 completion pass/fail on synthetic artifacts; T2 bundle with contradictory
  item outputs beyond bound → fail; T1 coherence runs the work-order acceptance
  checks; forged bare-True evidence → `compare_against_policy` fail/unknown,
  never pass; unmeasurable → `unknown`.
- **Dependency declarations:** NONE on other batch lanes.
- **Permitted write scope:** `~/workspace/compute/pipeline/` only.
- **Resource budget:** 0 provider calls; local pytest; est. M.

### Batch-1 driver checklist

- [ ] 4 worktrees created (or in-place scope confirmed), brief-lint passed ×4
- [ ] All 4 lanes dispatched in parallel (dependencies on brief text only)
- [ ] Each lane: tests green → commit same-turn → receipt
- [ ] Post-batch: `ls ~/workspace/compute/pipeline/` shows
      `__init__.py workorder.py workorder_test.py goaltypes.py goaltypes_test.py
      partition.py partition_test.py allocate.py allocate_test.py QUOTA-SEEDS.md
      checks.py checks_test.py`
- [ ] No file outside `~/workspace/compute/pipeline/` modified — verify per worktree
- [ ] Working-slice demo (driver-run, synthetic, 0 provider calls):
      parse plain-text work order → goal-type registry lookup → Partition (T3 units,
      subdivision only by type permission) → Group (T2 bundles) → tiered Assign →
      Schedule (T3→T2→T1 ordering with stub terminal results) →
      per-tier completion checks → all terminal states reached
- [ ] Next batch (PIPE-001, PIPE-005, PIPE-006, PIPE-008, PIPE-009) dispatchable
      once batch-1 is merged; conformance of lanes 2–4 against lane 1's validator
      is the first next-batch test

---

## Provider use

None — direct synthesis from evidence bundle f1–f8 (no NVIDIA NIM generation,
no Gemini critique), to preserve exact symbol grounding. Fallback per task
authorization ("record `direct` fallback in receipts").
