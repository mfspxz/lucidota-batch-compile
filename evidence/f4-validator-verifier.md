# F4 — Validator + Verifier + Acceptance Pipeline (forensic inventory)

**Mode:** read-only discovery. No code modified, no suites executed by this investigation.
**Standard:** EXISTING AND VERIFIED = code read + enforcing test found. No suite was re-run here;
last-run outcomes cited are from documents/verdict artifacts, not this investigator's execution.

## Architecture summary (as implemented)

Three distinct authorities, deliberately separated by import bans enforced in the verifier sources:

- **Governor** (`~/workspace/compute/governor.py`) — owns ALLOCATION. Entry point: `govern()`.
- **Verifier(s)** — own TRUTH. Independent from the court by construction (no `court` import for
  judgment, no `court.derive_status` / `court.request_completion_review` calls; `independent_verifier_tests.py`
  enforces this via AST inspection).
- **Ledger** — owns HISTORY. `~/workspace/compute/ledger.py` (compute ingest) and
  `~/workspace/proof-ledger/` (PL, Rust `pl` binary + Python bindings).

Doctrine banner in `governor.py` docstring: "MUSE IS A WORKER. THE GOVERNOR OWNS ALLOCATION.
THE VERIFIER OWNS TRUTH. THE LEDGER OWNS HISTORY."

---

## 1. Validator / acceptance authority: `court.py`

**Path:** `~/workspace/compute/court.py`
**State:** EXISTING AND VERIFIED (code read; enforcing tests found: `canon_court_e2e.py`, `court_identity_tests.py`)

### Key symbols + signatures
- `REQUIRED_GATES` (line 38) — dict mapping claim classification → required gates.
- `class Claim` (line 61) — claim record. Fields observed in use: `claim_id, subject, actor, version,
  scope, statement, classification, falsification_conditions`.
- `file_claim(claim: Claim) -> dict` (line 82)
- `derive_status(evidence: dict, claim_id: str) -> dict` (line 94) — THE acceptance function.
  Returns dict with keys observed in `canon_court_e2e.py`: `verdict` (ESTABLISHED | NOT_ESTABLISHED |
  UNKNOWN), `unbound` (gates with unbound evidence), `canon` (`heads`, `context_hash`), `derivation`, `note`.
  Rule observed: bound evidence → ESTABLISHED; forged bare-`True` evidence (no receipts) → UNKNOWN
  with gates listed in `unbound`.
- `_canon_basis() -> tuple` (line 208) — reads `canon snapshot` into the verdict (canon heads,
  context hash, normative basis evidence INV-01/02/03).
- `request_completion_review(claim_id: str, evidence: dict) -> dict` (line 368)
- `record_falsification(claim_id, attack_id, attacker, ...)` (line 383) — appends to
  `~/workspace/compute/falsification.jsonl` (the adversarial ledger the verifiers read).
- `falsifications(claim_id=None, ...)` (line 404)
- Module constants: `CLAIMS_PATH = CDIR/"claims.jsonl"` (line 27),
  `PL_LEDGER_PATH = /home/hatch/workspace/proof-ledger/ledger.jsonl` (line 31).

### Enforcing tests
- `~/workspace/compute/canon_court_e2e.py` — end-to-end canon→court wiring. 14 `check()` calls
  counted in the file (documents cite "13/13" — count discrepancy noted in Gaps).
  Cases: (1) PL-bound evidence → ESTABLISHED with snapshot canon heads in verdict;
  (2) forged bare-True evidence → UNKNOWN, gates in `unbound`; (3) tampered canon store →
  `canon snapshot` fails → `derive_status` fails closed to UNKNOWN with canon note.
  All cases run in sandboxes (canon store copies via `CANON_DIR`, temp claims.jsonl, temp PL ledger);
  real stores never touched. Also pins XIMPL-1 canonical form (`ensure_ascii=False`) against
  `integrity._canonical`.
- `~/workspace/compute/court_identity_tests.py` — referenced by `pl_canon_verifier._verify_finding_fixed`
  as the re-run target for the VERIFY-RED finding (cited as "22" tests in the verifier source).
  File exists; content not re-read here.

### Acceptance predicates enforced by `derive_status`
1. Every required gate (per `REQUIRED_GATES` for the claim's classification) must have evidence
   bound to a PL receipt (evidence dicts carry `receipt: {claim_id, evidence_hash}`).
2. Unbound/forgeable evidence → verdict UNKNOWN, never ESTABLISHED.
3. Canon state must verify (`canon snapshot` exit 0); corrupt canon → fail closed to UNKNOWN.
4. A worker never declares DONE — verdicts are ASSESSMENTS consumed by the driver/court.

---

## 2. Governor: `governor.py` (enforcement layer / validator at allocation time)

**Path:** `~/workspace/compute/governor.py`
**State:** EXISTING AND VERIFIED (code read; enforcing test suite found)

### Key symbols + signatures
- `MAX_GOVERN_DEPTH = 3` — RT-C12 anti-loop guard on recursive `govern()` re-entry.
- `REASON_CODES` (11 standard codes): HARD_CONSTRAINT, BUDGET_EXCEEDED, INSUFFICIENT_CAPABILITY,
  LOW_EXPECTED_UTILITY, LATENCY_VIOLATION, AUTHORITY_VIOLATION, INSUFFICIENT_VERIFICATION,
  UNAVAILABLE, STRATEGIC_RESOURCE_RESERVED, NO_MEASURED_EVIDENCE, UNMAPPED_REASON.
- `_codify(reason: str) -> str` — maps free-text infeasibility to codes; RT-B7: unrecognized reasons
  fail closed to `UNMAPPED_REASON` (never silently defaults to LOW_EXPECTED_UTILITY).
- `govern(task: TaskFeatures, proposer: str = "muse", preference: str | None = None,
  evaluation_time: str | None = None, _depth: int = 0) -> dict`
  Returns `{decision: RoutingDecision, receipt, governance: {...}}`.
  - RT-A3: routes through `router.decide()`; every decision carries a replay receipt
    (decision hash, policy hash, capability hash, quota snapshot, evaluation time).
  - Enforces govern/decide divergence assertion: `decision.chosen_source ==
    receipt["selected_plan"]["source"]` else raises (nondeterminism tripwire).
  - Every infeasible candidate carries a `_codify`ed reason code.
  - RT-B5 proposer-eliminator detection: `required_capabilities` / `characterizes_source` /
    `needs_write` extras forcing a single feasible source are flagged
    (`proposer_single_source: True`, `eliminators` list).
  - Proposer preference is advisory only: `preference_outcome` ∈ {none, aligned, overridden}.
  - Policy constant: `"MUSE_PROPOSES_GOVERNOR_DISPOSES"`.
- `audit() -> dict` — Section 34 self-audit; returns quota utilization, observation counts,
  per-source share, and INDICATORS (not verdicts): `nvidia_underuse`, `muse_overuse`, `low_diversity`.
  "Indicators trigger review, not automatic action."

### Enforcing tests
- `~/workspace/compute/governor_tests.py` — "The policy as executable proofs." 19 `check()` calls
  (A–R; K runs two checks). Tests A–H are the ordering-sensitive core re-used by
  `independent_verifier._check_contract`. Each test asserts an allocation predicate:
  - A trivial→not-NVIDIA · B large-context→NVIDIA candidate · C unknown-cap→NVIDIA exploration ·
    D high-value+low-util→NVIDIA strategic · E needs_write→local/lucidota-agent ·
    F NVIDIA-beats-cheaper · G second_opinion→cross_check strategy · H impossible→NO_FEASIBLE_SOURCE ·
    I failure→observation (via `router.verify_execution(ex, "exact", {"passed": False})` +
    `router.observe(d, ex, v, verified_value=0.0)`; asserts `obs["outcome"]=="failure"` and
    `obs["actual_success"]==0.0`) · J preference-overridden · K replay-identical (decision_hash
    equality) + time-independence · L–N RT-B1/B3/B4 flag-ignoring · O capability-change-changes-hash
    (decision hash covers capability.json content) · P govern-emits-receipt · Q proposer-P0-capped ·
    R eliminator-flagged.
  - Docstring states: no NVIDIA API calls spent (allocation decisions only).
  - NOTE: test O temporarily rewrites `/home/hatch/workspace/nvidia-usage/capability.json` and
    restores it — the suite is not strictly side-effect-free on disk (restores byte-identical).

---

## 3. Verifier A: `independent_verifier.py` (governor-claim verifier, 11 gates)

**Path:** `~/workspace/compute/independent_verifier.py` (446 lines)
**State:** EXISTING AND VERIFIED (code read; dedicated harness test suite found)

### Interface contract
- Input: none (reads `~/workspace/compute/` corpus: claims.jsonl, falsification.jsonl, test suites,
  executions.jsonl, bench_results.json, threat_tests.py, recovery_tests.py).
- `_gate_defs() -> list[dict]` — 11 gates, each `{gate, requirement, evidence_sources, check}`.
  Gate names (in order): contract, tests, adversarial, boundaries, independent, dogfood,
  benchmark, security, recovery, reproducible, evidence_complete.
- Each `check(ctx) -> (status, evidence, note)` with status ∈ {PASS, FAIL, UNKNOWN}.
- `run() -> dict` — re-runs 10 suites via subprocess, evaluates all gates, recomputes
  `evidence_complete` last. Verdict rule: all PASS → `ESTABLISHED`; any FAIL → `NOT_ESTABLISHED`;
  else `UNKNOWN`. Writes `~/workspace/compute/independent_verdict.json` on `__main__`.
- Independence invariants (docstring + enforced by tests): never imports `court` for judgment
  (only `record_falsification` for filing findings), never calls `court.derive_status` /
  `court.request_completion_review`, gate requirements formulated from constitution §6 +
  claim contract, evidence re-measured (suites re-run, not trusted from prior assertions).

### Per-gate executable checks (the acceptance predicates, mechanically)
| Gate | Check symbol | Predicate |
|---|---|---|
| contract | `_check_contract` | claims.jsonl record has statement, ≥2 falsification_conditions, contract.lexicographic_order ≥5, ordering implemented (governor_tests A–H) |
| tests | `_check_tests` | 8 suites (governor, registry, dispatch, integrity, strategies, errors, mediums, court_identity) all exit 0, zero failures, zero masked skips |
| adversarial | `_check_adversarial` | falsification.jsonl findings for claim: none OPEN with severity CRITICAL/HIGH/BLOCKING |
| boundaries | `_check_boundaries` | threat_tests.py (TM-1..TM-8) green |
| independent | `_check_independent` | external measurement present (nvidia-usage/capability.json cells, gemini-usage/) |
| dogfood | `_check_dogfood` | executions.jsonl has real governed execution records |
| benchmark | `_check_benchmark` | bench_results.json exists and is not stale (mtime ≥ router.py/governor.py/budget.py) |
| security | `_check_security` | threat suite green AND zero OPEN CRITICAL falsifications |
| recovery | `_check_recovery` | recovery_tests.py green AND real SIGKILL confirmed in output |
| reproducible | `_check_reproducible` | `router.decide` replay-identical: same inputs → same `decision_hash` |
| evidence_complete | `_check_evidence_complete` | every other gate cites ≥1 evidence pointer |

### Enforcing tests
- `~/workspace/compute/independent_verifier_tests.py` (116 lines) — tests the harness itself:
  11 gates present in constitution order with requirement/evidence-sources/check-fn; check-function
  contract on synthetic ctx (status ternary, evidence list, non-empty note); verdict rule truth table
  (all-pass→ESTABLISHED, one-fail→NOT_ESTABLISHED, unknown-only→UNKNOWN, fail-beats-unknown);
  independence invariants via AST (no `derive_status`/`request_completion_review`/`REQUIRED_GATES`
  usage; `court` imported only for `record_falsification` or not at all); verdict-file well-formedness
  (11 gates, assessment in {ESTABLISHED, NOT_ESTABLISHED, UNKNOWN, DISPROVEN}, summary adds to 11).
  Note: the DISPROVEN verdict value appears only in the test's allowed-values list; `run()` itself
  never emits it.

---

## 4. Verifier B: `pl_canon_verifier.py` (PL + canon verifier)

**Path:** `~/workspace/thesis-defense/verifiers/pl_canon_verifier.py` (759 lines)
**State:** EXISTING BUT UNVERIFIED (code read in full; no dedicated test file for the verifier itself
found — unlike Verifier A, there is no `pl_canon_verifier_tests.py`). Its per-gate checks are
executable and re-run real suites/probes, but nothing tests the harness's own contract.
Prior run artifacts exist: `pl_canon_verdict-2026-10-08T21-{15,32,36,38}Z.json` (4 files).

### Interface contract
- Input: none. Reads `~/workspace/compute`, `~/workspace/proof-ledger`, `~/workspace/canon`.
- `_pl_gate_defs()` — 10 PL gates (assessed vs GATE 4 BEHAVIORALLY PROVEN);
  `_canon_gate_defs()` — 7 canon gates (assessed vs GATE 3 DEPLOYED).
- `_assess(claim_id, gate_label, defs, ctx) -> dict`; `run() -> dict` with `claims: [proof-ledger, canon]`.
- `__main__` writes `thesis-defense/verifiers/pl_canon_verdict-<UTC ts>.json` (never touches existing verdicts).
- Independence rules identical to Verifier A (no `court` import at all; evidence re-measured;
  probes run on `/tmp` copies; production stores never mutated).
- Design spec: `~/workspace/thesis-defense/verifiers/GATE-MATRIX.md` (65 lines) — the gate matrix
  this file implements.

### PL gates → executable check
| Gate | Check | Predicate |
|---|---|---|
| envelope_contract | `_pl_contract` | RECEIPT-ENVELOPE.md pins canonical JSON (`ensure_ascii`, i64); `gen_envelope_vectors.py` regen byte-identical to checked-in `fixtures/envelope-vectors.json` |
| ingest_adoption | `_pl_ingest` | `compute/ledger.py` imports envelope + `verify_envelopes` + `request_hash_for`; `envelope_test.py` green (incl. `test_ledger_record_emits_envelope`) |
| signature_layer | `_pl_sig` | `envelope.verify` rejects missing-sig, attacker-key re-sign, tampered payload with `EnvelopeError` |
| freshness_replay | `_pl_freshness` | synthetic chained ledgers in /tmp via `pl audit --full`: verbatim duplicate → FAIL REPLAY; 48h-old observation → FAIL STALE |
| tamper_detection | `_pl_tamper` | production `ledger.verify_envelopes()` True; single-byte payload flip → `EnvelopeError` |
| cross_implementation | `_pl_ximpl` | `cargo test` green in `proof-ledger/rs`; `KNOWN_DIVERGENT` pins exactly `[("bigint","XIMPL-2")]` (by-design i64 contract) |
| adversarial | `_pl_adversarial` | PL-scoped falsification scan: no genuinely-open HIGH/CRITICAL; scans `rs/src` for `record_level_seal`/`seal_record` patterns (root-cause check for FABRICATE-1). Stale-open findings (defect verified fixed, closure pending) are reported, not blocking. |
| durability | `_pl_durability` | `envelope_test.py` green + `rs/tests/durability.rs` green (inside cargo test) |
| audit_gating | `_pl_audit` | `pl audit --full` on production `proof-ledger/ledger.jsonl` → exit 0 |
| evidence_complete | `_check_evidence_complete` | meta-check over gate results |

### Canon gates → executable check
| Gate | Check | Predicate |
|---|---|---|
| frozen_state | `_canon_frozen` | git commit `272ed80` present; `CANON-FREEZE-2026-10-08.md` present; 4 store files clean |
| chain_integrity | `_canon_audit` | `canon audit` re-run → "audit OK" |
| consumable_interface | `_canon_interface` | `src/api.rs` present; `canon snapshot` emits 4-heads JSON with context_hash; tampered COPY → exit 3 `AUDIT FAIL` |
| court_integration | `_canon_court` | `canon_court_e2e.py` green (sandboxed) |
| deployment_identity | `_canon_deploy` | **STALE vs matrix** — code searches for Dockerfile/deploy*/.github only; returns FAIL "no deployment identity beyond the local build". Does NOT exercise the wave-10 deploy-identity machinery (see Gaps). |
| adversarial | `_canon_adversarial` | falsification ledger scan for OPEN canon HIGH/CRITICAL (excluding ximpl/envelope/fabricate/twotier false positives); proof-bundle matrix canon section D-CANON-005 fixed |
| evidence_complete | `_check_evidence_complete` | meta-check |

### Honest known outcomes (from GATE-MATRIX.md, recorded not re-run)
- PL `adversarial` is expected FAIL while FABRICATE-1 (HIGH OPEN) stands: a direct file-write
  attacker can mint fully-VERIFIED claims; closure needs record-level authority sealing, blocked on
  the operator's key-custody decision (tracked: `goal_b4eaabcc3b4d`).
- CANON `deployment_identity` is PASS WITH CAVEAT per the matrix: machinery exists and is tested
  (ed25519-signed manifests, MATCH/MISMATCH/UNKNOWN), but every manifest is stamped
  `TEST-KEY — NOT FOR PRODUCTION`. Production identity is honestly absent until key custody lands.
- Anything requiring Cloudflare, the operator, or not-yet-built machinery → UNKNOWN/HONEST GAP.

---

## 5. Receipt envelope layer (the thing the PL verifier verifies)

### Python: `~/workspace/compute/envelope.py`
**State:** EXISTING AND VERIFIED (code read; cross-language enforcing tests found)

Interface contract:
- `class EnvelopeError(ValueError)` — the single failure type; verification fails closed by raising it.
- `canonical(obj) -> str` — canonical JSON (mirrors Rust; XIMPL pins: raw UTF-8, signed-64-bit ints).
- `wrap(actor: str, claim_id: str, status: str, payload: dict, prev_hash: str = GENESIS,
  ts: str = "") -> dict` — seals payload; `status` must be in `STATUSES`; rejects empty
  actor/claim_id, non-dict payload. Emits `env, ts, actor, claim_id, status, payload,
  payload_hash, prev_hash, sig` (HS256 authority sig over canonical form), then `seal`
  (sha256 over canonical incl. sig — seal binds the signature into the chain).
- `verify(env: dict) -> None` — raises `EnvelopeError` on: non-object, unsupported `env` version,
  bad status, missing/malformed/invalid sig (AUTHENTICITY FIRST, fail closed, no legacy path),
  non-dict payload, `payload_hash` mismatch, `seal` mismatch.
- `verify_chain(envs: list, start_prev: str = GENESIS) -> None` — each envelope valid + prev_hash
  linked; `start_prev` anchors the first expected prev_hash (GENESIS for fresh chains; seal of last
  pre-sig envelope for two-tier chains, RT-2026-10-08-TWOTIER-1).
- `read_envelopes(path) -> list`.

### Rust: `~/workspace/proof-ledger/rs/src/envelope.rs`
**State:** EXISTING AND VERIFIED (symbols read; `cargo test` enforced by Verifier B `_pl_ximpl`)

Public API: `sign_bytes`, `verify_sig_str`, `wrap`, `wrap_with`, `has_visible_identity`,
`verify`, `verify_with`, `verify_chain`, `verify_chain_with`. 16 `#[test]` items counted in-file.
Cross-impl contract: `rs/tests/envelope_vectors.rs` `KNOWN_DIVERGENT` pins only `("bigint","XIMPL-2")`.

### Enforcing tests
- `~/workspace/compute/envelope_test.py` — cross-language equivalence. 10 `def test_*` functions
  counted in-file: `test_python_wrap_rust_verify`, `test_rust_wrap_python_verify`,
  `test_cross_tamper_rejected`, `test_ledger_record_emits_envelope` (asserts `sig` startswith
  `HS256:`, `verify_envelopes()` ok, envelope/claim binding), `test_missing_sig_rejected_both_directions`,
  `test_two_tier_mixed_chain`, `test_production_mixed_chain_tamper`,
  `test_verify_chain_start_prev_anchoring`, `test_ximpl2_i64_interop_pin`,
  `test_ximpl1_utf8_raw_parity`.
  **Discrepancy:** Verifier B and GATE-MATRIX.md reference "envelope_test.py 12/12"; the file
  contains 10 test functions (see Gaps).
- `pl` binary subcommands used as checks: `pl envelope op=verify|wrap`, `pl audit --full`.

---

## 6. PL audit enforcement (freshness + replay gates)

**Path:** `~/workspace/proof-ledger/rs/src/audit.rs` (compiled into `~/workspace/proof-ledger/pl` binary)
**State:** EXISTING AND VERIFIED (code read; enforced by Verifier B `_pl_freshness` re-executed probes)

- STALE detection: stale verification records (assertion supersedes verification) → audit reports
  "STALE verification" (closes RT-2026-10-08-STALE-EXEC).
- REPLAY/DUPLICATE detection: two verification records with identical content → second is a REPLAY
  unless the CLI witnessed distinct runs. This is the executable behind Verifier B's
  `_pl_freshness` probes (verbatim duplicate → FAIL REPLAY; 48h-old → FAIL STALE).

---

## 7. Compute ledger ingest (validator at record time)

**Path:** `~/workspace/compute/ledger.py`
**State:** EXISTING AND VERIFIED (symbols read; enforced by `envelope_test.py::test_ledger_record_emits_envelope`)

- `request_hash_for(source_id: str, prompt: str) -> str` (line 42) — ingest identity.
- `record(execution: Execution) -> dict` (line 122) — wraps every recorded execution in the
  `lucidota-receipt/1` envelope at ingest.
- `verify_envelopes(path=None) -> tuple[bool, str]` (line 155) — re-verifies the chain with
  honest tier counts; consumed by Verifier B `_pl_tamper` and `_pl_ingest`.

---

## 8. Canon binary authority surface

**Path:** `~/workspace/canon/` (Rust); binary at `target/debug/canon` / `target/release/canon`
**State:** EXISTING AND VERIFIED for audit/snapshot/fail-closed (code paths read; enforced by
Verifier B `_canon_audit`, `_canon_interface`, and `canon_court_e2e.py`)

- `canon audit` → "audit OK", exit 0 on valid chains (constitution/contracts/decisions/supersessions).
- `canon snapshot` → JSON with 4 `canon_heads` + `context_hash` + `normative_basis_evidence`
  (INV-01/02/03); exit 3 `AUDIT FAIL` on tampered store (fail closed).
- `src/api.rs` — machine-consumable library interface.
- `src/deploy.rs` — deployment identity machinery: `load_signing_key(path)`,
  `issue_manifest(operator_name, key) -> Result<String,String>` (ed25519-signed canonical-JSON
  manifest: constitution commit, store heads, snapshot hash, binary sha256, build provenance,
  operator name), `verify_manifest(manifest_json) -> VerifyReport` with `Verdict` enum
  (MATCH/MISMATCH/UNKNOWN), `KEY_CLASS_TEST = "TEST-KEY — NOT FOR PRODUCTION"`.
- CLI: `canon deploy-identity gen-key | name=<deployment> key=<secret-key-hex-file>`
  (`src/main.rs:546`); `canon verify-deployment` per matrix.
- Tests: `canon/tests/deploy_identity.rs::deploy_identity_suite` (single `#[test]` running all
  cases sequentially; CANON_DIR is process-global). All manifests stamped TEST-KEY.
- **Production deployment identity: honestly absent** — blocked on the operator's key-custody
  decision (`goal_b4eaabcc3b4d`). Per GATE-MATRIX.md: "NOT FOR PRODUCTION" until custody lands.

---

## 9. Boundary/adversarial suite: `threat_tests.py`

**Path:** `~/workspace/compute/threat_tests.py`
**State:** EXISTING AND VERIFIED (code read; consumed as the executable check by Verifier A
`boundaries` + `security` gates and Verifier B `_pl_adversarial` adjacent checks)

22 `check()` calls across TM-1..TM-8 (scenario names observed in-file):
TM-1 forged-capability (trust-file forgery), TM-2 unminted-reserve (budget band escalation),
TM-3 priority-self-grant + campaign-forgery (priority/campaign minting), TM-4 dispatch-forgery
(dispatch completion), TM-5 ledger-tamper, TM-6 receipt-forgery (decision replay/forgery),
TM-7 self-attestation (registry self-attestation), TM-8 rpm-ceiling (NVIDIA RPM ceiling).
Exits 0 only if all pass.

---

## 10. Verifier-mission lane-a: AttestationAdapter (external trust-domain adapter)

**Path:** `~/workspace/verifier-mission/lane-a/` (`attest.py`, `invariants.py`, `jwks.py`, `receipt.py`,
`trust_config.py`, `verify.py`, README.md, DOGFOOD-REPORT.md, RIM-STATUS.md, RIM-VERDICT.md, TEE-SURVEY.md)
**State:** EXISTING BUT UNVERIFIED (code read; README claims "built, tested (56/56)" but no test
file is present in the directory — claim cannot be re-verified from the tree as it stands)

- `class AttestationAdapter` (dataclass, `attest.py`): pipeline DISCOVER (fetch JWKS) →
  READ-ONLY PROBE → receipt → VERIFY LOCALLY → ADVERSARIAL TEST. Methods include
  `acquire_keyset()`, `load_keyset()`. Deliberately NOT wired into any Exchange execution path
  (integration gated on lanes E+G). Hard assertion in `_finalize`: this module never emits
  `AUTHORIZED` — max claim is `ESTABLISHED:MEASUREMENT`.
- `invariants.py` canonical laws: INV1 "Names don't create provenance." / INV2 "Assertions don't
  create evidence." / INV3 "Observation doesn't create authority." / INV4 "A verifier that cannot
  reject is not a verifier." CLAIM_KIND triple split: CLAIMED vs ESTABLISHED vs AUTHORIZED, never
  collapsed. Epistemic stages: PARSE → KEY_RESOLUTION → SIGNATURE → CLAIMS → POLICY_DECISION.
- `receipt.py::write_receipt(kind, body, receipt_dir=None) -> {path, sha256, receipt}` —
  content-addressed JSON receipts; rejections produce receipts, not just exceptions; receipts never
  journal key material (public kids/fingerprints only).

---

## Gaps, discrepancies, unknowns

1. **Verifier B `_canon_deploy` is stale vs the matrix.** `pl_canon_verifier.py::_canon_deploy`
   searches only for Dockerfile/deploy*/.github and returns FAIL "no deployment identity beyond the
   local build" — it never exercises `canon/src/deploy.rs` (`issue_manifest`/`verify_manifest`) or
   `tests/deploy_identity.rs`. GATE-MATRIX.md rates deployment_identity PASS WITH CAVEAT based on
   that machinery. The verifier code and the matrix disagree; the verifier under-reports.
   → verifier needs extension to test the actual deploy-identity contract.
2. **Test-count discrepancies (documents vs tree):** `envelope_test.py` contains 10 `def test_*`
   functions; Verifier B / GATE-MATRIX.md cite "12/12". `canon_court_e2e.py` contains 14 `check()`
   calls; documents cite "13/13". Counts not reconciled — re-run would settle it.
3. **FABRICATE-1 (HIGH, OPEN):** direct file-write attacker can mint fully-VERIFIED PL claims;
   Verifier B `_pl_adversarial` confirms root cause (no `record_level_seal`/`seal_record` in
   `rs/src`). PL `adversarial` gate honestly FAILs until record-level authority sealing exists;
   blocked on operator key-custody decision (`goal_b4eaabcc3b4d`).
4. **`router.verify_execution` / `router.observe` signatures** cited from `governor_tests.py`
   usage only (`verify_execution(ex, "exact", {"passed": False})`;
   `observe(d, ex, v, verified_value=0.0)` → `{outcome, actual_success, observation_id}`);
   `router.py` itself not read in this investigation.
5. **DISPROVEN verdict value** appears only in `independent_verifier_tests.py`'s allowed-values
   assertion; no code path in `independent_verifier.run()` emits it.
6. **Canon normative content** (constitution §6 DONE equation, INV-01/02/03 full text) referenced
   by verifiers as requirement sources but not re-read here; the forensic scope covered the
   enforcement machinery, not the normative text.
7. **Last-run verdict values** (`independent_verdict.json`, `pl_canon_verdict-*.json`) exist as
   artifacts but were not re-executed by this investigation; current pass/fail state is UNKNOWN
   until a wave re-runs them.

## Symbol index (exact names for the synthesis wave)

`court.derive_status` · `court.file_claim` · `court.request_completion_review` ·
`court.record_falsification` · `court.Claim` · `court.REQUIRED_GATES` · `court._canon_basis` ·
`court._bind_entry` · `governor.govern` · `governor.audit` · `governor._codify` ·
`governor.REASON_CODES` · `governor.MAX_GOVERN_DEPTH` ·
`independent_verifier.run` · `independent_verifier._gate_defs` · `independent_verifier._check_contract`
(+ `_check_tests`, `_check_adversarial`, `_check_boundaries`, `_check_independent`, `_check_dogfood`,
`_check_benchmark`, `_check_security`, `_check_recovery`, `_check_reproducible`,
`_check_evidence_complete`) ·
`pl_canon_verifier.run` · `pl_canon_verifier._pl_gate_defs` · `pl_canon_verifier._canon_gate_defs` ·
`pl_canon_verifier._assess` · (PL gates) `_pl_contract` `_pl_ingest` `_pl_sig` `_pl_freshness`
`_pl_tamper` `_pl_ximpl` `_pl_adversarial` `_pl_durability` `_pl_audit` · (canon gates)
`_canon_frozen` `_canon_audit` `_canon_interface` `_canon_court` `_canon_deploy` `_canon_adversarial` ·
`envelope.wrap` · `envelope.verify` · `envelope.verify_chain` · `envelope.canonical` ·
`envelope.EnvelopeError` · `envelope.read_envelopes` · `envelope::wrap` · `envelope::verify` ·
`envelope::verify_chain` · `envelope::wrap_with` · `envelope::verify_with` ·
`ledger.record` · `ledger.verify_envelopes` · `ledger.request_hash_for` ·
`canon deploy-identity` · `canon verify-deployment` · `canon audit` · `canon snapshot` ·
`deploy::issue_manifest` · `deploy::verify_manifest` · `deploy::load_signing_key` ·
`deploy::KEY_CLASS_TEST` · `AttestationAdapter` · `invariants.KERNEL` (INV1–INV4) ·
`receipt.write_receipt` · threat models TM-1..TM-8.
