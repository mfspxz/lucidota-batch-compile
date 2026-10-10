# F5 — Proof Ledger (PL) Forensic Inventory

**Investigator:** subagent 24996aa7 (forensic, read-only)
**Date:** 2026-10-09 ~11:45 PDT
**Mode:** read-only. No source/data modified, no ledger writes made, no key material read.
**Scope note:** there are three ledger-adjacent artifacts in the workspace. This finding covers all three and their relationships.

---

## 1. What "the Proof Ledger" actually is (three artifacts, not one)

| # | Artifact | Path | Role |
|---|---|---|---|
| L1 | Main agent ledger | `~/ledger/ledger-0001.jsonl` (6.8 MB, seq 5249 as of investigation) | Append-only record of every action/decision/chat across all agents. Zack's non-negotiable guardrail (2026-10-05). |
| L2 | Proof-ledger claim store | `~/workspace/proof-ledger/ledger.jsonl` (51+ records) | Hash-chained claim store for the proof-ledger subsystem itself (Rust `pl` binary). |
| L3 | Compute execution chain | `~/workspace/compute/ledger.py` + chained records + envelopes | Execution records from the compute fabric, chained via `integrity.append_chained`, each with a `lucidota-receipt/1` envelope. |

Plus derived/projection layers: `proof-ledger/projection.py` (RFC 6902 state projection over L2), `proof-ledger/projection.json`.

---

## 2. Append-only mechanics — as implemented

### L1 writer: `~/ledger/ledger.py`
- `append_locked(entry)` — opens `ledger-NNNN.jsonl` with `a+` (O_APPEND: writes always land at end), takes an **exclusive `fcntl` flock**, re-counts lines under lock, assigns `seq`, injects `ts` (UTC ISO) if absent, writes one JSON line, `flush()` + `os.fsync()`, releases lock.
- **Rotation rule:** refuses writes to any file ≥ 10 GB (`TEN_GB = 10 * 1024**3`); scans to next `ledger-NNNN.jsonl`. Rule set by Zack 2026-10-05 (`~/ledger/LEDGER-RULES.md`): notify Zack, index, compress, archive, rotate.
- Duplicate-seq race under agent-fleet bursts was **proven and fixed** by the lock (comment in code).
- Best-effort live mirror: after every append, background-spawns `~/workspace/system/ledger-sync.py` (throttled to ≥90 s between spawns, errors swallowed — push never breaks local append; 30-min cron is the backstop).
- Correction model (LEDGER-RULES.md #3): no edits/deletions/rewrites — corrections are **new entries referencing the old ones**.

### L2 writer/verifier: `~/workspace/proof-ledger/rs/src/ledger.rs`
- `pub fn append(mut e: Map<String, Value>) -> Result<(), LedgerError>` — opens with `.append(true)`, exclusive lock (fs2, unix + wasm32 cfg), **re-reads the tail under lock** to derive `prev_hash` (invariants: I — serialize writers), stamps `schema`, `prev_hash`, `observed_at`, `recorded_at`, default `actor: "lucidota"`, computes `hash` via `canon::hash_record`, canonicalizes the whole record via `canon::canonical`, writes **record + newline in a single `write_all`** (a crash mid-append leaves at most one unterminated tail line), `flush` + `fsync` before reporting success.
- `pub fn verify_chain(entries: &[Map<String, Value>]) -> Result<usize, LedgerError>` — checks **I1: `prev_hash` continuity** (GENESIS-anchored) and **I2: hash recomputation** (`canon::hash_record` over record-minus-`hash` must equal `hash`). Any mismatch → `LedgerError::Chain { line, msg }`.
- `pub fn repair() -> Result<RepairReport, LedgerError>` — explicit tail repair (amputates a truncated tail; the repair itself is appended as a record). `pub struct RepairReport { truncated_at_line, removed_bytes, removed_sha256, kept_records }`.
- `pub fn read_strict() -> Result<Vec<...>, LedgerError>` — reports truncated tail as error rather than silently dropping.
- Canonical JSON: `rs/src/canon.rs` — `pub fn canonical(v)`, `pub fn canonical_any(v)`, `pub fn hash_record(v)`. Sorted keys, compact separators, UTF-8 raw (no `\uXXXX`), **no floats ever**, integers i64.

### Chain anchors (point-in-time pins)
- `proof-ledger/evidence/chain-anchors.jsonl` — authority-signed `lucidota-receipt/1` envelopes pinning SHA-256 of the pinned prefix + tail hash of `proof-ledger/ledger.jsonl` (51 records) and `compute/falsification.jsonl` (147 records) as of 2026-10-09T06:05Z (wave-44, lane `chain-keying-broader`).
- `proof-ledger/repro/verify-chain-anchors.sh` — fail-closed verifier: (1) `pl envelope op=verify` checks HMAC sig + `prev_hash` chain over all anchors; (2) prefix pin: `sha256(first N lines) == file_sha256`; (3) tail pin: last record's `hash == tail_hash`. `repro/chain-anchor-tamper-demos.txt` documents tamper demonstrations.

---

## 3. Receipt envelope v1 (`lucidota-receipt/1`) — schema

Spec: `~/workspace/proof-ledger/RECEIPT-ENVELOPE.md` (adopted Oct-8 repair wave). Doctrine: **bespoke claim logic, boring envelope** — the ternary claim schemas stay custom (SCITT/SLSA don't model claimed/established/authorized); the transport wrapper is fixed. New code MUST NOT invent a second envelope.

| Field | Meaning |
|---|---|
| `env` | `"lucidota-receipt/1"` — verifiers reject anything else |
| `ts` | RFC3339 UTC sealing time (opaque string; `+00:00` hashes as written, not normalized) |
| `actor` | who sealed it (human, service, device) |
| `claim_id` | the claim this receipt speaks about |
| `status` | `claimed` \| `established` \| `authorized` |
| `payload` | arbitrary JSON object (the bespoke record) |
| `payload_hash` | sha256 over canonical `payload` |
| `prev_hash` | previous envelope's `seal`, or `"GENESIS"` |
| `seal` | sha256 over canonical envelope **minus `seal`** — but **computed OVER `sig`**, binding the signature into the chain |
| `sig` | authority signature layer (wave-2, closes RT-2026-10-08-ENV-1). Format `"HS256:<hex>"` = HMAC-SHA256 (RFC 2104, over the audited `sha2` crate — primitive is vetted, only the standard construction is local code) over canonical envelope minus `seal` and minus `sig`. Algorithm-agile: verifiers dispatch on the `ALG:` prefix, reject unknown algorithms. |

### Status vocabulary (decided 2026-10-08 — disjoint states)
- `claimed` =def. chain opened ∧ terminal observation absent. Intent/attempt recorded; outcome unknown. Covers infra errors pre-empting a terminal state.
- `established` =def. terminal observation present ∧ chain verifies. **The guest's exit code is orthogonal** — a failed guest is still an established receipt; what is established is the *observation*, not the success.
- `authorized` =def. receipt endorsed by the sealing authority (endorsement axis; semantics unchanged).
- **RCPT-009 resolution:** the daemon was right to mark a completed-but-guest-failed execution `established`; the benchmark corpus expectation (reading "established" as "succeeded") was the error, corrected in corpus spec §4. **All receipts ever minted remain valid under these definitions** (monotonic extendibility: no migration, no re-sealing).

### Signature / key custody
- Key: `$PL_SIG_KEY` or `~/workspace/keys/PL_SIG_KEY` (mode 600, exists — presence verified, value never read). 32 bytes hex-encoded. Read at call time, never logged, never committed. Missing/unreadable key **fails wrap AND verify closed**.
- Verifiers **REJECT** envelopes with missing/malformed/invalid `sig` — fail closed; no legacy/unsigned path for authentication.
- Two-tier strictness (`compute/ledger.py::verify_envelopes`, RT-2026-10-08-TWOTIER-1): chain linkage verified **uniformly** across every envelope; per-envelope: signed → must authenticate, unsigned → integrity-only, reported honestly as such. Tier is a property of the envelope (`sig` present or not), never timestamps. Pre-sig unsigned envelopes are history, not a bypass.
- HS256 chosen deliberately (documented, not defaulted): sign+verify both live inside the authority's custody boundary on this machine; symmetric MAC is the boring standard there. ed25519 becomes right the day signing/verifying split across trust boundaries — that is the **open AUTHORITY-KEY CUSTODY question** (`proof-ledger/KEY-CUSTODY.md`, goal_b4eaabcc3b4d).

### Canonical JSON contract (pinned 2026-10-08, ENVELOPE-XIMPL)
- UTF-8 raw (NOT `\uXXXX` — matches JCS RFC 8785 and Rust `serde_json::to_string`); keys sorted (codepoint/byte order); compact separators; no floats; integers i64 contract; timestamps opaque.
- **XIMPL-1 (HIGH, CLOSED 2026-10-08, wave-26):** Python port used `ensure_ascii=True` → `payload_hash`/`sig`/`seal` diverged on non-ASCII payloads. Fixed (`ensure_ascii=False` in `compute/envelope.py` and `compute/integrity.py::_canonical`); differential 0/19 divergences.
- **XIMPL-2 (MEDIUM, OPEN):** Python accepts arbitrary-precision integers (exact decimal digits); Rust `serde_json` parses >u64 as f64 and the canonicalizer rejects floats → **accept/reject divergence** on the numeric contract. Interoperable contract is i64; payloads MUST NOT carry integers outside [-2^63, 2^63-1] until both impls agree on arbitrary precision. Tracked as future extension, not silent behavior gap.

### Reference implementation — symbols
- `rs/src/envelope.rs` (695 lines): `pub fn sign_bytes`, `pub fn verify_sig_str`, `pub fn wrap` / `pub fn wrap_with` (key-injectable, hermetic tests), `pub fn verify` / `pub fn verify_with`, `pub fn verify_chain` / `pub fn verify_chain_with`, `pub fn has_visible_identity` (Unicode Cf-format-char identity gate; parity with Python `_has_visible_identity` via 213-case differential, 0 mismatches — NIH finding #4).
- CLI: `pl envelope op=wrap actor=... claim_id=... status=... payload='...' [prev=SEAL]` / `pl envelope op=verify file=envelopes.jsonl`. Built binary: `proof-ledger/pl` (built 2026-10-09 14:19).
- Python port: `compute/envelope.py` (byte-faithful; proven by `compute/envelope_test.py`: Python wrap → Rust verify AND Rust wrap → Python verify, both directions green; cross-language tamper rejected both ways).
- JS port: `exchange/envelope.js` — `verifyEnvelope(env, keyHex)` (line 117), `verifyEnvelopeChain(envs, keyHex, startPrev)` (line 157).
- Ingest gate: `exchange/worker.js::requireEnvelope` (line 252) — fail-closed on POST `/v1/complete`, `/v1/observe`, `/v1/ballots`: key not provisioned → 503 + audit; missing envelope → 400 + audit; verify fail → 401 + audit; **replay (seal already seen) → 409**; registry full → 503; `checkClaimBinding` anti-transplant (wave-36: a well-sealed envelope lifted from claim A to claim B is rejected). Rejections audited via `recordEnvelopeRejection` (`envelope_rejections` table).

---

## 4. Recorded-claim vs independent-proof — the distinction as implemented

This is the load-bearing distinction in the whole stack, and it is implemented mechanically, not just asserted:

**Recording (what the ledger does):**
- An entry in any of L1/L2/L3 records *that a claim was made, by whom, when* — with actor attribution (`actor`), UTC timestamps (`ts`/`observed_at`/`recorded_at`), and hash linkage. Recording is cheap and total (LEDGER-RULES #1: 100% capture).
- A recorded entry is **not** proof. Per the design: *"The ledger records evidence; it does not magically make unsupported claims true."*

**Proof (what independent verification does):**
- `verify_chain` (I1 prev_hash continuity + I2 hash recomputation) — anyone can re-derive; no trust in the writer.
- Envelope `sig` authentication against the authority key — proves the receipt was sealed by the authority, not just written by anyone with file access.
- `status` vocabulary: `established` means the *observation chain verifies*, independent of whether the underlying guest succeeded (RCPT-009). Outcome lives in the payload's outcome fields; status describes the receipt's own standing. Evaluators are instructed: determine status from structure first, then score the payload.
- Honest adoption reporting: `compute/ledger.py::envelope_coverage()` — pre-adoption executions (17 records) have no envelopes; **reported honestly, not backfilled**.
- Corrections are new claims with `supersedes` edges (PROVENANCE-ENFORCEMENT.md §6.4); history is never rewritten.

**The v2 upgrade (PROVENANCE-ENFORCEMENT.md, Zack's Primary Rule, 2026-10-09):** proof envelope extends `lucidota-receipt/1` with `claim_hash` (BLAKE3), `parents` (Merkle DAG), `citations` (`{uri, content_hash, retrieved_at}`), LiteBox `execution` receipt; verification via binary fuse filter (µs hot path), Merkle inclusion proofs (warm path), full re-verification (cold path). **Status: doctrine recorded; machinery not yet built** (see §7).

---

## 5. Exact file paths + key symbols

| Path | Key symbols / contents |
|---|---|
| `~/ledger/ledger.py` | `append_locked(entry)` — flock, seq, O_APPEND, fsync, 10 GB refusal |
| `~/ledger/ledger-0001.jsonl` | live L1 ledger (6.8 MB) |
| `~/ledger/LEDGER-RULES.md` | the 6 non-negotiable rules (100% capture, append-only, 10 GB rotation, attribution, trinary) |
| `~/workspace/proof-ledger/rs/src/envelope.rs` | `wrap`, `wrap_with`, `verify`, `verify_with`, `verify_chain`, `verify_chain_with`, `sign_bytes`, `verify_sig_str`, `has_visible_identity` |
| `~/workspace/proof-ledger/rs/src/ledger.rs` | `append`, `verify_chain`, `repair`, `read_strict`, `RepairReport`, `LedgerError` |
| `~/workspace/proof-ledger/rs/src/canon.rs` | `canonical`, `canonical_any`, `hash_record` |
| `~/workspace/proof-ledger/rs/src/{audit,bundle,model,probe,projection,time}.rs` | audit trails, bundles, models, probes, RFC-6902 projection |
| `~/workspace/proof-ledger/pl` | built CLI binary |
| `~/workspace/proof-ledger/RECEIPT-ENVELOPE.md` | envelope v1 spec + sig layer + XIMPL contract + adoption checklist |
| `~/workspace/proof-ledger/PROVENANCE-ENFORCEMENT.md` | Primary Rule doctrine + v2 envelope + 3-path verification design (UNTRACKED in git as of investigation) |
| `~/workspace/proof-ledger/KEY-CUSTODY.md` | open authority-key custody question (goal_b4eaabcc3b4d) |
| `~/workspace/proof-ledger/ledger.jsonl` | L2 claim store |
| `~/workspace/proof-ledger/evidence/chain-anchors.jsonl` | signed chain-tail anchors |
| `~/workspace/proof-ledger/repro/verify-chain-anchors.sh` | fail-closed anchor verifier |
| `~/workspace/proof-ledger/fixtures/envelope-vectors.json` | 14 vectors + 5 negative vectors (sealed with PUBLIC test key 0x5a×32) |
| `~/workspace/proof-ledger/projection.py` | RFC 6902 state projection; `build`, `check`, `replay`, `atomic_write_json` |
| `~/workspace/compute/ledger.py` | `record()` (identity gate → `UnidentifiedExecutionError`, chained append, envelope emit), `verify_envelopes()` (two-tier), `envelope_coverage()` |
| `~/workspace/compute/envelope.py` | Python byte-faithful port of envelope |
| `~/workspace/compute/envelope_test.py` | cross-language interop suite |
| `~/workspace/exchange/envelope.js` | JS verify port: `verifyEnvelope`, `verifyEnvelopeChain` |
| `~/workspace/exchange/worker.js` | `requireEnvelope` (L252), `checkClaimBinding`, `recordEnvelopeRejection`; wired at L2249 (`complete`), L2533 (`ballots`), L2733 (`observe`) |
| `~/workspace/keys/PL_SIG_KEY` | authority key, mode 600 (presence only verified) |

---

## 6. Tests enforcing it

| Test | What it enforces | Result at investigation |
|---|---|---|
| `rs` unit tests in `envelope.rs` (16 `#[test]`) | wrap/verify roundtrip, forged envelope rejected, forged chain member rejected, chain break detected, tampered payload rejected, missing/malformed/wrong-alg sig rejected, `sig` covers seal chain, invisible-identity actors rejected, bad status/malformed prev_hash/missing fields rejected | **16/16 green (re-ran just now)** |
| `rs/tests/envelope_vectors.rs` | Rust reference reproduces every Python-generated fixture vector byte-identical; known divergences pinned by defect ID (XIMPL-2 `bigint`); a pinned vector that stops diverging fails the suite (forced promotion — this mechanism is what promoted XIMPL-1) | **green (re-ran just now)** |
| `rs/tests/rt_spree.rs` | red-team: chain rewrite, envelope forgery, verifier fuzzing (`rt_fuzz_envelope_verifier`) | **green (re-ran just now)** |
| `rs/tests/durability.rs` | concurrent writers, append atomicity, crash-during-append, explicit repair (work-order B5 acceptance) | green per git history (not re-run) |
| `rs/tests/{projection,projection_incremental,cli_flags}.rs` | projection + CLI behavior | green per git history (not re-run) |
| `compute/envelope_test.py` | cross-language interop (both directions), tamper rejection both ways, production-chain two-tier verification, XIMPL-1 UTF-8 parity, XIMPL-2 i64 pin | **ALL OK (re-ran just now)** |
| `proof-ledger/projection_tests.py` | projection build/check semantics | present; not re-run |
| `repro/verify-chain-anchors.sh` | anchor sig + prefix-pin + tail-pin, fail-closed | present; tamper demos in `repro/chain-anchor-tamper-demos.txt` |
| Exchange ingest (doc-reported) | 71 local checks green, wave-32, exchange@3a9ef2b; JS port `envelope.js` | reported green in RECEIPT-ENVELOPE.md; not re-run by this investigation |
| Git history | latest: `cf2fe76` "Spree: 4 Rust bugs + 4 Python bugs… 87+11 tests green"; `dc38252` wave-44 chain-tail anchors | evidence of continuous adversarial testing |

---

## 7. State per finding

| Finding | State | Basis |
|---|---|---|
| L1 `~/ledger/ledger.py` append-only mechanics (flock, seq, O_APPEND, fsync) | **EXISTING AND VERIFIED** | Code read; live ledger 6.8 MB / seq 5249 in production use |
| L1 10 GB rotation refusal | **EXISTING BUT UNVERIFIED** | Code path present; not exercised (ledger is 6.8 MB, far below trigger) |
| L2 `rs` hash-chained ledger (`append`/`verify_chain`/`repair`) | **EXISTING AND VERIFIED** | Code read; unit + durability tests green; verify_chain I1/I2 as specified |
| Receipt envelope v1 schema + spec | **EXISTING AND VERIFIED** | Spec doc + 2 impls + cross-impl tests re-run green |
| `sig` authority layer (HS256, fail-closed, two-tier verify) | **EXISTING AND VERIFIED** | Code read; 4 dedicated rejection tests green; key file exists mode 600 |
| XIMPL-1 canonicalization parity (UTF-8 raw) | **EXISTING AND VERIFIED** | Fixed 2026-10-08; differential 0/19; promoted by the pin mechanism itself |
| XIMPL-2 numeric contract (bigint accept/reject divergence) | **EXISTING BUT UNVERIFIED** — open defect, pinned, behavior gap acknowledged | Pinned in `envelope_vectors.rs` KNOWN_DIVERGENT; i64-only contract enforced by convention |
| Recorded-claim vs independent-proof distinction | **EXISTING AND VERIFIED** | Implemented in code (verify paths, RCPT-009, honest coverage reporting, supersedes-not-rewrite) and documented |
| Exchange envelope ingest gate (`requireEnvelope` + anti-transplant + replay registry) | **EXISTING BUT UNVERIFIED** | Code read and matches spec; "71 local checks green" is doc-reported, not re-run here; doc notes LOCAL-ONLY (live-D1 apply/deploy is CF-gated) |
| Chain-tail anchors + fail-closed verifier | **EXISTING AND VERIFIED** | Anchor envelopes present with valid `sig` shape; verifier script read; tamper demos documented |
| Authority-key custody decision (HS256 vs ed25519 migration) | **UNKNOWN** (open by design) | `KEY-CUSTODY.md`; goal_b4eaabcc3b4d; Zack's decision pending |
| PROVENANCE-ENFORCEMENT.md v2 machinery (envelope v2 JSON Schema, fuse-filter builder, Merkle tree + STHs, governor ingest gate, LiteBox receipt auto-fill, provenance graph projection, brief-lint extension) | **NOT IMPLEMENTED** (doctrine only) | Rollout checklist: 1/8 done (doctrine recorded); doc is untracked in git |
| `pl` binary CLI (`envelope op=wrap/verify`) | **EXISTING AND VERIFIED** | Binary present, built 2026-10-09 14:19; CLI contract in spec |
| projection.py (RFC 6902 over append-only ledger) | **EXISTING** (tests present; not re-run) | `projection_tests.py` exists; treat as BUT UNVERIFIED for current run |

## 8. Gaps / open questions for the spec author (Prompt 2)

1. **XIMPL-2 (OPEN):** the numeric contract diverges between impls. Any scheduler spec that puts integers in envelope payloads must either pin the i64 contract explicitly or resolve the arbitrary-precision question first.
2. **Authority-key custody (UNKNOWN):** HS256-today vs ed25519-later is decided by key custody, which is Zack's open decision. The spec must not assume cross-boundary signing.
3. **PROVENANCE-ENFORCEMENT v2 gates unbuilt:** the fuse filter, Merkle tree/STHs, and governor ingest gate are doctrine, not code. A spec that treats them as existing enforcement would be inventing capability — classify as NEW WORK.
4. **Exchange gate is LOCAL-ONLY:** live-D1 apply/deploy is Cloudflare-gated; the ingest gate is proven in the local worker build only.
5. `PROVENANCE-ENFORCEMENT.md` is untracked in the proof-ledger git repo (present in working tree, not committed) — durability risk if the working tree is disturbed.
6. L1's 10 GB refusal path has never fired; rotation procedure (index/compress/archive) is documented in LEDGER-RULES.md but unexercised.
