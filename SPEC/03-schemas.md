# Versioned Data Schemas — batch-compile (`lucidota-sched/1`)

**SPEC §12 deliverable 3.** Owner: mission §4 (Task and artifact contracts).
Specification only — no code changes, no deletions, no deploys.
State of schema work: **SPEC (new)** — every schema below is a contract to be built, not a description of existing code.

## §0. Global conventions (apply to every schema)

### §0.1 Schema identity and versioning
- Schema namespace: `lucidota-sched`. Current version: **`1`**.
- Every record carries `"schema": "lucidota-sched/1#<contract>"` (e.g. `lucidota-sched/1#task-manifest`).
- Validators **fail closed** on unknown `schema` ids (cf. canon `store::allowed_fields`: unknown fields cannot smuggle semantics; canon freeze §56).
- Compatibility policy within version `1`: **additive fields only**. Renames, removals, type changes, or vocabulary changes require a new major version (`lucidota-sched/2`) and a migration record. Additive fields default to "unknown/unspecified" semantics and must never change the meaning of existing fields.
- **Unknown fields are rejected, not ignored** (canon precedent: `required_fields`/`allowed_fields` per kind, `store.rs`). A record carrying any field not in its schema is invalid. This is load-bearing for the anti-self-acceptance property (§0.6).

### §0.2 Integer contract (XIMPL-2 i64 pin — OPEN divergence)
Per envelope cross-implementation defect **XIMPL-2** (proof-ledger RECEIPT-ENVELOPE.md): Python accepts arbitrary-precision integers; Rust `serde_json` canonicalizer rejects floats and parses >u64 as f64. The interoperable contract is **signed 64-bit only**:
- Every integer field in every schema is `i64`, valid range `[-2^63, 2^63-1]`.
- **Arbitrary-precision integers are FORBIDDEN in payloads** until the XIMPL-2 divergence is resolved.
- Canonical JSON: UTF-8 raw (no `\uXXXX`), sorted keys, compact separators, **no floats ever**, timestamps opaque strings (XIMPL-1 pinned).
- Validators MUST reject any integer outside i64 range with `NUMERIC_CONTRACT_VIOLATION`.

### §0.3 Identity rules (mission §4)
- **Task identity is stable across attempts**: `task_id` is minted once at task creation and never changes.
- **Attempt identity is unique**: each execution of a task mints a new `attempt_id`. No two attempt records share an `attempt_id`.
- `task_id` format: `"task-" + 12 lowercase hex chars` (queue.py convention).
- `attempt_id` format: `"att-" + 12 lowercase hex chars`, unique across the run; includes `task_id` and `attempt_n` (i64 ≥ 1, monotonically increasing per task).

### §0.4 Artifact binding (mission §4)
Every artifact manifest MUST bind to:
- the originating `task_id` + `attempt_id` (which attempt produced it),
- the **exact** `input_hash` (sha256 over canonical input bytes — the request as sealed, not as asserted),
- the `base_revision` (the revision of the world the artifact applies against),
- `validation_evidence`: references to validation-result records (ids), never bare boolean claims.
An artifact record missing any of the four is invalid.

### §0.5 Reused vocabularies — verbatim from measured evidence
No new vocabularies are invented. Exact definitions below; case is significant.

**Envelope claim statuses** (`lucidota-receipt/1`, RCPT-009 resolution, f2/f5):
- `claimed` =def. chain opened ∧ terminal observation absent. Intent/attempt recorded; outcome unknown. Covers infra errors pre-empting a terminal state.
- `established` =def. terminal observation present ∧ chain verifies. The guest's exit code is orthogonal — a failed guest is still an established receipt; what is established is the *observation*, not the success.
- `authorized` =def. receipt endorsed by the sealing authority (endorsement axis; semantics unchanged).

**Court verdicts** (`compute/court.py:33`, f2/f4):
- `ESTABLISHED | NOT_ESTABLISHED | DISPROVEN | UNKNOWN`.
- `UNKNOWN` is fail-closed: unbound/forged evidence → never `ESTABLISHED` (`court.derive_status`).
- A worker never declares DONE — verdicts are assessments consumed by the driver/court.

**Job states** (`compute/queue.py:35-36` `QUEUE_STATUSES`):
- `queued | dispatched | executing | completed | failed | expired` (`blocked` retained for back-compat).
- Verified transitions: `running → deferred` when retryable AND `defer_count < 8`; `running → failed` when permanent or `defer_count ≥ 8`; stale `running` (no receipt, >10 min) → `deferred` (zombie sweep, worker.js:2814–2822).

**Worker claim outcomes** (exchange `WORKER-PROTOCOL-v1.md`, worker.js:153–158):
- `SUCCEEDED | FAILED_RETRYABLE | FAILED_PERMANENT | QUARANTINED | EXPIRED`. Anything else → reject (400 analog).

**Failure taxonomy** (worker.js:24,745 — never collapsed into "failed"):
- `RETRYABLE_FAILURE | PERMANENT_FAILURE | POLICY_FAILURE | AUTH_FAILURE | QUOTA_FAILURE | CAPABILITY_FAILURE | PROVIDER_FAILURE | VERIFICATION_FAILURE`.

**Governor reason codes** (`governor.py` `REASON_CODES`): `HARD_CONSTRAINT | BUDGET_EXCEEDED | INSUFFICIENT_CAPABILITY | LOW_EXPECTED_UTILITY | LATENCY_VIOLATION | AUTHORITY_VIOLATION | INSUFFICIENT_VERIFICATION | UNAVAILABLE | STRATEGIC_RESOURCE_RESERVED | NO_MEASURED_EVIDENCE | UNMAPPED_REASON`. Unrecognized reasons fail closed to `UNMAPPED_REASON`.

**Task-dependency edges** (dev-graph `SCHEMA.md`, closed vocabulary — no new edge ontology):
- `part_of | informs | enables | tests | demos | targets | mitigates | decides | scheduled_for`.
- `enables` is the scheduling edge: a task is not ready until all `enables`-predecessors are `done` (`devgraph.py ready` computation). Task-dependency contracts use `enables` for ordering; other vocabulary edges may be recorded for provenance but never gate scheduling.

### §0.6 Anti-self-acceptance property (mission §4 — provable from schema)
A model response must NEVER be able to: self-accept, raise its own budget, authorize a tool, change policy, or fabricate a test result. Enforcement is two-layer:

1. **Absent fields (schema layer).** The worker-response schema contains NO field for:
   - acceptance or verdict (response carries an *outcome* — what happened — not a verdict — what it means);
   - budget, quota, or spend adjustments;
   - tool authorization, policy content, or policy references;
   - test results as claims (only `artifact_refs` by content hash; results are re-measured).
2. **Validator-side rejection (governor layer).** Any worker-submitted record carrying a forbidden field name — including `authority`, `verified`, `execute`, `claim_status`, `budget`, `budget_increase`, `authorize_tool`, `policy`, `accepted`, `test_result`, or any field not in the schema — is **rejected with reason `AUTHORITY_VIOLATION`** before any other processing. (Precedent: `AiProposal::sanitize` strips smuggled authority-bearing fields; `canon store::allowed_fields` rejects unknown fields; threat model TM-7 self-attestation.)
3. **Verdicts are structurally separate.** Acceptance lives only in validation-result and acceptance-decision records, produced by validators (independent verifier, `court.derive_status`), never by workers. Invariant INV-01: an AI assertion cannot create proof; INV-02: assertions don't create evidence.
4. **Budgets are governor-owned.** Quota pool and reservation states are written only by the governor/quota coordinator; the schema for worker-facing records has no write path to them.
5. **Test results are re-measured.** Artifact validation re-executes acceptance tests in the sandbox; worker-claimed results are treated as `claimed` evidence, never `established`. Evaluators determine status from structure first, then score payload (RCPT-009 doctrine).

**Proof sketch:** let R be any worker response record. Acceptance of an artifact requires an acceptance-decision record whose producer is a validator (schema §14 requires `producer_role ∈ {validator, court, verifier}` and `verdict ∈ {ESTABLISHED,…}`). R's schema has no field that can write or influence an acceptance-decision record, no field a validator reads as acceptance, and unknown/forbidden fields cause rejection of R itself. Therefore no content of R can move the acceptance state. ∎

### §0.7 Evidence receipt transport (constraint a)
All evidence receipts are **`lucidota-receipt/1` envelopes** — no second envelope may be invented.
Symbols: `envelope.wrap(actor, claim_id, status, payload, prev_hash=GENESIS, ts)` · `envelope.verify(env)` (raises `EnvelopeError` fail-closed) · `envelope.verify_chain(envs, start_prev=GENESIS)` — mirrored in `compute/envelope.py` and `proof-ledger/rs/src/envelope.rs` (16 Rust unit tests, cross-language interop both directions).
Envelope fields (spec `~/workspace/proof-ledger/RECEIPT-ENVELOPE.md`): `env="lucidota-receipt/1" | ts | actor | claim_id | status | payload | payload_hash | prev_hash | sig ("HS256:<hex>", authority signature, fail-closed, no legacy unsigned path) | seal` (sha256 over canonical envelope incl. sig — binds signature into chain).
Anti-transplant: `claim_id` binding enforced at ingest (cf. `checkClaimBinding`); replay rejected (cf. 409 on seen seal). Payload integers pinned to i64 (§0.2).

### §0.8 What this spec does NOT define (hard rules)
- No second governor, router, ledger, scheduler, or validator is introduced. All records reference the existing authorities: governor (`governor.py::govern`), router (`router.decide`), verifiers (`independent_verifier`, `pl_canon_verifier`), court (`court.derive_status`), proof ledger (`ledger.py`/`pl`), canon (`canon audit/snapshot`).
- **Cap'n Maps gets no schema and no role.** F6-12: the term exists only in the batch-compile mission docs; no artifact exists in workspace or ledger. Any DAG role for it is BLOCKED until a real contract is discovered.
- Measured vs declared values are tagged: `[M]` measured, `[D]` declared/unmeasured. Declared values are never promoted to measured (f3 doctrine).

---

## 1. `lucidota-sched/1#execution-run` — Execution run

The top-level campaign object. One run = one bounded batch-compile campaign with a fixed objective and budget.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#execution-run"` |
| `run_id` | string | yes | `"run-" + 12 lowercase hex`, unique |
| `objective` | string | yes | ≤ 4096 chars; the objective the run serves (fixed at creation) |
| `state` | string | yes | `planned | running | draining | complete | aborted` |
| `created_ts` | string (RFC3339 UTC) | yes | opaque; set once |
| `policy_snapshot` | string | yes | sha256 of the policy/constitution under which the run executes (cf. receipt `policy_version`) |
| `quota_reservation_id` | string | yes | top-level reservation covering the run's budget |
| `max_concurrent_tasks` | i64 | yes | ≥ 1; ≤ concurrency ceiling enforced by governor |
| `terminal_reason` | string | no | set when `state ∈ {complete, aborted}`; free text ≤ 512 chars |

**State transitions:** `planned → running → draining → complete`; `running → aborted`; `draining → aborted`. No other transitions. `complete` and `aborted` are terminal. Forward-only (dev-graph `devgraph.py` precedent).
**Validation rules:** `run_id` unique; `policy_snapshot` must verify against the live canon snapshot (`canon snapshot` exit 0) at creation; `max_concurrent_tasks` must not exceed governor's measured concurrency (currently UNKNOWN for providers — see §5; scheduler must not invent one).
**Compatibility:** additive-only; `terminal_reason` added v1.x without breaking readers.

---

## 2. `lucidota-sched/1#task-manifest` — Task manifest

The fixed unit of delegated work. Task identity (`task_id`) is **stable across attempts** (§0.3).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#task-manifest"` |
| `task_id` | string | yes | `"task-" + 12 lowercase hex`; stable across attempts |
| `run_id` | string | yes | parent run |
| `tier` | string | yes | `tier1 | tier2-glue | final-glue | acceptance` (mission §2 tier split) |
| `state` | string | yes | `queued | dispatched | executing | completed | failed | expired` (+ `blocked` back-compat only) |
| `node_type` | string | yes | dev-graph node type: `goal|epic|task|track|feature|research|design|plan|practice|ktest|benchmark|query|demo_beat|schema_label|decision|risk|deliverable|milestone` (SCHEMA.md; prefer `epic`/`task`) |
| `objective` | string | yes | ≤ 4096 chars |
| `required_capabilities` | string[] | yes | ≥ 1; capability names from the measured registry |
| `acceptance_tests` | object | yes | test spec: `{command: string, expect: string, timeout_ms: i64}` array; ≥ 1 test |
| `input_spec` | object | yes | bounded input description (see §7 worker request envelope) |
| `max_input_bytes` | i64 | yes | ≥ 0; hard bound |
| `max_output_bytes` | i64 | yes | ≥ 0; hard bound |
| `retry_budget` | i64 | yes | 0–8 (`defer_count < 8` precedent, f2) |
| `failure_class` | string | no | set when failed: failure taxonomy (§0.5) |
| `defer_count` | i64 | yes | default 0; incremented on retryable defer |
| `supersedes` | string | no | `task_id` of a superseded task (corrections are new records, PROVENANCE-ENFORCEMENT §6.4) |

**State transitions:** `queued → dispatched → executing → completed | failed | expired`. `dispatched → queued` permitted on claim expiry without execution (UNCERTAIN — provider may have executed; never re-claimed as free, f2 Lifecycle C). `blocked` is legacy-only: may appear from old records, never minted. Forward-only otherwise. `running`-analogs (`executing`) older than 10 min with no receipt → `queued` via zombie sweep + `evidence_log` (f2 Lifecycle B).
**Validation rules:** `acceptance_tests` must be executable by the artifact validator (no worker-graded tests); `required_capabilities` must exist in the registry (`registry.py`); `retry_budget ≤ 8`; a task in `failed` must carry `failure_class`.
**Compatibility:** new optional fields additive; `state` vocabulary frozen.

---

## 3. `lucidota-sched/1#task-dependency` — Task dependency

Ordering + provenance between tasks, reusing the dev-graph edge vocabulary (§0.5). **No new edge ontology.**

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#task-dependency"` |
| `dep_id` | string | yes | `"dep-" + 12 lowercase hex` |
| `run_id` | string | yes | scope |
| `from_task` | string | yes | predecessor `task_id` |
| `to_task` | string | yes | dependent `task_id`; ≠ `from_task` |
| `edge` | string | yes | closed vocabulary: `part_of | informs | enables | tests | demos | targets | mitigates | decides | scheduled_for` |
| `note` | string | no | ≤ 512 chars; rationale (never trusted as evidence) |

**Semantics:** only `enables` gates scheduling: `to_task` is not `ready` until all `enables`-predecessors are `completed` (`devgraph.py ready` computation). Other edges are provenance only.
**Validation rules:** no self-edges; no `enables` cycles (DAG check at ingestion — cycle → reject with `HARD_CONSTRAINT`); both endpoints must exist in the run; duplicate `(from_task, to_task, edge)` → idempotent no-op (merge-by-id, never regress status — `enrich-graphs.py` precedent).
**State transitions:** none (dependency records are immutable once admitted; corrections via `supersedes` on a new record).
**Compatibility:** vocabulary frozen; cycle-rejection is validator behavior, not schema change.

---

## 4. `lucidota-sched/1#model-provider-profile` — Model/provider profile

Capability + quota facts about a provider lane. **Declared vs measured is explicit and never promoted** (f3 doctrine).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#model-provider-profile"` |
| `profile_id` | string | yes | `"prof-" + 12 lowercase hex` |
| `provider` | string | yes | e.g. `nvidia-nim`, `gemini-direct`, `ai-router`, `deepseek`, `local-subprocess` |
| `model` | string | yes | provider's model id string (opaque) |
| `role` | string | yes | `generate | critique | verify` (provider-routing doctrine: DeepSeek/NVIDIA generate; Gemini critiques; verifier models verify) |
| `rpm_limit` | i64 | no | requests/min ceiling; **provenance required** |
| `rpm_provenance` | string | no | required iff `rpm_limit` present: `measured | declared` |
| `input_tpm` | i64 | no | measured only; `null` = UNKNOWN |
| `output_tpm` | i64 | no | measured only; `null` = UNKNOWN |
| `concurrency` | i64 | no | measured only; `null` = UNKNOWN |
| `context_window` | i64 | no | declared or measured; provenance in note |
| `observed_max_input` | i64 | no | measured hosted max (e.g. `[M]` NVIDIA nemotron-3-super `524288`, nemotron-3-ultra `393216`, per f8) |
| `health` | string | yes | `healthy | degraded | unhealthy | unknown` (maps to Exchange resource health: `AVAILABLE|DEGRADED|THROTTLED|EXHAUSTED|QUARANTINED|UNKNOWN`) |
| `cost_model` | string | yes | `free-tier | credit-pool-estimate | zero-dollar`; never dollars unless a provider meter exists |
| `notes` | string | no | provenance citations (file + line, e.g. `adapters/nvidia.py:109-111`) |

**Measured facts pinned at spec time [M]:** Gemini direct: `rpm_limit=10`, `rpm_provenance=measured` (adapter-enforced ceiling, probe-proven 2026-10-08); NVIDIA: `rpm_limit=39`, `rpm_provenance=measured` (adapter-enforced hard ceiling, operational order; provider limit UNVERIFIED — not 39); NVIDIA 5,000-call budget = UNVERIFIED_ESTIMATE (governance only, never capacity); Gemini 20 requests/day free-tier floor [M]; all TPM/concurrency values UNKNOWN (null, not 0).
**Validation rules:** `rpm_limit` without `rpm_provenance` → reject; a `declared` rpm_limit MUST NOT be used in scheduling math (adapter protocol: forbids promoting declarations); scheduler may only pace on `measured` values.
**State transitions:** none for the profile itself; `health` changes are recorded as observations, not edits (append-only health_observations precedent).

---

## 5. `lucidota-sched/1#quota-pool` and `lucidota-sched/1#quota-reservation` — Quota pool + reservation

One contract section, two record kinds (both governor-owned; no worker write path exists — §0.6).

### 5a. Quota pool
| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#quota-pool"` |
| `pool_id` | string | yes | `"pool-" + 12 lowercase hex` |
| `profile_id` | string | yes | backing provider profile |
| `window_kind` | string | yes | `rate-1m | rate-10m | daily-count | credit-estimate | none` |
| `limit` | i64 | yes | ≥ 0; the enforced ceiling (measured or policy) |
| `limit_provenance` | string | yes | `measured | policy | estimate` (`estimate` ⇒ governance-only, never capacity — budget.py doctrine) |
| `held` | i64 | yes | ≥ 0; currently reserved, not yet consumed |
| `consumed` | i64 | yes | ≥ 0; consumed in the current window |
| `band` | string | no | `normal_ops | catastrophic_debugging | final_architecture | capability_research` (budget.py bands: <0.60 / <0.80 / <0.90 / ≤1.00 of estimate) |
| `guard` | i64 | no | utilization numerator guard, e.g. `55` = 0.55 pause threshold (burn.py `NVIDIA_BAND_GUARD`, pause at ≥0.55, resume <0.50) |

### 5b. Quota reservation
| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#quota-reservation"` |
| `reservation_id` | string | yes | `"rsv-" + 12 lowercase hex` |
| `pool_id` | string | yes | source pool |
| `task_id` | string | yes | reserving task |
| `attempt_id` | string | yes | reserving attempt (unique) |
| `units` | i64 | yes | ≥ 1; ≤ pool limit |
| `state` | string | yes | `reserved | consumed | released | expired` |
| `expires_ts` | string (RFC3339 UTC) | yes | lease expiry (cf. Exchange 60s lease precedent: bounded, atomic winner) |

**State transitions (reservation):** `reserved → consumed | released | expired`. Terminal: all three. No resurrection. On task abort: `reserved → released`.
**Validation rules:** `held + units ≤ limit` at reserve time (atomic check); `estimate`-provenance pools gate on bands/guards, never on provider-confirmed capacity; reservations are minted only by the governor/quota coordinator — a reservation naming a worker as minter is rejected (`AUTHORITY_VIOLATION`).
**Compatibility:** additive; band semantics frozen.

---

## 6. `lucidota-sched/1#attempt-record` — Attempt record

One execution of a task. `attempt_id` unique per attempt; `task_id` stable (§0.3).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#attempt-record"` |
| `attempt_id` | string | yes | `"att-" + 12 lowercase hex`, unique run-wide |
| `task_id` | string | yes | stable task identity |
| `attempt_n` | i64 | yes | ≥ 1; monotonic per `task_id` |
| `state` | string | yes | `prepared | dispatched | running | reported | closed` |
| `outcome` | string | no | set when `closed`: `SUCCEEDED | FAILED_RETRYABLE | FAILED_PERMANENT | QUARANTINED | EXPIRED` |
| `failure_class` | string | no | set when outcome is a failure: failure taxonomy (§0.5) |
| `request_seal` | string | no | seal of the worker-request envelope (binding) |
| `response_seal` | string | no | seal of the worker-response envelope |
| `receipt_seal` | string | no | seal of the evidence receipt closing this attempt |
| `dispatch_ts` / `report_ts` | string (RFC3339 UTC) | no | set on transition |
| `idempotency_key` | string | yes | unique; replays with the same key are no-ops (W2 precedent: ×10 → 1 accepted) |

**State transitions:** `prepared → dispatched → running → reported → closed`. `dispatched → prepared` on lease expiry without execution. Terminal: `closed`. Forward-only otherwise. `running` without receipt beyond the attempt timeout → `EXPIRED` outcome (UNCERTAIN: provider may have executed — never re-claimed as free).
**Validation rules:** `attempt_id` unique (duplicate → reject, not merge); `attempt_n` = max(previous)+1 for the task; `outcome` restricted to the 5 worker outcomes — anything else → reject (worker.js:153–158 "Anything else → 400"); `failure_class` required when outcome ≠ SUCCEEDED; a `closed` attempt must carry `response_seal` and `receipt_seal`.
**Compatibility:** additive; outcome vocabulary frozen.

---

## 7. `lucidota-sched/1#worker-request-envelope` — Worker request envelope

The **fixed task envelope** per the batch-compile doctrine: bounded inputs, explicit outputs, constraints, acceptance tests. LLM workers get this, do the work, return bounded artifacts, exit. No long conversations.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#worker-request-envelope"` |
| `envelope_id` | string | yes | `"wreq-" + 12 lowercase hex` |
| `task_id` / `attempt_id` | string | yes | binding (attempt unique, task stable) |
| `inputs` | object | yes | bounded input payload; canonical bytes ≤ `max_input_bytes` |
| `input_hash` | string | yes | sha256 over canonical `inputs` — the identity of the work, recomputed by validator |
| `base_revision` | string | yes | revision the work applies against (commit sha or content hash) |
| `outputs_spec` | object | yes | what the worker must return: `{artifacts: [{name, kind, max_bytes}], fields: [names]}` |
| `constraints` | object | yes | hard constraints: `{timeout_ms: i64, max_output_bytes: i64, no_network: bool, sandbox: string}` |
| `acceptance_tests` | object[] | yes | ≥ 1: `{command, expect, timeout_ms}` — executed by the validator, never by the worker |
| `model_profile_id` | string | yes | which lane this request targets |
| `reservation_id` | string | no | quota reservation covering this request |
| `state` | string | yes | `sealed | dispatched | consumed | closed` |

**State transitions:** `sealed → dispatched → consumed → closed`. Terminal: `closed`. One envelope = one attempt; never re-dispatched (replay → reject via `idempotency_key` on the attempt).
**Validation rules:** `len(canonical(inputs)) ≤ max_input_bytes` (from task manifest); `sha256(canonical(inputs)) == input_hash` (recomputed — never trusted from the proposer); `acceptance_tests` non-empty; NO auth/policy/budget/tool fields — presence → `AUTHORITY_VIOLATION` (§0.6); `timeout_ms` within sandbox wall-clock caps.
**Compatibility:** additive; inputs/outputs specs are versioned by content hash, not by schema bump.

---

## 8. `lucidota-sched/1#worker-response-envelope` — Worker response envelope

What the worker returns. Carries *observations*, never *judgments* (§0.6).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#worker-response-envelope"` |
| `envelope_id` | string | yes | `"wrsp-" + 12 lowercase hex` |
| `attempt_id` | string | yes | binding to the unique attempt |
| `task_id` | string | yes | binding to the stable task |
| `outcome` | string | yes | `SUCCEEDED | FAILED_RETRYABLE | FAILED_PERMANENT | QUARANTINED | EXPIRED` — what happened, not what it means |
| `failure_class` | string | no | required unless `SUCCEEDED`: failure taxonomy (§0.5) |
| `artifact_refs` | object[] | yes (may be empty) | `[{name, sha256, bytes: i64}]` — content-addressed; `bytes ≤ max_output_bytes` |
| `logs_ref` | string | no | content hash of captured logs (16 MiB cap precedent, f7) |
| `wall_time_ms` | i64 | yes | ≥ 0; measured by the runtime, not asserted |
| `exit_code` | i64 | yes | guest exit code; orthogonal to acceptance (RCPT-009) |

**FORBIDDEN FIELDS (validator-side rejection, §0.6):** `accepted`, `verdict`, `approved`, `budget`, `budget_increase`, `spend`, `authorize_tool`, `tool`, `policy`, `policy_change`, `test_result`, `tests_passed`, `authority`, `verified`, `execute`, `claim_status`, and ANY field not in this table. Presence of any → reject record, `AUTHORITY_VIOLATION`, and file a falsification entry (`court.record_falsification`, TM-7 precedent).
**State transitions:** none (immutable once sealed by the worker; the attempt record, not the response, carries lifecycle state).
**Validation rules:** `sha256(artifacts) == artifact_refs[].sha256` recomputed by the validator; `outcome` vocabulary exact; unknown fields → reject (not strip) — fail closed.
**Compatibility:** additive; forbidden-field list only grows.

---

## 9. `lucidota-sched/1#artifact-manifest` — Artifact manifest

The deliverable descriptor. Binds artifact → task + exact input + base revision + validation evidence (§0.4).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#artifact-manifest"` |
| `artifact_id` | string | yes | `"art-" + sha256(canonical artifact bytes)[0:12]` — content-addressed |
| `task_id` / `attempt_id` | string | yes | originating task (stable) + producing attempt (unique) |
| `input_hash` | string | yes | sha256 of the exact sealed input this artifact was produced from |
| `base_revision` | string | yes | revision the artifact applies against |
| `name` / `kind` | string | yes | e.g. `code`, `test`, `report`, `receipt`; kind ∈ a closed list per tier |
| `bytes` | i64 | yes | ≥ 0; ≤ `max_output_bytes` of the task |
| `sha256` | string | yes | content hash; `artifact_id` must embed its prefix |
| `validation_evidence` | string[] | yes (may be empty initially) | validation-result ids; an artifact is *usable* only when this is non-empty |
| `supersedes` | string | no | `artifact_id` this replaces (explicit, INV-07) |
| `state` | string | yes | `produced | hash-pinned | validation-scheduled | validated | rejected` |

**State transitions:** `produced → hash-pinned → validation-scheduled → validated | rejected`. `validated → rejected` is FORBIDDEN (corrections are new artifacts with `supersedes`, never edits). Terminal: `validated`, `rejected`.
**Validation rules:** `sha256` recomputed from bytes — mismatch → reject; `input_hash` must equal the sealed request's `input_hash` (anti-transplant, cf. `checkClaimBinding`); `base_revision` must match the run's current base or an explicit rebase record; `validated` requires ≥1 validation-result id in `validation_evidence` whose verdict is `PASS`.
**Compatibility:** additive; `state` vocabulary frozen.

---

## 10. `lucidota-sched/1#validation-result` — Validation result

Independent re-measurement of an artifact by the artifact validator (sandbox execution). Worker claims are `claimed`; this record makes them `established` or not (RCPT-009).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#validation-result"` |
| `validation_id` | string | yes | `"val-" + 12 lowercase hex` |
| `artifact_id` | string | yes | content-addressed binding |
| `validator` | string | yes | identity of the validator (service actor, not a model) |
| `checks` | object[] | yes | ≥ 1: `{name, command, expect}` — the acceptance tests from the task manifest, re-run |
| `results` | object[] | yes | 1:1 with checks: `{name, observed: string, pass: bool, wall_time_ms: i64, exit_code: i64}` — measured, never asserted |
| `verdict` | string | yes | `PASS | FAIL | UNKNOWN` (verifier gate ternary: PASS/FAIL/UNKNOWN) |
| `evidence_refs` | string[] | yes | seals of the receipts emitted during validation |
| `ts` | string (RFC3339 UTC) | yes | when validation ran |

**Validation rules:** every check result must be measured in the sandbox (liteboxd `inspect` evidence or equivalent); `verdict=PASS` requires all checks `pass=true`; any tampered/unreproducible result → `UNKNOWN` (fail closed, `court.derive_status` precedent); `results` entries with no observed output → `FAIL` (W8 precedent: empty 200 → FAILED_RETRYABLE at attempt level; at validation level, empty evidence → FAIL).
**State transitions:** none (immutable measurement record).
**Compatibility:** additive; `verdict` vocabulary frozen.

---

## 11. `lucidota-sched/1#retry-record` — Retry / dead-letter record

The retry budget ledger. Enforces the defer cap (`defer_count < 8`) and the permanent-failure dead letter.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#retry-record"` |
| `retry_id` | string | yes | `"rty-" + 12 lowercase hex` |
| `task_id` | string | yes | stable task identity |
| `attempt_id` | string | yes | the failed attempt being retried |
| `attempt_n` | i64 | yes | the attempt number that failed |
| `failure_class` | string | yes | failure taxonomy (§0.5) |
| `retry_count` | i64 | yes | ≥ 0; retries already consumed by this task |
| `disposition` | string | yes | `requeued | dead-lettered` |
| `reason` | string | no | ≤ 512 chars |
| `ts` | string (RFC3339 UTC) | yes | |

**Disposition rules (validator-enforced):**
- `failure_class = PERMANENT_FAILURE | POLICY_FAILURE | AUTH_FAILURE` → `dead-lettered` immediately (cf. "all-permanent → failed").
- `failure_class = RETRYABLE_FAILURE | QUOTA_FAILURE | CAPABILITY_FAILURE | PROVIDER_FAILURE | VERIFICATION_FAILURE` AND `retry_count < retry_budget (≤8)` → `requeued` (cf. "running → deferred when retryable AND defer_count < 8").
- Retryable classes with `retry_count ≥ retry_budget` → `dead-lettered` (cf. "defer_count ≥ 8 → failed").
- DISPROVEN_DEPENDENCY auto-prune: a task whose `enables`-predecessor is dead-lettered with class `VERIFICATION_FAILURE`/`PERMANENT_FAILURE` is `dead-lettered` with reason `disproven_dependency` (f2 A2 precedent), never requeued.
**Validation rules:** `retry_count` must equal the task's `defer_count`; `dead-lettered` is terminal — no new attempts may reference the task (enforced by scheduler).
**Compatibility:** additive; disposition vocabulary frozen.

---

## 12. `lucidota-sched/1#integration-result` — Integration result

Records what happened when tier-N artifacts were glued into the next tier's tree (tier2-glue, final-glue).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#integration-result"` |
| `integration_id` | string | yes | `"int-" + 12 lowercase hex` |
| `run_id` | string | yes | scope |
| `task_ids` | string[] | yes | ≥ 1; tasks whose artifacts were integrated |
| `artifact_ids` | string[] | yes | content-addressed artifacts consumed |
| `base_revision` | string | yes | revision integrated onto |
| `result_revision` | string | no | revision produced (set on success) |
| `outcome` | string | yes | `INTEGRATED | CONFLICT | FAILED` |
| `validation_refs` | string[] | yes | validation-result ids for the integration suite run (contract checks, interface tests, full integration suite per drift boundaries 4–5) |
| `conflicts` | string[] | no | conflicting artifact ids (when `CONFLICT`) |
| `ts` | string (RFC3339 UTC) | yes | |

**Validation rules:** `INTEGRATED` requires all `validation_refs` to resolve to `PASS` verdicts; tree edits must be in isolated worktrees with patch validation and deterministic merge gates (drift boundary 6); the integration suite (drift boundary 5: full integration suite) must be re-run, never trusted from tier1 claims.
**State transitions:** none (immutable record of an integration event).
**Compatibility:** additive.

---

## 13. `lucidota-sched/1#patch-merge-request` — Patch / merge request

The merge proposal into the base tree. Explicit supersession; no force-push semantics anywhere (AGENTS.md: `push --force` forbidden; history is append-only).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#patch-merge-request"` |
| `patch_id` | string | yes | `"pmr-" + 12 lowercase hex` |
| `run_id` | string | yes | scope |
| `base_revision` | string | yes | revision the patch applies to |
| `patch_hash` | string | yes | sha256 of canonical patch bytes |
| `artifact_refs` | string[] | yes | ≥ 1; validated artifacts composing the patch |
| `author_task_ids` | string[] | yes | ≥ 1; tasks that produced the artifacts (never a human name unless the human authored it) |
| `state` | string | yes | `proposed | validated | merged | rejected` |
| `supersedes` | string | no | `patch_id` this replaces (explicit, INV-07) |
| `merge_receipt_seal` | string | no | seal of the evidence receipt for the merge (set when `merged`) |

**State transitions:** `proposed → validated → merged | rejected`. `validated → rejected` permitted (review finds a defect); `rejected`/`merged` terminal. No backward transitions; supersession via new record.
**Validation rules:** `validated` requires all `artifact_refs` to have validation verdict `PASS` and `base_revision` to be the current tree head (or an explicit rebase record); merge must pass deterministic merge gates (patch validation, conflict check); every merge emits an evidence receipt (`merge_receipt_seal` required for `merged`); **destructive operations forbidden**: the merge machinery must never invoke `reset`/`stash`/`clean -f`/`checkout --force`/`push --force`/history rewriting (NO DESTRUCTIVE GIT OPS, AGENTS.md) — a merge request whose plan includes any is rejected with `HARD_CONSTRAINT`.
**Compatibility:** additive; `state` vocabulary frozen.

---

## 14. `lucidota-sched/1#acceptance-decision` — Acceptance decision

The court's verdict on a claim. Produced only by validators/court/verifiers — never by workers (§0.6).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#acceptance-decision"` |
| `decision_id` | string | yes | `"acc-" + 12 lowercase hex` |
| `claim_id` | string | yes | the claim being judged |
| `claim` | object | yes | court Claim fields: `{claim_id, subject, actor, version: i64, scope, statement, classification, falsification_conditions: string[]}` (`court.Claim`, f4) |
| `verdict` | string | yes | `ESTABLISHED | NOT_ESTABLISHED | DISPROVEN | UNKNOWN` — verbatim court vocabulary |
| `producer_role` | string | yes | `court | verifier | validator` — workers excluded by schema (enum has no worker value) |
| `evidence_bindings` | object[] | yes | `[{gate, receipt_seal, evidence_hash}]` — every required gate (per `REQUIRED_GATES` for the claim's classification) bound to a PL receipt |
| `unbound` | string[] | yes (may be empty) | gates with unbound evidence |
| `canon_context` | object | yes | `{heads: string[], context_hash: string}` — canon snapshot the verdict was derived under |
| `derivation` | string | yes | ≤ 2048 chars; how the verdict was derived (the `derivation` field from `derive_status`) |
| `note` | string | no | ≤ 512 chars |
| `ts` | string (RFC3339 UTC) | yes | |

**Validation rules (acceptance predicates, `court.derive_status`):**
1. Every required gate for the claim's classification must have evidence bound to a PL receipt (`evidence_bindings` covers all required gates; `unbound` empty).
2. Unbound/forgeable evidence → `UNKNOWN`, never `ESTABLISHED`.
3. Canon state must verify (`canon snapshot` exit 0 at the pinned heads); corrupt canon → fail closed to `UNKNOWN`.
4. `producer_role` must be a validator-class actor; a decision naming a worker/model as producer is rejected (`AUTHORITY_VIOLATION`, INV-01).
**State transitions:** none (verdicts are immutable assessments; a re-review is a new decision with a new `decision_id` referencing the claim).
**Compatibility:** additive; `verdict` vocabulary frozen; new classifications extend `REQUIRED_GATES` (court-owned), not this schema.

---

## 15. `lucidota-receipt/1` envelope as the evidence-receipt contract

No second envelope is invented (constraint a). The evidence receipt **is** a `lucidota-receipt/1` envelope; this section pins its use as the batch-compile receipt transport.

| Envelope field | Contract value / constraint |
|---|---|
| `env` | `"lucidota-receipt/1"` — verifiers reject anything else |
| `ts` | RFC3339 UTC sealing time (opaque string) |
| `actor` | sealing authority identity (human, service, device) |
| `claim_id` | the batch-compile claim this receipt speaks about (e.g. `run_id:task_id:attempt_n` or `artifact_id`) |
| `status` | `claimed | established | authorized` — RCPT-009 definitions verbatim (§0.5) |
| `payload` | the bespoke record (any of §§1–14, 16 record kinds by content); integers i64 only (§0.2) |
| `payload_hash` | sha256 over canonical payload |
| `prev_hash` | previous envelope's `seal`, or `"GENESIS"` |
| `sig` | `"HS256:<hex>"` authority signature over canonical envelope minus `seal`/`sig`; missing/malformed/invalid → reject, fail closed, no legacy path |
| `seal` | sha256 over canonical envelope minus `seal` but **over `sig`** — binds the signature into the chain |

**Symbols:** `envelope.wrap(actor, claim_id, status, payload, prev_hash=GENESIS, ts)` · `envelope.verify(env)` (raises `EnvelopeError`) · `envelope.verify_chain(envs, start_prev=GENESIS)` — `~/workspace/compute/envelope.py`, mirrored in `~/workspace/proof-ledger/rs/src/envelope.rs` (16 unit tests; cross-language interop both directions green).
**Usage rules in batch-compile:**
- Every attempt close (§6), every validation (§10), every merge (§13), and the final run summary (§16) emits an evidence receipt.
- Receipt `status` semantics: `claimed` = attempt opened, terminal observation absent; `established` = terminal observation present and chain verifies — a failed guest is still an `established` receipt (RCPT-009); `authorized` = endorsed by the sealing authority (endorsement axis).
- `claim_id` anti-transplant: a receipt sealed for claim A is rejected when presented for claim B (cf. `checkClaimBinding`).
- Replay: a `seal` already seen is rejected (cf. 409 on replay).
- Pre-envelope records (if any) are reported honestly as uncovered, never backfilled (cf. `envelope_coverage()`).
**Compatibility:** the envelope is versioned independently (`lucidota-receipt/1`); batch-compile schemas ride inside `payload`. A future envelope major version requires a batch-compile schema bump.

---

## 16. `lucidota-sched/1#final-run-summary` — Final run summary

The terminal accounting of a run. Emitted once, sealed as an evidence receipt (§15).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#final-run-summary"` |
| `run_id` | string | yes | the run |
| `outcome` | string | yes | `complete | aborted` |
| `task_counts` | object | yes | `{queued: i64, dispatched: i64, executing: i64, completed: i64, failed: i64, expired: i64, blocked: i64}` — must sum to the run's task total |
| `attempt_counts` | object | yes | per-outcome counts over the 5 worker outcomes |
| `artifact_counts` | object | yes | `{produced: i64, validated: i64, rejected: i64}` |
| `acceptance` | object | yes | `{established: i64, not_established: i64, disproven: i64, unknown: i64}` — court verdict tallies |
| `quota_consumed` | object[] | yes | per-pool `{pool_id, units: i64, limit: i64, limit_provenance}` — accounting from measured consumption, never worker assertion (W6 precedent: worker cost assertions ignored) |
| `evidence_head_seals` | string[] | yes | seals of the receipt-chain heads (run, acceptance decisions, merges) — the final proof |
| `policy_snapshot` | string | yes | must equal the run's `policy_snapshot` |
| `ts` | string (RFC3339 UTC) | yes | |

**Validation rules:** counts must reconcile with the underlying records (recomputed by the validator, not trusted from any summary the run produced); `quota_consumed` written from measured cost, never from worker assertions; the summary is sealed in a `lucidota-receipt/1` envelope with `status=established` (terminal observation present) — or `authorized` after authority endorsement.
**State transitions:** none (terminal record; corrections are new summaries with `supersedes`, referencing the old `run_id`).
**Compatibility:** additive; `outcome` vocabulary frozen.

---

## Appendix A — Schema inventory (acceptance check)

| # | Contract | Schema id | Section |
|---|---|---|---|
| 1 | execution run | `lucidota-sched/1#execution-run` | §1 |
| 2 | task manifest | `lucidota-sched/1#task-manifest` | §2 |
| 3 | task dependency | `lucidota-sched/1#task-dependency` | §3 |
| 4 | model/provider profile | `lucidota-sched/1#model-provider-profile` | §4 |
| 5 | quota pool + reservation | `lucidota-sched/1#quota-pool`, `lucidota-sched/1#quota-reservation` | §5 |
| 6 | attempt record | `lucidota-sched/1#attempt-record` | §6 |
| 7 | worker request envelope | `lucidota-sched/1#worker-request-envelope` | §7 |
| 8 | worker response envelope | `lucidota-sched/1#worker-response-envelope` | §8 |
| 9 | artifact manifest | `lucidota-sched/1#artifact-manifest` | §9 |
| 10 | validation result | `lucidota-sched/1#validation-result` | §10 |
| 11 | retry/dead-letter record | `lucidota-sched/1#retry-record` | §11 |
| 12 | integration result | `lucidota-sched/1#integration-result` | §12 |
| 13 | patch/merge request | `lucidota-sched/1#patch-merge-request` | §13 |
| 14 | acceptance decision | `lucidota-sched/1#acceptance-decision` | §14 |
| 15 | evidence receipt | `lucidota-receipt/1` envelope (reused, §0.7) | §15 |
| 16 | final run summary | `lucidota-sched/1#final-run-summary` | §16 |

Note: the task lists 15 contract types but names 16 (quota pool + reservation counts as one section with two record kinds). All 16 named contracts are specified; nothing was dropped.

## Appendix B — Vocabulary provenance (measured facts only)

| Vocabulary | Source | Measured state |
|---|---|---|
| `claimed|established|authorized` (+RCPT-009 defs) | `compute/envelope.py:34`; RECEIPT-ENVELOPE.md | EXISTING AND VERIFIED (claimed/established); `authorized` EXISTING BUT UNVERIFIED (no call site) |
| `ESTABLISHED|NOT_ESTABLISHED|DISPROVEN|UNKNOWN` | `compute/court.py:33` | EXISTING AND VERIFIED |
| queue states + defer-cap-8 + zombie sweep | `compute/queue.py:35-36`; worker.js:1035,1188,1244,2814–2822 | EXISTING AND VERIFIED |
| worker outcomes (5) | worker.js:153–158 WORKER_OUTCOMES | EXISTING AND VERIFIED |
| failure taxonomy (8) | worker.js:24,745 | EXISTING AND VERIFIED |
| governor reason codes (11) | `compute/governor.py` REASON_CODES | EXISTING AND VERIFIED |
| dev-graph node types (18) + edge vocabulary (9) | `~/workspace/dev-graph/SCHEMA.md` | EXISTING AND VERIFIED |
| envelope symbols wrap/verify/verify_chain | `compute/envelope.py`; `proof-ledger/rs/src/envelope.rs` | EXISTING AND VERIFIED (16/16 Rust tests; cross-impl both directions) |
| court Claim fields | `compute/court.py:61` | EXISTING AND VERIFIED |
| i64 pin / XIMPL-2 | RECEIPT-ENVELOPE.md (XIMPL-2, MEDIUM, OPEN) | EXISTING BUT UNVERIFIED (open divergence; i64 is the convention) |
| quota numbers (Gemini 10 RPM [M], NVIDIA 39 RPM policy, 5000-call UNVERIFIED_ESTIMATE) | f8 evidence | measured where tagged [M]; estimate/declared never promoted |
| Cap'n Maps | f6-12 | UNKNOWN — no schema, no role (term exists only in mission docs) |

## Appendix C — Provider use

Direct drafting (no provider generation or critique). All vocabularies and symbols were copied verbatim from the mission and evidence files read in this session (MISSION-2-SYNTHESIS.md §4; evidence f1–f8); per TOOLS.md, the direct path is recorded here in place of a provider-generation receipt.

---

## Appendix D — Schema delta §§17–21: minimal architecture (owner directives 2026-10-09)

Governing frame: the architecture is MINIMAL — Prompts → Typed work order → Partitioner → Allocator → Workers → Ledger → fixed retry rules → repeat.
CUT: semantic-judge LLM, validator hierarchies, LLM-debates-LLM, autonomous objective reinterpretation.
KEEP as deterministic ops: Compare / Calculate / Compare-against-policy, Route / Track / Stop.
These sections append to §§0–16 + Appendices A–C; nothing prior is modified or renumbered.

### Provider use — schema delta (this extension)

- GENERATE: NVIDIA NIM, `moonshotai/kimi-k3`, temperature 0.2, max 3000 tokens, ≥15s pacing between calls. First model id (`nvidia/llama-3.3-nemotron-super-49b-v1.5`) returned HTTP 410 Gone; a later call read-timed-out and succeeded on one retry.
- CRITIQUE: Gemini direct attempted via `~/workspace/compute/adapters/gemini.py` (`gemini-3.8-flash`) → HTTP 429 `rate_limited`; per the hard-stop doctrine no further requests were made to that provider in this task. The adversarial critique was applied directly by the integrator against the hard rules instead (findings F1–F6 below, all applied before writing).
- INTEGRATE: direct. Provider output was treated as draft material only; the typed-work-order section (§18) was written to the owner's verbatim work-order input spec rather than taken from generation.

### Self-critique findings (applied before writing)

- F1 (§18): removed a reference to an undefined "run's registered registry" — subdivision now requires explicit declaration in the work order's own manifest; an undeclared `goal_type` (or absent manifest) means subdivision is NOT permitted (fail closed).
- F2 (§19): the draft matched rules against a `unit_type` vocabulary that the work-order spec no longer defines; rules now match on registered `goal_type` from the work-order manifest.
- F3 (§19): predicate operator `in` requires an array value — validation rule added.
- F4 (§21): the draft's T2 group min-length-2 contradicted the structural partitioning rule (a single item with an `enables` edge MUST go to Tier 2); `item_ids` is now ≥1, with single-item Tier-2 assignment valid only when the item carries an `enables`-dependency.
- F5 (§21): Tier-3 `rule_text` pinned to the work order's `development_rules` (basic dev rules, verbatim).
- F6 (§20): clarified that court verdicts (§14) remain the acceptance authority; the check-result replaces only the layered validator/judge machinery.

## 17. `lucidota-sched/1#prompt-record` — Prompts registry: reusable versioned content-addressed instruction sets

The single registry record for prompts used to author work orders and execute units. Content is immutable: corrections are new records linked via `revision_of`; identity is derived from canonical content hash, never from name or version. Prompts are developer-defined/supplied — the scheduler distributes them, never authors or judges them (cf. §21).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#prompt-record"` |
| `prompt_id` | string | yes | `"prm-" + sha256(canonical content)[0:12]`; unique |
| `name` | string | yes | non-empty, ≤ 128 chars |
| `version` | i64 | yes | ≥ 1 |
| `content_sha256` | string | yes | 64 lowercase hex; sha256 of canonical content |
| `role` | string | yes | closed, exact-case: `work-order-author | unit-executor | partitioner-rule | glue-integration | retry-dispatcher` |
| `inputs_spec` | object | yes | declared input fields; unknown keys rejected |
| `max_input_bytes` | i64 | yes | > 0 |
| `revision_of` | string | no | `prompt_id` of superseded record; must exist in registry |
| `state` | string | yes | closed, exact-case: `draft | frozen | retired` |
| `policy_snapshot` | string | yes | 64 lowercase hex; sha256 pinning the policy the prompt was authored under |

**State transitions:** `draft → frozen`; `frozen → retired`. `draft → retired` directly is forbidden; frozen content is immutable.
**Validation rules:** `prompt_id` must equal `"prm-" + sha256(canonical content)[0:12]`; `content_sha256` must match stored content; `revision_of` must reference an existing record in state `frozen` or `retired`; unknown fields rejected; no floats or arbitrary-precision values (§0.2).
**Compatibility:** additive-only — new optional fields may be added; existing fields, enums, and constraints never change or are removed.

## 18. `lucidota-sched/1#typed-work-order` — Typed work order (wraps the plain-text work order)

**The work order defines the requested work; the scheduler defines its allocation and execution.**

A work order is a plain-text prompt containing:

```
Objective: <what is wanted>
Development rules: <e.g. preserve existing work; reuse existing stack; keep deterministic logic deterministic; do not exceed assigned resource limits>
Goals:
1. ...
2. ...
3. ...
```
(individually numbered). It may be written directly by a human or generated by any LLM — both equally valid; **no special authoring pipeline is required**.

The typed record WRAPS this plain-text-plus-manifest shape: it carries the objective, development rules, and numbered goals **VERBATIM** (no normalization, no rewriting), plus an optional simple accompanying manifest for dependencies/metadata (inline or attached).

A work order is an **organelle**: typed, given traits, works as a function (Zack's thesis articulation, Oct 9 2026). Types and traits come off the GO-50/D-25/C-25 graph — the ontological and epistemological guide; organelles compose fractally, each level keeping the same simple interface.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#typed-work-order"` |
| `work_order_id` | string | yes | `"wo-" + 12 lowercase hex`; unique |
| `run_id` | string | yes | binds record to run |
| `author` | string | yes | human identity string OR `prompt_id` from the prompts registry |
| `objective` | string | yes | ≤ 4096 chars; VERBATIM from the work order |
| `development_rules` | string | yes | ≤ 4096 chars; VERBATIM from the work order |
| `goals` | object[] | yes | ≥ 1; each goal VERBATIM |
| `goals[].goal_n` | i64 | yes | 1-based, exactly the numbering in the work-order text; strictly increasing from 1, no gaps |
| `goals[].goal_type` | string | yes | registered goal type (resolves in `manifest.goal_type_registry`) |
| `goals[].traits` | string[] | no | declared traits off the GO-50/D-25/C-25 graph (never inferred by the scheduler); type+traits = the organelle's interface |
| `goals[].goal_text` | string | yes | ≤ 4096 chars; VERBATIM from the work order |
| `raw_text` | string | no | the complete work order as written (full plain text) |
| `raw_text_sha256` | string | no | required iff `raw_text` present; 64 lowercase hex |
| `manifest` | object | no | optional simple manifest: `{dependencies, metadata, goal_type_registry, attachments}` |
| `manifest.dependencies` | object[] | no | `{from_goal_n: i64, to_goal_n: i64, edge}`; `edge` closed enum `part_of | informs | enables | tests | demos | targets | mitigates | decides | scheduled_for` (reuse only, §0.5) |
| `manifest.metadata` | object | no | free-form metadata (never trusted as evidence) |
| `manifest.goal_type_registry` | object[] | no | `{goal_type: string, subdivision_permitted: bool}` — the registered goal types for this order |
| `manifest.attachments` | string[] | no | content hashes (64 lowercase hex) of attached manifests |
| `state` | string | yes | closed, exact-case: `draft | sealed | partitioned | complete | aborted` |
| `prompt_id` | string | no | prompts-registry record (role `work-order-author`), required iff the order was generated by an LLM through the registry; human-authored orders may omit it |

**State transitions:** `draft → sealed → partitioned → complete`; `draft | sealed | partitioned → aborted`. Sealing freezes `objective`, `development_rules`, `goals`, and `manifest`.
**Validation rules:**
- VERBATIM: `objective`, `development_rules`, and each `goal_text` are carried as written — no normalization, no rewriting. When `raw_text` is present, the sections must match it.
- Each numbered goal is the DEFAULT unit of work (atomic partition boundary): the Partitioner emits ≥ 1 task manifest per goal and NEVER merges two goals into one unit.
- The Partitioner may split a goal ONLY when its registered goal type explicitly permits subdivision: the goal's `goal_type` must appear in `manifest.goal_type_registry` with `subdivision_permitted=true`. A goal whose type is absent from the registry — or a work order with no manifest — is atomic (fail closed).
- Dependencies and metadata may be inline or in the manifest (attached manifests bound by content hash); `enables` edges between goals constrain unit scheduling (same semantics as §3).
- A bad objective faithfully executed is a work-order defect, never a license to reinterpret: NO objective-reinterpretation fields; no judgment fields (§0.6 anti-self-acceptance).
- Traits are declared (on the goal or in the manifest), never inferred by the Partitioner or scheduler.
**Compatibility:** additive-only.

## 19. `lucidota-sched/1#partitioner-rules` — Explicit typed-unit partition rules

Explicit rules the deterministic Partitioner executes mechanically. Rules are data, not judgment: predicates are structured field/operator/value comparisons over unit fields only — no free-text predicates, no severity, no scoring.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#partitioner-rules"` |
| `ruleset_id` | string | yes | `"prl-" + 12 lowercase hex`; unique |
| `prompt_id` | string | yes | prompts-registry binding; role must be `partitioner-rule` |
| `rules` | object[] | yes | ≥ 1; see rule fields below |
| `rules[].rule_id` | string | yes | unique within ruleset |
| `rules[].goal_type` | string | yes | must resolve in the target work order's `manifest.goal_type_registry` (registered goal type); the unit carries `{work_order_id, goal_n, goal_type}` provenance |
| `rules[].predicate` | object | yes | structured `{field, operator, value}` comparisons over unit fields only; `operator` closed enum `eq | neq | lt | lte | gt | gte | in | contains`; no free-text |
| `rules[].max_units_per_manifest` | i64 | yes | ≥ 1 |
| `rules[].split_on` | string | yes | field name of the unit record |
| `rules[].group_by` | string | no | field name of the unit record |
| `deterministic` | bool | yes | must be `true`; validator rejects `false` |
| `version` | i64 | yes | ≥ 1 |

**State transitions:** none — rulesets are immutable once written; corrections are new `ruleset_id`s with incremented `version`.
**Validation rules:** `predicate.field`, `split_on`, `group_by` must name declared unit fields; `predicate.value` type must match the referenced field type (i64 comparisons only for integers; operator `in` requires an array value); `deterministic=false` rejected; `prompt_id` must resolve to a frozen prompt-record with role `partitioner-rule`; unknown fields rejected; no floats or arbitrary-precision values (§0.2). Goal subdivision is governed by the work order's `goal_type_registry` (§18): the Partitioner may apply a split rule to a goal ONLY when that goal's registered type declares `subdivision_permitted=true` — the numbered goal is otherwise the atomic partition boundary.
**Compatibility:** additive-only — new optional fields and new predicate operators may be added; existing fields, enums, and constraints never change or are removed.

## 20. `lucidota-sched/1#check-result` — Deterministic check result

The SINGLE deterministic check record of the minimal architecture. It collapses any layered validation hierarchy — semantic-judge LLM, validator hierarchies, LLM-debates-LLM are CUT (owner directive): one check = one record. Court verdicts (§14) remain the acceptance authority; this record replaces only the layered validator/judge machinery, and a check never declares acceptance.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#check-result"` |
| `check_id` | string | yes | `"chk-" + 12 lowercase hex`; unique per run |
| `run_id` | string | yes | binds the check to its run |
| `task_id` / `attempt_id` | string | yes | task (stable) + attempt (unique) under check |
| `op` | string | yes | closed, exact-case: `Compare | Calculate | Compare-against-policy` |
| `operands_ref` | string[] | yes | ≥ 1; content hashes of the measured values being compared/calculated — measurements, never claims |
| `policy_ref` | string | no | required iff `op=Compare-against-policy`: sha256 of the policy artifact version compared against; MUST be absent for other ops |
| `outcome` | string | yes | closed, exact-case: `pass | fail` |
| `evidence` | string[] | yes | ≥ 1; receipt seals or content hashes of the measurements; bare booleans rejected |
| `wall_time_ms` | i64 | yes | ≥ 0; measured by the runtime, never self-reported by the worker |
| `ts` | string (RFC3339 UTC) | yes | when the check ran |

**State transitions:** none — immutable once written; it is an outcome artifact, not a lifecycle object.
**Validation rules:** unknown fields rejected; `policy_ref` present with `op ≠ Compare-against-policy` → reject, and `op=Compare-against-policy` without `policy_ref` → reject; a failed op execution yields outcome `fail` — there is no judgment, verdict, or acceptance field (acceptance is a separate court record, §14); `operands_ref` hashes are recomputed by the checker from measurements — worker-supplied values are never trusted as operands; `evidence` entries must be seals/hashes; all integer fields i64 (§0.2).
**Compatibility:** additive-only — new optional fields may be added; existing fields, enums, and constraints frozen.

### §20 ADDENDUM — batch-1 concrete check-result profile (ADDITIVE)

Added 2026-10-09 (conformance lane, wave 4). Purely additive: the §20 base
table above is UNCHANGED. Where this profile differs, the §13 pinned batch
layout (`12-implementation-backlog.md` §13 "Pinned interface") is normative
for the batch, and the lane-4 module codes to it.

1. **Op vocabulary.** The batch profile uses the 9-op closed, exact-case,
   lowercase vocabulary pinned in §13:
   `compare | compare-policy | calculate | route | track | stop |
   t3-completion | t2-consistency | t1-coherence`.
   (The §20 base table pins `Compare | Calculate | Compare-against-policy`;
   the batch vocabulary is recorded here additively, not substituted into the
   table.) Coded reference: `compute/pipeline/checks.py:54-64` (`OPS`).
2. **Tri-state outcome.** The batch profile serializes the outcome as field
   `pass` with tri-state values `True | False | None` (pass | fail | unknown),
   and carries seals/hashes in field `evidence_refs`.
   (The §20 base table uses field `outcome: pass | fail` and field `evidence`.)
   `unknown` (None) is required by INV-02: unmeasurable → unknown, never
   inferred-pass; `pass=True` still requires ≥ 1 evidence ref; bare booleans
   remain rejected evidence. The tri-state extends — never narrows — the
   base `pass | fail` semantics. Coded reference:
   `compute/pipeline/checks.py:99-165` (`CheckResult`), `to_dict`
   `compute/pipeline/checks.py:136-145`.
3. Base §20 semantics are otherwise unchanged: court verdicts (§14) remain
   the acceptance authority; a check never declares acceptance; unknown fields
   are rejected.

## 21. `lucidota-sched/1#worker-assignment-envelope` — Tier-scoped worker assignment envelope

Tier-scoped assignment extending the fixed worker request envelope (§7). Tiers encode **context/responsibility scope only** — never model capability. Inverted numbering: **Tier 1 is the TOP**. N=3, fixed; no fourth tier.

Tier vocabulary (owner spec):
- **Tier 3 — single-check worker:** basic dev rules + ONE checklist item + specific inputs/context + defined output + completion condition. Performs ONLY if performable with supplied context alone.
- **Tier 2 — check-group worker:** basic rules + GROUP of related items + relevant Tier 3 results + shared context + group output + completion condition. Related/dependent checks stay at Tier 2.
- **Tier 1 — full-context developer:** complete rules + entire checklist + objective + specs/constraints + Tier 2 results + evidence.

Prompts are developer-defined/supplied; the scheduler DISTRIBUTES them, never authors or judges them.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema` | string | yes | `"lucidota-sched/1#worker-assignment-envelope"` |
| `assignment_id` | string | yes | `"was-" + 12 lowercase hex`; unique per run |
| `run_id` | string | yes | scope |
| `task_id` / `attempt_id` | string | yes | task (stable) + attempt (unique) this assignment covers |
| `tier` | i64 | yes | closed enum: `{1, 2, 3}`; nothing else permitted |
| `envelope_id` | string | yes | references the worker-request-envelope (§7) this assignment targets |
| `context_scope` | object | yes | tier-dependent required content (below); a field NOT in this tier's scope is rejected — over-contextualization is a violation |
| `context_scope.item_id` | string | tier=3 | exactly ONE checklist item |
| `context_scope.rule_text` | string | tier=3 | the basic dev rules applying to this item — from the work order's `development_rules`, verbatim |
| `context_scope.inputs` | string | tier=3 | specific inputs/context for the item |
| `context_scope.expected_output` | string | tier=3 | defined output for the single item |
| `context_scope.item_ids` | string[] | tier=2 | ≥ 1; the group of related checklist items. A single-item group is valid ONLY when that item carries an `enables`-dependency (dependent checks stay at Tier 2, never Tier 3) |
| `context_scope.tier3_result_refs` | string[] | tier=2 | check-result `check_id`s feeding this group |
| `context_scope.shared_context` | string | tier=2 | context shared across the group |
| `context_scope.full_checklist` | string[] | tier=1 | the entire checklist |
| `context_scope.objective` | string | tier=1 | the overall objective |
| `context_scope.specs_ref` | string | tier=1 | content hash of the specs |
| `context_scope.constraints_ref` | string | tier=1 | content hash of the constraints |
| `context_scope.tier2_result_refs` | string[] | tier=1 | check-result `check_id`s from the Tier-2 groups |
| `context_scope.evidence_refs` | string[] | tier=1 | evidence seals/hashes bound to the assignment |
| `completion_condition` | string | yes | ≤ 512 chars; tier=3: the single check resolves to a check-result with outcome `pass | fail` + evidence pointer; tier=2: every member item consumed + group output produced; tier=1: checklist exhausted + evidence bound |

**State transitions:** `assigned → dispatched → reported → closed`. Forward-only, no skipping, no re-entry; `closed` terminal.
**Validation rules:**
- Unknown fields rejected; a `context_scope` field outside the tier's scope is rejected (over-contextualization is a violation).
- STRUCTURAL PARTITIONING (schema-level): tier=3 is permitted ONLY when the assigned item has no `enables`-dependency on another item in the same assignment graph; items with `enables` edges MUST be assigned at tier ≥ 2 (related/dependent checks stay at Tier 2).
- `tier ∉ {1,2,3}` rejected — there is no fourth tier.
- The envelope carries assignment and scope only: no acceptance, verdict, authority, policy, budget, tool-authorization, or self-evaluation fields (§0.6).
- Integers i64 only, no floats (§0.2).
**Compatibility:** additive-only — tier semantics, scope shapes, and the scope-partitioning rule are frozen.

### Appendix D — Schema inventory (delta acceptance check)

| # | Contract | Schema id | Section |
|---|---|---|---|
| 17 | prompts registry / prompt record | `lucidota-sched/1#prompt-record` | §17 |
| 18 | typed work order | `lucidota-sched/1#typed-work-order` | §18 |
| 19 | partitioner rules | `lucidota-sched/1#partitioner-rules` | §19 |
| 20 | deterministic check result | `lucidota-sched/1#check-result` | §20 |
| 21 | tier-scoped worker assignment envelope | `lucidota-sched/1#worker-assignment-envelope` | §21 |
