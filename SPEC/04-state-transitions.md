# SPEC §12-4 — State Transitions (re-scoped: minimal DAG + tier model)

**Mission 2 §2 execution DAG + §12-4, per OWNER DIRECTIVE — ARCHITECTURE SIMPLIFICATION
+ TIER MODEL UPDATE (Tier 1 is the TOP; tiers defined by context/responsibility scope,
NOT model capability; N=3, fixed).**
The DAG is: **work-order → Partition → Group → Assign → Schedule → execute (T3 → T2 → T1)
→ Record → Repeat.**
Validator-hierarchy stages are DROPPED from the DAG — the former "validation tiers"
are deterministic check ops (Compare/Calculate) consumed as predicates, not stages.
Per-tier completion conditions are the transition guards between execution tiers.

State vocabularies below reuse the Exchange's EXACT measured vocabularies (f2).
No second status vocabulary is invented. All transition rules are measured from source;
anything unmeasured is labeled UNKNOWN.

---

## 1. The DAG (dependency graph with overlap points)

```
work-order ──► Partition ──► Group ──► Assign ──► Schedule ──► execute ──► Record ──► Repeat
   (B1)          (Calc)       (Calc)     (Route)     (Route/       (T3 → T2 → T1,    (Track)    (Track/
                  │            │                     Calc)         §1A)                        Stop)
                  │            │
                  │            └─► Tier 2 bundles (related items grouped;
                  │                 singletons stay ungrouped per the
                  │                 partitioning rule — §1A)
                  │
                  └─► typed units (dev-graph nodes, SCHEMA.md vocabulary)

Overlap points:
- Partition → Group → Assign are pure Calculate/Route over the work graph:
  they complete before any execution but re-run incrementally if the work order
  changes (immutable once authored — re-partition only on a new work order).
- Schedule is continuous: cmd_ready recomputed on every Record; T3 units dispatch
  while earlier T3 units still run; T2 groups start the moment their item set's
  T3 results are all Recorded; T1 starts when all T2 groups are Recorded.
- Record is streaming: every execution writes its ExecutionResult + envelope to the
  Ledger immediately; check ops consume receipts as they land (not at tier end).
- Repeat re-enters at Schedule (the Allocator tail); dependency-blocked stays blocked.

Dependency rules:
- A unit is dispatchable iff `cmd_ready` includes it (open ∧ all `enables`-predecessors
  in state `done`). Predecessor `done` = its check ops all PASS and its receipts are in
  the Ledger.
- The Schedule op never dispatches a unit whose predecessors are not all `done`.
- A check-op FAIL on unit U blocks U's successors (they stay out of `cmd_ready`) but
  never blocks unrelated units — the queue keeps processing independent work.
- Retries re-enter at the Schedule tail; dependency-blocked stays blocked
  (no spurious unblocking on retry of a sibling).

## 1A. Execution tiers (T3 → T2 → T1) and per-tier completion conditions

Tiers are defined by context/responsibility scope, NOT model capability. N=3, fixed.
Tier 1 is the TOP. All tiers follow the same basic development rules with progressively
broader context and responsibility. No fourth tier. Prompts are developer-defined and
developer-supplied — the scheduler distributes them, never authors or judges them.

### Tier 3 — single-check workers (maximize independent parallel work)

- **Context:** basic dev rules + ONE explicit checklist item + the specific inputs/context
  for that check. Minimal context overhead.
- **Output:** the check's defined output.
- **Completion condition (transition guard T3 → Record):** the single check's defined
  output exists AND its completion condition holds (per its prompt). A T3 unit whose
  output fails its completion condition goes to Repeat (bounded) or dead-letter.
- **Partitioning rule (structural, not judgment):** a checklist item may go to Tier 3
  ONLY if it is performable with its supplied context alone — no `enables`-predecessor
  outside its own context, no dependency on another check's output. Encoded as a rule on
  the work graph (checkable via `devgraph.py`: the item's `enables`-predecessors must all
  be satisfied by the supplied context, not by sibling checks).

### Tier 2 — check-group workers (combine related results)

- **Context:** basic dev rules + a GROUP of related checklist items + the relevant Tier 3
  results and shared context.
- **Output:** defined group-level output.
- **Responsibilities:** combines related results, handles local dependencies, resolves
  bounded inconsistencies WITHIN the group.
- **Completion condition (transition guard T2 → Record):** group-level output exists;
  every item in the group resolved or explicitly carried as an open item; no cross-group
  concern raised without being recorded. Cross-group concerns are recorded as open items
  for Tier 1 — Tier 2 does not resolve them.

### Tier 1 — full-context developer (owns overall coherence)

- **Context:** complete dev rules + entire checklist + work-order objective + relevant
  specs/architecture/constraints + Tier 2 results and their evidence.
- **Output:** final integration output with all evidence bound.
- **Responsibilities:** owns overall coherence and final integration; addresses
  cross-group concerns.
- **Completion condition (transition guard T1 → Record/accept):** whole checklist
  accounted for; cross-group concerns resolved; final integration output exists with all
  evidence bound; all check ops PASS. Only then does the run's work reach `done`.

### Tier flow guards (summary)

| Transition | Guard (completion condition) |
|---|---|
| T3 unit → Record | single check's defined output exists + its completion condition holds |
| T2 group → Record | group-level output exists; items resolved or carried open; cross-group concerns recorded (not silently dropped) |
| T1 → run `done` | whole checklist accounted; cross-group concerns resolved; final output + all evidence bound; check ops all PASS |
| any tier → Repeat | bounded retries per the retry matrix (§3); re-enter at Schedule tail |
| any tier → dead-letter | terminal failure class (§3); Ledger records; loop continues |

---

## 2. State vocabularies (exact, measured — never reinvented)

### 2.1 Run-level job states (Exchange D1 vocabulary, f2 Lifecycle B)

Source: `~/workspace/exchange/worker.js` (lines 805, 1035–1036, 1105–1128, 1188–1197,
1243–1250, 1961, 2093–2094, 2105, 2814–2864). Terminals: `done | failed | blocked | deferred`.
Non-terminal: `running`.

| Transition | Condition (measured) | Source |
|---|---|---|
| `running → done` | all check ops PASS; receipts ledgered | worker.js:2093–2094 |
| `running → deferred` | failure retryable AND `defer_count < 8` | worker.js:1035, 1188, 1243, 2859 |
| `running → failed` | permanent failure, OR `defer_count ≥ 8` | worker.js:1105–1128, 1190, 1244 |
| any-retryable rejection → `deferred` | adapter error maps to RETRYABLE_FAILURE | worker.js:1949, 2105 |
| all-permanent → `failed` | adapter error maps to PERMANENT_FAILURE | worker.js:1949, 2105 |
| policy/capability rejection → `blocked` | POLICY_FAILURE / CAPABILITY_FAILURE | worker.js:1949, 2105 |
| stale `running` (no receipt, >10 min) → `deferred` | zombie sweep + `evidence_log` | worker.js:2814–2822 |
| dependent deferred jobs → `failed` | DISPROVEN_DEPENDENCY auto-prune + prune receipt | worker.js:1117–1128, WORKER-PROTOCOL-v1.md A2 |

### 2.2 Local task states (compute vocabulary, f2 Lifecycle I)

Source: `~/workspace/compute/queue.py:35–36` `QUEUE_STATUSES` =
`("queued", "dispatched", "executing", "completed", "failed", "expired", "blocked")`.
`mark()` asserts membership (queue.py:115). Dispatch fold (f2 Lifecycle J):
`dispatched → executing → completed | failed | expired`, with the measured guard
**`executing` reachable only from `dispatched`** (`dispatch.py:137–139` fold guard;
`mark_executing()` at `dispatch.py:187–194` raises `RuntimeError` otherwise); `stale_flagged` flag;
`blocked` retained for back-compat.

| Transition | Condition | Guard |
|---|---|---|
| `queued → dispatched` | Allocator `drain()` + `create_dispatch()` | — |
| `dispatched → executing` | worker start | fold guard: only from `dispatched` |
| `executing → completed` | check ops PASS | — |
| `executing → failed` | check ops terminal FAIL / attempts exhausted | — |
| `executing → expired` | reservation/lease expiry (EXPIRED claim outcome) | never claimed free (f2 Lifecycle C) |
| any → `blocked` | back-compat rows only; new rows use run-level `blocked` | — |

Two objects, two vocabularies, explicit mapping (01 §B6): the local task state is the
scheduler's native machine; the run-level job state (§2.1) is the public lifecycle.
A local `completed` maps to run-level `done` only after the Ledger holds all receipts.

### 2.3 Worker claim outcomes (f2 Lifecycle C)

Source: `~/workspace/exchange/worker.js:153–158` `WORKER_OUTCOMES`:
`SUCCEEDED | FAILED_RETRYABLE | FAILED_PERMANENT | QUARANTINED | EXPIRED`.
Anything else → 400 (worker.js:897–898). Claims table: `status TEXT DEFAULT 'active'`,
`lease_expiry TEXT NOT NULL` (worker.js:461–468).

| Outcome | Meaning | Retry rule entry |
|---|---|---|
| `SUCCEEDED` | execution completed, receipt sealed | → check ops |
| `FAILED_RETRYABLE` | transient (rate limit, timeout, 5xx, network) | → requeue at tail, bounded |
| `FAILED_PERMANENT` | bad response, policy block, capability mismatch | → dead-letter |
| `QUARANTINED` | worker signal / integrity suspicion | → Ledger + human review, never auto-retry |
| `EXPIRED` | lease expired; execution marked UNCERTAIN — the provider may have executed, never claim free | → replan as new attempt with idempotency key (W2: replay ×10 → 1 accepted) |

### 2.4 Evidence ladder — resource trust (f2 Lifecycle D)

Source: `~/workspace/exchange/worker.js:39–40, 396–404` `EVIDENCE_LADDER`:
`DISCOVERED → ACCESSIBLE → FREE → QUOTA → AVAILABLE → VERIFIED`.
`UNKNOWN` = move on; `PARKED` = shelved (credential AUTH_ERROR → PARKED; never auto-promotes,
worker.js:404, 603). Promotion only from recorded evidence (`warrantedTier`, 568–603).

Scheduler rule: a provider lane below `AVAILABLE` is not eligible for allocation
(governor `UNAVAILABLE` reason code). The ladder describes *resource* trust; artifact
acceptance uses court verdicts (§2.5) — never conflated.

### 2.5 Artifact acceptance verdicts (f2 Lifecycle H)

Source: `~/workspace/compute/court.py:33` `VERDICTS`:
`ESTABLISHED | NOT_ESTABLISHED | DISPROVEN | UNKNOWN`.
`derive_status()` (court.py:94): bound evidence → ESTABLISHED; forged bare-True →
UNKNOWN with gates in `unbound`; tampered canon → fail closed UNKNOWN.

These verdicts are the check-op outputs consumed at the `Record → Repeat` edge of the DAG.
They are predicates, not stages: no tier waits for a "verification phase."

### 2.6 Resource health states (f2 Lifecycle E)

Source: `~/workspace/exchange/worker.js:67`:
`AVAILABLE | DEGRADED | THROTTLED | EXHAUSTED | QUARANTINED | UNKNOWN`.
THROTTLED = exponential backoff 2^(n-1) min, cap 60. EXHAUSTED = suspend until recheck
(5 min). Governor quarantines on DEGRADED/THROTTLED (worker.js:997–1000).

Scheduler port (01 §B5): the quota coordinator keeps this table locally, driven by
measured adapter signals (429/timeout → THROTTLED; sustained failures → QUARANTINED).
Backoff constants reused verbatim.

### 2.7 Failure taxonomy — 8 classes (f2)

Source: `~/workspace/exchange/worker.js:24, 745`:
`RETRYABLE_FAILURE | PERMANENT_FAILURE | POLICY_FAILURE | AUTH_FAILURE |
QUOTA_FAILURE | CAPABILITY_FAILURE | PROVIDER_FAILURE | VERIFICATION_FAILURE`.
Never collapsed into "failed". Mapped from adapter error classes
(RATE_LIMITED | TIMEOUT | SERVER_ERROR | BAD_RESPONSE | NETWORK | POLICY_BLOCKED | UNKNOWN).

---

## 3. Retry matrix (fixed rules — the `Record → Repeat` edge)

Per failure class: detection, retryable?, max attempts, backoff/cooldown, alternate
provider eligible?, terminal state, evidence retained. These are policy data consumed by
Compare-against-policy — not discretion.

| Class | Retryable | Max attempts | Backoff | Alt provider? | Terminal state | Evidence retained |
|---|---|---|---|---|---|---|
| `RETRYABLE_FAILURE` | yes | defer_count < 8 (measured, §2.1) | THROTTLED 2^(n-1) min cap 60 | yes | `failed` at cap | all attempt receipts |
| `QUOTA_FAILURE` | yes | defer_count < 8 | bucket `retry_after_s` (measured signal) | yes — different pool | `deferred` until recheck | quota before/after |
| `PROVIDER_FAILURE` | yes | defer_count < 8 | EXHAUSTED 5-min recheck | yes | `failed` at cap | provider error class |
| `VERIFICATION_FAILURE` | yes | bounded (policy; default 3 — unquantified, labeled) | none (deterministic re-run) | no — same check op | `failed` (NOT_ESTABLISHED) | check receipts |
| `PERMANENT_FAILURE` | no | 0 | — | no | `failed` | attempt receipt |
| `POLICY_FAILURE` | no | 0 | — | no | `blocked` | deny receipt + policy snapshot |
| `AUTH_FAILURE` | no | 0 | — | no | `blocked` | auth rejection receipt |
| `CAPABILITY_FAILURE` | no | 0 | — | yes — capable source only | `blocked` | capability evidence |

Special cases:
- `QUARANTINED` claim outcome → never auto-retried; Ledger records; human review.
- `EXPIRED` claim outcome → execution UNCERTAIN; replan as a NEW attempt with the same
  idempotency key (replay protection W2).
- DISPROVEN_DEPENDENCY → dependent deferred units → `failed` with prune receipt
  (worker.js:1117–1128); no retry.
- Kill-switch (Stop): running requests → `kill()`; reserved quota released; partial
  artifacts stay receipted; completed side effects recorded, not rolled back.

Termination argument: every unit's defer_count is bounded (< 8, measured); every
non-retryable class is terminal on first occurrence; `QUARANTINED` exits the loop to
human review. Under the stated fairness (Allocator processes the ready set round-robin;
no unit starves while dispatchable) and availability (at least one AVAILABLE lane or
the run halts with `blocked`), every unit reaches `done | failed | blocked | deferred |
dead-letter` — the loop cannot spin forever because no transition increases a
unit's remaining attempt budget.

---

## 4. Envelope statuses on the DAG (f2 Lifecycle G, f5)

`~/workspace/compute/envelope.py:34` `STATUSES = ("claimed", "established", "authorized")`.
- `claimed` = chain opened, terminal observation absent — emitted at **Schedule**
  (dispatch) and at **Repeat** requeue.
- `established` = terminal observation present ∧ chain verifies — emitted at **Record**
  when check ops PASS (the guest's exit code is orthogonal — a failed guest is still an
  established observation, RCPT-009).
- `authorized` = endorsement axis — **no call site in `~/workspace/compute`; out of scope**
  for the scheduler (Blocked, 01 §B8). The DAG terminates at `established`.

---

## 5. What is NOT in this DAG

- No validator-hierarchy stages (cut per owner directive). `independent_verifier.run()` and
  `pl_canon_verifier.run()` are check ops consumed at the `Record → Repeat` edge.
- No "final glue" layer and no merge-authority tier: glue work is a Tier 2 group (or a
  Tier 1 cross-group concern); merge is a Compare-against-policy check op.
- No Cap'n Maps role (NOT PRESENT in evidence — f6 §8; BLOCKED/UNKNOWN; 01 §C3).
- No LLM judge, no debate layer, no objective reinterpretation. No fourth tier.
- No invented states: every status above is quoted from its measured source file and line.

## Provider use

None — state tables transcribed directly from the measured Exchange vocabularies
(f2) and the owner directive; no NVIDIA NIM or Gemini calls used for this file.

## Acceptance checklist (spot checks performed)

- `exchange/worker.js:158` `WORKER_OUTCOMES` 5-tuple ✓
- `compute/envelope.py:34` `STATUSES` 3-tuple ✓
- `exchange/worker.js:400` `EVIDENCE_LADDER` 6 rungs ✓
- `exchange/worker.js:67` health states 6-tuple ✓
- `exchange/worker.js:24` failure taxonomy 8 classes ✓
- `compute/court.py:33` `VERDICTS` 4-tuple ✓
