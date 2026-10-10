# SPEC §12.10 — Failure/Recovery Matrix
*Mission 2 (§6) · SPEC deliverable #10 of §12.12*
*Authoring: spec agent (subagent 4afd911e) · 2026-10-09*
*Status: SPECIFICATION ONLY — no code changes. Reuses the Exchange's EXACT measured vocabulary; nothing invented.*

## 0. Fixed vocabularies (measured, not designed)

**Failure taxonomy** — `exchange/worker.js:24,745` (mapped from adapter error classes
`RATE_LIMITED | TIMEOUT | SERVER_ERROR | BAD_RESPONSE | NETWORK | POLICY_BLOCKED | UNKNOWN`):
`RETRYABLE_FAILURE | PERMANENT_FAILURE | POLICY_FAILURE | AUTH_FAILURE | QUOTA_FAILURE | CAPABILITY_FAILURE | PROVIDER_FAILURE | VERIFICATION_FAILURE`

**Worker outcomes** — `exchange/worker.js:153–158` (`WORKER_OUTCOMES`; anything else → 400):
`SUCCEEDED | FAILED_RETRYABLE | FAILED_PERMANENT | QUARANTINED | EXPIRED`

**Provider health** — `exchange/worker.js:67`:
`AVAILABLE | DEGRADED | THROTTLED | EXHAUSTED | QUARANTINED | UNKNOWN`

**Terminal task states** (this spec; Mission §6): `accepted | rejected | blocked | cancelled | explicitly-unresolved`.
Non-terminal: `ready | dispatched | executing | deferred`.

**Lease/zombie semantics** (measured): lease = 60 s (`createLease`, worker.js:767–775);
zombie sweep: stale `running` (no receipt, >10 min) → `deferred` + evidence_log (worker.js:2814–2822);
expired claims → EXPIRED, execution marked UNCERTAIN — provider may have executed, never claimed free (worker.js:1206–1250, BUILD-RECORD v0.6 §8);
DISPROVEN_DEPENDENCY auto-prune: dependent deferred jobs → `failed` with prune receipt (worker.js:1117–1128, WORKER-PROTOCOL-v1.md A2);
`running → deferred` when retryable AND defer_count < 8; `running → failed` when permanent or defer_count ≥ 8 (worker.js:1035, 1105–1128, 1188–1197, 1243–1250, 2859).

**Column key** (same for every row): Detection · Retryable? · Same budget? · Backoff/cooldown · Max attempts · Alternate provider eligible? · Repair model allowed? · Revalidation required? · Terminal state · Evidence retained.

## Per-tier failure routing (tier-scoped; terminal states unchanged)

Failures route by tier scope, never to a judge. **No failure class in §§1–8 routes to an LLM judge**: detection = Compare (shape-based, never prose), accounting = Calculate, routing = Route/Track/Stop. "Repair" everywhere in this file means bounded Worker regeneration strictly within assignment + deterministic re-check — a Worker, never a judge, never a debate.

- **T3 item failure → fixed retry → dead-letter.** The failed T3 unit retries under the fixed rules (tail, ≤8 dispatched attempts, same bounded envelope, same single checklist item). Attempts exhausted → dead-letter (`rejected`), artifact archived. The T2 group does NOT wait: it assembles with the dead-letter recorded as evidence (07 §2 ready_scan). One T3 death never kills its group, and T3 retries never widen scope.
- **T2 group inconsistency beyond bound → escalate to T1 as cross-group concern.** T2 spends its bounded resolution budget (structural compare + deterministic pick rule + ≤2 bounded regeneration rounds). Beyond the bound → Stop resolving; Route the conflict receipt to T1. T2 never loops on what it cannot structurally resolve and never judges which side is "right".
- **T1 integration failure → work-order problem → human.** T1 gets one bounded regeneration attempt per cross-group conflict receipt. Persistent failure means the work order itself is defective (bad partition, contradictory specs, impossible constraints) → run `blocked` pending human work-order revision. The revision is a NEW work order lineage (new order_id via 07 §1.6); the blocked run stays blocked as evidence (CANON C12: superseded records never silently resurrect). This is the only path that leaves the pipeline, and it leaves to the human — not to a smarter model, not to a judge layer.

Tier escalation preserves termination: T2→T1 is a Route into a bounded T1 attempt (finite, §7.9 of 07); T1→human is terminal `blocked` (finite). No tier can spin another tier, and no tier re-opens a terminal state.

---

## 1. RETRYABLE_FAILURE — transient, no fault signal

- **Detection:** provider HTTP 429/503-overloaded/timeout, or empty-200 (exchange W8: empty 200 → FAILED_RETRYABLE); shape-based, never prose-based (07 §4).
- **Retryable?** YES → worker outcome FAILED_RETRYABLE.
- **Same budget?** YES — same band, same category; the attempt consumed ~1 call of estimate, no re-mint needed.
- **Backoff/cooldown:** provider → THROTTLED with 2^(n-1) min backoff, cap 60 (worker.js). Task re-queued at TAIL.
- **Max attempts:** 8 total (mirrors defer_count < 8 → deferred; ≥ 8 → failed).
- **Alternate provider eligible?** YES — failover via govern() re-run with provider excluded (07 §7).
- **Repair model allowed?** NO — nothing to repair; the artifact never arrived.
- **Revalidation required?** N/A (no artifact). Next success validates normally (07 §5).
- **Terminal state:** `rejected` (as `failed`) only after 8 attempts → dead-letter.
- **Evidence retained:** attempt record {attempt_id, outcome, http class, latency, measured tokens}; provider health before/after.

## 2. PERMANENT_FAILURE — our request was malformed; retrying identically is futile

- **Detection:** HTTP 400 caused by OUR envelope (schema violation, oversize, bad base_revision); deterministic pre-flight check fails twice.
- **Retryable?** NO as-is → worker outcome FAILED_PERMANENT. Retry allowed ONLY with a corrected envelope, which counts as a NEW attempt with new idempotency key (never replay the bad bytes — W2 idempotency is per attempt_id).
- **Same budget?** YES for the corrected attempt (still normal_operations unless category says otherwise).
- **Backoff/cooldown:** none (no provider fault); task to tail after correction.
- **Max attempts:** 8 counting corrected attempts; 3 consecutive same-shape 400s → task `blocked` pending operator (evidence: malformed-envelope loop is a generator bug, not luck).
- **Alternate provider eligible?** NO — the fault is ours; failing over exports our bug.
- **Repair model allowed?** NO — repair targets artifacts, not envelopes. The deterministic envelope builder is fixed by engineering, not by model proposal.
- **Revalidation required?** YES — corrected attempt is a fresh attempt; full §5 on any artifact.
- **Terminal state:** `rejected` (dead-letter) or `blocked` (generator-bug loop).
- **Evidence retained:** the malformed envelope bytes (archived), the 400 response, the correction diff.

## 3. POLICY_FAILURE — a gate said no; the work is not authorized

- **Detection:** 10-gate denial at IDENTITY/AUTHORITY/DATA (worker.js:1457–1492; T2 test: sensitive inference BLOCKED at DATA gate); or brief-lint failure; or destructive-git-op attempt in a lane (07 §8 absolute rule).
- **Retryable?** NO → maps to `blocked` (exchange: policy/capability → blocked, worker.js:1949, 2105).
- **Same budget?** N/A — no spend authorized; reservations are REFUSED at the QUOTA/COST gates before spend.
- **Backoff/cooldown:** none. Unblock requires a NEW authorization (governor decision, user evidence, policy change) — never the passage of time.
- **Max attempts:** 0 retries. Re-proposal with new authorization = new task lineage (new idempotency key; the blocked task stays `blocked` as evidence).
- **Alternate provider eligible?** NO — policy binds the task, not the provider. Failing over to evade a policy denial is itself a POLICY_FAILURE (proposer-eliminator pattern, governor RT-B5).
- **Repair model allowed?** NO.
- **Revalidation required?** N/A.
- **Terminal state:** `blocked` (permanent unless re-authorized out-of-band; re-authorization creates a new task, it does not resurrect the blocked one — CANON C12: superseded records never silently resurrect).
- **Evidence retained:** gate trace with the denying gate named, policy version (sha256), unreached gates labeled "vacuous".

## 4. AUTH_FAILURE — credential invalid; the provider does not know us

- **Detection:** HTTP 401/403 on provider call; credential probe fails.
- **Retryable?** NO → worker outcome FAILED_PERMANENT for the attempt; provider → PARKED-equivalent (QUARANTINED with reason=auth): credential parked until EXPLICIT re-verify, never auto-promoted (evidence-ladder PARKED rule, worker.js:404, 603).
- **Same budget?** N/A — no spend occurred (auth fails before metering).
- **Backoff/cooldown:** indefinite park; re-verify is an operator action, not a timer.
- **Max attempts:** 1 — a second attempt with the same credential is forbidden (it burns nothing but proves nothing; repeated 401s look like credential-stuffing from the provider's side).
- **Alternate provider eligible?** YES — other providers' credentials are independent; govern() re-run excludes the parked provider.
- **Repair model allowed?** NO.
- **Revalidation required?** N/A.
- **Terminal state:** `blocked` on the parked provider's tasks until re-verify; tasks may proceed via failover → `accepted`/`rejected` on their own merits.
- **Evidence retained:** 401/403 class (never the credential), park receipt, re-verify checklist pointer.

## 5. QUOTA_FAILURE — we hit a measured ceiling

- **Detection:** adapter-bucket denial (`nvidia_rpm.acquire` → False; burn observed `rate_limited=64` with ZERO provider 429s — bucket gating, not provider wrath); provider 429 with quota semantics; budget.check → (False, BUDGET_EXCEEDED).
- **Retryable?** YES → worker outcome FAILED_RETRYABLE, task `deferred`.
- **Same budget?** CONDITIONAL: retry allowed in the same band only if headroom remains (`used < CEILINGS[category] * estimate`). Crossing into a reserve band needs `reserve_authorized_by="governor"` (budget._category RT-B6). Otherwise the task waits for utilization to drop (burn hysteresis 0.55/0.50).
- **Backoff/cooldown:** bucket refill (39/min NVIDIA, 10/min Gemini — measured ceilings); budget-hysteresis pause/resume; provider 429 → THROTTLED 2^(n-1) min cap 60 → EXHAUSTED suspend-until-recheck 5 min (worker.js).
- **Max attempts:** 8; quota-deferred tasks do NOT burn attempts while the lane is paused (paused ≠ failed — attempts count only dispatched attempts).
- **Alternate provider eligible?** YES — the canonical failover case (quota is per-provider).
- **Repair model allowed?** NO.
- **Revalidation required?** N/A (no artifact yet).
- **Terminal state:** `rejected` only if quota never recovers within 8 dispatched attempts; otherwise waits as `deferred`. Never `blocked` — quota is temporal, not policy.
- **Evidence retained:** bucket state before/after, budget utilization at denial, band, headroom.

## 6. CAPABILITY_FAILURE — the provider cannot do what the task needs

- **Detection:** model returns capability refusal / context overflow at measured `observed_hosted_max` (e.g. ultra-550b 503 at 524,288 > measured 393,216 max); govern() infeasibility with INSUFFICIENT_CAPABILITY reason code.
- **Retryable?** NO on the same provider/model → maps to `blocked` for that provider (exchange: policy/capability → blocked).
- **Same budget?** The failed attempt consumed ~1 call; no further spend on the incapable provider for this task shape.
- **Backoff/cooldown:** none — capability does not recover with time. Re-probe only after a measured capability change (capability.json update → decision hash changes, governor test O).
- **Max attempts:** 1 per (task, provider) pair. Task may try other providers.
- **Alternate provider eligible?** YES — the primary remedy. govern() re-run with capability filter.
- **Repair model allowed?** NO — you cannot prompt a model into a capability it measuredly lacks; task must be re-scoped (new manifest, new idempotency key) or moved.
- **Revalidation required?** N/A.
- **Terminal state:** `blocked` if NO provider has the measured capability (governor: NO_FEASIBLE_SOURCE, test H); `accepted`/`rejected` via capable provider otherwise.
- **Evidence retained:** capability probe record, measured max that was exceeded, reason code INSUFFICIENT_CAPABILITY.

## 7. PROVIDER_FAILURE — the provider is down or misbehaving

- **Detection:** 5xx (non-overload), network errors, adapter exceptions, timeouts beyond SLA, model-lie (exchange W9: receipt discrepancy — output contradicts its own claims).
- **Retryable?** CONDITIONAL → worker outcome FAILED_RETRYABLE for 5xx/timeout/network; QUARANTINED for model-lie/misuse signals (worker signals; governor quarantines on DEGRADED/THROTTLED — worker.js:997–1000).
- **Same budget?** YES for 5xx/timeout (no useful work, same band). QUARANTINED provider: no further spend on that provider until explicit un-quarantine.
- **Backoff/cooldown:** 5xx → THROTTLED backoff; repeated → EXHAUSTED (5-min recheck); model-lie → QUARANTINED indefinitely (operator review).
- **Max attempts:** 8 for 5xx/timeout; 1 for quarantine-class (second attempt on a quarantined provider is forbidden).
- **Alternate provider eligible?** YES — immediate failover is the expected path.
- **Repair model allowed?** NO for 5xx (nothing to repair); NO for model-lie (the output is untrusted — discard, do not repair; repair would launder the lie).
- **Revalidation required?** Any artifact from a provider that later quarantines is RE-VALIDATED from scratch; prior ACCEPTED verdicts from that provider in the same run are re-derived (07 §8 final acceptance).
- **Terminal state:** `rejected` after 8 attempts across providers, or `blocked` if all providers QUARANTINED/EXHAUSTED with no recovery.
- **Evidence retained:** full error class, provider health transition, quarantine receipt with reason, discrepancy record for model-lie (W9 pattern).

## 8. VERIFICATION_FAILURE — the artifact failed its acceptance checks

- **Detection:** §5 class checks fail; secret-scan hit; `court.derive_status` → NOT_ESTABLISHED/DISPROVEN/UNKNOWN-with-unbound-gates; sanitize strips authority-smuggling fields (indy-reads pattern).
- **Retryable?** YES → worker outcome FAILED_RETRYABLE (the provider call succeeded; the ARTIFACT failed — Mission §7: successful response ≠ successful artifact).
- **Same budget?** YES — same band; verification is part of the task's cost. Repair rounds (max 2/attempt) draw from the same budget.
- **Backoff/cooldown:** none provider-side; task to TAIL.
- **Max attempts:** 8 attempts; within an attempt, max 2 bounded repair rounds (07 §7.7). Repair input = {artifact, failing checks, check outputs} — never the full transcript.
- **Alternate provider eligible?** YES — a different model may produce a valid artifact where the first failed.
- **Repair model allowed?** YES — the ONLY class where repair is allowed, and only as bounded Worker regeneration (a Worker within assignment, never a judge): 2 rounds, bounded inputs. Repair output re-enters §5 from step 1; a repair never inherits a prior ACCEPTED.
- **Revalidation required?** ALWAYS — every new artifact (retry or repair) gets the full §5 pipeline; `derive_status` re-run with fresh canon snapshot at final acceptance (07 §8).
- **Terminal state:** `rejected` (dead-letter) after attempts exhausted; falsification entry filed if the failure reveals a generator defect pattern.
- **Evidence retained:** artifact bytes (archived), failing check outputs, bound-evidence receipts, repair diffs, final verdict.

---

## Lease, zombie, and idempotency semantics (apply to all classes)

1. **Reservation lease (60 s):** a reservation not consumed by dispatch within 60 s EXPIRES; tokens refunded under fcntl; task returns to ready tail. Receipt RESERVE_EXPIRED.
2. **Execution lease:** provider call in flight past its deadline → outcome EXPIRED; execution marked UNCERTAIN (provider may have executed — never claimed free). Task → retry path; the retry carries the UNCERTAIN flag so §5 treats any duplicate-side-effect evidence with suspicion.
3. **Zombie sweep:** `executing`/`dispatched` with no heartbeat and age > 10 min → `deferred` + evidence_log (worker.js:2814–2822). Sweep is deterministic and runs on every recover() and on a cheap interval watch — NOT a timer-driven scheduler (eventd doctrine: interval watches detect change; agents act on events).
4. **Idempotency:** attempt_id unique per try; task identity stable across attempts (Mission §4). Duplicate delivery of a completion → idempotent ACK, no double-apply (exchange W2: ×10 replays → 1 accepted). `queue.mark` asserts status ∈ QUEUE_STATUSES; `_fold_state` guards `executing`-only-from-`dispatched`.
5. **DISPROVEN dependency prune:** a dependency verdict DISPROVEN auto-prunes dependent deferred tasks → `failed` with prune receipt (worker.js:1117–1128 A2). Dependents never spin on a dead branch.
6. **Partial artifacts:** retained under attempt_id in staging, never promoted; archived on dead-letter (archive-don't-delete). A partial artifact is evidence, not output.

## Kill-switch semantics

`cancel(run_id | task_id, reason)` — deterministic, immediate, receipted:

| In-flight element | Kill-switch behavior |
|---|---|
| Running provider requests | Cancellation signaled; provider-side completion after cancel → outcome EXPIRED, execution UNCERTAIN, result archived not applied. No new dispatches after the switch. |
| Reserved quota (unconsumed) | Reservations EXPIRED immediately; tokens refunded under fcntl; receipted. |
| Reserved quota (consumed by in-flight) | Counted as spent (measured usage stands); no refund fiction. |
| Partial artifacts | Frozen in staging under attempt_id; retained as evidence; never validated, never promoted. |
| Completed side effects | NEVER rolled back (no destructive ops exist to roll back with — 07 §8). Recorded in the kill receipt: {side_effect, commit_hash?, reversible?}. Merge-controller commits already on the integration branch stand; the run's final acceptance will mark the run `cancelled`, not `accepted`. |
| Queued/deferred tasks | → `cancelled` with CANCELLED receipt; dependency-blocked tasks → `cancelled` (not `blocked` — the run ended). |
| Provider health / budget | Untouched — kill-switch is per-run; provider quarantine or budget state belongs to the fleet, not the run. |
| Receipt chain | KILL receipt appended (envelope.wrap, chained); chain remains verifiable. |

Fail-closed: if the kill signal itself cannot be recorded (receipt store unwritable), the switch STILL stops new dispatches (in-memory gate) and reports KILL_UNRECEIPTED — stopping work never depends on the ability to log it, but the gap is itself receipted at the next writable moment.

## Termination proof sketch

**Claim:** every task reaches `accepted | rejected | blocked | cancelled | explicitly-unresolved`, and the queue keeps processing independent work on failure.

**Assumptions (stated):**
- (F1 Fairness) The scheduler considers every ready task infinitely often (no starvation of the ready set; tail-retry preserves this).
- (F2 Attempt bound) Every dispatch consumes one of ≤ 8 attempts; attempts are durable in the append-only log.
- (F3 Availability) At least one provider with a measured-feasible capability is not permanently QUARANTINED/EXHAUSTED for the run's duration — OR the task is capability/policy-blocked, which is itself terminal (`blocked`).
- (F4 Lease expiry) All reservations and executions carry finite leases; the zombie sweep runs.
- (F5 Deterministic classification) Every provider response maps to exactly one worker outcome (07 §4 shape rules); unclassifiable responses → FAILED_RETRYABLE with receipt (fail-open toward retry, never toward accept).

**Argument:**
1. A task not yet dispatched is `ready`, `blocked` (dependency/policy/capability), or `deferred`. Blocked-on-dependency resolves when the dependency goes terminal: accepted → dependent becomes ready; DISPROVEN → dependent pruned to `failed` (= `rejected`); cancelled → dependent `cancelled`. Dependency DAG is acyclic by construction (07 §2 cycle check), so resolution propagates in finite steps — no infinite blocked chains.
2. A dispatched task consumes an attempt (F2) and, by F4, cannot remain `dispatched`/`executing` forever: lease expiry or zombie sweep forces a worker outcome. By F5 the outcome is classified.
3. SUCCEEDED → §5 validation → `accepted` or VERIFICATION_FAILURE retry. Each retry path either decrements remaining attempts or hits a terminal class: POLICY/AUTH/CAPABILITY (same-provider) → `blocked`; attempts exhausted → `rejected` (dead-letter); kill-switch → `cancelled`; unrecoverable infra (log missing, canon unverifiable at final) → `explicitly-unresolved` with receipt.
4. Retries go to TAIL (never head), so a failing task cannot starve independent tasks (F1): the queue keeps processing independent work while any task cycles through backoff.
5. Attempts are bounded (F2: 8) and each attempt terminates (steps 2–3), so every task's retry loop terminates. Dependency-blocked tasks stay blocked without consuming attempts or quota.
6. Therefore every task reaches a terminal state in finite steps under F1–F5. ∎

**What the proof does NOT cover (honest gaps):** F3 is an operational assumption — a total provider outage with no recovery turns tasks `deferred`-forever, which the spec surfaces as `explicitly-unresolved` at run teardown rather than pretending otherwise. F5's fail-open-to-retry means a pathologically unclassifiable provider burns all 8 attempts before dead-letter; that is the priced cost of never mis-accepting.

## Queue-liveness on failure (operational rule)

- Failure of one task NEVER blocks the ready set: classification, retry scheduling, and failover are per-task; the scheduler loop continues over remaining ready tasks.
- Provider quarantine/exhaustion removes that provider from `govern()` eligibility; tasks fail over or defer — the loop does not spin on the dead provider (07 §7 FAIL path: FAILOVER_DEFERRED, no busy-spin).
- Budget-hysteresis pause (0.55/0.50) parks the NVIDIA lane only; other lanes continue. Tasks stay `ready`; no attempts consumed while parked.
- Dead-letter is per-task and archived; the run continues until all tasks are terminal or the kill-switch fires.

---

## Provider use

No NVIDIA NIM generation and no Gemini critique were used in authoring this file. The matrix was written directly from the evidence bundle (f2 lifecycle/taxonomy/health/outcomes, f1 governor reason codes, f4 court/envelope acceptance, f8 measured quotas and burn-guard behavior) with symbol spot-checks against `compute/` sources. Provider use: **none — direct authoring** (per PROVIDER ROUTING fallback: report which provider did what).
