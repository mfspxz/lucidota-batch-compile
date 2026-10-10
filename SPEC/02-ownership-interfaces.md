# SPEC §12-2 — Ownership + Interfaces (re-scoped: collapsed boundaries)

**Mission 2 §5 synthesis, per OWNER DIRECTIVE — ARCHITECTURE SIMPLIFICATION.**
The 13 elaborate per-party boundary contracts are collapsed. Boundaries are now:
**deterministic check ops** (Compare / Calculate / Compare-against-policy) plus the
**allocator's Route / Track / Stop**. Governor + CANON stay as the authorization gates.
Specification only — no code changes, no deletions, no deploys.

**Authority hierarchy (f1, EXISTING AND VERIFIED):** CANON > PL > GIT > AI.
Fail-closed everywhere: when auth, evidence, policy state, or check services are
unavailable, the operation is DENIED / not-accepted — never defaulted.

The "13 boundary parties" from the task brief re-home to loop stages as follows
(see 01 §G for the component→stage mapping):

| Original party | Loop stage | Boundary kind |
|---|---|---|
| task planner | Prompts / Typed work order | authorship (human/authoring LLM) |
| deterministic scheduler | Allocator (composer of queue.drain + govern + route + quota) | Route / Calculate |
| provider router (`compute/router.py::route()`) | Allocator | Route / Calculate |
| quota coordinator (`budget.py`, `nvidia_rpm`, `gemini_rpm`) | Allocator | Calculate |
| governor (`compute/governor.py::govern()`) | Allocator — **authorization gate for allocation** | Compare-against-policy |
| dispatch-gate governor (`admit_action()`) | Loop entry — **authorization gate for admission** | Compare-against-policy |
| worker runtime (adapters) | Workers | Track / Stop |
| artifact validator (`court.derive_status()`) | Deterministic check ops | Compare-against-policy |
| independent verifier (`independent_verifier.run()`, `pl_canon_verifier.run()`) | Deterministic check ops | Compare / Calculate |
| PL + witnesses | Ledger | Track |
| graph services (dev-graph; graph MCP server) | Partitioner (dev-graph); provenance lookup (MCP, read-only) | Calculate / Compare |
| sandbox (liteboxd + ExecutionBackend) | Workers | Track / Stop |
| integration/glue workers | Workers (glue = a unit type, NOT a privileged tier) | Track |
| merge controller | Deterministic check ops (compatible+authorized gate) + Ledger | Compare-against-policy |

Glue/integration work is demoted: it is a *unit type* executed by ordinary Workers under
the same manifest limits and the same check ops — never a privileged layer with merge
authority. Merge = a Compare-against-policy check (compatible + authorized only) whose
result the Ledger records.

---

## Boundary contracts (collapsed)

Each boundary: request contract, response contract, auth check, state mutation,
timeout, retry semantics, receipt.

### B1. Authoring → Typed work order (Prompts → work order)

- **Request:** human or authoring LLM submits a work order: typed units (schema §12-3),
  relationships (`enables` edges), expected outputs, resource limits (max attempts,
  token ceilings, time bounds).
- **Response:** `task-<uuid12>` record via `queue.add()` in `queue.jsonl`, status `queued`;
  immutable thereafter (identity stable across attempts).
- **Auth check:** none at authoring (authorship is the human's); the work order is GIT-tier
  (source history), not authority.
- **State mutation:** one append to `queue.jsonl`.
- **Timeout / retry:** authoring is synchronous local I/O; on write failure the work order
  does not exist — author retries.
- **Receipt:** queue record itself + envelope `claimed` (actor = author).

### B2. Loop entry gate (Compare-against-policy)

- **Request:** `admit_action(proposal, scope, user_authorized, auth_evidence)` —
  `~/workspace/governor/governor.py:114`.
- **Response:** `(allowed, receipt)`; CLI exit 0=ALLOW, 1=DENY, 2=ERROR→DENY.
- **Auth check:** scope vs live `dispatch-policy.json`; `FROZEN_SCOPES` always DENY;
  remediation scopes only when in policy's `active_remediation`; `--user-authorized`
  requires `--auth-evidence`; unknown scope → DENY.
- **State mutation:** decision appended to `dispatch-log.jsonl` + PL claim via
  `record_to_ledger()`; ALLOW + ledger-write-failure → converted to DENY (fail-closed).
- **Timeout / retry:** local subprocess; no retry on DENY (policy decision, not transient).
- **Receipt:** `(allowed, receipt)` tuple + PL claim `governor-{uuid}`.

### B3. Partitioner (Calculate)

- **Request:** typed work order → run-scoped dev-graph.json (`dev-graph/SCHEMA.md`
  vocabulary, `enables` edges).
- **Response:** `cmd_ready(slug)` → set of dispatchable unit ids
  (open ∧ all `enables`-predecessors done); `cmd_blocked` → blocked set.
- **Auth check:** none (pure function of graph state); graph carries no secrets, ever.
- **State mutation:** unit status transitions via `cmd_set_status` (forward-only:
  open → in_progress → done); `validate` green required.
- **Timeout / retry:** local; recompute per tick/event — idempotent.
- **Receipt:** dev-graph.json itself (versioned per run).

### B4. Allocator (Route / Calculate) — the governor + router + quota boundary

- **Request:** ready-unit set + per-tick quota snapshot (read ONCE).
- **Response:** `govern()` → `RoutingDecision` + replay receipt (decision hash, policy hash,
  capability hash, quota snapshot); `route()` → `_route_impl()` provider/model selection;
  `queue.drain()` + `dispatch.create_dispatch()` bind decision→task.
- **Auth check (Compare-against-policy):** `govern()` enforces MUSE_PROPOSES_GOVERNOR_DISPOSES —
  proposer preference is advisory (`preference_outcome` ∈ {none, aligned, overridden});
  proposer-eliminator laundering flagged (RT-B5); `_codify` fail-closes unrecognized reasons
  to `UNMAPPED_REASON`; `MAX_GOVERN_DEPTH=3` anti-loop.
- **State mutation:** atomic quota reservation (bucket acquire with expiry; release on
  failure/completion); dispatch record appended to `dispatches.jsonl`; task `mark()`
  queued → dispatched.
- **Timeout:** reservations expire (lease-style; Exchange precedent: 60s lease expiry in
  `worker.js:767–775` for the D1 path — local reservations get an explicit expiry in §12-5,
  never indefinite).
- **Retry semantics:** bucket refusal → `rate_limited` Execution recorded, unit returns to
  the Allocator tail (never dispatched over-ceiling). Deterministic, no backoff guessing —
  the bucket's `retry_after_s` is the signal.
- **Receipt:** governor replay receipt + `route_with_receipt()` (quota_before/quota_used) +
  envelope `claimed` at dispatch.

### B5. Workers (Track / Stop)

- **Request:** `adapters/*.py::execute(model, prompt, max_tokens, ...)` with an
  `ExecutionManifest` (input bounds, `ResourceEnvelope`, `EvidencePolicy`); execution runs
  through liteboxd (`prepare → start → inspect`, bearer token, enforcer mandatory).
- **Response:** `ExecutionResult {exit_code, output_digests, wall_time_ms, peak_memory_bytes,
  killed}` + receipt fragments (`lucidota-receipt/1` payload).
- **Auth check:** worker NEVER self-accepts, never raises its own budget, never authorizes
  tools, never fabricates test results (f4 §4 contract). MCP authority server is
  NEEDS-JUSTIFICATION (01 §G) — until tested, workers communicate via the verified
  queue/dispatch file path; its `gate.check` remains advisory-only and is never the
  enforcement point.
- **State mutation:** none by the worker beyond its manifest-bounded guest FS (dies with the
  process; host-observable outputs are stdout/stderr/exit code only — f7 §3 honest limits).
- **Timeout:** `wall_time_secs` → SIGKILL (`kill()` always succeeds for a known handle,
  even mid-hang); NETWORK=DENY semantics as characterized (f7).
- **Retry semantics:** worker failures are classified by the fixed retry rules (B8) —
  the worker itself retries nothing.
- **Receipt:** `ExecutionResult` + envelope written to the Ledger at ingest
  (`compute/ledger.py::record()`, identity gate via `request_hash_for`).

### B6. Ledger (Track)

- **Request:** run decisions (`~/ledger/ledger.py::append_locked`), execution envelopes
  (`compute/ledger.py::record`), claims (PL `pl` binary).
- **Response:** seq/chain position; envelope `seal`.
- **Auth check:** append-only (flock, O_APPEND, fsync); envelope `verify` at ingest
  (two-tier: signed → authenticate, unsigned → integrity-only, reported honestly).
- **State mutation:** appends only; corrections are new entries referencing old
  (LEDGER-RULES.md #3). Rotation refusal at 10 GB (unexercised — f5 gap 6).
- **Timeout / retry:** local; `append_locked` retries the lock, never skips the write.
- **Receipt:** the chain itself (`verify_chain`, `pl audit --full`, chain anchors).

### B7. Deterministic check ops (Compare / Calculate / Compare-against-policy)

- **Request:** artifact + its Ledger receipts (attempt record, execution receipt,
  input/base-revision binding).
- **Response:** ternary per op — PASS / FAIL / UNKNOWN — with a fixed verdict rule:
  - `court.derive_status()`: all `REQUIRED_GATES` bound to PL receipts → ESTABLISHED;
    unbound/forged → UNKNOWN; tampered canon → UNKNOWN (fail closed).
  - `envelope.verify()`/`verify_chain()`: raise `EnvelopeError` on any tamper (fail closed).
  - Suite re-runs (`independent_verifier`, `pl_canon_verifier`): exit 0 + zero failures +
    zero masked skips = PASS; any FAIL → NOT_ESTABLISHED.
- **Auth check:** the op compares evidence against policy (REQUIRED_GATES, envelope spec,
  suite exit codes) — it does not exercise judgment. CANON supplies the normative basis
  (`_canon_basis` reads `canon snapshot` heads + context_hash); canon unverifiable →
  UNKNOWN, fail closed (INV-02).
- **State mutation:** none — check ops are pure reads over the Ledger + re-execution.
  They write nothing but their own check receipt.
- **Timeout / retry:** suite re-runs bounded by the same `wall_time_secs` discipline;
  a timed-out check = UNKNOWN (never PASS).
- **Receipt:** check receipt (op name, inputs hashed, verdict, evidence pointers).

### B8. Fixed retry rules (Track / Stop)

- **Request:** check-op FAIL/UNKNOWN + failure-class classification (8-class taxonomy).
- **Response:** one of {requeue-at-tail (bounded attempts), dead-letter, stay-blocked,
  kill-switch}.
- **Auth check:** the rules are policy data (max attempts, backoff, terminal states per
  class) — Compare-against-policy, not discretion.
- **State mutation:** `dispatch.fail_dispatch` / requeue; reservation release; dead-letter
  record appended to the Ledger.
- **Timeout:** per-class cooldowns (Exchange precedent: THROTTLED 2^(n-1) min cap 60;
  EXHAUSTED recheck 5 min — ported as scheduler constants, 01 §B5).
- **Retry semantics:** retries go to the Allocator tail and consume the same quota;
  dependency-blocked stays blocked; queue keeps processing independent work.
- **Receipt:** retry/dead-letter record (attempt #, class, backoff, terminal state).

### B9. Merge (Compare-against-policy) + final acceptance

- **Request:** patch set staged in isolated worktrees + full deterministic suite results +
  check-op receipts for every artifact.
- **Response:** merge or reject.
- **Auth check:** merge requires compatible (no conflicts, suite green on the final tree)
  AND authorized (admission receipt + allocation receipts chain to the patch). No
...[truncated 1728 chars]
---

## Provider use

None — synthesized directly from the evidence files f1–f8 and the owner directive;
no NVIDIA NIM or Gemini calls used for this file.
