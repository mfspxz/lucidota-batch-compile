# SPEC §12.7 — Executable Pseudocode: Minimal Pipeline
*Mission 2 (§6, §7, §9) · SPEC deliverable #7 of §12.12 · RE-SCOPED per owner directive 2026-10-09 (architecture simplification)*
*Authoring: spec agent (subagent 4afd911e) · 2026-10-09*
*Status: SPECIFICATION ONLY — nothing here executes. Every identifier resolves to the exact symbol or store named; nothing new is invented.*
*Tier model: owner update 2026-10-09 — N=3, numbering INVERTED (Tier 1 = top). Tiers defined by context/responsibility scope, NOT model capability. No fourth tier.*

## 0. Minimal architecture

```
Prompts → Typed work order → Partition → Group → Assign → Schedule → Workers → Record → Repeat
   [M]          [M→D]             [D]       [D]      [D]        [D]        [M]       [D]      [D]
                                                        T3 → T2 → T1 (tier flow)
```

Scheduler ops vocabulary (deterministic): **Partition, Group, Assign, Schedule, Record, Repeat**.
Assign mapping: T3 ← single checks · T2 ← check groups · T1 ← complete kit.
Prompts are developer-defined/supplied; the scheduler DISTRIBUTES, never authors, never judges.

### Tier definitions (context/responsibility scope — N=3, fixed)

- **Tier 3 — single-check worker:** basic dev rules + ONE checklist item + specific inputs/context + defined output + completion condition. Max parallel, minimal context. A T3 unit is performable with its supplied context alone — this is the structural partitioning rule (see §2): if an item needs context beyond its own supply, it is NOT T3.
- **Tier 2 — check-group worker:** basic rules + GROUP of related items + relevant Tier 3 results + shared context + group output + completion condition. Combines T3 results, handles local dependencies, resolves bounded in-group inconsistencies. Inconsistency beyond the bound → escalate to Tier 1 as a cross-group concern (never resolved by judgment).
- **Tier 1 — full-context developer:** complete rules + entire checklist + objective + specs/constraints + Tier 2 results + evidence. Owns coherence + final integration + cross-group concerns. T1 is the top, not the bottom.

Tier flow: **T3 completion → T2 group assembly (bounded in-group inconsistency resolution) → T1 integration (cross-group concerns, final coherence).** Tiers are scope labels on the same deterministic pipeline, not capability ranks and not validator layers.

- **[D]** = DETERMINISTIC: pure function of inputs; replay-identical. No model call. The kept deterministic ops are exactly: **Compare, Calculate, Compare-against-policy, Route, Track, Stop**.
- **[M]** = MODEL PROPOSAL: generative output, untrusted until a **[D]** check op accepts it. There are exactly TWO [M] points in the pipeline: (1) work-order authoring (human + authoring LLM), (2) Worker generation strictly within assignment. Everything between is **[D]**.
- A model proposal can never: self-accept, raise its own budget, authorize a tool, change policy, reinterpret the objective, or fabricate a check result (Mission §4 contract).

### CUT (explicit — do not reintroduce)

1. **Semantic-judge LLM** — no model ever grades, scores, or judges another model's output. Acceptance is check ops (Compare/Calculate), never judgment.
2. **Hierarchy of validators** — no stacked verifier layers (no independent-verifier-over-court-over-PL chains). One flat set of check ops + one deterministic aggregation rule.
3. **LLM-debates-LLM layers** — no adversarial debate rounds, no cross-examination between models. Disagreement is resolved by deterministic re-check, not by argument.
4. **Autonomous reinterpretation of the human's objective** — no stage may restate, expand, or "improve" the objective. Deviation = POLICY_FAILURE, terminal `blocked`.

### Reused building blocks (no second governor/router/ledger/scheduler/validator)

| Symbol | Source (measured) | Pipeline role |
|---|---|---|
| `compute.governor.govern()` | `compute/governor.py:65`, 19 checks A–R GREEN | Assign/Schedule: provider selection + replay receipt; `MAX_GOVERN_DEPTH=3`; `_codify()` reason codes |
| `compute.budget.check()` / `budget.CEILINGS` / `budget.quota_state()` | `compute/budget.py:112,36,205` | Assign/Schedule: bands `normal_operations [0,0.60)`, `catastrophic_debugging [0.60,0.80)`, `final_architecture [0.80,0.90)`, `capability_research [0.90,1.00)`; reserve bands authority-gated (`reserve_authorized_by="governor"`) |
| `burn.budget_guard()` / `burn.NVIDIA_BAND_GUARD=0.55` | `compute/burn.py:900,90` | Assign/Schedule: pause at utilization ≥ 0.55, resume at < 0.50 |
| `nvidia_rpm.acquire(n)` | `compute/nvidia_rpm.py:52` | Assign/Schedule: token bucket (capacity 39, refill 39/min), `fcntl` cross-process lock, atomic test-and-set — the pattern for ALL provider buckets |
| `dispatch.create_dispatch / mark_executing / complete_dispatch / fail_dispatch / reconcile` | `compute/dispatch.py:164,187,197,233,269` | Track: crash-atomic event append |
| `dispatch._fold_state()` | `compute/dispatch.py:112` | Track: append-only fold; `executing` only from `dispatched` (guard) |
| `queue.add / mark / drain` | `compute/queue.py:39,114,125` | Route: `queued → dispatched → executing → completed | failed | expired` |
| `court.derive_status()` | `compute/court.py:94` | **Single** deterministic acceptance aggregation: required checks bound to receipts → verdict. Used as a [D] Compare-against-policy op, NOT as a judge layer. |
| `envelope.wrap / verify / verify_chain` | `compute/envelope.py:144,169,200` | Track: `lucidota-receipt/1` seal (canonical JSON, HS256 sig, `seal = sha256(canonical incl. sig)`) |
| `ledger.record / verify_envelopes / request_hash_for` | `compute/ledger.py:122,155,42` | Track: every execution wrapped in envelope at ingest |
| Exchange health states | `exchange/worker.js:67` | `AVAILABLE | DEGRADED | THROTTLED | EXHAUSTED | QUARANTINED | UNKNOWN` — cooldown vocabulary |
| Exchange failure taxonomy | `exchange/worker.js:24,745` | `RETRYABLE_FAILURE | PERMANENT_FAILURE | POLICY_FAILURE | AUTH_FAILURE | QUOTA_FAILURE | CAPABILITY_FAILURE | PROVIDER_FAILURE | VERIFICATION_FAILURE` |
| Worker outcomes | `exchange/worker.js:153–158` | `SUCCEEDED | FAILED_RETRYABLE | FAILED_PERMANENT | QUARANTINED | EXPIRED` |
| `devgraph.py ready <slug>` | `workspace/bin/devgraph.py:9,95` | Partition/Group/Schedule: ready = open nodes with all enables-predecessors done |
| `full-send/brief-lint.sh` | `full-send/brief-lint.sh` | Pre-dispatch gate: briefs must pass; lint forbids authorizing destructive git ops |
| Measured quotas (f8) | adapter probes 2026-10-07/08 | NVIDIA 39 RPM adapter ceiling (provider limit UNVERIFIED); Gemini 10 RPM probe-proven (4×200 then 503; 20 generate/day); operational cadences 37 / 8.5 RPM; lease 60 s; zombie sweep > 10 min |

---

## 1. Typed work order — authoring [M], validation [D]

The work order is the ONLY place a model may shape the objective, and only as a drafting assistant to the human. Once typed, the objective is frozen.

```
author_work_order(prompts):                            [M] human + authoring LLM
  IN: human prompts (the objective, in the human's words).
  The authoring LLM drafts a TYPED work order; the human approves.
  OUT: work_order {order_id, objective_text (frozen), units_declared,
       acceptance_checks (executable check-op refs, not prose),
       budget_class, base_revision, canon_heads_ref}
  -- The draft is a proposal. It becomes binding ONLY after §1 validation.

validate_work_order(wo):                                [D] Compare / Compare-against-policy
  PRE: wo is a dict; `canon snapshot` exit 0.
  FAIL: any PRE false or any check below fails → WORK_ORDER_REJECTED receipt;
    nothing downstream runs. Fail-closed.
    1. schema: all typed fields present, correct types, no unknown fields.
       Unknown field → REJECT (INV-03: unknown fields cannot smuggle semantics).
    2. no self-accept: fields named accepted/verified/done → REJECT.
    3. acceptance_checks are executable: every entry names a check op from
       the §5 registry keyed by artifact class. Prose checks ("looks good") →
       REJECT. (Mission §7: docs are not development.)
    4. boundedness: every declared unit carries max_output_tokens + artifact
       size cap + single-turn constraint (no long conversations, Mission §7).
    5. budget_class ∈ budget.CEILINGS keys or "non_nvidia_free"; reserve bands
       require reserve_authorized_by="governor" (budget._category RT-B6).
    6. idempotency: order_id = sha256(canonical(objective_text, units_declared,
       acceptance_checks, base_revision)); duplicate → return EXISTING.
    7. authority: actor ≠ master-equivalent (role_claim master/exchange_master
       → REJECTED outright, mcp governor-server pattern).
  OUT: ACCEPTED(order_id) + envelope.wrap status="claimed" receipt.
```

Anti-reinterpretation rule **[D]**: downstream stages receive the frozen `objective_text` hash. Any Worker output whose declared objective hash ≠ frozen hash → POLICY_FAILURE, terminal `blocked`. No stage restates the objective. Ever.

---

## 2. Partition / Group / Assign — deterministic [D]

Scheduler vocabulary for this section: **Partition, Group, Assign**. The scheduler distributes developer-supplied prompts; it never authors or judges.

```
partition(work_order):                                  [D] Calculate — Partition
  PRE: work order ACCEPTED (§1).
  FAIL: cycle in declared dependencies → all units REJECTED, CYCLE receipt.
    1. units: one per work_order.units_declared. Each unit gets
       {unit_id, inputs (bounded refs), outputs schema, constraints,
        check_ops (from work order acceptance_checks), objective_hash}.
    2. sizing rules (no judgment): split any unit exceeding max_output_tokens
       or artifact size cap into N = ceil(size / cap) sub-units with explicit
       interface boundaries. Splitting is arithmetic, not semantic.
    3. edges: declared depends_on → "enables" edges (devgraph.py semantics).
       Cycle check: deterministic DFS.
    4. persist units as versioned records, prev_hash-chained.
  OUT: unit DAG.

group(dag):                                             [D] — Group
  Structural tier rule (encoded on the work graph, not judged):
    TIER 3 ⟸ item performable with its supplied context ALONE.
             Test [D]: unit.inputs ⊇ everything the checklist item references;
             no enables-edge to a not-yet-completed unit except declared
             shared fixtures. Single checklist item, minimal context.
    TIER 2 ⟸ related/dependent checks: a group of T3 units sharing context,
             local dependencies, or one checklist section. Grouped by declared
             relations (same artifact, same interface, shared fixtures) —
             grouping is graph-structural, never semantic.
    TIER 1 ⟸ exactly one assembly per work order: the complete kit
             (objective + specs/constraints + entire checklist + all T2 group
             outputs + evidence). N=3 fixed; no fourth tier.
  OUT: tiered plan {t3_units[], t2_groups[{group_id, member_unit_ids,
    shared_context}], t1_kit}.

assign(tiered_plan):                                     [D] — Assign
  T3 ← single checks (max parallel, minimal context per unit).
  T2 ← groups (group envelope = basic rules + related items + relevant T3
       results slot + shared context + group output schema + completion cond).
  T1 ← complete kit (complete rules + entire checklist + objective +
       specs/constraints + T2 results slot + evidence slot).
  Assignment is routing by tier label. The scheduler does not choose which
  model fills a slot beyond govern() provider selection (§3) — tiers are
  scope, not capability ranks.

ready_scan(tiered_plan):                                 [D] — Schedule input
  T3: ready(unit) = all enables-predecessors terminal-accepted (devgraph ready).
  T2 group: schedulable when ALL member T3 units terminal (accepted or
      dead-lettered — a dead-lettered member is recorded, not waited on).
  T1 kit: schedulable when ALL T2 groups terminal.
  Dependency-blocked stays blocked — never scheduled, never retried into ready.
  DISPROVEN dependency → dependents pruned to `failed` with prune receipt
  (exchange worker.js:1117–1128 A2). Deferred units re-enter at queue TAIL.
```

Tier flow: **T3 completion → T2 group assembly (bounded in-group inconsistency resolution) → T1 integration (cross-group concerns, final coherence).** The partitioner/grouper does not understand the work. It counts, splits, links, labels by the structural rule, and cycle-checks.

---

## 3. Assign / Schedule — deterministic [D] (Route)

Assign + Schedule = `govern()` (who) + budget (may we spend) + bucket (is there rate) + dispatch (go). Operates per tier slot from §2; tier does not change the mechanics, only the envelope (§4) and retry scope (§7).

```
allocate(unit):                                         [D]
  PRE: unit ready (§2); provider health ∉ {EXHAUSTED, QUARANTINED}.
  FAIL: PRE false → NO reservation; unit stays ready; RESERVE_DENIED receipt
    with _codify() reason code.
    1. decision = govern(task_features(unit), proposer="allocator")
       -- divergence assert: decision.chosen_source == receipt source
       -- (nondeterminism tripwire, governor.py). Proposer preference advisory.
    2. (allowed, reason) = budget.check(provider, unit, used=single_read)
       -- RT-A2 single quota read; non-NVIDIA → always True.
       -- category = budget._category(unit); allowed iff
       -- used < CEILINGS[category] * estimate; nothing at/over estimate.
    3. burn hysteresis: u = budget.quota_state()["utilization"];
       u ≥ 0.55 → lane PAUSED; u < 0.50 → RESUMED (burn.budget_guard pattern).
       Paused lane: reserve DENIED(BUDGET); unit stays ready; no attempt burned.
    4. reserve via provider bucket (nvidia_rpm.acquire pattern, per provider):
       with fcntl LOCK_EX: refill; if tokens ≥ 1: tokens -= 1; write
       {unit_id, attempt_id, provider, reserved_at, lease_expiry = now+60s};
       crash-atomic tmp-write + replace. Else DENIED(RATE).
       -- Buckets: nvidia 39/min, gemini 10/min (measured ceilings); unknown
       -- pools capacity 1 (fail-closed). Token estimates advisory only
       -- (no TPM probes exist — recorded unquantified).
    5. dispatch.create_dispatch(decision, unit_id); queue.mark(unit,"dispatched").
       Launch provider call with the FIXED worker envelope (§4).
       mark_executing on first byte (fold guard: executing only from dispatched).
  OUT: executing handle. All state changes append-only + receipted.
```

Reservation expiry: unconsumed within 60 s → EXPIRED, tokens refunded under fcntl, unit to ready tail (exchange EXPIRED-claim pattern).

---

## 4. Workers — the second and last [M] point, strictly within assignment

Tier-scoped envelopes. The tier sets context scope, not model rank. Every envelope is developer-supplied prompts distributed by the scheduler — the scheduler never authors prompts.

```
worker_envelope(slot, attempt_id):                       [D] constructed, [M] executed
  common: {slot_id, tier (3|2|1), attempt_id, objective_hash (frozen),
           idempotency_key, lease_expiry, merge_authority=false,
           budget_class, constraints}
  T3: + {basic_dev_rules, ONE checklist item, specific inputs/context,
         defined output schema, completion condition}
       -- minimal context; max parallel. No T3 unit sees another unit's work.
  T2: + {basic_rules, GROUP of related checklist items, relevant T3 results
         (accepted artifacts of member units), shared context, group output
         schema, completion condition}
       -- combines T3 results; resolves bounded in-group inconsistencies
       -- structurally (re-run, pick by deterministic rule — never by taste).
  T1: + {complete rules, ENTIRE checklist, objective, specs/constraints,
         Tier 2 group results, evidence}
       -- owns coherence + final integration + cross-group concerns.
  -- Fixed envelopes per Mission §7: bounded prompt, explicit inputs/outputs/
  -- constraints/acceptance tests, return bounded artifact, exit. No
  -- conversation turns. Inputs are bounded refs only — NEVER full transcripts.
  -- No tools beyond the assignment's declared set.

worker_generate(envelope):                               [M]
  The model produces artifact bytes within the envelope. NOTHING ELSE.
  Forbidden (each → POLICY_FAILURE, terminal blocked, lane quarantined):
    self-acceptance fields; budget/authority claims; policy changes;
    objective restatement (objective_hash mismatch); tool use outside
    the declared set; output exceeding bounded caps; T3/T2 claiming
    cross-group authority (T3 sees only its item; T2 only its group).
```

Worker output is evidence. It is never a verdict, never an authorization, never a reinterpretation. A T2 worker combining T3 results performs deterministic assembly per its group rules; genuine cross-group conflict is NOT resolved here — it escalates to T1 (§8).

---

## 5. Check ops — deterministic [D] (Compare / Calculate / Compare-against-policy)

One flat set. No hierarchy, no judges, no debates. Each op is Compare (diff against expected), Calculate (run it, read the exit code), or Compare-against-policy (match an allowlist / threshold).

```
run_checks(unit, artifact, attempt_id):                   [D]
  PRE: worker outcome SUCCEEDED (shape-classified, §6/07-§4 rules);
       artifact staged under attempt_id; canon snapshot verifies.
  FAIL: PRE false → artifact stays staged; unit → FAILED_RETRYABLE
    (check-infra failure is retryable, not artifact failure).
    1. shape Compare: artifact matches outputs schema; required files present;
       no undeclared executables. Sanitize: strip worker-minted
       accepted/verified/authority fields (AiProposal::sanitize pattern);
       verdict never depends on them (INV-01).
    2. secret-scan Compare-against-policy: fail-closed scan (secret-scrub.py
       pattern); candidate secret → VERIFICATION_FAILURE, no retry on same input.
    3. class Calculate ops (exact, per artifact class):
       compile:      pinned toolchain build exit 0; warnings ≤ baseline.
       unit:        named suites exit 0; zero failures; zero masked skips.
       integration: contract tests from versioned interfaces exit 0.
       adversarial: artifact threat-cases exit 0 AND no OPEN CRITICAL/HIGH
                    falsification against this artifact.
       security:    secret-scan + dependency allowlist; no undeclared egress.
       final-tree:  clean-checkout reproduce + full suite + canon snapshot
                    verify + envelope.verify_chain over run receipts.
    4. evidence bind [D]: each passing check → receipt {check, artifact_hash,
       attempt_id, ts} via envelope.wrap.
    5. aggregate [D]: verdict = court.derive_status(
         evidence={gate: {receipt:{claim_id, evidence_hash}} per
                   court.REQUIRED_GATES[unit.classification]},
         claim_id=unit.claim_id)
       -- all required checks bound → ESTABLISHED → artifact ACCEPTED.
       -- unbound/forged → UNKNOWN (gates listed in `unbound`).
       -- canon unverifiable → UNKNOWN (fail-closed).
       -- This is the SINGLE acceptance aggregation: deterministic
       -- Compare-against-policy, not a judge layer.
  OUT: ACCEPTED → artifact manifest published (claimed→established envelope);
       REJECTED → fixed retry rules (§7) with VERIFICATION_FAILURE.
```

Tier relation: T3 workers PERFORM the checklist items [M]; the §5 check ops VERIFY the resulting artifacts [D] — performing ≠ verifying, and the same tier never does both for the same item. T2 groups combine verified T3 results (bounded in-group inconsistency resolution is structural: re-run or deterministic pick rule, never taste). T1 owns final coherence: entire-checklist re-verification on the integrated tree (final-tree class op) + cross-group concerns. No tier judges another; each tier's output is check-op verified before the next tier consumes it.

Successful response ≠ successful artifact; passing unit test ≠ system correctness (Mission §7). Both are Compare/Calculate facts, not judgments.

---

## 6. Record — deterministic [D] (Track)

```
emit_receipt(event_type, payload, prev_seal):             [D]
  env = envelope.wrap(actor, claim_id, status, payload, prev_hash=prev_seal)
  -- status ∈ {claimed, established}; "authorized" has no compute/ call site
  -- (f2 gap) — this spec never emits it.
  append crash-atomic (tmp-write + replace); prev_seal = env["seal"].
  Every state-changing op in §§1–5, 7–9 emits exactly one receipt.
  ledger.record() wraps every execution at ingest (ledger.py:122).
  Unreached steps labeled "vacuous", never faked (10-gate rule).
```

The ledger tracks. It does not judge (recording ≠ truth, f1).

---

## 7. Repeat — fixed retry rules, deterministic [D] (Route / Track / Stop)

The kept piece. Full per-class matrix: `10-failure-recovery.md` (unchanged terminal states: `accepted | rejected | blocked | cancelled | explicitly-unresolved`).

```
schedule_retry(unit, failure_class, attempt_record):       [D]
  1. Row lookup: {retryable?, same_budget?, backoff, max_attempts,
     alt_provider?, repair?, revalidation?} — 10-failure-recovery.md §1–8.
  2. Not retryable → terminal per row (rejected | blocked | quarantined).
  3. attempts+1 ≥ 8 → terminal `rejected` (dead-letter record appended).
     -- attempts count DISPATCHED attempts only; budget-paused or
     -- provider-paused waiting burns no attempts.
  4. Backoff: provider cooldown per row (THROTTLED 2^(n-1) min cap 60;
     EXHAUSTED 5-min recheck). Unit re-enters READY AT TAIL — never head.
  5. Same-budget? No → retry needs reserve_authorized_by="governor" or waits
     for utilization < 0.50 (budget._category RT-B6).
  6. Alt provider? Yes → govern() re-run with provider excluded; failover
     (§3 on new provider); fallback_chain recorded. No → same provider
     after cooldown.
  7. Repair = bounded WORKER REGENERATION (not a judge, not a debate):
     allowed ONLY for VERIFICATION_FAILURE (and narrow RETRYABLE rows per
     matrix). New bounded envelope: inputs = {artifact, failing check outputs}
     — never the full transcript. Max 2 regeneration rounds per attempt.
     Regenerated artifact re-enters §5 from step 1; never inherits a prior
     ACCEPTED. Revalidation ALWAYS required on any new artifact.
  8. Kill-switch → `cancelled` (10-failure-recovery.md kill-switch table).
  9. Tier scoping [D] — retries are fixed AND tier-scoped:
     T3 item failure → fixed retry of THAT item (same bounded envelope,
        max parallel unaffected) → dead-letter after 8 attempts. A
        dead-lettered T3 member does NOT block its T2 group: the group
        assembles with the dead-letter recorded as evidence (§2 ready_scan).
     T2 group inconsistency beyond the resolution bound → NOT retried at T2
        further; escalated to T1 as a cross-group concern with the conflict
        receipt attached. T2 never loops on what it cannot structurally resolve.
     T1 integration failure → work-order problem → HUMAN. T1 gets one bounded
        regeneration attempt per conflict; persistent failure escalates out
        of the pipeline with full evidence. T1 does not spin.
  OUT: unit ready (tail) with attempts+1, or terminal state.
```

Stop is a first-class op: dead-letter, prune, cancel, and quarantine are all deterministic routing decisions.

---

## 8. T2 group assembly → T1 integration — tier flow, deterministic [D]

Tier flow: **T3 completion → T2 group assembly → T1 integration.** No tier judges another; each tier's output is check-op verified before the next tier consumes it.

```
assemble_group(t2_group):                                 [D] assemble, [M] bounded resolve
  PRE: all member T3 units terminal (accepted or dead-lettered, §2).
  FAIL: PRE false → group waits; never assembles on partial T3 results.
    1. collect accepted T3 artifacts + dead-letter records (evidence, not gaps).
    2. bounded in-group inconsistency resolution [D then bounded M]:
       structural compare first: duplicate/overlapping outputs → deterministic
       pick rule (newest attempt_id wins; declared priority order) [D].
       residual inconsistency within the resolution bound → ONE bounded T2
       worker regeneration (envelope: {member artifacts, conflict receipt,
       group rules}; max 2 rounds), then deterministic re-check (§5) [M/D].
    3. inconsistency BEYOND the bound → STOP resolving; escalate to T1 as a
       cross-group concern with the conflict receipt. T2 never loops on what
       it cannot structurally resolve (§7.9). [D] Route.
    4. group output check-op verified (§5, group output schema) → group
       ACCEPTED; envelope claimed→established.
  OUT: accepted group output, or escalation receipt to T1.

t1_integrate(accepted_groups):                            [D] integrate, [M] bounded
  PRE: all T2 groups terminal (accepted or escalated); base_revision pinned.
  FAIL: base_revision mismatch → batch REJECTED; re-base or new work order.
    1. cross-group conflict detect [D] Compare:
       each group output declares {files_touched, interface_deltas,
       dependency_edges}. Pairwise overlap or contradictory interface deltas
       → cross-group CONFLICT receipt. Undeclarable touch-set → REJECT.
    2. T1 worker (full-context: complete rules + entire checklist + objective +
       specs/constraints + T2 results + evidence) produces the integrated
       resolution [M] — bounded: one attempt per conflict receipt, then
       deterministic re-check (§5). Persistent cross-group failure →
       work-order problem → HUMAN (§7.9). T1 does not spin.
    3. merge [D] (only conflict-free after step 2):
       isolated worktree: `git worktree add <wt> <base_revision>` (additive;
       main checkout untouched — verified via `git status`).
       brief-lint.sh must pass pre-dispatch (forbidden: reset/stash/clean -f/
       checkout --force/push --force/rebase — POLICY_FAILURE if attempted).
       merge gates inside worktree [D]: class checks re-run (§5.3) +
       regression (previously green stays green) + conflict re-scan +
       secret-scan on diff.
       gate failure → worktree ARCHIVED under archive/failed-merges/<id>
       (evidence kept, not deleted); conflict → §7.9 T1 retry/escalation.
       gate success → merge commit on integration branch (history append-only,
       INV-06). Worktree removed only after merge commit exists.
  OUT: merged commit hash + merge receipt, or escalation to human.
```

Final acceptance **[D]**: all slots terminal; `envelope.verify_chain` over run receipts; `court.derive_status` re-run per artifact on fresh canon snapshot; final-tree checks on clean checkout; run verdict names the blocking dimension if not all ESTABLISHED (INV-10 REQUIRED NEXT ACTION pattern). T1 owns coherence — the final acceptance IS the T1 completion condition.

---

## 9. Crash recovery + reconciliation — deterministic [D] (Track)

State is append-only event logs; current state is ALWAYS a fold. Recovery = re-fold + reconcile. No model is asked what happened.

```
recover():                                                [D]
  PRE: event logs present. Missing log → subsystem state UNKNOWN; affected
    units parked explicitly-unresolved, never assumed.
  FAIL: fold raises on corrupt line → quarantine TAIL from corrupt offset;
    head still recoverable; FOLD_CORRUPT receipt with byte offset.
    1. state = _fold_state() (dispatches) + queue fold + receipt-chain fold.
    2. reconcile(now) [D]:
       a. executing with no heartbeat past lease → EXPIRED (execution
          UNCERTAIN — provider may have executed, never claimed free);
          unit → §7 retry with UNCERTAIN flag.
       b. zombie sweep: dispatched/executing, no heartbeat, age > 10 min →
          `deferred` + evidence_log.
       c. reservations expired unconsumed → refund under fcntl.
       d. dispatched-never-executing + lease expired → FAILED_RETRYABLE.
       e. provider-200-but-no-completion-record (crash in the gap): probe
          idempotency key; executed → complete_dispatch with UNCERTAIN-PROVEN
          note; else retry. Never double-apply.
       f. budget: used_calls() re-counted; quota_state() recomputed;
          hysteresis re-evaluated (§3.3).
       g. provider health → UNKNOWN until first probe (PARKED never
          auto-promotes).
    3. ready set recomputed (§2); loop resumes. Attempt counts durable in log.
  OUT: RECOVERY receipt; scheduler resumes. No unit is lost.
```

---

## 10. Determinism ledger — the minimal pipeline

| Stage (scheduler op) | [D] deterministic | [M] model proposal |
|---|---|---|
| 1 work order | schema/bound/authority/idempotency validation; anti-reinterpretation hash check | authoring draft (human + authoring LLM) |
| 2 Partition | sizing arithmetic, enables-edges, cycle DFS | — |
| 2 Group | structural tier rule (T3 ⟸ context-alone; T2 ⟸ related/dependent; T1 ⟸ complete kit, N=3) | — |
| 2 Assign | tier-slot routing (T3 ← single checks, T2 ← groups, T1 ← complete kit); ready() | — |
| 3 Schedule | govern(), budget.check, hysteresis, bucket test-and-set, dispatch guards | — |
| 4 worker | envelope construction (tier-scoped), forbidden-field sanitize | generation strictly within assignment (T3 item / T2 group / T1 kit) |
| 5 check ops | Compare/Calculate/Compare-against-policy; evidence bind; derive_status aggregation | — |
| 6 Record | wrap/verify/verify_chain, crash-atomic append | — |
| 7 Repeat | row lookup, tier-scoped bounds (§7.9), tail placement, failover routing, Stop decisions | bounded regeneration output (Worker, §7.7) |
| 8 T2 assembly | structural compare, deterministic pick rule, escalation routing | bounded in-group regeneration (T2 Worker) |
| 8 T1 integrate | cross-group conflict Compare, worktree mechanics, merge gates | integrated resolution (T1 Worker, one attempt per conflict) |
| 9 recover | fold, guards, reconcile, refund | — |

Truth determination never depends on generative AI (INV-11): every verdict, route, and stop is **[D]**. The ONLY [M] points remain work-order authoring and Worker generation strictly within assignment — at T3, T2, and T1 alike, the Worker never judges, never authors prompts, never reinterprets the objective.

---

## Provider use

No NVIDIA NIM generation and no Gemini critique were used in authoring this file — including the tier-model update. Written directly from the owner directives, the evidence bundle (f1, f2, f4, f8), and the prior spec draft, with symbols re-verified against `compute/` sources. Provider use: **none — direct authoring** (per PROVIDER ROUTING fallback: report which provider did what).
