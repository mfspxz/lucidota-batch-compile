# F1 — CANON Authority Hierarchy + Governor Enforcement (Forensic Inventory)

**Investigator:** subagent 7ee2a0c7 (read-only pass) · **Date:** 2026-10-09 11:38 PDT
**Method:** source read + test-symbol extraction; no code executed, nothing modified.
Ledger context consulted via grep (CANON-* claim families, CANON-FREEZE, CANON-INDEPENDENT-VERIFIER entries exist; no details copied).
**Provider use:** none — no NVIDIA NIM or other model calls used in this pass. All findings from direct source reads.

## 0. Component map (what exists)

| # | Component | Path | Role |
|---|-----------|------|------|
| 1 | CANON (Rust crate) | `~/workspace/canon/` | Normative authority: hash-chained constitution/contracts/decisions/supersessions stores, read-only library API, deployment identity, context receipts |
| 2 | Compute Governor (Python) | `~/workspace/compute/governor.py` | Allocation authority for the LUCIDOTA Compute Exchange: decides which compute source gets a task |
| 3 | Dispatch-Gate Governor (Python) | `~/workspace/governor/governor.py` + `dispatch-gate.py` | Dev-freeze admission control: ALLOW/DENY on proposed work, ledger-backed |
| 4 | Governor/Authority MCP server | `~/workspace/mcp-servers/governor/server.py` | Authority boundary for workers: checks authority, never holds it |
| 5 | Indy_Reads Governor (Rust) | `~/workspace/indy-reads/src/governor.rs` | Product-level: deterministic authority over AI proposals, replies, provider decisions, state transitions |
| 6 | cost-governor (Rust crate) | `~/workspace/lanectl/crates/cost-governor` | **Not examined in this pass** (path discovered, not read) |

## 1. CANON — normative authority (`~/workspace/canon/`)

### 1.1 Authority hierarchy as implemented

From `src/context.rs` `build()` — the AUTHORITY section of every context receipt:

- **CANON** = normative architecture ("what we are required to do")
- **PL** = evidence/proof ("what has been demonstrated")
- **GIT** = source history ("what source exists")
- **AI** = proposal/reasoning only ("what should we do next")

This is not prose-only: `src/api.rs` `Canon::open()` fails closed on any chain corruption (no partial view), and `invariants.rs` test `every_enforcement_point_resolves_to_real_file_line` mechanically ties each invariant's enforcement point to an existing `file:line`.

### 1.2 Stores and symbols

| Symbol | File | Signature | Behavior |
|--------|------|-----------|----------|
| `store::append` | `src/store.rs` | `pub fn append(kind: &str, e: Map<String, Value>) -> Result<(), StoreError>` | Exclusive file lock (`fs2`), chain link (`prev_hash`), fsync, duplicate-id rejection, schema-2 validation before write; all-or-nothing |
| `store::verify_chain` | `src/store.rs` | `pub fn verify_chain(kind: &str, entries: &[Map<String, Value>]) -> Result<usize, StoreError>` | Recomputes every hash; `prev_hash` mismatch or hash mismatch → `StoreError::Chain` (fatal) |
| `store::validate_new` | `src/store.rs` | `pub fn validate_new(kind: &str, e: &Map<String, Value>) -> Result<(), StoreError>` | Required-field allowlist; unknown field → `StoreError::Semantic` (exit 4); severity enum constrained to `advisory\|required\|non_negotiable` |
| `store::effective_status` | `src/store.rs` | `pub fn effective_status(id: &str, supersessions: &[Map<String, Value>], own_status: Option<&str>) -> &'static str` | SUPERSEDED wins over own status; superseded records never silently resurrect (C12) |
| `store::read_strict` | `src/store.rs` | `pub fn read_strict(kind: &str) -> Result<Vec<Map<String, Value>>, StoreError>` | Malformed line = fatal; missing file = empty store (not corruption) |
| `store::required_fields` / `allowed_fields` | `src/store.rs` | `pub fn required_fields(kind: &str) -> &'static [&'static str]` | Per-kind schema; unknown fields cannot smuggle semantics (e.g. a fake "verified" flag) |
| `Canon::open` | `src/api.rs` | `pub fn open() -> Result<Canon, StoreError>` | Verifies all 4 chains before returning; read-only API (no mutation surface; writes stay on CLI append path) |
| `Canon::invariants` | `src/api.rs` | `pub fn invariants(&self) -> Vec<&Map<String, Value>>` | ACTIVE schema-2 constitution records (the 12 INV-* invariants) |
| `Canon::normative_basis` | `src/api.rs` | `pub fn normative_basis(&self, keywords: &[&str]) -> Vec<String>` | Consumers (e.g. the court) cite the normative basis of enforced policy — invariant text stays authoritative in CANON |
| `context::build` | `src/context.rs` | `pub fn build(project: &str) -> Result<Receipt, StoreError>` | Deterministic receipt: same CANON + same git revision + same PL ledger = byte-identical; detects decision conflicts (V1) and PL FAILED dimensions (V2); never invents PL state (degrades to UNKNOWN if `pl` binary missing) |
| `deploy::issue_manifest` | `src/deploy.rs` | `pub fn issue_manifest(operator_name: &str, key: &SigningKey) -> Result<String, String>` | Binds deployment to frozen constitution: constitution commit + store heads + snapshot hash, ed25519-signed. Manifests stamped TEST-KEY; production custody is Zack-gated (per DEPLOYMENT-IDENTITY.md) |
| `deploy::verify_manifest` | `src/deploy.rs` | `pub fn verify_manifest(manifest_json: &str) -> VerifyReport` | Signature + head verification |

Store files (all at crate root): `constitution.jsonl` (24 records: 12 schema-1 seeds SUPERSEDED + 12 INV-* ACTIVE), `contracts.jsonl` (6 records: C-CLI-001, C-STORE-001, C-CONTEXT-001, C-SEARCH-001 ACTIVE + 2 legacy probe fixtures PL-C-OLD/PL-C-NEW — see §6 note), `decisions.jsonl` (D-CANON-002..006 schema-2 + D-CANON-001 superseded), `supersessions.jsonl` (14 records). Freeze state: §56 minimum FROZEN 2026-10-08 (`CANON-FREEZE-2026-10-08.md`), `invariants.json` projection (14,169 bytes, regenerated 2026-10-09 14:31).

### 1.3 The 12 frozen invariants (INV-01..INV-12)

Severity split: 8× `non_negotiable`, 4× `required` (INV-05, INV-07, INV-09, INV-10, INV-12 = required... measured: INV-01,02,03,04,06,08,11 = non_negotiable; INV-05,07,09,10,12 = required).

| ID | Statement | Enforcement point (as recorded in constitution) |
|----|-----------|-------------------------------------------------|
| INV-01 | AI agents cannot self-certify; an AI assertion cannot create PL VERIFIED | PL verify pipeline: only PL execution may emit VERIFIED; canon CLI has no command that writes a verification verdict |
| INV-02 | UNKNOWN is the default; missing evidence never becomes positive state through inference | `canon search` no-match prints explicit NO ACTIVE DECISION FOUND marker; receipt marks unavailable PL state as UNKNOWN |
| INV-03 | Evidence is not proof; evidence exists independently of verification | Schema allowlist: CANON records have no verification-verdict field; context receipt queries PL live instead of caching verdicts |
| INV-04 | Verification executes; VERIFIED requires execution of an authorized verification procedure | Context receipt surfaces PL FAILED dimensions as violations (V2); CANON never emits VERIFIED itself |
| INV-05 | Corruption is visible; malformed canonical state cannot silently disappear | `read_strict` fails on any malformed line; `verify_chain` fails on any hash/prev_hash mismatch |
| INV-06 | History is immutable | Append-only CLI surface (no update/delete command); duplicate-id rejection; fs2 exclusive lock serializes writers |
| INV-07 | Supersession is explicit | `canon supersede` requires both endpoint ids to exist plus a reason; `effective_status` surfaces SUPERSEDED |
| INV-08 | Source truth and runtime truth differ; a source artifact cannot prove runtime behavior | Receipt records git revision AND working_tree state AND live PL state as three separate fields |
| INV-09 | Deployment and implementation differ; compilation cannot prove deployment | Receipt PL STATE section separates implemented/deployed/proven per claim; no single "done" field exists in any schema |
| INV-10 | Shipped ≡ implemented VERIFIED ∧ deployed VERIFIED ∧ proven VERIFIED | CANON records the rule; PL computes `overall=shipped`; receipt REQUIRED NEXT ACTION names the blocking dimension |
| INV-11 | Deterministic core: truth determination MUST NOT depend on generative AI | Pure Rust, zero network, zero model calls; `context(A)==context(A)` testable; receipt carries `context_hash` |
| INV-12 | Authority is explicit: every authoritative record has an identifiable origin | Every record carries `actor` + `created_at` (UTC ISO); contracts validate constitution/decision refs on append |

### 1.4 Tests that enforce acceptance (file + symbol)

- `tests/hashchain.rs` → `#[test] fn hashchain_suite()` runs 12 cases: `t_canonical_encoding`, `t_prev_hash_linkage`, `t_corruption_detection`, `t_truncation_midfile`, `t_truncation_end_boundary` (asserts the exact boundary: chain alone cannot see a clean tail), `t_duplicate_detection`, `t_concurrent_append` (8 writers × 25 records, chain intact), `t_malformed_records`, `t_schema_validation`, `t_schema1_readable`, `t_receipt_determinism`, `t_cli_rejects_unknown_args`. **State: EXISTING AND VERIFIED.** Freeze doc records all green as of 2026-10-08.
- `tests/invariants.rs` → `invariants_have_all_seven_fields` (12 invariants, every §56 field non-empty — prose-only rules fail), `every_enforcement_point_resolves_to_real_file_line` (each cited enforcement point resolves to a real file:line; UNENFORCED entries must carry an explicit reason), `anchor_check_is_non_vacuous`, `no_completion_shortcut_fields_in_allowlist`. **State: EXISTING AND VERIFIED** (code + tests read; file mtime 2026-10-09 03:05 — newer than the freeze doc's green report, last-run state of this suite not separately confirmed in this read-only pass).
- `tests/verify_gaps.rs` → `spec_gap_v_battery` runs `v01_search_no_match`, `v02_pl_unavailable`, `v03_closed_command_set`, `v04_supersede_lifecycle` against the real CLI. **State: EXISTING AND VERIFIED** (same recency caveat as invariants.rs).
- `tests/deploy_identity.rs` → `deploy_identity_suite` (ephemeral test keys). **State: EXISTING AND VERIFIED** as code+test; production key custody is Zack-gated (goal_b4eaabcc3b4d) — deployment to production is UNKNOWN/blocked, not disproven.
- `src/api.rs` unit tests: `open_reads_default_dir`, `invariants_are_schema2_active` (asserts exactly 12), `normative_basis_finds_evidence_invariants`, `snapshot_shape`. **State: EXISTING AND VERIFIED.**

### 1.5 Policy implementation

Frozen §56 (2026-10-08): schema-2 field allowlists, no prose-only enforced rules, fail-closed append validation, read-only library API, TEST-KEY deployment manifests. INV-12 authority map references RFC-002 §32 (not separately read in this pass).

## 2. Compute Governor — allocation authority (`~/workspace/compute/governor.py`, 199 lines)

### 2.1 Hierarchy as implemented

`USER/SYSTEM POLICY -> GOVERNOR -> ROUTING ENGINE -> REGISTRY` (module docstring). Governing doctrine: **MUSE_PROPOSES_GOVERNOR_DISPOSES** — the proposer (Muse/operator) proposes computation; the Governor decides allocation. Proposer preference is advisory input, never a bypass.

### 2.2 Key symbols

| Symbol | Signature | Behavior |
|--------|-----------|----------|
| `govern` | `def govern(task: TaskFeatures, proposer="muse", preference=None, evaluation_time=None, _depth=0) -> dict` | THE entry point. Routes through `router.decide()` + `router.route()`; asserts govern/decide divergence never happens (`assert decision.chosen_source == receipt["selected_plan"]["source"]`). Builds mandatory delegation consideration (every candidate with a standard reason code). Detects proposer-eliminator laundering (RT-B5): if proposer extras forced a single feasible source, flags it. Preference recorded and overridden on evidence (test J). Returns decision + replay receipt + governance metadata |
| `MAX_GOVERN_DEPTH` | constant `= 3` | RT-C12 anti-loop guard: recursive orchestration bounded; exceeding depth yields `NO_FEASIBLE_SOURCE` with loop_guard=True |
| `_codify` | `def _codify(reason: str) -> str` | Maps free-text infeasibility to 11 standard `REASON_CODES`; **fail-closed on unrecognized reasons** (RT-B7: returns `UNMAPPED_REASON` instead of silently defaulting) |
| `audit` | `def audit() -> dict` | Section 34 self-audit: quota utilization, observation counts, under/over-delegation indicators (nvidia_underuse, muse_overuse, low_diversity). Indicators trigger review, not automatic action |

Reason codes (11): HARD_CONSTRAINT, BUDGET_EXCEEDED, INSUFFICIENT_CAPABILITY, LOW_EXPECTED_UTILITY, LATENCY_VIOLATION, AUTHORITY_VIOLATION, INSUFFICIENT_VERIFICATION, UNAVAILABLE, STRATEGIC_RESOURCE_RESERVED, NO_MEASURED_EVIDENCE, UNMAPPED_REASON.

### 2.3 Wiring (live call sites found by grep)

- `~/workspace/compute/queue.py:142` — `g = G.govern(to_features(rec), proposer="queue")`
- `~/workspace/compute/burn.py:503,556,639` — `gov = G.govern(Q.to_features(rec), proposer="burn-engine", ...)`
- Test doubles: `dispatch_tests.py:190` `_fake_govern` (fake provider for dispatch tests)

### 2.4 Tests that enforce acceptance

`~/workspace/compute/governor_tests.py` — 19 checks, all run against the real governor + real registry, zero NVIDIA spend (allocation decisions only). Named acceptance predicates: A `trivial->not-NVIDIA`, B `large-context->NVIDIA candidate`, C `unknown-cap->NVIDIA exploration`, D `high-value+low-util->NVIDIA strategic`, E `write-authority->agent`, F `NVIDIA-beats-cheaper`, G `second-opinion->cross_check`, H `impossible->NO_FEASIBLE_SOURCE`, I `failure->observation` (exercises the identity gate via `ledger.request_hash_for`), J `preference-overridden` (Muse preference suppressed → governor still chooses NVIDIA), K `replay-identical` + `time-independence` (decision-hash determinism), L `no-value->no-NVIDIA` (RT-B1), M `bare-characterizes-flag-ignored` (RT-B3), N `fake-campaign-ignored` (RT-B4), O `capability-change-changes-hash` (RT-A1: decision hash covers capability.json content), P `govern-emits-receipt` (RT-A3), Q `proposer-P0-capped` (RT-B2), R `eliminator-flagged` (RT-B5).
**State: EXISTING AND VERIFIED.**

## 3. Dispatch-Gate Governor — dev-freeze admission (`~/workspace/governor/`)

### 3.1 What it is

Built for INCIDENT-2026-10-09-DEV-FREEZE (`INCIDENT-2026-10-09-DEV-FREEZE.json` referenced; policy `dispatch-policy.json`: `freeze_active: true`, `active_remediation: ["F0","F4","F5","F6"]`, updated 2026-10-09T11:25-07:00 by main-agent). Purpose: mechanical enforcement of the failure inventory — denies timer crons (failures #18/#23), unauthorized scopes, docs-as-dev (#24), requires verification before "done", fail-closed on ledger-write failure.

### 3.2 Key symbols

| Symbol | File | Signature | Behavior |
|--------|------|-----------|----------|
| dispatch gate (script) | `dispatch-gate.py` | CLI: `--propose`, `--scope`, `--user-authorized`, `--auth-evidence`; exit 0=ALLOW, 1=DENY, 2=ERROR(treated as DENY) | `FROZEN_SCOPES` (12: product-dev, router, d1, adhkey, exchange, indie-vercel, drive-recovery, hypertimeline, redteam-wave, provider-expansion, geppetto-build, feature-dev) always denied; `AUTHORIZED_REMEDIATION_SCOPES` (F0–F6) allowed only if also in policy's `active_remediation`; `--user-authorized` without `--auth-evidence` → DENY; unknown scope → DENY; decision appended to `dispatch-log.jsonl` |
| `admit_action` | `governor.py` | `def admit_action(proposal, scope, user_authorized=False, auth_evidence=None) -> (allowed, receipt)` | Gate check → record decision (ALLOW and DENY) to proof ledger via `pl claim`; **ALLOW + ledger-write-failure → converted to DENY (fail-closed)** |
| `record_to_ledger` | `governor.py` | `def record_to_ledger(event_type, data) -> (success, message)` | Writes via `~/workspace/proof-ledger/rs/target/release/pl claim` with `governor-{uuid}` claim id |
| `verify_ledger` | `governor.py` | `def verify_ledger() -> (valid, message)` | Runs `pl audit`; returncode 0 = chain valid |
| `status` | `governor.py` | `def status() -> dict` | freeze state, active remediation, ledger validity, allow/deny counts from dispatch-log.jsonl |

### 3.3 Tests that enforce acceptance + measured state

`test-governor.py` — 12 tests: `test_timer_cron_denied` (failures #18/#23), `test_unknown_scope_denied` (fail-closed), `test_frozen_product_scopes_denied`, `test_remediation_allowed`, `test_inactive_remediation_denied`, `test_user_auth_requires_evidence`, `test_user_auth_with_evidence_allowed`, `test_governor_admit_denied_scope` (exit 1, action BLOCKED), `test_governor_admit_allowed_scope` (exit 0, ADMITTED, ledger_recorded=True), `test_ledger_chain_valid`, `test_dispatch_log_append_only`, `test_fail_closed_on_policy_error` (missing policy file → DENY; backup/restore around the test).
**State: EXISTING AND VERIFIED.** Measured evidence: `test-results.json` records **12/12 PASS** at 2026-10-09T18:27:50Z; `dispatch-log.jsonl` contains 41 ALLOW/DENY entries (both kinds present), latest entries 2026-10-09T18:27:49Z showing ALLOW(product-dev w/ user evidence), DENY(router), ALLOW(F6-regression-tests).

## 4. Governor/Authority MCP server (`~/workspace/mcp-servers/governor/server.py`)

Boundary doctrine (module docstring): **"This server CHECKS authority; it does not HOLD it."**
- The Exchange master key is NEVER accepted (role_claim `master`/`exchange_master`/`exchange_key` or a `master_key` param → REJECTED outright).
- Governor-only ops (`lease.issue`, `health.transition`) require a scoped credential whose sha256 matches `GOVERNOR_MCP_CREDENTIAL_SHA256`; the value is never stored/echoed/logged.
- Worker callers are self-declared `worker:<id>` → `DECLARED_NOT_VERIFIED`: sufficient to DENY governor ops (fail closed), never sufficient to GRANT.
- `gate.check` is explicitly ADVISORY/NON-ENFORCEMENT (policy oracle over 10 worker invariants + authority rules; receipts watermarked advisory; the tools remain the enforcement point). Authority resolved through `role_of()` (credential check), NEVER the caller-supplied actor string.
- Tools: `lease.inspect` (any role), `lease.issue` (GOVERNOR ONLY), `gate.check` (advisory), `health.transition` (GOVERNOR ONLY; worker signal is evidence, never authority), `authority.verify`.
**State: EXISTING BUT UNVERIFIED** — server code read; no test file found for this server in this pass (`DOGFOOD-REPORT.md` exists in the same dir, not evaluated).

## 5. Indy_Reads Governor (`~/workspace/indy-reads/src/governor.rs`, 1636 lines)

Product-level deterministic authority. HARD LAW: `LLM ≠ authority, database, policy engine, permission system, epistemic authority, source of truth`. Key public surface:
- `AiProposal::sanitize(mut self) -> (Self, Vec<String>)` — strips and records authority-bearing smuggled fields (`authority`, `verified`, `execute`, `claim_status`) the model tried to inject (line 70).
- `normalize_for_match`, `claims_authority`, `validate_reply`, `classify_intent`, `evaluate_utterance`, provider `select_provider` (line 733) / `consume_provider_decision` (890) / `record_provider_result` (970) / `record_state_transition` (1008), `reconstruct_chain`, `verify_chain_linkage` (receipt-chain integrity).
- WASM portability: compiles to wasm32-unknown-unknown; wasm facade includes this file via `#[path]` (single source of truth); wasm-unsafe dependency = intended fail-closed build break.
- Tests: `tests/governor_adversarial.rs` — 10 adversarial tests: `direct_provider_call_cannot_forge_governor_authorization`, `over_budget_probe_sweep_is_bounded_by_governor`, `unauthorized_state_transition_is_blocked_with_veto_receipt`, `replayed_state_transition_is_blocked`, `suppressed_refusal_yields_no_usable_provider`, `forged_approval_is_absent_from_the_governor_stream`, `replayed_decision_is_rejected_at_consumption`, `transplanted_decision_to_another_request_is_rejected`, `forged_decision_nonce_is_rejected`, `distinct_decisions_same_shape_both_consume`.
**State: EXISTING AND VERIFIED** (implementation + adversarial test symbols read; suite bodies not individually re-executed in this pass).

## 6. Notes and discrepancies (read-only; recorded, not fixed)

1. **D-CANON-001 effective status:** its `status` field reads `"active"` in `decisions.jsonl`, but `supersessions.jsonl` contains `D-CANON-001 -> D-CANON-002` ("§56 freeze: decision re-recorded..."). `effective_status()` therefore reports SUPERSEDED — consistent with the freeze doc's claim that D-CANON-001 is superseded. Callers that read the raw field instead of `effective_status()`/`Canon::status_of()` would see a stale "active". (Matches the C12 warning in `store.rs`.)
2. **Legacy probe fixtures still ACTIVE:** `contracts.jsonl` contains `PL-C-OLD` and `PL-C-NEW` (subject "probes") with `status: "active"` — the two legacy probe fixtures the freeze doc counts as 2 of 6 contracts. They are not errors, but they are non-production records in the active set.
3. **Authority claims in multiple crates:** CANON (normative), compute governor (allocation), dispatch-gate (admission), MCP server (authority checking), Indy_Reads (product authority) are five distinct authority surfaces with distinct scopes. No evidence in this pass of a second ledger or second scheduler being created — but the batch-compile spec should name which "governor" each boundary contract refers to.
4. **`~/workspace/lanectl/crates/cost-governor`** discovered but not examined (out of scope for this pass) — enforcement status UNKNOWN.
5. Production deployment of CANON (`deploy::issue_manifest` beyond TEST-KEY) is blocked pending Zackary's key-custody decision (goal_b4eaabcc3b4d) — UNKNOWN, not disproven.
6. The `tests/invariants.rs` and `tests/verify_gaps.rs` suites are newer (mtime 2026-10-09 03:05) than the freeze doc's green report (2026-10-08); their last-run pass state was not separately confirmed in this read-only pass (test sources + asserted invariants were read).

## 7. Summary of states

| Finding | State |
|---------|-------|
| CANON 4-store hash chain (store.rs) | EXISTING AND VERIFIED |
| CANON read-only library API (api.rs) | EXISTING AND VERIFIED |
| 12 INV-* invariants with enforcement points | EXISTING AND VERIFIED (each enforcement point mechanically resolved to file:line by `every_enforcement_point_resolves_to_real_file_line`) |
| CANON context receipts (context.rs) | EXISTING AND VERIFIED |
| CANON deployment identity (deploy.rs, TEST-KEY) | EXISTING AND VERIFIED (code+test); production custody UNKNOWN/blocked on Zackary |
| CANON authority hierarchy (CANON > PL > GIT > AI) | EXISTING AND VERIFIED (in receipt body + freeze doc + RFC-002) |
| Compute governor allocation (`compute/governor.py`) | EXISTING AND VERIFIED (19 checks A–R); wired into queue.py + burn.py |
| Dispatch-gate freeze governor (`~/workspace/governor/`) | EXISTING AND VERIFIED (12/12 PASS 2026-10-09T18:27:50Z; 41 live log entries) |
| MCP authority server (`mcp-servers/governor/server.py`) | EXISTING BUT UNVERIFIED (no test file found) |
| Indy_Reads governor (`indy-reads/src/governor.rs`) | EXISTING AND VERIFIED (10 adversarial tests) |
| lanectl cost-governor | UNKNOWN (not examined) |
