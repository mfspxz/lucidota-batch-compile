# SPEC §12.13 — Unresolved Facts Blocking Safe Implementation

**Status:** DRAFT specification.
**Scope:** every UNKNOWN / BLOCKED item from evidence f1–f8. Each entry states
the exact missing fact, why it changes the design, and what is blocked on it.
Unknowns are unchanged by the architecture re-scope and tier-model update —
the minimal pipeline is designed to carry them as labeled parameters, not to
assume them away.

**Severity vocabulary:** **BLOCKED** = the design may not depend on this;
**UNKNOWN (parameter)** = the design carries it as an explicit symbolic /
labeled value until measured.

---

## BLOCKED — hard

### UF-001 — Cap'n Maps: no contract exists
- **Missing fact:** the canonical identity and contract of "Cap'n Maps". Greps
  across the workspace, ledger, and all `*.md` return only the batch-compile
  mission documents themselves. Zero code, zero docs, zero ledger entries.
- **Why it changes the design:** mission §8 asks for stack integration "by
  discovered contract". With no contract, any DAG role, interface, or data flow
  assigned to it would be invented.
- **Blocked on it:** any scheduler role, boundary contract, or dependency edge
  involving Cap'n Maps. (If the intended referent was Cap'n Web, that is a
  different component with an RPC/capability contract — name it correctly first.)

### UF-002 — FalkorDB production role
- **Missing fact:** whether FalkorDB becomes a production dependency. Measured:
  live server on 127.0.0.1:6379 (Redis 8.10.2 + falkordb.so, 10 graphs), role
  today = hackathon practice/dogfood only (Graph Hacks, Oct 15–18); the goal's
  hard boundary forbids mixing it with the main project. No production pipeline
  reads or writes it.
- **Why it changes the design:** task discovery / dependency queries would move
  from dev-graph.json + `devgraph.py` semantics to Cypher if FalkorDB goes
  production; the partitioner's graph-read interface must be built behind an
  adapter, not hardwired.
- **Blocked on it:** any production dependency on FalkorDB; Cypher-based work-graph reads.

### UF-004 — Authority-key custody (goal_b4eaabcc3b4d)
- **Missing fact:** Zackary's custody decision for the authority signing key
  (`proof-ledger/KEY-CUSTODY.md`). Today: HS256 HMAC, key at
  `~/workspace/keys/PL_SIG_KEY` (mode 600), valid only inside the custody
  boundary on this machine. ed25519 becomes right the day signing/verifying
  split across trust boundaries.
- **Why it changes the design:** cross-boundary receipt signing (any scheduler
  or worker outside this machine sealing envelopes) requires the ed25519
  migration; the spec must not assume it.
- **Blocked on it:** production deployment identity (CANON `deploy::issue_manifest`
  beyond TEST-KEY); multi-machine scheduler/claimant topologies; closure of
  FABRICATE-1 (record-level authority sealing).

### UF-006 — `authorized`-envelope promotion path
- **Missing fact:** who promotes an envelope from `established` to `authorized`,
  and where. `envelope.py::STATUSES` includes `authorized`; no call site in
  `~/workspace/compute` wraps with `status="authorized"` (f2 §G).
- **Why it changes the design:** the pipeline's final-acceptance state cannot
  include an `authorized` envelope until a producer exists; acceptance must stop
  at `established` + court verdict.
- **Blocked on it:** any acceptance predicate requiring `authorized` envelopes.

### UF-011 — Live-deploy parity of `exchange/worker.js` v0.6.14
- **Missing fact:** whether the live worker
  (`lucidota-exchange.cutecity.workers.dev`) runs the exact v0.6.14 source read
  in `~/workspace/exchange/worker.js`; D1 mirror (`d1-mirror.db`) staleness unknown.
- **Why it changes the design:** the migration assumes the read source matches
  the deployment. Any pipeline↔Exchange integration built against a diverged
  deployment would enforce the wrong gates.
- **Blocked on it:** any scheduler integration with live Exchange endpoints
  (none is in the minimal pipeline's scope; the block matters for future phases).

### UF-012 — GO-50/O-25/C-25 ontology crate path missing
- **Missing fact:** the framework doc
  (`~/workspace/user/files/GO_ONTOLOGY_FRAMEWORK_10_bsn6.md`) claims a
  `go-ontology` crate at `PALANTOUR/crates/go-ontology/` with 5 passing tests;
  the path was not found in the workspace (possibly private PALANTOUR checkout).
- **Why it changes the design:** ontology-tagged provenance fields cannot be
  validated against the crate; the doc is reference-only.
- **Blocked on it:** any pipeline validation of GO-50/O-25/C-25 tags.

---

## UNKNOWN (parameter) — carried symbolically, never assumed

### UF-003 — XIMPL-2 bigint divergence (OPEN defect)
- **Missing fact:** the agreed numeric contract. Python accepts arbitrary-precision
  integers; Rust `serde_json` parses >u64 as f64 and the canonicalizer rejects
  floats → accept/reject divergence. Pinned in `envelope_vectors.rs` KNOWN_DIVERGENT.
- **Why it changes the design:** any scheduler payload carrying integers outside
  i64 breaks cross-implementation verification. The work-order/parsed schemas pin
  i64-only until both implementations agree on arbitrary precision.
- **Blocked on it:** arbitrary-precision integers in envelopes/payloads (carried as
  i64-only contract).

### UF-005 — PROVENANCE-ENFORCEMENT v2 machinery unbuilt
- **Missing fact:** the code. Doctrine recorded (fuse filter, Merkle tree + STHs,
  governor ingest gate, LiteBox receipt auto-fill, provenance graph projection,
  brief-lint extension); rollout checklist 1/8 done; the doc is **untracked in git**
  (durability risk if the working tree is disturbed).
- **Why it changes the design:** a spec that treats µs claim lookup or Merkle
  inclusion proofs as existing enforcement would invent capability. Pipeline
  provenance rests on v1 envelopes (EXISTING AND VERIFIED).
- **Blocked on it:** depending on v2 machinery anywhere in the pipeline (14: D-08).

### UF-007 — TPM / concurrency unmeasured for ALL providers
- **Missing fact:** no token-per-minute (in/out) probe and no concurrency probe
  exists for NVIDIA, Gemini, DeepSeek, or any ai-router lane. Adapters run
  single-flight pacers; multi-concurrency behavior untested.
- **Why it changes the design:** the λ equation's token terms and C·μ term are
  unquantified. Pacing must stay on request-rate ceilings (39/10 RPM) + measured
  latency bounds; token-heavy tasks risk invisible TPM caps.
- **Blocked on it:** quantified token/concurrency scheduling (carried as symbolic
  `UNMEASURED` in the allocator).

### UF-008 — DeepSeek quotas: zero measurements (+ code-gen defect)
- **Missing fact:** no RPM/TPM/concurrency/context numbers anywhere; skill is
  credential-verified only. Plus TOOLS.md (2026-10-09): `deepseek-chat` leaks
  chain-of-thought into stdout — unusable for code generation.
- **Why it changes the design:** the DeepSeek generation lane cannot be paced or
  trusted for code artifacts; the allocator must mark it capability-restricted.
- **Blocked on it:** DeepSeek in any paced or code-generating pipeline role.

### UF-009 — ai-router lane `rpmLimit` unmeasured
- **Missing fact:** per-lane `rpmLimit` values (15/30/60/10/40/20/15/30/10/30/10/2/2)
  are router-config DECLARED values from `/health`, never wire-measured; the
  adapter protocol forbids promoting declarations to measurements.
- **Why it changes the design:** pacing the scheduler off them assumes the router
  enforces them (red-team wave 10 saw a 502 with "nvidia timeout, kilo empty,
  llm7 429, pollinations 402, ovh timeout" — keyless lanes flake under load).
- **Blocked on it:** treating lane caps as capacity (carried as `DECLARED_ONLY`).

### UF-010 — NVIDIA provider limit + budget unmeasured
- **Missing fact:** 39 RPM is Zackary's operator pacing directive implemented as a
  Governor token bucket (`nvidia_rpm.py`), NOT NVIDIA's published limit — no
  429/402 ever observed, true provider ceiling UNKNOWN. `provider_budget_estimate
  = 5000` calls is an UNVERIFIED community estimate (2926 used per `calls.jsonl`);
  the account dashboard shows no meter.
- **Why it changes the design:** budget bands (0.60/0.80/0.90/1.00, burn guard
  0.55) are governance choices, not capacity facts. The allocator carries them as
  soft constraints with hard-stop at the estimate.
- **Blocked on it:** capacity planning against the 5000 estimate or any assumed
  provider RPM.

### UF-013 — MCP authority server untested
- **Missing fact:** `~/workspace/mcp-servers/governor/server.py` (checks authority,
  never holds it) has no test file; only a DOGFOOD-REPORT.md (not evaluated).
- **Why it changes the design:** scheduler authority-check calls to it cannot be
  trusted as enforcement. Its own `gate.check` is advisory by design — treat the
  whole server as advisory until tested.
- **Blocked on it:** depending on the MCP server for enforcement decisions.

### UF-014 — Hostile-test receipt provenance gap (LiteBox)
- **Missing fact:** `~/workspace/litebox/litebox/hostile-tests/receipts/*.json`
  claim `verdict: "contained"` but their `ts` fields read 2026-09-10, predating
  the claimed 2026-10-09 run by a month; fixture binaries absent (`bin/` empty);
  the suite is untracked on the local clone.
- **Why it changes the design:** containment claims cannot ground sandbox trust.
  LiteBox stays characterized as cooperative-guest witnessing + receipts
  (f7: linux_userland NO-GO as a hostile-agent boundary — DISPROVEN as security claim).
- **Blocked on it:** any hostile-containment security claim for the sandbox.

### UF-015 — Gemini operational envelope (partially measured)
- **Missing fact:** measured ceiling is 10 RPM (adapter-enforced, probe-proven:
  4×200 then 503 at 2s spacing). "~9 RPM" is Zackary's operational pace (90% of
  ceiling), not a measurement. Free-tier floor: 20 generateContent req/day for
  gemini-3.8-flash. Rolling token window ~600–700K/10min then 429 (ledger seq
  5185) is a single operational observation, not a measured limit.
- **Why it changes the design:** the allocator enforces min(10 RPM, 20/day) as
  hard; the token window is an unquantified risk, not a schedulable parameter.
- **Blocked on it:** scheduling against the token window as a known limit.

### UF-016 — Queue-lifecycle dedicated tests missing
- **Missing fact:** `QUEUE_STATUSES` asserted in `queue.mark()` but no dedicated
  queue transition test file found (only inline RT-C7/RT-C15 comments).
- **Why it changes the design:** the pipeline's Route/Track ops depend on these
  transitions; the gap is small but real.
- **Blocked on it:** nothing structural — covered by a new test in implementation
  (classified EXISTING BUT UNVERIFIED in 14-traceability.md).

### UF-017 — lanectl cost-governor unexamined
- **Missing fact:** `~/workspace/lanectl/crates/cost-governor` discovered, never read;
  enforcement status UNKNOWN.
- **Why it changes the design:** cost-governance overlap with the allocator is
  unknown; the pipeline must not duplicate or contradict it blindly.
- **Blocked on it:** allocator cost-policy decisions that might collide with it
  (read the crate before wiring cost authority).

### UF-018 — Verifiers' last-run states unknown
- **Missing fact:** `independent_verdict.json` and `pl_canon_verdict-*.json`
  artifacts exist but were not re-executed by the f4 investigator; current
  pass/fail UNKNOWN until a wave re-runs them.
- **Why it changes the design:** "verified" for the verifier harnesses means
  code-present + prior artifacts, not currently-green. Pipeline acceptance that
  cites them should re-run them.
- **Blocked on it:** citing current verifier verdicts as acceptance evidence
  without re-running.

### UF-019 — 9-stage pipeline has no single state machine
- **Missing fact:** DISCOVER→…→REPLAN is verified stage-by-stage in `worker.js`
  but has no enum, transition table, or test walking all nine.
- **Why it changes the design:** any mapping of pipeline lifecycle onto the nine
  stages is interpretive. The minimal pipeline uses its own six-op lifecycle
  (Partition/Group/Assign/Schedule/Record/Repeat); the 9-stage vocabulary is
  DEPRECATED from pipeline scope (14: D-07).
- **Blocked on it:** treating the 9-stage narrative as an enforceable machine.

### UF-020 — `pl_canon_verifier._canon_deploy` stale vs deploy machinery
- **Missing fact:** `_canon_deploy` searches for Dockerfile/deploy*/.github and
  FAILs, never exercising `canon/src/deploy.rs` (`issue_manifest`/`verify_manifest`)
  or `tests/deploy_identity.rs`; GATE-MATRIX.md rates deployment_identity
  PASS WITH CAVEAT on that machinery. Code and matrix disagree.
- **Why it changes the design:** the verifier under-reports deployment-identity
  capability. The pipeline does not depend on this gate, but acceptance reports
  citing it must note the staleness.
- **Blocked on it:** trusting `_canon_deploy` FAIL at face value.

### UF-021 — court-claim ↔ envelope-claim mapping by convention only
- **Missing fact:** `claims.jsonl` uses `"CLAIMED"` (court pipeline) while
  `envelope.py` uses `"claimed"` (seal pipeline); the mapping is by convention
  (`ledger._emit_envelope`), not one enforced transition.
- **Why it changes the design:** pipeline acceptance must bind both explicitly
  (envelope `claim_id` carries the court claim id); a single lifecycle must not
  be assumed.
- **Blocked on it:** assuming one unified claim lifecycle.

### UF-022 — Exchange ingest gate is LOCAL-ONLY
- **Missing fact:** `worker.js::requireEnvelope` (fail-closed ingest, anti-transplant,
  replay registry) is proven in the local worker build; live-D1 apply/deploy is
  Cloudflare-gated ("71 local checks green" is doc-reported).
- **Why it changes the design:** envelope-at-ingest enforcement cannot be assumed
  on the live worker until deploy parity (UF-011) is verified.
- **Blocked on it:** relying on live ingest-gate enforcement.

### UF-023 — L1 10 GB rotation unexercised
- **Missing fact:** `~/ledger/ledger.py` refuses writes ≥10 GB; the ledger is
  6.8 MB — the path never fired. Rotation procedure (index/compress/archive per
  LEDGER-RULES.md) is documented but untested.
- **Why it changes the design:** none for the pipeline today (far below trigger),
  but the pipeline's Record op inherits the dependency — a rotation event would
  need the procedure to work.
- **Blocked on it:** nothing today; noted for operations.

### UF-024 — LiteBox generation gate not live on production lanes
- **Missing fact:** PROVENANCE-ENFORCEMENT.md mandates sandbox witnessing, but no
  evidence was found that any production lane executes through `liteboxd` today;
  plus uncommitted local modifications to `litebox_shim_linux/` (working tree,
  intent unknown).
- **Why it changes the design:** the pipeline cannot claim sandboxed provenance
  for worker-executed tasks; worker receipts are provider/adapter receipts only.
  Sandbox stays optional (14: §1 item 8).
- **Blocked on it:** provenance claims requiring sandbox witnessing.

---

## What changes once known (summary)

| If this lands… | Design change |
|---|---|
| UF-001 contract discovered | Revisit 14: B-01; assign a real DAG role or confirm exclusion |
| UF-002 production decision | Partitioner gains a Cypher adapter behind the graph-read interface |
| UF-003 contract agreed | Schemas relax i64-only to the agreed numeric contract |
| UF-004 custody decided | ed25519 migration path; multi-machine topologies unblocked |
| UF-006 promotion producer built | Acceptance may include `authorized` envelopes |
| UF-007 measured | Allocator λ terms become quantified; pacing tightens to real limits |
| UF-008 measured + defect fixed | DeepSeek enters the paced generation pool |
| UF-009 measured | Lane caps become schedulable capacity |
| UF-010 verified | Bands become capacity planning, not just governance |
| UF-011 verified | Exchange integration phases unblocked |
| UF-013 tested | MCP server graduates from advisory to enforcement-trusted |
| UF-014 re-run clean | Sandbox containment claims become citable |
| UF-017 read | Allocator cost authority reconciled with cost-governor |
| UF-018 re-run green | Verifier verdicts citable as current |
| UF-024 gate live | Provenance claims may cite sandbox witnessing |

---

## Provider use

None — direct synthesis from evidence bundle f1–f8 (no NVIDIA NIM generation,
no Gemini critique), to preserve exact symbol grounding. Fallback per task
authorization ("record `direct` fallback in receipts").
