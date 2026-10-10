# 09 — Observability Runbook (§12.9)

**Owner:** SPEC section agent · **Date:** 2026-10-09 (re-scoped per owner directive same day) ·
**Mode:** specification only — no code, no deploys.
**Context:** synthesis mission `~/workspace/batch-compile/MISSION-2-SYNTHESIS.md`;
MASTER DIRECTIVE delta 3: "Measure accepted artifacts, not agent count."

## 0. The minimal pipeline and its deterministic ops

```
Prompts → Typed work order → Partitioner → Allocator → Workers → Ledger → fixed retry rules → repeat
```

| Stage | Deterministic ops in play | What can go wrong (observably) |
|-------|--------------------------|-------------------------------|
| Typed work order | Compare-against-policy (schema allowlist) | malformed orders, smuggled authority fields |
| Partitioner | Calculate (deterministic split) | nondeterminism, transition-graph violations |
| Allocator | Calculate (λ, reservations) · Compare-against-policy (buckets, bands, gates) · Route (dispatch, failover) | bucket exhaustion, band trips, stuck queue, shared-quota races |
| Workers | Compare (envelope verify, binding match) | forgeries, replays, stale receipts, mismatched artifacts, budget-escalation attempts |
| Ledger | Compare (chain verify) | crash tails, forks, write failures |
| Retry rules | Track (sweeps) · Stop (prune, kill) | zombies, dangling dependents, kill reconciliation |

No semantic judge, no validator hierarchy, no LLM-debates-LLM — so there is
nothing to observe *about* a hierarchy. Every metric below is a count, a rate,
or a deterministic predicate over an existing artifact.

## 1. Metrics per stage

Naming: `bc.<stage>.<metric>`. Each row: definition · source artifact ·
measured baseline (or UNBASELINED) · cadence.

### Work order

| Metric | Definition | Source | Baseline | Cadence |
|--------|-----------|--------|----------|---------|
| `bc.wo.received` | work orders submitted | work-order intake log | UNBASELINED | per min |
| `bc.wo.schema_rejected` | rejected by schema allowlist (WO-1) | intake log, reject reason | UNBASELINED; healthy > 0 under adversarial input, = 0 is fine under clean input | per min |
| `bc.wo.sanitized` | orders with authority fields stripped (WO-2) | sanitization receipts | any > 0 under hostile prompts = the gate working | per min |

### Partitioner

| Metric | Definition | Source | Baseline | Cadence |
|--------|-----------|--------|----------|---------|
| `bc.pt.output_count` | tasks emitted per work order | partition receipts | UNBASELINED (shape: stable per order hash) | per order |
| `bc.pt.determinism_violations` | same order → different partition (PT-1) | partition hash log | 0 — any > 0 is CRITICAL | per order |

### Allocator

| Metric | Definition | Source | Baseline | Cadence |
|--------|-----------|--------|----------|---------|
| `bc.al.queue_depth` | non-terminal tasks | `queue.jsonl` / `dispatches.jsonl` | reference: `queue_pending=839` at burn shutdown = backlog-under-failure, not a healthy baseline | per min |
| `bc.al.queue_age_p95` | p95 non-terminal age | ts deltas in queue/dispatch stores | UNBASELINED; alert on 3-window growth while utilization < 50% | per 5 min |
| `bc.al.bucket_utilization` | dispatches/min ÷ ceiling | `nvidia_rpm_state.json`, `gemini_rpm_state.json` | ceilings: nvidia 39/min (operator), gemini 10/min (measured, f3) | per min |
| `bc.al.rate_limited` | adapter-bucket refusals (NOT provider 429s) | `burn.STATUS.json` (`rate_limited`), `executions.jsonl` outcome | 64 in 2026-10-08→09 burn, all adapter-bucket, zero provider 429s | per min |
| `bc.al.no_feasible_source` | `NO_FEASIBLE_SOURCE` decisions | governor decision receipts (`REASON_CODES`) | UNBASELINED; spike = outage signal | per min |
| `bc.al.band_utilization` | calls ÷ 5000 unverified estimate | `nvidia-usage/calls.jsonl` count vs `budget.json` | 0.5852 (2926/5000, 2026-10-09); guard trips at 0.55, resumes < 0.50 (burn.py:90) | per 5 min |

### Workers

| Metric | Definition | Source | Baseline | Cadence |
|--------|-----------|--------|----------|---------|
| `bc.wk.yield` | accepted artifacts / dispatched tasks | dispatch fold + acceptance log | measured reliability: nvidia 61.9% (1576/2543, incl. 550 invalid + 416 error), ai-router-free 96.3% (104/108), gemini-direct 18 ok / 16 error (f3/f8) | per batch |
| `bc.wk.latency_p50_p95` | completion latency | `executions.jsonl` | nvidia 20.1/41.9s; gemini 2.6/12.3s; ai-router 10.8/19.1s | per batch |
| `bc.wk.invalid_rate` | `invalid` (partial/empty) / completions | `executions.jsonl` outcome | nvidia 550/2543 = 21.6% invalid (adapter marks partial `invalid`, never success) | per batch |
| `bc.wk.compare_rejects` | Compare-op rejections (forgery/replay/stale/binding) | WK-2..WK-4 + ingest audit rows (`envelope_rejections` pattern, f5) | any > 0 under hostile input = gates working | per min |
| `bc.wk.escalation_attempts` | budget/priority self-grant attempts (WK-5/WK-6, TM-2/TM-3) | falsification-style audit rows (`court.record_falsification` sink) | 0 in clean runs; any attempt filed + held | per attempt |

### Ledger

| Metric | Definition | Source | Baseline | Cadence |
|--------|-----------|--------|----------|---------|
| `bc.lg.append_rate` | records appended / min | `~/workspace/compute/envelopes.jsonl`, `~/workspace/proof-ledger/ledger.jsonl` | UNBASELINED | per min |
| `bc.lg.audit_exit` | `pl audit --full` exit code | `pl` binary on production ledger | 0 (Verifier B `_pl_audit` predicate); nonzero = CRITICAL | per audit run |
| `bc.lg.envelope_coverage` | executions with envelopes / total | `ledger.verify_envelopes()` / `envelope_coverage()` | 17 pre-adoption records without envelopes = honest history (f5); alert only if coverage DECREASES | per ledger write |
| `bc.lg.repair_count` | `RepairReport` records appended | ledger scan | 0 expected; any = crash event worth reading | continuous |

### Retry rules

| Metric | Definition | Source | Baseline | Cadence |
|--------|-----------|--------|----------|---------|
| `bc.rt.retry_count` | retries by failure class | retry records (RT-1 taxonomy) | UNBASELINED | per batch |
| `bc.rt.dead_letter_count` | defer_count ≥ 8 → failed | dispatch fold | 0 in clean runs | per batch |
| `bc.rt.zombie_reaped` | sweep reaps (stale running >10 min → deferred) | sweep evidence_log rows | 0 in clean runs; > 5% of running = HIGH | per sweep |
| `bc.rt.kill_receipts` | kill receipts emitted | RT-4 artifacts | 0 unless kill fired | per kill |

## 2. Alerting rules (thresholds tied to measured baselines)

1. **BAND-GUARD-TRIP** · `bc.al.band_utilization ≥ 0.55` · burn.py:90 (measured trip 2026-10-09) · HIGH · P1.
2. **BAND-ESTIMATE-EXHAUST** · `≥ 1.00` of the 5000 UNVERIFIED estimate · `budget.py` fail-closed · CRITICAL · P1 — treat as "re-verify the account," not "quota is empty."
3. **PROVIDER-THROTTLED** · health → THROTTLED · worker.js:67 · MEDIUM · P1 (backoff 2^(n-1) min cap 60 + failover).
4. **PROVIDER-EXHAUSTED** · health → EXHAUSTED · worker.js:67 · HIGH · P1 (suspend; recheck 5 min, f2).
5. **PROVIDER-429-STORM** · provider-issued 429s > 5 / 10 min (distinct from adapter `rate_limited`) · no baseline — zero ever observed on NVIDIA (f8) · HIGH · P1; first-ever NVIDIA provider 429 also opens the "verify the real provider limit" work item.
6. **YIELD-COLLAPSE** · `bc.wk.yield` < 50% of the lane's measured reliability (nvidia 61.9%, ai-router 96.3%) · f3/f8 · MEDIUM · check latency + rate_limited first.
7. **LATENCY-BLOWOUT** · p95 > 2× measured (nvidia 83.8s, gemini 24.6s, ai-router 38.2s) · f3 · MEDIUM · P1.
8. **QUEUE-STUCK** · `bc.al.queue_age_p95` growing 3 consecutive windows while bucket utilization < 50% · shape rule · HIGH · P2.
9. **DETERMINISM-BREAK** · `bc.pt.determinism_violations > 0` · PT-1 · CRITICAL · halt partitioning, diff the divergent outputs.
10. **GATE-DOWN** · any deterministic gate unavailable > 60s (envelope key missing, ledger unwritable, bucket state unreadable) · fail-closed doctrine · CRITICAL · P3 (hold; no self-acceptance).
11. **CHAIN-FORK** · `bc.lg.audit_exit ≠ 0` (REPLAY/STALE/tamper) · `pl audit --full` · CRITICAL · P4.
12. **ESCALATION-ATTEMPT** · `bc.wk.escalation_attempts > 0` · TM-2/TM-3 · HIGH · file falsification row, hold the task.
13. **KILL-FIRED** · informational CRITICAL · run RT-4 reconciliation.

Severity handling: CRITICAL = operator attention, report don't auto-fix; no
alert auto-remediates quota, policy, or code (secret freeze; governor decides
allocation; the operator decides the rest).

## 3. The four incident procedures (mapped to deterministic ops)

### P1 — Throttled / band-exhausted provider → Compare-against-policy + Route

1. **Compare-against-policy:** read `nvidia_rpm_state.json`, `calls.jsonl` count vs
   5000 estimate, resource health. Classify: THROTTLED (backoff 2^(n-1) min,
   cap 60 — worker.js:67) · band ≥ 0.55 (lane paused by `budget_guard()`, resume
   < 0.50) · band ≥ 1.00 (lane halted, fail closed).
2. **Route:** `govern()` re-decides affected tasks to eligible lanes
   (gemini-direct 10/min measured; ai-router keyless lanes with measured fail
   rates — pollinations 6/31, kilo 46/28, ovh 4/26, llm7 0/15 and already
   429ing). Task identity and evidence chain preserved (AL-10).
3. During THROTTLED backoff, probes only on UNKNOWN/DEGRADED/QUARANTINED/stale
   resources (f2). Never override `budget_guard()` — the guard IS the enforcement.
4. Record: decision receipt with `REASON_CODES`
   (`STRATEGIC_RESOURCE_RESERVED` / `BUDGET_EXCEEDED`).

### P2 — Stuck queue → Track + Stop

1. **Track:** run the zombie sweep — stale `running` (no receipt, >10 min) →
   `deferred` + one evidence_log row per job (worker.js:2814–2822). Never reap a
   job with a live receipt.
2. **Stop:** dependency deadlock — dependents of a DISPROVEN dependency are
   auto-pruned to `failed` with prune receipts (worker.js:1117–1128 A2), not
   left dangling. defer_count ≥ 8 → `failed` (terminal).
3. If QUEUE-STUCK fired (age growing, utilization < 50%): the blockage is
   logical, not capacity — inspect the dependency graph (`devgraph.py`
   `enables` edges), not the provider lanes.
4. Record: sweep report (reaped count, evidence_log row ids).

### P3 — Deterministic gate down → fail-closed hold (Compare unavailable → Stop)

Doctrine: a model response must never self-accept (MISSION §4). When the gate
that would check it is down, there is no acceptance — only holding.

1. Confirm the outage (envelope key unreadable → `wrap`/`verify` fail closed
   per f5; ledger unwritable; bucket state unreadable). 60s grace, then declare.
2. **Stop:** allocator holds — new completions stay non-terminal
   (`executing→pending-validation`); ZERO acceptances; admissions that require a
   recorded decision convert to DENY (f1 `admit_action` fail-closed).
3. **Track:** in-flight receipts spill to a durable spill file (hashed); on
   recovery, replay in order and re-verify the chain (LG-3).
4. Recovery: drain held work FIFO through the restored gate; record the hold
   window in the batch receipt. Never invent a self-acceptance path under pressure.

### P4 — Receipt-chain fork → Compare → Stop + Track

1. **Compare:** `pl audit --full` ≠ 0 — classify: REPLAY (verbatim duplicate),
   STALE (superseded verification), tamper (hash/prev_hash break). Fail closed:
   no downstream step may cite the affected segment.
2. **Stop:** quarantine the forked segment; canon corrupt (`canon audit` ≠ OK /
   `snapshot` exit 3) degrades all dependent checks to UNKNOWN (R9 case-3 pattern).
3. **Track:** restore from verified anchors — `chain-anchors.jsonl` +
   `verify-chain-anchors.sh` (PL); CANON-FREEZE-2026-10-08.md + git commit
   `272ed80` (canon). Never repair canonical state in place.
4. Record: L1 ledger incident entries (append-only) + falsification row via
   `court.record_falsification`.

## 4. Observation loop (event-driven, never timer-polled)

Per standing doctrine (no timers; eventd watches + hook wakes): the runbook
triggers on EVENTS — dispatch-log appends, `burn.STATUS.json` counter changes,
health transitions, `pl audit` failures, gate outages. A cheap eventd watch
fires on change; the agent wake layer runs the matching P-procedure. Metrics in
§1 are computed on wake, not on schedule. Never add a polling cron for
something an eventd watch can cover.

## 5. Wiring table — metric → existing artifact

| Metric(s) | Existing artifact (exact) |
|-----------|--------------------------|
| `bc.al.rate_limited`, `bc.al.band_utilization`, queue_pending | `~/workspace/compute/burn.STATUS.json` (rate_limited=64, queue_pending=839 measured) |
| `bc.al.bucket_utilization` | `~/workspace/compute/nvidia_rpm_state.json`, `adapters/gemini_rpm.py` state |
| `bc.al.no_feasible_source`, `bc.wk.escalation_attempts` | governor decision receipts (`REASON_CODES`); `~/workspace/governor/dispatch-log.jsonl` (41 entries); `~/workspace/compute/falsification.jsonl` (147 records anchored) |
| `bc.wk.yield`, `bc.wk.latency_p50_p95`, `bc.wk.invalid_rate` | `~/workspace/compute/executions.jsonl` (n=2543/1121/108); `~/workspace/nvidia-usage/calls.jsonl` (2926 lines) |
| `bc.lg.append_rate`, `bc.lg.audit_exit`, `bc.lg.envelope_coverage` | `~/workspace/compute/envelopes.jsonl` via `ledger.verify_envelopes()`; `pl audit --full` on `~/workspace/proof-ledger/ledger.jsonl` |
| `bc.rt.*`, `bc.al.queue_*` | `~/workspace/compute/queue.jsonl`, `dispatches.jsonl` (R10 fold guards) |
| canon health (P4) | `canon audit` / `canon snapshot` (exit 0/3) |

## 6. What observability must NOT do

- Never auto-remediate quota, policy, or code on an alert (secret freeze; no
  independent rotations; indicators trigger review, not action).
- Never promote a declared number to a measured baseline (ai-router per-lane
  `rpmLimit` = DECLARED, f3 — may gate routing, never alerting).
- Never conflate adapter `rate_limited` (64 measured) with provider 429s (0 ever observed).
- Never observe a validator hierarchy — there isn't one anymore. If a metric
  can't be expressed as a count, rate, or deterministic predicate, it doesn't
  belong in this runbook.

## Provider use

No provider calls used. Re-scope written directly from the owner directive plus
the measured evidence (f2 lifecycle constants, f3/f8 quota and latency
measurements, f4 gate predicates, f5 ledger mechanics) and MASTER-DIRECTIVE.md
delta 3. All thresholds cite measured baselines or are marked UNBASELINED. No
NVIDIA NIM or Gemini calls — zero quota consumed.

## 7. Per-tier metrics and incident handling

Naming extends the §1 scheme: `bc.t3.*`, `bc.t2.*`, `bc.t1.*` — the same one
naming scheme with a tier dimension alongside the stage dimension (not a
second scheme). Every threshold is a measured baseline or UNBASELINED — no
invented numbers. Tier 1 is the TOP (owner's inverted numbering); Tier 3 is
the max-parallel single-check tier.

| Metric | Definition | Source | Baseline | Cadence |
|--------|-----------|--------|----------|---------|
| `bc.t3.throughput` | single-check completions / min | Tier 3 result receipts | UNBASELINED (shape: tracks allocator dispatch rate up to the lane ceiling) | per min |
| `bc.t3.completion_rate` | completions / Tier 3 dispatches | dispatch fold + result receipts | UNBASELINED; collapse rule follows the `bc.wk.yield` lane reliabilities (nvidia 61.9%, ai-router-free 96.3%) — no separate baseline | per batch |
| `bc.t3.scope_violations` | TR-1 rejections (extra item / undeclared field in a T3 envelope) | TR-1 artifacts | 0 in clean runs; any > 0 under adversarial input = the structural gate working | per min |
| `bc.t2.assembly_latency` | group completion ts − first member T3 result ts | group receipts | UNBASELINED; alert on 3-window growth while `bc.t3.completion_rate` holds (blockage is logical, not capacity — P2 §3 pattern) | per group |
| `bc.t2.assembly_blocks` | group completions blocked by missing/mismatched member (TR-2) | TR-2 artifacts | 0 in clean runs | per group |
| `bc.t2.partition_rejects` | items refused Tier 3 by the structural rule (TR-4) | TR-4 artifacts | UNBASELINED (shape: > 0 expected on any checklist with dependent items) | per batch |
| `bc.t1.cycle_time` | integration sign-off ts − previous sign-off ts | Tier 1 sign-off receipts | UNBASELINED | per campaign |
| `bc.t1.evidence_blocks` | sign-offs blocked by missing evidence / hash mismatch (TR-3) | TR-3 artifacts | 0 in clean runs; any > 0 under adversarial input = the completeness gate working | per campaign |

### 7.1 Per-tier alert additions (continue §2 numbering)

14. **TIER3-SCOPE-VIOLATION** · `bc.t3.scope_violations > 0` under clean input ·
    TR-1 · HIGH · the envelope assignment path is injecting items — hold
    assignment, diff the divergent envelopes (DETERMINISM-BREAK pattern,
    rule 9).
15. **TIER2-ASSEMBLY-BREAK** · a group marked complete while TR-2 logic says
    incomplete · TR-2 · CRITICAL · quarantine the group result (P4 pattern);
    no Tier 1 sign-off may cite it.
16. **TIER1-EVIDENCE-BREAK** · sign-off declared with `bc.t1.evidence_blocks`
    > 0 outstanding · TR-3 · CRITICAL · the sign-off is void; hold integration
    (P3 fail-closed pattern).
17. **TIER2-ASSEMBLY-SLOW** · `bc.t2.assembly_latency` growing 3 consecutive
    windows while `bc.t3.completion_rate` holds · shape rule · MEDIUM ·
    blockage is logical (missing dependency placement per TR-4), not provider
    capacity — inspect group member sets, not lanes.

### 7.2 Per-tier incident handling

- **T3 incident (scope creep / envelope violation):** quarantine the envelope;
  never reassign its contents wholesale — re-emit per the structural rule
  (TR-4 decides the tier per item). Record: TR-1 artifact + falsification-style
  audit row via `court.record_falsification` (the same sink as
  `bc.wk.escalation_attempts`).
- **T2 incident (assembly blocked / completed-with-missing-member):** Track —
  list the missing member task_ids from the group manifest and re-dispatch
  only those members (P2 pattern). Stop — if a group completed with a member
  missing, quarantine the group result and fail closed on any dependent Tier 1
  sign-off (P4 pattern). Record: TR-2 artifact.
- **T1 incident (incomplete evidence at sign-off):** hold the sign-off —
  integration never self-accepts on partial evidence (P3 fail-closed pattern).
  Track — name the missing Tier 2 results / hash-mismatched artifacts (INV-10
  pattern); the missing inputs re-enter the queue, never the sign-off. Record:
  TR-3 artifact + the blocking set.

## Provider use (per-tier metrics section)

No provider calls used. Metrics are derived from the TR suite in
`08-verification-plan.md` §7 and the existing §1–§6 machinery; every threshold
is measured or marked UNBASELINED. Direct route (same reasoning as 08 §7) —
zero quota consumed.
