# 08 — Hostile Verification Suite (§10 mission; SPEC §12.8)

**Owner:** SPEC section agent · **Date:** 2026-10-09 (re-scoped per owner directive same day) ·
**Mode:** specification only — no code, no deploys.
**Context:** synthesis mission `~/workspace/batch-compile/MISSION-2-SYNTHESIS.md` §10,
evidence bundle `~/workspace/batch-compile/evidence/` (f1–f8).

## 0. The minimal architecture (what is verified)

```
Prompts → Typed work order → Partitioner → Allocator → Workers → Ledger → fixed retry rules → repeat
```

The deterministic ops are the ONLY enforcement surface:

| Op | Meaning | Where it fires |
|----|---------|----------------|
| **Compare** | byte/hash equality checks: `envelope.verify`, hash recompute, (task_id, input_hash, base_revision) binding match, conflict detection | worker ingest, ledger read paths |
| **Calculate** | quota arithmetic: λ math, bucket balances, reservation sums, budget utilization, makespan estimates | allocator |
| **Compare-against-policy** | ceilings, bands, gate predicates: 39/10 RPM buckets, budget bands, governor REASON_CODES, schema allowlists | allocator, governor gates |
| **Route / Track / Stop** | dispatch, sweeps, kill: eligible-work selection, zombie sweep, failover, kill-switch | allocator, runbook procedures |

**CUT, by owner directive:** semantic-judge LLM, hierarchy of validators,
LLM-debates-LLM layers, autonomous reinterpretation of the human's objective.
Consequence for this suite (§6 lists the cuts explicitly): tests whose purpose
was *certifying a validator hierarchy* are DROPPED. Tests *attacking the
deterministic boundary* are KEPT — they are now the whole suite, organized by
pipeline stage: **WO** (work order) · **PT** (partitioner) · **AL** (allocator) ·
**WK** (workers) · **LG** (ledger) · **RT** (retry rules) · **LD** (load).

Doctrines unchanged: fake providers + virtual time for all load/scale tests
(zero real quota burned); measured numbers only; reuse suites by exact
file+symbol; a FAIL artifact must name the enforcement mechanism that failed
to fire; UNKNOWN is a valid outcome, never "probably fine."

## 1. Deterministic boundary map

| Boundary | Enforcing symbol(s) | What the hostile test proves |
|----------|--------------------|------------------------------|
| Work-order schema | canon-style field allowlists (`store::validate_new` pattern: unknown field → reject); typed envelope schemas | WO-1..WO-3 |
| Partitioner determinism | partition function (deterministic; same manifest → same tasks) | PT-1..PT-2 |
| Quota buckets | `~/workspace/compute/nvidia_rpm.py` (`acquire()`/`DEFAULT_RPM=39`), `~/workspace/compute/adapters/gemini_rpm.py` (10), `adapters/nvidia.py::execute()` gate | AL-1, AL-7, AL-9 |
| Budget bands | `~/workspace/compute/budget.py` (bands) + `burn.py:90` `budget_guard()` (0.55 pause / <0.50 resume) | AL-3, WK-5 |
| Governor gates | `governor.govern` + `REASON_CODES` (11, fail-closed `_codify`), `governor_tests.py` A–R | WK-7, TM suite |
| Receipt authenticity | `compute/envelope.py::verify` / `verify_chain` / `EnvelopeError`; `pl audit --full` REPLAY/STALE | WK-2..WK-4, LG-2 |
| Binding | (task_id, input_hash, base_revision) triple match (worker.js `checkClaimBinding` anti-transplant pattern) | WK-1 |
| Ledger chain | `proof-ledger/rs/src/ledger.rs` (`append`/`verify_chain`/`repair`/`read_strict`), `canon::canonical`/`hash_record` | LG-1..LG-3 |
| Retry rules (fixed) | defer cap 8 → failed; zombie sweep stale running >10 min → deferred (worker.js:2814–2822); kill semantics | RT-1..RT-4 |

## 2. Reused foundations (exact file + symbol — in scope only)

| ID | Suite | Path | Symbols / coverage | State |
|----|-------|------|-------------------|-------|
| R1 | governor_tests.py | `~/workspace/compute/governor_tests.py` | 19 checks A–R (allocation predicates; RT-A1/A3/B1–B5/C12). The deterministic-gate battery for allocator authority. | EXISTING AND VERIFIED |
| R5 | threat_tests.py | `~/workspace/compute/threat_tests.py` | **TM-1..TM-8 stay** — they test deterministic gates (forged capability, unminted-reserve, priority self-grant, dispatch forgery, ledger tamper, receipt forgery, self-attestation, rpm ceiling). | EXISTING AND VERIFIED |
| R6 | envelope_test.py | `~/workspace/compute/envelope_test.py` | 10 tests (`test_python_wrap_rust_verify`, `test_rust_wrap_python_verify`, `test_cross_tamper_rejected`, `test_ledger_record_emits_envelope`, `test_missing_sig_rejected_both_directions`, `test_two_tier_mixed_chain`, `test_production_mixed_chain_tamper`, `test_verify_chain_start_prev_anchoring`, `test_ximpl2_i64_interop_pin`, `test_ximpl1_utf8_raw_parity`). The Compare-op battery. | EXISTING AND VERIFIED |
| R7 | envelope.rs + vectors + durability | `~/workspace/proof-ledger/rs/src/envelope.rs` (16 `#[test]`), `rs/tests/envelope_vectors.rs`, `rs/tests/rt_spree.rs`, `rs/tests/durability.rs` | wrap/verify, byte-identical vectors (XIMPL pins), red-team fuzz, concurrent-writer durability | EXISTING AND VERIFIED |
| R8 | canon tests | `~/workspace/canon/tests/hashchain.rs` (`hashchain_suite`: `t_corruption_detection`, `t_truncation_end_boundary`, `t_concurrent_append` 8×25, `t_receipt_determinism`, …), `tests/invariants.rs` (`every_enforcement_point_resolves_to_real_file_line`) | chain + schema-allowlist enforcement (the allowlist pattern the work-order schema copies) | EXISTING AND VERIFIED |
| R10 | dispatch_tests.py | `~/workspace/compute/dispatch_tests.py` | `dispatch._fold_state()` transition guards (`executing` only from `dispatched`; `_fake_govern`) | EXISTING AND VERIFIED |
| R11 | worker-battery | `~/workspace/exchange/worker-battery.py` (W1–W10), `worker-battery-v3.py`, `worker-battery-v4.py`, `worker-battery-v4-integrity.py`, `redteam2-*.py`, `rt2-dup-replay.py`, `exchange/tests/envelope-vectors.test.mjs`, `tests/ingest-envelope.test.mjs` | claim race, replay idempotency, forged completion, lease expiry, zombie sweep, cost-assertion ignored, secret scan, empty-output failure, model-lie, crash→UNCERTAIN | EXISTING AND VERIFIED |
| R12 | governor gate + dispatch-gate | `governor.audit()` indicators; `~/workspace/governor/test-governor.py` (12 tests, 12/12 PASS 2026-10-09T18:27:50Z); `dispatch-log.jsonl` (41 ALLOW/DENY entries) | allocation authority + admission fail-closed | EXISTING AND VERIFIED |
| R13 | recovery_tests.py | `~/workspace/compute/recovery_tests.py` | recovery + SIGKILL confirmation | EXISTING AND VERIFIED |
| R14 | governor_adversarial | `~/workspace/indy-reads/tests/governor_adversarial.rs` (10 tests: forged approval absent, replayed decision rejected at consumption, transplanted decision rejected, forged nonce rejected) | authority hostile battery — the pattern for WK-6/WK-7 | EXISTING AND VERIFIED |
| R16 | measured baselines | `~/workspace/compute/bench_results.json` (governor policy: scarce_selection_rate 0.51, trivia_burn_rate 0.0, mean_effective_quality 0.6885, decision p99 113ms), `burn.STATUS.json`, `burn.log`, `nvidia-usage/calls.jsonl` | all thresholds in §4–§5 | EXISTING AND VERIFIED |

## 3. The hostile battery

Conventions: **I** invariant · **S** setup · **E** expected · **F** failure signal ·
**A** evidence artifact. All load tests use FAKE PROVIDERS + VIRTUAL TIME.

### WO — Typed work order (schema is a deterministic gate)

- **WO-1 (schema violations rejected)** I: a work order with an unknown field,
  missing required field, or wrong type is rejected at the boundary — never
  hashed into the chain, never partitioned (pattern: `store::validate_new`
  → unknown field → reject, f1).
  S: 200 synthetic work orders: 50 valid, 150 malformed (unknown fields,
  missing ids, float where i64 required, non-ASCII-escaped JSON, bigint
  payloads per XIMPL-2 convention).
  E: 50 accepted; 150 rejected with the exact offending field named.
  F: any malformed order accepted or partitioned.
  A: `wo-schema.json` (per-order accept/reject + offending field).

- **WO-2 (no smuggled authority)** I: authority-bearing fields a model injects
  (`authority`, `verified`, `execute`, `claim_status` — f1 `AiProposal::sanitize`
  pattern) are stripped and receipted, never acted on.
  S: prompts whose outputs embed those fields; R14-style adversarial set.
  E: fields stripped; sanitization receipt lists removals; downstream treats
  output as unprivileged evidence.
  F: any smuggled field reaching a gate check.
  A: `wo-sanitize.json`.

- **WO-3 (canonical form)** I: identical semantic content → identical bytes
  (sorted keys, compact separators, UTF-8 raw, i64 ints — f5 canonical contract).
  S: 1000 semantically-identical orders with shuffled key order / whitespace.
  E: single canonical byte string; single `payload_hash`.
  F: two byte-distinct canonical forms for the same content.
  A: `wo-canonical.json`.

### PT — Partitioner (deterministic function, not a judge)

- **PT-1 (determinism)** I: same work order → same task set, byte-identical,
  across runs and processes (determinism, not consensus).
  S: 50 work orders partitioned 5× each, two processes, virtual clock fixed.
  E: 250/250 identical partitions (hash-equal).
  F: any divergence.
  A: `pt-determinism.json`.

- **PT-2 (state-transition closure)** I: every task reaches exactly one terminal
  state in {accepted, rejected, blocked, cancelled, explicitly-unresolved}; no
  transition outside the permitted graph (extends R10 fold guards + R11 W5).
  S: randomized driver over queue/dispatch/exchange job states, 10k random
  event sequences, seed recorded.
  E: 100% terminate with one terminal state; every observed transition in the
  permitted graph.
  F: non-terminal task after event exhaustion, or `completed → executing`.
  A: `pt-transition-<seed>.jsonl`. **NEW WORK:** queue-lifecycle dedicated test
  file (f2 gap 3) — this is its spec.

### AL — Allocator (Calculate + Compare-against-policy + Route)

- **AL-1 (λ math)** I: `λ = min(RPM_ceiling, C·μ)` never exceeded under clamped
  fake quotas. S: fake provider RPM=2/min, latency L, concurrency C ∈ {1,2,4},
  virtual clock 100 ms steps. E: completions/min ≤ min(2, C·(60/L)), equality
  at saturation. F: bucket counter negative (dispatch past empty bucket).
  A: `al-lambda-<sweep>.json`.

- **AL-2 (reservation accounting)** I: `reserved ≥ dispatched` at every instant;
  every reservation released/exhausted by run end (no orphans).
  S: fake provider with variable actual tokens; 500 synthetic tasks.
  E: zero orphaned reservations; no `reserved < actual` instant.
  F: baseline drift upward over 100 cancels (leak).
  A: `al-reservation-ledger.jsonl`.

- **AL-3 (budget bands)** I: pause at guard 0.55, resume below 0.50
  (`budget_guard()`, burn.py:90), fail closed at 1.00 of the unverified estimate.
  S: fake NVIDIA lane at utilization 0.54 / 0.55 / 0.56 / 0.60 / 1.00 of the
  5000-estimate; `govern()` per task.
  E: 0.54 → dispatch; 0.55 → pause with `STRATEGIC_RESOURCE_RESERVED`; <0.50 →
  resume; 1.00 → hard refuse citing band.
  F: any dispatch at ≥ 0.55.
  A: `al-bands.json`.

- **AL-4 (simulated-clock buckets)** I: adapter buckets gate exactly at measured
  ceilings — NVIDIA 39/min, Gemini 10/min; refusal records `rate_limited`
  and never dispatches (f3: exactly once in 2543 executions).
  S: virtual clock; burst of 50 at t=0 to each fake adapter.
  E: 39 / 10 accepted in minute 0; the rest refused with `retry_after_s`
  matching refill; zero provider calls on refusals.
  F: dispatch over ceiling, or refusal that consumed quota.
  A: `al-bucket-<provider>.json`.

- **AL-5 (idempotency)** I: duplicate claims with the same idempotency key
  accepted exactly once (extends R11 W2: ×10 → 1).
  S: 100 duplicate deliveries of 20 claims at the local ingest gate
  (replay → 409 semantics); virtual time.
  E: 20 accepted, 1980 rejected 409; accounting rows == claims accepted.
  F: `accounting_rows > claims_accepted`.
  A: `al-idempotency.json`.

- **AL-6 (cancel releases)** I: killing a task releases quota + lease within the
  60 s lease-expiry bound (f2 worker.js:767–775).
  S: fake provider; cancels at {reserved, dispatched, executing}; virtual clock.
  E: release receipt per cancel; `reserved_total` back to baseline after
  max(lease_expiry) virtual time.
  F: reservation leak.
  A: `al-cancel-release.jsonl`.

- **AL-7 (backoff)** I: THROTTLED backoff = 2^(n-1) min cap 60 (worker.js:67);
  no probes during backoff.
  S: fake provider 429s n=1..8 then healthy; virtual clock.
  E: intervals 1,2,4,8,16,32,60,60 min; health THROTTLED throughout.
  F: interval deviates, or probe issued inside backoff window.
  A: `al-backoff.json`.

- **AL-8 (429/timeout/outage)** I: 429/503 (measured on Gemini: 4×200 then 503,
  f8) → RATE_LIMITED + bounded retry (≤3) → deferred; timeout (300s nvidia
  default) → attempt failed, defer_count +1 exactly; full outage (as observed
  2026-10-08: all CF endpoints DOWN(0)) → zero dispatches, tasks stay queued,
  decisions → `NO_FEASIBLE_SOURCE`/`UNAVAILABLE`.
  S: fake lanes with scripted failure modes; virtual clock.
  E: no task marked success on a 429; queue keeps processing independent tasks;
  no partial output accepted (adapter marks partial `invalid`, never success —
  f3: 550 invalid in nvidia history).
  F: success on 429; queue stalled behind a dead lane; partial accepted.
  A: `al-failures.json`.

- **AL-9 (shared quota)** I: independent schedulers never each assume the whole
  pool — reservation is global and atomic (MASTER DIRECTIVE delta 1).
  S: two fake NVIDIA lanes sharing one account pool; five schedulers, virtual clock.
  E: combined ≤ 39/min (direct-path ceiling, NOT the router's declared 40);
  one scheduler's reservation blocks another past the ceiling.
  F: combined rate > ceiling, or double-reserved quota unit.
  A: `al-shared-pool.json`.

- **AL-10 (failover preserves identity)** I: a task failed over from a THROTTLED
  lane re-enters with the same task id, manifest, budget, and gates; evidence
  chain links the original failure record.
  S: NVIDIA fake lane → THROTTLED; eligible = fake gemini-direct, ai-router-free.
  E: failover decision carries reason code; task id unchanged; failure record linked.
  F: task re-queued as a new id (identity break).
  A: `al-failover.json`.

- **AL-11 (distribution honesty)** I: makespan estimates use measured p50/p95
  (nvidia 20.1/41.9s, gemini 2.6/12.3s, ai-router 10.8/19.1s) and measured
  reliability (nvidia 61.9%, ai-router 96.3%); scheduled λ never assumes 100%
  success.
  S: fake providers replaying empirical latency histograms; lognormal tokens.
  E: conservative makespan ≥ observed in ≥95% of runs.
  F: observed > conservative, or λ scheduled at 100% success.
  A: `al-dist.json`.

### WK — Workers (Compare at the boundary; Compare-against-policy on budgets)

- **WK-1 (binding)** I: artifact manifest's (task_id, input_hash, base_revision)
  triple must match the dispatched envelope (`checkClaimBinding` anti-transplant
  pattern, f5).
  S: well-formed artifacts bound to a different task_id / input_hash /
  base_revision (transplant attack).
  E: rejection citing binding mismatch.
  F: any mismatched artifact accepted.
  A: `wk-binding.json`.

- **WK-2 (replay)** I: verbatim duplicate verification record → audit FAIL
  REPLAY (f4 `_pl_freshness`); duplicate seal at ingest → 409 + audit row.
  S: synthetic chained ledgers in /tmp; duplicate seal to local ingest gate.
  E: `pl audit --full` reports REPLAY; ingest returns 409.
  F: duplicate accepted silently.
  A: `wk-replay.json`.

- **WK-3 (stale)** I: 48h-old observation as fresh verification → FAIL STALE
  (closes RT-2026-10-08-STALE-EXEC).
  S: verification record ts 48h past, chain otherwise valid.
  E: FAIL STALE; treated as assertion, not verification.
  F: stale record counted as verification evidence.
  A: `wk-stale.json`.

- **WK-4 (forgery)** I: missing sig / attacker-key re-sign / tampered payload →
  `EnvelopeError`, AUTHENTICITY FIRST (R6, f4 `_pl_sig`); invisible-identity
  actors rejected (`has_visible_identity`, R7).
  S: `fixtures/envelope-vectors.json` + 5 negative vectors.
  E: every negative vector rejected.
  F: any forged envelope verifying.
  A: `wk-forge.json`.

- **WK-5 (budget escalation — TM-2 pattern)** I: a worker cannot raise its own
  budget band or mint quota; accounting is written from measured cost, never
  worker assertion (f2 worker.js:471; R11 W6 cost=$99999 ignored).
  S: completion with inflated `cost`, `reserve` above delegated ceiling,
  self-promotion request.
  E: all rejected; falsification-style audit row filed.
  F: any self-granted budget accepted.
  A: `wk-unminted.json`.

- **WK-6 (priority/campaign self-grant — TM-3 + RT-B5)** I: `priority: P0` extras
  forcing a single feasible source are flagged (`proposer_single_source: True`
  + `eliminators` list); fake campaign tokens ignored (R1 tests Q/R).
  S: tasks with eliminator extras; fake campaign tokens.
  E: flagged, priority capped; no eliminator-flagged decision dispatched unreviewed.
  F: flagged decision dispatched.
  A: `wk-eliminator.json`.

- **WK-7 (unauthorized actions — TM-1/TM-4/TM-6/TM-7/TM-8)** I: forged
  capability (TM-1), dispatch forgery (TM-4), receipt forgery/replay (TM-6),
  self-attestation (TM-7), rpm-ceiling breach (TM-8) are all rejected by the
  deterministic gate each targets. Run `threat_tests.py` TM-1..TM-8 as the
  executable battery.
  S: R5 as-is.
  E: exit 0, all 22 checks pass.
  F: any TM check red.
  A: `threat_tests.py` output + `wk-tm.json` summary.

- **WK-8 (conflicting artifacts)** I: two accepted artifacts editing the same
  base-revision hunks are both recorded, neither silently overwrites the other;
  deterministic conflict detection (Compare op) names the conflict set.
  S: two artifacts, same base revision, overlapping hunks.
  E: conflict detected; both stay `accepted`-but-unapplied; no partial apply.
  F: conflicted apply landing, or silent overwrite.
  A: `wk-conflict.json`.

### LG — Ledger (append-only; recording ≠ truth)

- **LG-1 (crash recovery)** I: kill -9 mid-append → at most one unterminated
  tail line; `repair()` appends a `RepairReport` record; `verify_chain` passes
  post-repair (f5 `ledger.rs`; R13 SIGKILL semantics).
  S: kill -9 at 10 random offsets during 10k-record writes; then repair + verify.
  E: chain verifies; repair recorded as its own chained record.
  F: silently dropped tail, or unrecorded repair.
  A: `lg-crash-<offset>.json`.

- **LG-2 (two-tier honesty)** I: `verify_envelopes()` verifies chain linkage
  uniformly; signed→must-authenticate, unsigned→integrity-only, tier reported
  honestly (RT-2026-10-08-TWOTIER-1; R6 `test_verify_chain_start_prev_anchoring`).
  S: mixed signed/unsigned chain + tier-mislabeling attempt.
  E: honest tier counts; mislabel → verify fails.
  F: tier silently promoted/downgraded.
  A: `lg-twotier.json`.

- **LG-3 (ledger down → fail-closed)** I: ALLOW without a recorded decision is
  impossible — ledger-write failure converts admission to DENY (f1
  `admit_action`); in-flight receipts spill durably and replay in order on
  recovery.
  S: PL/`ledger.py` write path fails (disk-full simulation).
  E: all admissions DENY; spill file hashed; replay verifies post-recovery.
  F: any ALLOW without a decision record, or a lost receipt.
  A: `lg-ledger-down.json`.

- **LG-4 (end-to-end acceptance on the final tree)** I: acceptance =
  deterministic gates green on the final tree: every artifact's envelope chain
  verifies, every binding triple matches, every work order schema-validates,
  budget reconciles to zero orphans, and the WORK's own test suites pass.
  No validator hierarchy is consulted; "passing unit test ≠ system correctness"
  still holds — acceptance requires the full deterministic set, not one suite.
  S: a real (non-fake) campaign run, ≥1 artifact per stage; T-suite run on final tree.
  E: acceptance declared iff ALL deterministic checks green AND no masked skips;
  any red names the blocking check (INV-10 pattern).
  F: acceptance with any red/skipped/masked check.
  A: `lg-acceptance/` (per-check logs, blocking-check report).

### RT — Fixed retry rules (no discretion, no LLM judgment)

- **RT-1 (taxonomy)** I: every failure maps to exactly one of the fixed classes
  (RETRYABLE_FAILURE | PERMANENT_FAILURE | POLICY_FAILURE | AUTH_FAILURE |
  QUOTA_FAILURE | CAPABILITY_FAILURE | PROVIDER_FAILURE | VERIFICATION_FAILURE —
  f2 worker.js:24,745); retryable → tail, defer_count < 8 → deferred,
  ≥ 8 → failed, policy/capability → blocked.
  S: one synthetic failure per class.
  E: the exact prescribed terminal/queue transition per class.
  F: any failure in the wrong bucket, or a retryable failure dropped.
  A: `rt-taxonomy.json`.

- **RT-2 (zombie sweep)** I: stale `running` (no receipt, >10 min) → `deferred` +
  evidence_log; never reaps a live job (extends R11 W5).
  S: mixed live/crashed workers; virtual clock +12 min.
  E: exactly crashed jobs reaped; one evidence_log row each.
  F: live job reaped, or crashed job left running.
  A: `rt-zombie.json`.

- **RT-3 (dependency prune)** I: DISPROVEN_DEPENDENCY auto-prunes dependent
  deferred jobs → `failed` with prune receipt (f2 worker.js:1117–1128 A2).
  S: dependency marked DISPROVEN with dependents deferred.
  E: dependents → failed with prune receipts; nothing left dangling.
  F: dependent stuck deferred forever.
  A: `rt-prune.json`.

- **RT-4 (kill-switch)** I: kill → zero new dispatches within 1 virtual second;
  reservations released (AL-6); partial artifacts quarantined, never accepted;
  tasks → `cancelled` with kill receipts bound to campaign id (Route/Track/Stop).
  S: 150 workers mid-run (LD harness); kill at virtual t+300s.
  E: as invariant.
  F: any dispatch post-kill, any held reservation past kill+lease_expiry,
  any partial accepted.
  A: `rt-kill.json`.

### LD — Load (fake providers + virtual time; never real quota)

- **LD-1 (scaling sweep)** I: throughput scales with workers until the binding
  constraint, then plateaus at ≤ `min(RPM_ceiling, C·μ)`; queue depth grows
  monotonically under saturation (no silent drops).
  S: workers ∈ {1,5,50,100,150}; fake provider RPM=39/min, virtual latency p50
  20.1s (measured nvidia); task mix from AL-11.
  E: λ at 1/5 workers ≈ unconstrained; at 50+ λ plateaus ≤39/min with excess
  held or rate_limited.
  F: λ > ceiling at any scale, or flat queue depth while λ < ceiling (silent loss).
  A: `ld-scaling.json`.

- **LD-2 (claim race at 150)** I: single conditional-UPDATE winner (extends R11 W1).
  S: 150 workers claim the same job; atomic conditional UPDATE; virtual clock.
  E: exactly 1 `active` claim; 149 receipted rejections; losers' reservations released.
  F: >1 active claim.
  A: `ld-claim-race.json`.

- **LD-3 (mixed-provider saturation)** I: under saturation the allocator sheds
  load to eligible lanes by policy order (Compare-against-policy), never by
  exceeding any lane's ceiling.
  S: 150 workers; fake nvidia (39/min) + fake gemini (10/min) + fake ai-router
  lane (declared cap, never exceeded); virtual clock.
  E: per-lane dispatch ≤ per-lane ceiling at every virtual minute; overflow
  held in queue.
  F: any lane over ceiling.
  A: `ld-mixed.json`.

## 4. Kept NEW tests (re-scoped)

| ID | Test | Status / blocker |
|----|------|------------------|
| N1 | FABRICATE-1 regression (record-level seal) | Specified; cannot go green until record-level authority sealing exists — **blocked on operator key-custody decision** (`goal_b4eaabcc3b4d`). The deterministic boundary is incomplete until this lands; the suite must FAIL LOUD here, not skip. |
| N2 | XIMPL-2 i64 pin (beyond R6) | OPEN (MEDIUM): payloads MUST NOT carry integers outside [-2^63, 2^63-1] until Python and Rust agree on arbitrary precision. WO-1 enforces the convention at the boundary. |
| N4 | Queue lifecycle transition tests | f2 gap 3: `QUEUE_STATUSES` asserted in `mark()` but no dedicated file. Specified as PT-2's foundation. |
| N5 | `authorized` envelope promotion path | f2 gap 2: no call site wraps `status="authorized"` — UNKNOWN until implemented; no test may assert it green. |
| N6 | 9-stage pipeline as one machine | Re-scoped: the minimal pipeline (Prompts→…→repeat) REPLACES the 9-stage narrative as the verified machine. PT-2 + AL transitions are its executable spec; the old narrative is superseded, not tested. |

## 5. CUT list (dropped by the simplification directive — recorded, not silently lost)

| Dropped | Why |
|---------|-----|
| Verifier A 11-gate hierarchy as an acceptance certifier (`independent_verifier.run()` as the thing-that-declares-done) | Hierarchy certifying a hierarchy. Its *components* survive where they test deterministic gates: `boundaries` (R5), `reproducible` (PT-1 pattern), `recovery` (LG-1/R13). |
| Verifier B (`pl_canon_verifier`) as a certifier; N3 `_canon_deploy` staleness fix | Same reason. Its deterministic probes survive individually: `_pl_freshness` → WK-2/WK-3, `_pl_sig` → WK-4, `_pl_tamper` → LG-1, `_pl_ximpl` → WO-3/N2. Deployment identity belongs to the deploy pipeline, not batch-compile acceptance. |
| Court `derive_status` verdict hierarchy as acceptance (`canon_court_e2e.py` as certifier) | Verdict hierarchies are cut. `court.record_falsification` SURVIVES as the append-only falsification sink (LG-class deterministic op) — filing findings is recording, not judging. |
| LiteBox adversarial-harness suite as an acceptance gate | Sandbox witnessing is provenance evidence, not a batch-compile gate. Envelope fragments still use `lucidota-receipt/1` (no second envelope — f7 doctrine kept). |
| T12.2 merge-regression certifier (old numbering) | Assumed a merge controller with judgment. Replaced by WK-8 (deterministic conflict detection) + LG-4 (deterministic final-tree acceptance). |
| "Validator down / verifier down" as hierarchy outages (old T13.1/T13.2) | Replaced by LG-3: ANY deterministic gate unavailable (envelope key missing, ledger unwritable, bucket state unreadable) → hold, never self-accept. Same fail-closed doctrine, no hierarchy needed. |

## 6. Evidence artifact conventions

- All artifacts under `~/workspace/batch-compile/verification/<run-id>/`.
- Every artifact JSON: `test_id`, `run_id`, `virtual_time` (or `real_time` +
  `clock: real` where virtual is impossible, e.g. LG-4), `invariant`, `result`
  (PASS/FAIL/UNKNOWN), `failure_signal` if FAIL, `sha256` of raw log.
- FAIL names the enforcement mechanism that failed to fire.
- UNKNOWN is valid (INV-02) — never "probably fine."

## Provider use

No provider calls used. Re-scope written directly from the owner directive plus
the read evidence bundle (f1–f8) and `MISSION-2-SYNTHESIS.md` §10. Kept local
deliberately: every test references exact existing files/symbols, and a
generator without workspace read-access would risk inventing identifiers the
HARD RULES forbid. No NVIDIA NIM or Gemini calls — zero quota consumed.

## 7. Tier-conformance tests (TR suite)

Tier model (owner update 2026-10-09 — numbering INVERTED: Tier 1 is the TOP;
tiers are defined by context/responsibility scope, NOT model capability; N=3
fixed): Tier 3 = single-check workers (ONE checklist item + its inputs/context
+ output + completion condition, max parallel); Tier 2 = check-group workers
(GROUP of related items + relevant Tier 3 results + shared context; combines
results, local deps, bounded in-group inconsistencies); Tier 1 = full-context
developer (entire checklist + objective + specs/constraints + Tier 2 results +
evidence; owns coherence + final integration). Partitioning rule (structural):
Tier 3 ONLY if the item is performable with its supplied context alone;
related/dependent checks stay at Tier 2. Prompts are developer-defined/
supplied; the scheduler distributes, never authors/judges — nothing in this
suite authorizes the scheduler to judge output quality.

Every TR test is deterministic — schema allowlist, hash comparison, or set
equality over existing artifacts. No TR test judges the semantic content of a
worker's output. Conventions I/S/E/F/A as in §3; artifact conventions per §6.

- **TR-1 (T3 scope-confinement)** I: a Tier 3 assignment envelope contains
  exactly ONE checklist item plus the context fields declared for that item in
  the task manifest — verifiable by schema allowlist + hash, no scope creep.
  S: 200 T3 envelopes: 100 well-formed (single item, declared context only);
  100 adversarial (a second item injected, an extra undeclared context field,
  or the item id swapped for a non-declared item — WO-1/WO-2 smuggle patterns
  reused). The envelope's `item_count` and context field set are recomputed
  from the manifest and compared (Compare op; the canon `store::validate_new`
  allowlist pattern; `compute/envelope.py::verify` for envelope integrity).
  E: 100 accepted; 100 rejected with the offending field/item named and the
  manifest hash cited.
  F: an envelope with >1 item or an undeclared field passes assignment, or a
  well-formed envelope is rejected.
  A: `tr-scope.json` (per-envelope accept/reject + offending field).

- **TR-2 (T2 group-assembly correctness)** I: a Tier 2 group cannot be marked
  complete unless EVERY member Tier 3 result is present, each bound by
  (task_id, item_hash) to its declared member — set equality over the member
  list (Compare op), no judgment of result content.
  S: 100 group completions attempted: 40 with all members present and
  correctly bound; 30 missing ≥1 member result; 20 with a result bound to the
  wrong item_hash (transplant — WK-1 pattern); 10 with a duplicate result for
  one member and another member absent.
  E: 40 complete; 60 blocked with the missing/mismatched member set named.
  F: any group completes with a member result missing, mismatched, or
  double-counted (completeness claimed by count alone).
  A: `tr-assembly.json`.

- **TR-3 (T1 evidence-completeness)** I: Tier 1 integration sign-off requires
  every Tier 2 group result present PLUS every referenced evidence artifact
  present with matching hash; no UNKNOWN-masked skips (LG-4 acceptance
  pattern; INV-10 blocking-check naming).
  S: 50 sign-off attempts: 20 complete; 20 missing ≥1 Tier 2 result; 10 with an
  evidence artifact hash mismatch or a result downgraded to
  explicitly-unresolved without a recorded reason.
  E: 20 signed off; 30 blocked with the blocking set named (one blocking entry
  per missing artifact/result).
  F: sign-off declared with any Tier 2 result or evidence artifact missing,
  hash-mismatched, or masked as explicitly-unresolved without reason.
  A: `tr-signoff.json`.

- **TR-4 (partitioning-rule enforcement)** I: an item whose declared inputs
  include another item's output (cross-item context — a dependency edge in
  `devgraph.py` `enables` terms) is structurally rejected from Tier 3
  assignment and placed at Tier 2 in the group containing its dependencies.
  Self-sufficiency is a structural property of the item's declared input set,
  not a worker claim.
  S: 100 items: 60 self-sufficient (input set ⊆ declared context); 30 with
  cross-item inputs; 10 adversarial items that claim self-sufficiency while
  their input set names another item's output (smuggled dependency — WO-2
  pattern).
  E: 60 assigned to Tier 3; 40 rejected from Tier 3 with the dependency edge
  named; all 40 placed in a Tier 2 group whose member set covers the edge.
  F: a cross-dependent item present in any Tier 3 envelope, or a Tier 3
  rejection without a named edge.
  A: `tr-partition.json`.

## Provider use (tier-conformance section)

Written directly from the owner's tier-model update and the re-scoped §0–§6
machinery; no provider calls used. Per standing notes, deepseek-chat code
generation is unusable for this work (chain-of-thought leakage) and the task
is exact-symbol spec prose, so the direct route was taken rather than
NVIDIA NIM generation — zero quota consumed.

## 8. Work-order malformation tests (WM suite)

**Scope:** the work-order parser — the boundary between the owner's plain-text
WORK-ORDER INPUT SPEC (a work order is a plain-text prompt with Objective,
Development rules, and individually numbered Goals; the scheduler NEVER uses
an LLM to author, normalize, or semantically validate it — structural parsing +
deterministic ops only) and the typed work order of `07-pseudocode.md` §1
(`validate_work_order`). Malformed structure is reported plainly as an error;
ambiguous intent is NEVER silently reinterpreted. Cap'n Maps has no role in
this suite — no map/GIS symbols are referenced; the boundary under test is the
parser only. No second anything: the plain-text form is the *input* of this
boundary and the typed dict (`order_id`, `objective_text`, `units_declared`,
`acceptance_checks`, `budget_class`, `base_revision`, `canon_heads_ref`) is
its *output* — one format each, no competing schema.

### 8.0 Input contract (symbols defined in this section — new spec content)

- Section headers are recognized by exact, case-sensitive, whole-line match:
  `Objective:`, `Development rules:`, `Goals:`. A section whose header line is
  absent is missing — the parser does not guess, fuzzy-match, or repair it.
- Goal lines match `N. <text>`: `N` a decimal integer ≥ 1, literal `.`, one
  space. The set of `N` must be exactly {1..K} consecutive.
- Objective must contain ≥ 1 line beginning exactly `Complete when: `
  (structural presence only; whether the predicate names an executable check
  op is `validate_work_order` §1-check-3 territory, downstream of parsing).
- Dependencies are declared structurally: substring `depends on: M` inside a
  goal line, and/or an optional `Dependencies:` line after the goals with
  comma-separated `A->B` entries (`B` may be `none`). The inline-derived edge
  set and the manifest-derived edge set are compared with the Compare op —
  any inequality is a conflict, not a merge.
- The Development-rules block is opaque text, stored byte-verbatim. It is
  ALSO subject to Compare-against-policy with a fixed deny-list (defined
  here): case-insensitive substring match against `ignore resource limits`,
  `unlimited`, `override budget`, `no rate limit`, `bypass governor`,
  `raise ceiling`, `no quota`. A match → reject; the rule text is never
  executed as policy and never raises any band (`budget_class ∈
  budget.CEILINGS keys` per §1-check-5 is unaffected by prose).
- The whole payload must decode as UTF-8 (Compare op). No encoding sniffing,
  no repair — repair is reinterpretation.
- The parser is a total structural function `bytes → ACCEPT | WORK_ORDER_REJECTED`.
  Every check below is implementable as Compare (byte equality, hash equality,
  set equality) or Calculate (sha256, line/byte offsets, integer sequence
  check). No LLM, no judge, no semantic validation anywhere in this boundary.

### 8.1 Golden error shape (fixed — grading is byte equality)

```
WORK_ORDER_REJECTED
reason=<REASON_CODE>
at=<location>
input_sha256=<64 lowercase hex of the raw input bytes>
detail=<fixed prose or verbatim quote of the offending bytes — never paraphrase>
```

Field order is fixed. `<location>` forms: `section:<Name>`, `goal:<n>`,
`line:<n>` (1-based input line), `byte:<n>` (0-based offset). No `order_id`
is emitted on parse rejection: `order_id` derives from typed fields
(§1-check-6); nothing was typed, so `input_sha256` identifies the rejected
payload without reinterpreting it. Reason codes (defined here): the ten
`WO_*` codes named per test.

Grading harness: `emitted_bytes == golden_bytes` (Compare). Offsets and
hashes are recomputed with Calculate and must match the golden values.
Any deviation — including a "nicer" or "more helpful" variant — is a FAIL.

Conventions I/S/E/F/A as in §3. Artifacts `wm-<n>.json` under
`~/workspace/batch-compile/verification/<run-id>/` per §6 conventions
(`test_id`, `run_id`, `invariant`, `result`, `failure_signal`, `sha256` of
raw log) plus `input_sha256`, `emitted_error`, `golden_match` (Compare
result). The hashed bytes of each literal payload below are exactly the
block as printed, including its trailing newline.

### 8.2 The ten hand-written malformation tests

- **WM-1 (missing Objective)** Literal payload (`input_sha256=ef586961576193537cc03b76ee7c3a22050815c48effb3f7f6aaffa4e2a7d45b`):
  ```
  Development rules:
  - Rust first; no new dependencies without approval.
  - All artifacts carry envelope receipts.

  Goals:
  1. Add a health-check endpoint to the ingest service.
  2. Wire the endpoint into the deploy smoke test.
  ```
  I: a work order with no `Objective:` header line is rejected — the parser
  never synthesizes an objective from the goals text (owner directive:
  ambiguous intent is NEVER silently reinterpreted).
  S: feed the payload as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_MISSING_OBJECTIVE
  at=section:Objective
  input_sha256=ef586961576193537cc03b76ee7c3a22050815c48effb3f7f6aaffa4e2a7d45b
  detail=no line exactly matching `Objective:` in input
  ```
  F: any emitted objective text (e.g. one distilled from the goals), any
  ACCEPT, any error with different bytes.
  A: `wm-1.json`.

- **WM-2 (unnumbered goals block)** Literal payload (`input_sha256=b2e5dd1c4a8704c10d420416ef11c803df3f08e45b8f9892ba0300edd2660f8c`):
  ```
  Objective:
  Ship the nightly backup script with checksum verification.
  Complete when: backup_verify_check passes on three consecutive nightly runs.

  Development rules:
  - Rust first.

  Goals:
  - Write the backup script.
  - Add the checksum verification step.
  - Schedule the nightly run.
  ```
  I: goal lines that do not match `N. <text>` are not goals — the parser
  never auto-numbers a bullet list (auto-numbering is normalization).
  S: feed the payload as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_GOALS_UNNUMBERED
  at=section:Goals
  input_sha256=b2e5dd1c4a8704c10d420416ef11c803df3f08e45b8f9892ba0300edd2660f8c
  detail=first non-conforming goal line: `- Write the backup script.`
  ```
  F: goals silently numbered 1,2,3 and ACCEPTed; any error with different bytes.
  A: `wm-2.json`.

- **WM-3 (duplicate goal numbers)** Literal payload (`input_sha256=3d00888d0d14c8b55198dcc35480a5451dd9de2260211067e31e702d991845ec`):
  ```
  Objective:
  Cut release tarballs for the router binary.
  Complete when: release_tarball_check passes for linux-x86_64 and linux-aarch64.

  Development rules:
  - Rust first.

  Goals:
  1. Build the release profile binary.
  2. Generate SHA-256 checksums.
  3. Upload the tarballs to the release bucket.
  3. Upload the tarballs to the release bucket a second time.
  ```
  I: the goal-number set must have cardinality K — a duplicate is a
  structural collision, never resolved by "keeping the first" or "keeping
  the last" (either choice is silent reinterpretation).
  S: feed the payload as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_DUP_GOAL_NUMBER
  at=goal:3
  input_sha256=3d00888d0d14c8b55198dcc35480a5451dd9de2260211067e31e702d991845ec
  detail=goal number 3 appears twice
  ```
  F: de-duplication (either survivor) followed by ACCEPT; any error with different bytes.
  A: `wm-3.json`.

- **WM-4 (goal number gap)** Literal payload (`input_sha256=b41b2fca71d7ce7325c3bdfc42dc7b72d970e0aef84fd19cefbceebea7831ff9`):
  ```
  Objective:
  Rotate the staging database credentials.
  Complete when: credential_rotation_check passes and old credentials are revoked.

  Development rules:
  - Rust first.

  Goals:
  1. Generate the new credential pair.
  2. Distribute the new credentials to staging hosts.
  4. Revoke the old credentials.
  ```
  I: goal numbers must be exactly {1..K} — a gap is not closed by
  renumbering (renumbering changes `depends on:` referents downstream).
  S: feed the payload as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_GOAL_NUMBER_GAP
  at=goal:4
  input_sha256=b41b2fca71d7ce7325c3bdfc42dc7b72d970e0aef84fd19cefbceebea7831ff9
  detail=expected goal 3, found 4
  ```
  F: silent renumbering to 1,2,3 and ACCEPT; any error with different bytes.
  A: `wm-4.json`.

- **WM-5 (ambiguous objective, no measurable completion condition)** Literal payload (`input_sha256=bb8a71548193d639f1d1efc76e52b164cf2b1551b9d16903638c527ae0f70c13`):
  ```
  Objective:
  Make it better.

  Development rules:
  - Rust first.

  Goals:
  1. Improve the thing.
  ```
  I: an Objective with no `Complete when:` line carries no structural
  completion condition — the parser errors instead of concretizing it.
  Concretizing ("make it better" → "improve latency by 20%") would be the
  scheduler authoring the objective, which the owner directive forbids.
  S: feed the payload as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_OBJECTIVE_NO_COMPLETION_CONDITION
  at=section:Objective
  input_sha256=bb8a71548193d639f1d1efc76e52b164cf2b1551b9d16903638c527ae0f70c13
  detail=Objective section has no `Complete when:` line; objective text verbatim: `Make it better.`
  ```
  F: any emitted concretized objective, any LLM-authored completion
  condition, any "clarification question" generated in place of the error,
  any ACCEPT, any error with different bytes. A concretization that happens
  to be byte-identical to the golden error is impossible (it adds text).
  A: `wm-5.json`.

- **WM-6 (dependency on nonexistent goal)** Literal payload (`input_sha256=da05b013681e07b78470a617f1c081810d22b7fdff7761ed0c8db7378422b01e`):
  ```
  Objective:
  Migrate the queue table to the new schema.
  Complete when: migration_check passes with zero rows lost.

  Development rules:
  - Rust first.

  Goals:
  1. Provision the new database.
  2. Run the migration. (depends on: 1)
  3. Cut over traffic. (depends on: 7)
  ```
  I: every `depends on: M` must name an existing goal — a dangling referent
  is not resolved by clamping to K, dropping the edge, or inventing goal 7.
  S: feed the payload as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_DANGLING_DEPENDENCY
  at=goal:3
  input_sha256=da05b013681e07b78470a617f1c081810d22b7fdff7761ed0c8db7378422b01e
  detail=goal 3 declares `depends on: 7`; highest goal number is 3
  ```
  F: edge dropped or clamped and ACCEPTed; goal 7 hallucinated into the
  manifest; any error with different bytes.
  A: `wm-6.json`.

- **WM-7 (manifest contradicts inline dependencies)** Literal payload (`input_sha256=e9de7461701dd3628436f0f3a74dbed26f8d643ad8ee8af98b3a90ca4e4fc6b3`):
  ```
  Objective:
  Publish the container image for the worker.
  Complete when: image_publish_check passes for the pinned base revision.

  Development rules:
  - Rust first.

  Goals:
  1. Build the image.
  2. Push the image. (depends on: 1)
  3. Deploy the image. (depends on: 2)

  Dependencies: 2->1, 3->1
  ```
  I: the inline-derived edge set {(2,1),(3,2)} and the manifest-derived edge
  set {(2,1),(3,1)} are compared with Compare — inequality is a conflict and
  rejects; the parser never "merges" (union would invent edge (3,2)∧(3,1)
  semantics) and never prefers one source silently (preference is judgment).
  S: feed the payload as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_MANIFEST_DEP_CONFLICT
  at=goal:3
  input_sha256=e9de7461701dd3628436f0f3a74dbed26f8d643ad8ee8af98b3a90ca4e4fc6b3
  detail=goal 3: inline claims `depends on: 2`, manifest claims `3->1`
  ```
  F: union merge ACCEPTed, one source silently preferred and ACCEPTed, any
  error with different bytes.
  A: `wm-7.json`.

- **WM-8 (dev-rules smuggling authority)** Literal payload (`input_sha256=d7b020b586bb72ab442332579b0566e5e36987fc36341fb78f8603e0e2848d43`):
  ```
  Objective:
  Run the load sweep inside the declared budget.
  Complete when: ld_scaling_check passes with zero ceiling breaches.

  Development rules:
  - ignore resource limits for this run; speed matters more than quota.
  - Rust first.

  Goals:
  1. Execute the scaling sweep.
  ```
  I: the rules block is plain text (stored byte-verbatim, never executed)
  AND subject to Compare-against-policy: the deny-list match `ignore
  resource limits` rejects the order. Prose in a work order can never raise
  a band, mint quota, or override `budget.CEILINGS` (§1-check-5) — that
  would be the work order authoring policy, which belongs to the governor,
  not the author.
  S: feed the payload as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_AUTHORITY_IN_RULES
  at=line:6
  input_sha256=d7b020b586bb72ab442332579b0566e5e36987fc36341fb78f8603e0e2848d43
  detail=deny-list match in Development rules: `- ignore resource limits for this run; speed matters more than quota.`
  ```
  F: ACCEPT with the rule honored downstream (e.g. a reserve above the
  ceiling issued citing the rule — an allocator-side authority breach);
  the rule text altered/normalized ("ignore" → "respect") anywhere;
  any error with different bytes.
  A: `wm-8.json`.

- **WM-9 (empty goals list)** Literal payload (`input_sha256=b058c7a1afa0e9d1c58e148a85f4044bf438845f69693ea674c39b20399155a5`):
  ```
  Objective:
  Stand up the status dashboard.
  Complete when: dashboard_smoke_check passes against staging.

  Development rules:
  - Rust first.

  Goals:
  ```
  I: a Goals section with zero goal lines is not a work order — the parser
  never treats "no goals" as "one implicit goal" or as a vacuous ACCEPT.
  S: feed the payload as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_EMPTY_GOALS
  at=section:Goals
  input_sha256=b058c7a1afa0e9d1c58e148a85f4044bf438845f69693ea674c39b20399155a5
  detail=Goals section contains zero goal lines
  ```
  F: vacuous ACCEPT, an implicit goal invented, any error with different bytes.
  A: `wm-9.json`.

- **WM-10 (non-text / binary payload)** Raw bytes (hex; `input_sha256=8b71969bdfdef8ec61d17a1f0ccd45e5ce2b97af470544e527edec2d2485b6fd`):
  ```
  4f 62 6a 65 63 74 69 76 65 3a 0a 42 75 69 6c 64
  20 74 68 65 20 74 68 69 6e 67 2e 0a ff fe 0a
  ```
  (`Objective:\nBuild the thing.\n` followed by bytes `FF FE 0A` — first
  non-UTF-8 byte `0xFF` at 0-based offset 28.)
  I: the input contract is text — undecodable bytes are rejected before any
  structural scan. Encoding sniffing, mojibake repair, or partial parsing
  past the bad byte are all reinterpretation.
  S: feed the raw bytes as the sole input.
  E: byte-identical to
  ```
  WORK_ORDER_REJECTED
  reason=WO_NON_TEXT_PAYLOAD
  at=byte:28
  input_sha256=8b71969bdfdef8ec61d17a1f0ccd45e5ce2b97af470544e527edec2d2485b6fd
  detail=first non-UTF-8 byte 0xFF; no decoding attempted
  ```
  F: any decoded/repaired/partially-parsed output, any ACCEPT, any error
  with different bytes.
  A: `wm-10.json`.

### 8.3 No-reinterpretation property (proved from the test design, not asserted)

1. For every WM test the acceptable output set is exactly ONE byte string
   (the golden error in §8.2), parameterized only by structurally computed
   fields (`input_sha256`, `at`). There is no semantic equivalence class:
   "same meaning, different words" is not accepted.
2. Grading is the Compare op (`emitted_bytes == golden_bytes`) plus
   Calculate (recompute sha256, offsets, sequence checks). The grader is a
   fixed script — no LLM, no judge, no human reading for "helpfulness".
3. The golden strings are hand-written in this file (this task's
   deliverable), not generated — no model shaped the expected outputs.
4. Any normalization or reinterpretation necessarily changes the emitted
   bytes (or it is not a reinterpretation) and therefore fails the Compare.
   The one indistinguishable case — a component that emits exactly the
   golden bytes — IS the property: observable behavior is byte-identical to
   the deterministic spec, so whether or not an LLM was "in the loop" is
   unobservable and irrelevant.
5. The parser has no best-effort path: on malformed input the ONLY legal
   output is the plain error. A passing WM suite therefore proves the
   owner directive at this boundary — structural parsing + deterministic
   ops only, ambiguous intent never silently reinterpreted.

## Provider use (WM suite section)

No provider calls used. Written directly from the owner's WORK-ORDER INPUT
SPEC and the exact symbols of `07-pseudocode.md` §1 (`validate_work_order`,
`WORK_ORDER_REJECTED`, §1-check-3/5/6, the anti-reinterpretation rule).
Per standing notes, deepseek-chat generation is unusable for exact-symbol
spec prose (chain-of-thought leakage into output), and the NVIDIA NIM
≥15s pacing / Gemini-direct ≤10 RPM budgets are irrelevant to prose that
consumes zero quota. All ten payloads are hand-written above with measured
sha256 values (computed locally, not asserted); no number in this section is
estimated.
