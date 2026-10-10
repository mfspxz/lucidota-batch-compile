# SPEC §12.14 — Traceability Matrix (Minimal Pipeline + 3-Tier Model)

**Status:** DRAFT specification.
**Re-scoped 2026-10-09 per OWNER DIRECTIVE — ARCHITECTURE SIMPLIFICATION,**
as amended by the **TIER MODEL UPDATE** (same day; numbering INVERTED —
Tier 1 is the TOP; N=3 fixed; tiers = context/responsibility scope).

Every requirement maps to the minimal set
{Prompts, Work order, Partitioner, Allocator, Workers, Ledger, Retry rules,
Deterministic check ops} or is marked **DEPRECATION CANDIDATE** (with
justification) or **BLOCKED** (missing fact in 13-unresolved-facts.md).

Classification vocabulary: **EXISTING AND VERIFIED** · **EXISTING BUT UNVERIFIED** ·
**REQUIRES EXTENSION** · **NEW WORK** · **BLOCKED** · **DEPRECATION CANDIDATE**.

Conventions: implementation points use exact discovered symbols; tests name
exact files + symbols. Backlog IDs (`PIPE-001…`) refer to 12-implementation-backlog.md.

---

## 1. Prompts & work order

| ID | Requirement | Minimal mapping | Implementation point (symbol + file) | Test (file + symbol) | Classification |
|---|---|---|---|---|---|
| R-PRM-01 | Versioned immutable prompts registry | Prompts | NEW `~/workspace/compute/pipeline/prompts.py` — `register`, `get`, `pin` | `pipeline/prompts_test.py` — register→get roundtrip, re-register rejection | NEW WORK |
| R-PRM-02 | Prompts developer-defined/supplied; scheduler distributes, never authors/judges | Prompts | `pipeline/prompts.py` — no authoring path (static: no model-call imports) | `pipeline/prompts_test.py` — authoring-absence check | NEW WORK |
| R-WO-01 | Typed work order: plain-text interface parsed to `lucidota-sched/1#typed-work-order` (Objective + Development rules + numbered Goals) | Work order | NEW `~/workspace/compute/pipeline/workorder.py` — `parse_workorder`, `validate_parsed`, `REQUIRED_FIELDS`, `ALLOWED_FIELDS` | `pipeline/workorder_test.py` — ≥20 cases incl. adversarial | NEW WORK |
| R-WO-02 | Objective human-written, immutable, never reinterpreted | Work order | `pipeline/workorder.py` — parser preserves `objective` verbatim; no rewrite path | `pipeline/workorder_test.py` — objective-preservation case | NEW WORK |
| R-WO-03 | Numbered goals carry title + body + inline metadata (Depends-On / Group / Done-When) | Work order | `pipeline/workorder.py` — goal-block grammar + trailer-key extraction | `pipeline/workorder_test.py` — goal-shape cases | NEW WORK |
| R-WO-04 | No fourth tier (`tier` ∉ {1,2,3} rejected) | Work order | `pipeline/workorder.py` — tier validators for `lucidota-sched/1#worker-assignment-envelope` (tiers 3/2/1) | `pipeline/workorder_test.py` — `tier: 4` rejection | NEW WORK |
| R-WO-05 | **Work order is THE interface** (plain-text; human- or any-LLM-written, both valid) | Work order | `pipeline/workorder.py::parse_workorder` — THE entry point; all downstream stages consume `lucidota-sched/1#typed-work-order` only | `pipeline/workorder_test.py` — human-style + LLM-style fixtures both parse | NEW WORK |
| R-WO-06 | Explicit goal boundaries + registered goal types construct the work graph | Work order | `pipeline/workorder.py` (goal numbering/boundaries) + NEW `pipeline/goaltypes.py` — `register_type`, `get`, `types` (seeded `generic`, subdivisible=false) | `pipeline/workorder_test.py`; `pipeline/goaltypes_test.py` — duplicate registration rejected, unknown type → plain error | NEW WORK |
| R-WO-07 | Dependencies/metadata inline or sidecar manifest; conflict → plain error | Work order | `pipeline/workorder.py` — inline trailer parsing + `<wo>.manifest.json` sidecar; conflict = error (never silent precedence) | `pipeline/workorder_test.py` — conflict fixture → plain error | NEW WORK |
| R-WO-08 | Each numbered goal = DEFAULT unit of work; subdivision ONLY when its type explicitly permits | Partitioner | `pipeline/partition.py::maybe_subdivide` gated by `goaltypes.get(goal.type).subdivisible` (deterministic paragraph-boundary split over token budget) | `pipeline/partition_test.py` — non-subdivisible oversized goal stays one unit + reported; subdivisible splits deterministically | NEW WORK |
| R-WO-09 | Related goals → Tier 2 groups; Tier 1 receives the entire work order | Partitioner / Allocator | `pipeline/partition.py::group_related`; `pipeline/allocate.py::assemble_t1_kit` (checklist + objective + specs/constraints + T2 results + evidence) | `pipeline/partition_test.py`; `pipeline/allocate_test.py` — T1 kit assembled only after all T2 terminal | NEW WORK |
| R-WO-10 | Scheduler NEVER uses an LLM to author, normalize, or semantically validate the work order — structural parsing + deterministic ops only | Work order | `pipeline/workorder.py` — no model-call imports (static check); no normalization pass exists | `pipeline/workorder_test.py` — import-absence static check; normalization-attempt test (none possible) | NEW WORK |
| R-WO-11 | Malformed structure → plain error; ambiguous intent NEVER silently reinterpreted by a judge model | Work order | `pipeline/workorder.py::parse_workorder` returns `(None, errors: list[str])`; no reinterpretation path exists to invoke | `pipeline/workorder_test.py` — every malformed fixture yields the expected plain error; ambiguity fixtures yield errors, not guesses | NEW WORK |

## 2. Partition & Group (tier placement)

| ID | Requirement | Minimal mapping | Implementation point (symbol + file) | Test (file + symbol) | Classification |
|---|---|---|---|---|---|
| R-PT-01 | **Partition op:** numbered goals → typed Tier 3 units (one goal + inputs/context + output + completion); subdivision only by type permission (R-WO-08) | Partitioner | NEW `~/workspace/compute/pipeline/partition.py` — `partition_checklist`, `maybe_subdivide` | `pipeline/partition_test.py` — standalone goals → T3 units with own refs only | NEW WORK |
| R-PT-02 | **Structural partitioning rule:** Tier 3 ONLY if performable with supplied context alone | Partitioner | `pipeline/partition.py` — `can_standalone(goal, pw)` (TRUE iff `depends_on` empty ∧ all `context_ref`s resolve from work-order-supplied context ∧ `group` empty) | `pipeline/partition_test.py` — hidden-dependency smuggling stays T2 | NEW WORK |
| R-PT-03 | **Group op:** related/dependent items → Tier 2 bundles (group items + T3 result refs + shared context) | Partitioner | `pipeline/partition.py` — `group_related` | `pipeline/partition_test.py` — grouped items → single bundle; singleton dependents → T2 | NEW WORK |
| R-PT-04 | Partition/Group determinism | Partitioner | `pipeline/partition.py` — `partition_hash` | `pipeline/partition_test.py` — 3-run hash stability | NEW WORK |

## 3. Allocator (tiered Assign + Schedule + quota math)

| ID | Requirement | Minimal mapping | Implementation point (symbol + file) | Test (file + symbol) | Classification |
|---|---|---|---|---|---|
| R-AL-01 | **Tiered Assign:** T3 single checks → T3 workers; T2 groups → T2 workers; T1 complete kit → T1 worker | Allocator | NEW `~/workspace/compute/pipeline/allocate.py` — `assign_tiered`; the allocation record (`lucidota-sched/1#quota-reservation` + envelope join) carries `tier` + `unit_ref` | `pipeline/allocate_test.py` — tiered assignment demo | NEW WORK |
| R-AL-02 | **Schedule ordering T3→T2→T1:** T2 waits on referenced T3 results; T1 waits on all T2 + evidence | Allocator | `pipeline/allocate.py` — `schedule_order`; `assemble_t1_kit` (checklist + objective + specs/constraints + T2 results + evidence) | `pipeline/allocate_test.py` — ordering gates | NEW WORK |
| R-AL-03 | Quota math from measured ceilings (NVIDIA 39 / Gemini 10 RPM; TPM+concurrency symbolic) | Allocator | `pipeline/allocate.py` — pools seeded from `~/workspace/compute/nvidia_rpm.py::DEFAULT_RPM`, `adapters/gemini_rpm.py`; `UNMEASURED` sentinel | `pipeline/allocate_test.py`; `pipeline/QUOTA-SEEDS.md` provenance | NEW WORK (module) / EXISTING AND VERIFIED (seed inputs) |
| R-AL-04 | Atomic reservation + TTL + reconcile + expiry sweep | Allocator | `pipeline/allocate.py` — `reserve`, `release`, `reconcile`, `sweep_expired`; `~/workspace/compute/pipeline-reservations.jsonl` | `pipeline/allocate_test.py` — 32-way double-spend property test, simulated-clock expiry, kill-and-replay | NEW WORK |
| R-AL-05 | Governor disposes allocation (compare-against-policy) | Deterministic check ops | `~/workspace/compute/governor.py::govern` (KEEP — called, not copied) | `~/workspace/compute/governor_tests.py` — checks A–R | EXISTING AND VERIFIED |
| R-AL-06 | Provider selection via existing router | Allocator | `~/workspace/compute/router.py::route_with_receipt` (KEEP) | `~/workspace/compute/bench_results.json` (router-differential-001) | EXISTING AND VERIFIED |

## 4. Workers (tier-scoped envelopes)

| ID | Requirement | Minimal mapping | Implementation point (symbol + file) | Test (file + symbol) | Classification |
|---|---|---|---|---|---|
| R-WK-01 | **Tier 3 envelope:** one checklist item + inputs/context + output + completion; no out-of-allowlist refs | Workers | NEW `~/workspace/compute/pipeline/worker.py` — `t3_envelope` | `pipeline/worker_test.py` — allowlist containment | NEW WORK |
| R-WK-02 | **Tier 2 envelope:** group items + T3 results + shared context (broader than T3) | Workers | `pipeline/worker.py` — `t2_envelope` | `pipeline/worker_test.py` — breadth monotonicity | NEW WORK |
| R-WK-03 | **Tier 1 envelope:** entire checklist + objective + specs/constraints + T2 results + evidence (broadest) | Workers | `pipeline/worker.py` — `t1_envelope` | `pipeline/worker_test.py` — breadth monotonicity | NEW WORK |
| R-WK-04 | Bounded execution through the existing fold | Workers | `~/workspace/compute/dispatch.py` — `supervised_execute`, `_fold_state`, `create_dispatch`, `complete_dispatch`, `fail_dispatch` (KEEP) | `~/workspace/compute/dispatch_tests.py` | EXISTING AND VERIFIED |
| R-WK-05 | Task queueing lifecycle | Workers | `~/workspace/compute/queue.py` — `add`, `mark`, `drain`, `QUEUE_STATUSES` (KEEP) | inline RT-C7/RT-C15 notes; dedicated queue-lifecycle tests missing (UF-016) | EXISTING BUT UNVERIFIED (dedicated tests) |
| R-WK-06 | No self-acceptance / budget raise / tool authorize / policy change by workers | Workers | `pipeline/worker.py` — named violation classes (mirrors `indy-reads/src/governor.rs::AiProposal::sanitize`) | `pipeline/worker_test.py` — 10 adversarial responses | NEW WORK |
| R-WK-07 | Tier 1 owns coherence + final integration | Workers | `pipeline/worker.py` T1 path + `pipeline/checks.py::check_t1_coherence` | `pipeline/checks_test.py` | NEW WORK |

## 5. Ledger (Record op)

| ID | Requirement | Minimal mapping | Implementation point (symbol + file) | Test (file + symbol) | Classification |
|---|---|---|---|---|---|
| R-LD-01 | Append-only execution records via the existing path | Ledger | `~/workspace/compute/ledger.py::record` (KEEP) | `~/workspace/compute/envelope_test.py::test_ledger_record_emits_envelope` | EXISTING AND VERIFIED |
| R-LD-02 | v1 envelope sealing (`lucidota-receipt/1`), no second envelope | Ledger | `~/workspace/compute/envelope.py::wrap`, `verify`, `verify_chain` + `proof-ledger/rs/src/envelope.rs` (KEEP) | `envelope_test.py` (10 tests); `rs` 16 unit tests | EXISTING AND VERIFIED |
| R-LD-03 | **Record op:** every scheduler action (Partition/Group/Assign/Schedule/check/retry) emits a sealed receipt | Ledger | `pipeline/allocate.py` + `pipeline/checks.py` emit via `ledger.record()` | `pipeline/ledger_contract_test.py` (PIPE-008) | NEW WORK (wiring) / EXISTING AND VERIFIED (mechanics) |
| R-LD-04 | Attempt records carry tier + unit/bundle/kit refs | Ledger | `lucidota-sched/1#attempt-record` schema (`task_id`, `tier`, `allocation_ref`, `check_result_ref`) | `pipeline/ledger_contract_test.py` | NEW WORK |

## 6. Retry rules + Repeat

| ID | Requirement | Minimal mapping | Implementation point (symbol + file) | Test (file + symbol) | Classification |
|---|---|---|---|---|---|
| R-RT-01 | Fixed deterministic retry table (failure class → action), bounded attempts | Retry rules | NEW `~/workspace/compute/pipeline/retry.py` — `FAILURE_CLASSES`, `next_action`, `MAX_ATTEMPTS=5` | `pipeline/retry_test.py` — 200 tasks × 8 classes × 3 tiers fault injection | NEW WORK |
| R-RT-02 | T1-kit failure → `blocked` (never silent auto-rerun of the full-context developer) | Retry rules | `pipeline/retry.py` — tier-aware `next_action` | `pipeline/retry_test.py` — T1 failure case | NEW WORK |
| R-RT-03 | Terminal exhaustiveness: every task reaches `done\|failed\|blocked\|dead_letter\|explicitly_unresolved` | Retry rules | `pipeline/retry.py` — liveness by bounded attempts | `pipeline/retry_test.py` — exhaustiveness assertion | NEW WORK |
| R-RT-04 | **Repeat op:** loop until all terminal | pipeline driver | EXTEND `~/workspace/compute/burn.py::run_pipeline_cycle` (flag-guarded) | `pipeline/pipeline_mode_test.py` | REQUIRES EXTENSION |

## 7. Deterministic check ops (per-tier)

| ID | Requirement | Minimal mapping | Implementation point (symbol + file) | Test (file + symbol) | Classification |
|---|---|---|---|---|---|
| R-CK-01 | Compare/Calculate: run acceptance commands, compute pass/fail, hash artifacts | Deterministic check ops | NEW `~/workspace/compute/pipeline/checks.py::compare_calculate` | `pipeline/checks_test.py` | NEW WORK |
| R-CK-02 | T3 completion: the unit's completion condition, one item ⇒ one verdict | Deterministic check ops | `pipeline/checks.py::check_t3_completion` | `pipeline/checks_test.py` | NEW WORK |
| R-CK-03 | T2 bounded in-group inconsistency check (deterministic; inconsistencies beyond bound → fail) | Deterministic check ops | `pipeline/checks.py::check_t2_consistency` | `pipeline/checks_test.py` — contradictory-outputs case | NEW WORK |
| R-CK-04 | T1 coherence: work-order acceptance checks over the integrated artifact | Deterministic check ops | `pipeline/checks.py::check_t1_coherence` | `pipeline/checks_test.py` | NEW WORK |
| R-CK-05 | Tier boundary gates: T3 results feed T2 only on pass; T2 results feed T1 only on pass | Deterministic check ops | `pipeline/checks.py` — gate predicates in `schedule_order` consumption | `pipeline/checks_test.py` + `allocate_test.py` | NEW WORK |
| R-CK-06 | Compare-against-policy: allocation via governor, acceptance via court | Deterministic check ops | `~/workspace/compute/governor.py::govern`; `~/workspace/compute/court.py::derive_status` (KEEP) | `governor_tests.py`; `canon_court_e2e.py` | EXISTING AND VERIFIED |
| R-CK-07 | Calculate: quota reconciliation (reserved vs actual), cost accounting | Deterministic check ops | `pipeline/checks.py::calculate` | `pipeline/checks_test.py` — overrun flagging | NEW WORK |
| R-CK-08 | Route/Track/Stop: queue marks, dispatch fold transitions, kill-switch | Deterministic check ops | `~/workspace/compute/queue.py::mark`; `dispatch.py` fold; `PIPELINE_KILL` (KEEP / NEW flag) | `dispatch_tests.py`; `pipeline/pipeline_mode_test.py` | EXISTING AND VERIFIED / NEW WORK (flag) |

## 8. Scheduler ops coverage

| Op | Requirement IDs | Implementation |
|---|---|---|
| Partition | R-PT-01, R-PT-02, R-PT-04 | `partition.py::partition_checklist`, `can_standalone`, `partition_hash` (NEW WORK) |
| Group | R-PT-03, R-PT-04 | `partition.py::group_related` (NEW WORK) |
| Assign | R-AL-01, R-AL-05, R-AL-06 | `allocate.py::assign_tiered` + `govern()` + `route_with_receipt()` (NEW WORK + EXISTING AND VERIFIED) |
| Schedule | R-AL-02, R-AL-03, R-AL-04 | `allocate.py::schedule_order`, `reserve`, `reconcile` (NEW WORK) |
| Record | R-LD-01 – R-LD-04 | `ledger.py::record` + `envelope.wrap` (EXISTING AND VERIFIED) + pipeline wiring (NEW WORK) |
| Repeat | R-RT-01 – R-RT-04 | `retry.py` (NEW WORK) + `burn.py::run_pipeline_cycle` (REQUIRES EXTENSION) |

---

## 9. DEPRECATION CANDIDATES (elaborate — justification required)

Anything below stays in the tree (archive-don't-delete) but is NOT wired into
the minimal pipeline, and no backlog task extends it.

| ID | Candidate | Justification |
|---|---|---|
| D-01 | Semantic-judge LLM (LLM-as-judge of artifact quality) | Replaced by R-CK-01/R-CK-02 deterministic compare/calculate against typed acceptance criteria. An LLM judge reintroduces the authority confusion the governor architecture was built to prevent — INV-01 (AI cannot self-certify) and INV-11 (truth determination must not depend on generative AI), both EXISTING AND VERIFIED in `~/workspace/canon/`. |
| D-02 | Hierarchy of validators as a runtime layer (per-task `independent_verifier` 11-gate / `pl_canon_verifier` 17-gate runs) | Per-task 28-gate verifier runs serialize the pipeline and duplicate `court.derive_status` (R-CK-06, EXISTING AND VERIFIED). Verifiers remain as offline periodic audit tools — existing code kept, never wired into the hot path. |
| D-03 | LLM-debates-LLM decision layers | No evidence it improves artifact acceptance over deterministic checks; multiplies quota burn against measured ceilings (f8: NVIDIA 39 / Gemini 10 RPM). Provider generate/critique separation lives at builder level per Zack's routing order, not as pipeline machinery. |
| D-04 | Autonomous reinterpretation of the human's objective | Work-order objective is human-immutable (R-WO-02). Reinterpretation surrenders the operator's epistemic control — contradicts the master goal ("without surrendering epistemic or operational control to the machine"). |
| D-05 | Tier-2 LLM glue with merge authority (old Mission 2 tier language) | Superseded by the tier model: Tier 1 (full-context developer) owns coherence + final integration (R-WK-07). Integration is typed work with deterministic acceptance, not LLM negotiation. |
| D-06 | LLM conflict resolution in merges | Merge = deterministic checks (tests green, R-CK-01) + authorized scope (dispatch-gate, EXISTING AND VERIFIED). No judgment layer is needed or wanted. |
| D-07 | 9-stage exchange pipeline as the scheduler's lifecycle | The minimal lifecycle is the six scheduler ops (§8). The exchange worker (`worker.js` v0.6.14) is untouched; mapping its 9-stage vocabulary onto the pipeline is interpretive, not structural. |
| D-08 | PROVENANCE-ENFORCEMENT v2 as a pipeline dependency | Doctrine-only, unbuilt (UF-005). Pipeline provenance rests on v1 envelopes (R-LD-02, EXISTING AND VERIFIED). v2 machinery extends later; it never blocks the minimal pipeline. |

## 10. BLOCKED (missing facts — see 13-unresolved-facts.md)

| ID | Requirement | Blocker |
|---|---|---|
| B-01 | Any DAG role for Cap'n Maps | UF-001: no contract exists anywhere in workspace or ledger. No role assigned. |
| B-02 | FalkorDB as a production pipeline dependency | UF-002: live server is hackathon-practice-only; no production pipeline reads/writes it. |
| B-03 | `authorized`-envelope promotion in final acceptance | UF-006: no call site wraps `status="authorized"`. Pipeline acceptance stops at `established` + court verdict. |
| B-04 | Quantified TPM / concurrency terms in quota math | UF-007: unmeasured for all providers. Carried as symbolic `UNMEASURED`; pacing stays on request-rate ceilings + latency bounds. |
| B-05 | ai-router lane caps as capacity | UF-009: `rpmLimit` declared-only, never measured. Treated as advisory, not capacity. |
| B-06 | NVIDIA provider limit + true budget | UF-010: 39 RPM is operator pacing, provider limit UNVERIFIED; 5000-call budget UNVERIFIED_ESTIMATE (2926 used). Bands are governance, not capacity. |
| B-07 | Cross-boundary (multi-machine) receipt signing | UF-004: authority-key custody (goal_b4eaabcc3b4d) undecided. HS256 valid only inside the custody boundary. |
| B-08 | Live exchange parity for any pipeline↔worker.js integration | UF-011: deployed v0.6.14 not re-verified; D1 mirror staleness unknown. No integration attempted until verified. |

---

## 11. Classification rollup

- **EXISTING AND VERIFIED:** R-AL-05, R-AL-06, R-WK-04, R-LD-01, R-LD-02, R-CK-06, R-CK-08 (mechanics), Record-op mechanics.
- **EXISTING BUT UNVERIFIED:** R-WK-05 (queue-lifecycle dedicated tests missing — UF-016).
- **REQUIRES EXTENSION:** R-RT-04 (`burn.py::run_pipeline_cycle`, flag-guarded additive).
- **NEW WORK:** all `pipeline/` modules — R-PRM-01/02, R-WO-01–11, R-PT-01–04, R-AL-01–04, R-WK-01–03, R-WK-06/07, R-LD-03/04, R-RT-01–03, R-CK-01–05, R-CK-07, R-CK-08 (flag).
- **BLOCKED:** B-01 – B-08.
- **DEPRECATION CANDIDATE:** D-01 – D-08 (justified above).

---

## Provider use

None — direct synthesis from evidence bundle f1–f8 (no NVIDIA NIM generation,
no Gemini critique), to preserve exact symbol grounding. Fallback per task
authorization ("record `direct` fallback in receipts").
