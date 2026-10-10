# F2 — LUCIDOTA Free Compute Exchange Lifecycle (forensic inventory)

**Investigator:** subagent (read-only) | **Date:** 2026-10-09 | **Method:** read source directly; no summaries trusted.
**Provider note:** no LLM generation used for drafting — all findings from direct code reads. NVIDIA NIM not invoked.

## Where the Exchange lives (verified in tree)

| Component | Path | Version |
|---|---|---|
| Governor (Cloudflare Worker + D1) | `~/workspace/exchange/worker.js` | 0.6.14 (VERSION const, line 77) |
| D1 database | `exchange` (id 0ea89801-9b0a-4efa-9d2f-170d7d285e69) — 14+ tables, CREATE TABLE in worker.js lines 448–512 | live |
| Build/test evidence | `~/workspace/exchange/BUILD-RECORD.md`, `battery-v5.md`, `tests/`, `worker-battery*.py`, `redteam2-*.py` | — |
| Compute-side Python (queue/dispatch/registry/court/envelope) | `~/workspace/compute/{queue,dispatch,registry,court,envelope,ledger,governor,router}.py` | — |
| Rust claimant clients | `~/workspace/exchange-rs/` (nim-claimant, voting, probe-harness, exchange-client; API.md) | client lib only — no governor port |
| Worker protocol (frozen) | `~/workspace/exchange/WORKER-PROTOCOL-v1.md` | v1, frozen 2026-10-06, amendments A1–A3 (v0.6.3), voting (v0.6.4) |

**Naming collision (not the Exchange):** `~/workspace/mcp-servers/exchange/server.py` is a READ-mostly experimental-state MCP server for `go50-attack/compression` — unrelated to the Free Compute Exchange lifecycle. `~/workspace/krampus-express/krx-exchange/` is a separate Rust crate. Neither participates in the lifecycle below.

## Lifecycle A — 9-stage control pipeline (architectural narrative)

`DISCOVER → PROVE → AUTHORIZE → RESERVE → EXECUTE → VERIFY → ACCOUNT → LEARN → REPLAN`
(Source: `BUILD-RECORD.md:2` — Zackary's "COMPLETE THE EXCHANGE" directive.)

State per stage:

| Stage | What it is in code | Status |
|---|---|---|
| DISCOVER | `POST /v1/discover` → resource row, evidence DISCOVERED (worker.js:673–689, `setEvidence`) | EXISTING AND VERIFIED |
| PROVE | Evidence ladder promotion via recorded observations/receipts, `warrantedTier` (worker.js:549–603); delegated verify gauntlet `POST /v1/resources/:id/verify` | EXISTING AND VERIFIED |
| AUTHORIZE | `govern()` — 8 hard gates + EFFICIENCY scoring in trace (worker.js:1476–1492, GATE_ORDER) | EXISTING AND VERIFIED |
| RESERVE | `createLease()` — 60s expiry (worker.js:767–775); atomic `POST /v1/claim`, single conditional UPDATE winner (W1) | EXISTING AND VERIFIED |
| EXECUTE | Claimant executes via `/v1/complete`; inline `runJob()` path also exists (worker.js:1961–2105) | EXISTING AND VERIFIED |
| VERIFY | `GET /v1/receipts/:id/verify` — recomputes input_hash, checks all 10 gates in trace, policy_version, claim binding, accounting binding (worker.js:2694–2712) | EXISTING AND VERIFIED |
| ACCOUNT | `accounting` table — governor's books, written from measured cost not worker assertion (worker.js:471, W6) | EXISTING AND VERIFIED |
| LEARN | `health_observations` → health state + evidence tier updates; policy table NOT writable by observations (BUILD-RECORD v0.4 §8) | EXISTING AND VERIFIED |
| REPLAN | `scheduled()` cron: deferred-job replan (2/run, 8 defers max), orphan reaper, throttle/exhaust recovery (worker.js:2814–2864) | EXISTING AND VERIFIED |

**Caveat:** the 9-stage pipeline is not a single state machine in code — no enum or transition table names all nine. It is an architectural narrative verified stage-by-stage. Classified: **EXISTING BUT UNVERIFIED** as one machine; **EXISTING AND VERIFIED** per stage.

## Lifecycle B — Job states (D1, governor-owned)

Terminal states: `done | failed | blocked | deferred`. Non-terminal: `running`.
(Evidence: worker.js SQL updates at lines 805, 1035–1036, 1105–1128, 1188–1197, 1243–1250, 1961, 2093–2094, 2105, 2814–2864; BUILD-RECORD v0.4 §6.)

Transitions (verified in code):
- `running → deferred` when failure retryable AND defer_count < 8 (worker.js:1035, 1188, 1243, 2859)
- `running → failed` when permanent, or defer_count ≥ 8 (worker.js:1105–1128, 1190, 1244)
- any-retryable rejection → `deferred`; all-permanent → `failed`; policy/capability → `blocked` (worker.js:1949, 2105)
- zombie sweep: stale `running` (no receipt, >10 min) → `deferred` + evidence_log (worker.js:2814–2822)
- DISPROVEN_DEPENDENCY auto-prune: dependent deferred jobs → `failed` with prune receipt (worker.js:1117–1128, WORKER-PROTOCOL-v1.md A2)

**Status: EXISTING AND VERIFIED.**

## Lifecycle C — Worker claim outcomes (delegation protocol)

`SUCCEEDED | FAILED_RETRYABLE | FAILED_PERMANENT | QUARANTINED | EXPIRED`
(Evidence: worker.js:153–158 `WORKER_OUTCOMES` const; "Anything else → 400".)

- `claims` table: `status TEXT DEFAULT 'active'`, `lease_expiry TEXT NOT NULL` (worker.js:461–468)
- Expired claims → EXPIRED; execution marked UNCERTAIN (provider may have executed — never claimed free); job replanned (worker.js:1206–1250, BUILD-RECORD v0.6 §8)
- 10 worker invariants (no lease minting, no gate bypass, no self-accounting, …) — WORKER-PROTOCOL-v1.md

**Status: EXISTING AND VERIFIED.** Enforcing tests: W1–W10 battery (`worker-battery.py`, 9/9 PASS per BUILD-RECORD; W1 double-claim race, W2 replay idempotency ×10 → 1 accepted, W3 forged completion → 400/403, W4 lease expiry → LEASE_EXPIRED, W5 zombie → EXPIRED + replan, W6 cost=$99999 ignored, W7 secret scan, W8 empty 200 → FAILED_RETRYABLE, W9 model-lie → receipt discrepancy, W10 crash → UNCERTAIN).

## Lifecycle D — Evidence ladder (resource trust)

`DISCOVERED → ACCESSIBLE → FREE → QUOTA → AVAILABLE → VERIFIED`
(Evidence: worker.js:39–40, 396–404 `EVIDENCE_LADDER`, 400.)

- `UNKNOWN` = move on; `PARKED` = shelved (credential AUTH_ERROR → PARKED until explicit re-verify; worker.js:404, BUILD-RECORD v0.4 §5)
- Promotion only from recorded evidence (`warrantedTier`, worker.js:568–603); `PARKED` never auto-promotes (worker.js:603)
- New resources start DISCOVERED, unusable (worker.js:48, 681–689)

**Status: EXISTING AND VERIFIED.** Live proof in BUILD-RECORD v0.4 test evidence (lane-kilo 429 → QUOTA_FAILURE → deferred → gauntlet restored ACCESSIBLE→FREE→QUOTA→AVAILABLE).

## Lifecycle E — Resource health states

`AVAILABLE | DEGRADED | THROTTLED | EXHAUSTED | QUARANTINED | UNKNOWN` (worker.js:67)

- THROTTLED: exponential backoff on 429s (2^(n-1) min, cap 60)
- EXHAUSTED: suspends until recheck (5 min)
- QUARANTINED: worker signal; governor quarantines on DEGRADED/THROTTLED (worker.js:997–1000)
- Cron probes only UNKNOWN, DEGRADED, QUARANTINED, or stale resources (BUILD-RECORD v0.2 §6)

**Status: EXISTING AND VERIFIED.**

## Lifecycle F — Delegation object chain (D1)

`JOB → CLAIM → EXECUTION → RECEIPT → ACCOUNTING` — distinct objects (BUILD-RECORD v0.6 §2).

- Claim binds worker↔lease: `claim_id, resource_id, capability, input, policy_snapshot, lease_expiry, attempt, idempotency_key, receipt_requirements, credential_ref (opaque), requested_model` (BUILD-RECORD v0.6 §3)
- Receipts are the system of record: carry attempt_id, policy_version (sha256), lease snapshot, quota/cost/health before-after, fallback_chain (BUILD-RECORD v0.4 §4)

**Status: EXISTING AND VERIFIED.**

## Lifecycle G — Envelope claim statuses (seal layer)

`claimed → established → authorized` (+ UNKNOWN per MUSE-EXCHANGE-DESIGN.md:160)
(Evidence: `~/workspace/compute/envelope.py:34` `STATUSES = ("claimed", "established", "authorized")`.)

Key symbols:
- `envelope.wrap(actor: str, claim_id: str, status: str, payload: dict, prev_hash: str = GENESIS, ts: str = "") -> dict` — rejects bad status (line 144–146)
- `envelope.verify(env: dict) -> None` — raises EnvelopeError on tamper (line 169)
- `envelope.verify_chain(envs: list, start_prev: str = GENESIS) -> None` (line 200)
- `ledger._emit_envelope(rec)` maps execution record `status=="invalid"` → `claimed`, else `established` (ledger.py:82)

**Status: EXISTING AND VERIFIED** for claimed/established wrapping + verify. **`authorized` envelope status: EXISTING BUT UNVERIFIED** — no call site found in `~/workspace/compute` that wraps with `status="authorized"`. Rust mirror: `proof-ledger/rs/src/envelope.rs` (wrap/verify/verify_chain, 10/10 cargo tests per AGENTS.md).

## Lifecycle H — Court verdicts (claim adjudication)

`ESTABLISHED | NOT_ESTABLISHED | DISPROVEN | UNKNOWN`
(Evidence: `~/workspace/compute/court.py:33` `VERDICTS = (...)`.)

- `court.derive_status(evidence: dict, claim_id: str) -> dict` (court.py:94) — verdict derived UNDER a verified canon state; fail-closed UNKNOWN when canon unverifiable (court.py:138–169, 214)
- `court.file_claim(claim: Claim) -> dict` (court.py:82); `claims.jsonl` rows carry `"status": "CLAIMED"` (e.g. `exchange-free-compute-v06`)
- `court.request_completion_review(claim_id, evidence)` (court.py:368); RUNNING_ADVERSARIAL_GATE → GATE_COMPLETE states (court.py:451–461)

**Status: EXISTING AND VERIFIED** (court.py self-tests at lines 450–461 assert verdict transitions; `court_identity_tests.py` exists).

## Lifecycle I — Compute-side queue (local Python)

`queued → dispatched → executing → completed | failed | expired` (`blocked` retained for back-compat)
(Evidence: `~/workspace/compute/queue.py:35–36` `QUEUE_STATUSES`; comment notes RT-C7/RT-C15: dispatched is not terminal.)

- `queue.add(objective, ...) -> dict` — creates `task-<uuid12>`, status `queued` (queue.py:39)
- `queue.mark(task_id, status, decision_hash="")` — asserts status ∈ QUEUE_STATUSES (queue.py:114–115)
- `queue.drain(governor, limit=10, ...)` (queue.py:125)

**Status: EXISTING AND VERIFIED** as code; enforcing test file for queue transitions not located (see gaps).

## Lifecycle J — Compute-side dispatch events (folded state)

Events: `dispatched → executing → completed | failed | expired`; `stale_flagged` flag.
(Evidence: `~/workspace/compute/dispatch.py:112–156` `_fold_state()` — append-only `dispatches.jsonl`, crash-atomic append.)

- `dispatch.create_dispatch(decision, task_id="")`, `mark_executing(dispatch_id)`, `complete_dispatch(dispatch_id, artifact_path, ...)`, `fail_dispatch(dispatch_id, reason)`, `supervised_execute(...)`, `reconcile(...)` (dispatch.py:164–269)
- `executing` only reachable from `dispatched` (dispatch.py:142–143) — transition guard in the fold

**Status: EXISTING AND VERIFIED** (`dispatch_tests.py` exists; RT-C7/RT-C15 notes indicate red-team coverage).

## The 10 hard gates (order matters)

`IDENTITY → AUTHORITY → DATA → CAPABILITY → EVIDENCE → QUOTA → COST → INTEGRITY → (EFFICIENCY scores; scoring ≠ auth) → LEASE → EXECUTE`
(Evidence: worker.js:1457–1492; BUILD-RECORD v0.4 §1.)

- `govern()` records 8 gates + EFFICIENCY in trace; LEASE and EXECUTE recorded later per attempt in `runJob()` (worker.js:1480–1482, 1994–1996)
- Unreached gates recorded as explicitly-labeled "vacuous", never faked (worker.js:1486–1491)
- Receipt verify requires all 10 present in auth trace: `all_gates_recorded` check (worker.js:2704–2706)

**Status: EXISTING AND VERIFIED.** Enforcing: T2 test (sensitive inference BLOCKED at DATA gate, receipt verified True incl. vacuous labels — BUILD-RECORD v0.4); `tests/ingest-envelope.test.mjs` (envelope at ingest).

## Failure taxonomy (never collapsed into "failed")

`RETRYABLE_FAILURE | PERMANENT_FAILURE | POLICY_FAILURE | AUTH_FAILURE | QUOTA_FAILURE | CAPABILITY_FAILURE | PROVIDER_FAILURE | VERIFICATION_FAILURE`
(Evidence: worker.js:24, 745.)

**Status: EXISTING AND VERIFIED** (mapped from adapter error classes; v0.2 error classification: RATE_LIMITED | TIMEOUT | SERVER_ERROR | BAD_RESPONSE | NETWORK | POLICY_BLOCKED | UNKNOWN).

## State ownership

| State | Owner | Store |
|---|---|---|
| Job/claim/lease/execution/receipt/accounting/health/evidence | Governor | D1 `exchange` (worker.js) |
| Execution (pickup/validate/execute/capture/report) | Worker/claimant | ephemeral; only completion reports reach governor |
| Queue tasks, dispatch events | `queue.py` / `dispatch.py` | `~/workspace/compute/queue.jsonl`, `dispatches.jsonl` (+ `.lock` files) |
| Source registry, capability evidence | `registry.py` | `~/workspace/compute/registry.json` (+ seal/sha256) |
| Proof envelopes | `ledger.py` `_emit_envelope` | `~/workspace/compute/envelopes.jsonl` |
| Verdicts | `court.py` | `~/workspace/compute/claims.jsonl` + proof ledger |
| Worker credentials | governor admin | sha256-stored secrets (BUILD-RECORD v0.6 §1) |

Doctrine (WORKER-PROTOCOL-v1.md): Governor owns authority; worker owns execution; neither impersonates the other. Worker output is evidence; receipt verification decides what the Exchange believes.

## Tests enforcing transitions (verified present)

| Test | Enforces |
|---|---|
| `~/workspace/exchange/tests/envelope-vectors.test.mjs` | Envelope verify FAIL-CLOSED: forged payload, seal mismatch, payload_hash mismatch, missing sig, bad status, wrong key → all reject |
| `~/workspace/exchange/tests/ingest-envelope.test.mjs` | Envelope-at-ingest sealing |
| `~/workspace/exchange/worker-battery.py` (W1–W10) | Claim race, replay idempotency, forged completion, lease expiry, zombie sweep, cost assertion, secret scan, empty-output failure, model-lie, crash-uncertainty |
| `~/workspace/exchange/worker-battery-v3.py`, `worker-battery-v4.py`, `worker-battery-v4-integrity.py` | v3: verify backpressure, claim expiry re-check; v4 R1: atomic completion idempotency, INTEGRITY claimed-probe fix, max_cost ≤ spend_authority |
| `~/workspace/exchange/redteam2-*.py`, `rt2-dup-replay.py` | Ballot forgery, quorum, tally replica, duplicate replay (reports present) |
| `~/workspace/compute/envelope_test.py` | Python envelope wrap/verify (10/10 per AGENTS.md — recheck not run, read-only) |
| `~/workspace/compute/dispatch_tests.py`, `registry_tests.py`, `governor_tests.py`, `court_identity_tests.py`, `recovery_tests.py` | Dispatch fold, registry, governor determinism, court identity, recovery |
| `~/workspace/exchange/battery-v5.md` | REPLAN behavior battery (partial per its §106) |

## Gaps / UNKNOWNs (recorded, not fixed)

1. **9-stage pipeline has no single code-defined state machine** — verified stage-by-stage only. No enum, no transition table, no test walks all nine. (EXISTING BUT UNVERIFIED as a machine.)
2. **`authorized` envelope status has no call site** in `~/workspace/compute` — who promotes established→authorized, and where, is UNKNOWN from code. (MUSE-EXCHANGE-DESIGN.md:160 mentions the chain with UNKNOWN.)
3. **Queue transition test file not located** — `QUEUE_STATUSES` asserted in `mark()` but no dedicated queue lifecycle test file found (only `queue.py` inline comments referencing RT-C7/RT-C15).
4. **Deployment state of worker.js v0.6.14 vs live** — file says 0.6.14; live deploy at `lucidota-exchange.cutecity.workers.dev` not re-verified (read-only task, no network probe run). D1 mirror `~/workspace/exchange/d1-mirror.db` exists but staleness UNKNOWN.
5. **Two claim-side vs envelope-side status vocabularies**: `claims.jsonl` uses `"CLAIMED"` (court pipeline) while `envelope.py` uses `"claimed"` (seal pipeline) — related but distinct lifecycles; the mapping between a CLAIMED court claim and a claimed envelope is by convention (`_emit_envelope`), not by a single enforced transition.
6. `battery-v5.md:106` marks REPLAN coverage PARTIAL.

## Per-finding status summary

- EXISTING AND VERIFIED: job states + transitions, worker outcomes W1–W10, evidence ladder, health states, delegation chain, failure taxonomy, 10 gates, envelope wrap/verify/verify_chain, court verdicts, queue statuses, dispatch fold guards, state ownership split.
- EXISTING BUT UNVERIFIED: 9-stage pipeline as one machine; `authorized` envelope promotion path; queue-lifecycle dedicated tests.
- UNKNOWN: live-deploy parity of worker.js 0.6.14; D1 mirror staleness; court-claim ↔ envelope-claim promotion mapping.
