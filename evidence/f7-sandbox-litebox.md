# F7 — Sandbox + LiteBox Integration (forensic evidence)

**Method:** read-only inventory, 2026-10-09. Ledger consulted via grep (chat_verbatim entries, forks sync, litebox campaign). No modifications made. Verified only what the artifacts themselves show — presence of a fork is not integration; presence of tests is not proof.

## 1. What LiteBox is, here

- **Upstream:** Microsoft LiteBox v0.1.0 (Rust library OS, MIT), released ~2026-10-07. North = nix/rustix-inspired guest API; South = interchangeable platform trait (Linux userland, Windows userland, LVBS, OP-TEE, SEV-SNP).
- **Local clone:** `~/workspace/litebox/litebox/` — git repo on `main` at `9e8155f` ("Reject O_CREAT | O_EXCL before backend open (#1548)"). Remotes: `origin` → `microsoft/litebox`; `fork` → `mfspxz/litebox` (Zackary's fork, per ledger).
- **Only the Linux-userland south is wired anywhere in our stack.** Any other south is explicitly `NotIntegrated` in our code.

## 2. The adoption shape (doctrine: "use LiteBox, never be a LiteBox slave")

Adopted as specified — LiteBox is one backend behind an adapter, never the governor:

- **Trait:** `execution_backend_core::ExecutionBackend`
  (`~/workspace/goals/litebox-library-os-organelle-execution-substrate/build/execution-backend/execution-backend-core/src/backend.rs:138`)
  Lifecycle contract: `prepare` (side-effect-free, validate + mint handle) → `start` → `inspect` (evidence without disturbing) → `suspend` (unimplemented, stays `NotIntegrated`) → `kill`. Object-safe, `no_std`-clean. Default `guest_stdout`/`guest_stderr` return `BackendError::NotIntegrated` ("honest non-integration").
- **Implementors found (grep):**
  - `FixtureBackend` — `execution-backend/src/local.rs:31` (test/stand-in backend).
  - `LiteBoxLauncher` — `execution-backend/src/litebox/launcher.rs:601`.
- **Manifest:** `ExecutionManifest` (`execution-backend-core/src/manifest.rs:30`) + `ExecutionPersonality` (`personality.rs:81`) with `FsSemantics`, `ProcessSemantics`, `NetworkSemantics`, `MemorySemantics`, `Platform`, `IsolationMode`, `Authority`, `ResourceEnvelope`, `EvidencePolicy`. Hash via `manifest_hash` (canonical JSON → sha256).
- **Policy gate:** `assess_manifest_on_path` (`execution-backend-core/src/policy.rs:162`) returns `BackendAssessment` with per-(North, South) path verdicts (`PathVerdict`) — a flat "sandboxed" boolean is explicitly rejected (registry records per-path compatibility).
- **Receipt schema:** `lucidota-receipt/1` envelope payloads. Adversarial-harness fragments: `ReceiptFragment {env, claim_id, status: "established"|"claimed", prev_hash, payload_hash, payload, wrap_note}` (`build/adversarial-harness/src/receipt.rs:21`, `ENVELOPE` const at line 18). The harness emits payload-level fragments only; sealing/wrapping is the governor/CANON's job ("the harness invents no second envelope").
- **Critical integration fact:** the `execution-backend` crate does **not** link LiteBox crates. Its `Cargo.toml` deps are: `execution-backend-core` (path), `pl` (path to `~/workspace/proof-ledger/rs`), `serde`, `serde_json`, `sha2`, `libc`, `thiserror`, `anyhow`, `tracing`, `clap`. The launcher **spawns the built `litebox_runner_linux_userland` binary as a child process** (default path `~/workspace/litebox/litebox/target/debug/litebox_runner_linux_userland`), waits up to `wall_time_secs`, SIGKILLs on timeout, captures stdout/stderr (16 MiB cap each), digests outputs. "Adapter, never fork" is honored on the execution-backend path.
  - **Exception (experiment crates, verified 2026-10-09):** three crates DO link the upstream `litebox` crate as a path dep: `build/path-fuzz/Cargo.toml` (`litebox = { path = "../../../../litebox/litebox/litebox" }`), `build/dogfood/Cargo.toml` (same path dep), and `~/workspace/litebox-organelle-host/Cargo.toml` (`litebox = { version = "0.1.0", path = "../litebox/litebox/litebox" }` — description: "LiteBox (linux_userland) as inner OS personality inside an outer Linux sandbox (namespaces, seccomp, rlimits)", i.e. defense-in-depth around the weak inner boundary). These are experiment/research crates, not the governor-facing backend. The adapter doctrine holds where it matters (the production path); it does not hold uniformly across experiment crates.
- **Daemon:** `liteboxd` (`build/liteboxd/src/main.rs`) — real HTTP service, 127.0.0.1:8471, bearer-token-gated (token at `hidden_files/liteboxd-token`, chmod 600), enforcer mandatory on every execution, fail-closed on missing token/enforcer. API: `GET /v1/health`, `POST /v1/prepare`, `POST /v1/start`, `GET /v1/inspect`, `POST /v1/kill`. Every execution emits `lucidota-receipt/1` fragments; sealing is governor/CANON's job. **Verified live 2026-10-09 ~18:40 UTC:** `GET /v1/health` → `{"backend":"litebox-linux-userland","enforcer":true,"ok":true,"version":"0.1.0"}`. Process running (started 17:24 UTC).

## 3. Sandbox interface contract (exact)

```
Governor → liteboxd (HTTP, bearer token)
  prepare(ExecutionManifest) → ExecutionHandle {id, manifest_hash, backend_id}
  start(handle)             → ExecutionResult {exit_code, output_digests: [OutputDigest{name, sha256, bytes}], wall_time_ms, peak_memory_bytes, killed}
  inspect(handle)           → ExecutionEvidence {trace_digest?, events: [EvidenceEvent{ts, kind, detail}], resource_usage: ResourceUsage{wall_time_ms, peak_memory_bytes, peak_fds, peak_pids}}
  kill(handle)              → ExecutionResult
Backend failures are VALUES: BackendError {NotIntegrated, PolicyDenied, ManifestInvalid, ResourceExhausted, LimitExceeded, LaunchFailed, UnknownHandle, Internal} — no panics across the boundary.
```

Honest limits stated in `launcher.rs` header comments:
- Runner CLI has **no host-side output volume**: guest file writes go to in-memory guest FS and die with the process. Host-observable outputs are stdout, stderr, exit code only.
- `peak_memory_bytes` is REAL (per-child `wait4` `ru_maxrss`). `peak_fds` is a sampled maximum (~100ms cadence — stated, not a true peak). `peak_pids` = 0 = unknown (no cgroup; single-process runner).
- NETWORK=DENY on this path is **stated, not emergent**: UDP sendto SUCCEEDS from the guest's view (returns 3, packet silently dropped); TCP connect HANGS (killed by wall-clock SIGKILL). No per-syscall fail-fast at the shim (that would require forking upstream LiteBox — ruled out by doctrine).
- `suspend` is `NotIntegrated`.

## 4. Resource/isolation capabilities — PROVEN vs ASSUMED

| Capability | Status | Evidence |
|---|---|---|
| `prepare` side-effect-free manifest validation + handle mint | **EXISTING AND VERIFIED** | wave-2 lane-2 done receipt (claim "proven"), `litebox_real.rs` integration tests against real runner |
| `start` real sandboxed execution (exit code observed under LiteBox) | **EXISTING AND VERIFIED** | wave-2 lane-2 receipt: no-op guest `exit_group(7)` observed as exit code 7; runner binary present at `target/debug/litebox_runner_linux_userland` (72 MB, built Oct 9 15:48) |
| `kill` SIGKILL + reap, including hung guests | **EXISTING AND VERIFIED** | wave-2 receipt; launcher `kill` documented "always succeeds for a known handle, even mid-hang" |
| Network-deny semantics (UDP silently dropped, TCP wedged until timeout) | **EXISTING AND VERIFIED** | wave-2 lane-2 receipt; netsock/netconnect guest fixtures in `build/execution-backend/guests/` |
| Host-side resource enforcement (rlimits + seccomp-BPF via enforcer_shim) | **EXISTING AND VERIFIED** | `execution-backend/src/enforcer.rs`; wave-3 experiment PROVED the LiteBox config alone did not enforce the envelope (8192 fds vs budget 64, 64 GiB mapped vs 512 MiB, network blackholed not denied) — the enforcer applies `RLIMIT_NOFILE`/`RLIMIT_AS`/`RLIMIT_CPU` + seccomp-BPF syscall deny (EPERM) to the runner child pre-exec, inherited across exec. liteboxd health reports `"enforcer":true` |
| LiteBox-native security boundary on linux_userland (hostile-agent threat model) | **DISPROVEN (as a security claim)** — see below | Source-level assessment `hidden_files/assessment-2026-10-08.md:208`: "CONDITIONAL GO for a cooperative-guest pilot; **NO-GO as a hostile-agent boundary**." linux_userland has **no memory isolation** (guest shares host address space — Microsoft's own crate docs); syscall rewriter is explicitly not a security boundary (JIT'd syscalls bypass); no namespaces/chroot/Landlock; seccomp-BPF allowlist is the only host backstop |
| 5 hostile-fixture containment suite ("contained" verdicts) | **EXISTING BUT UNVERIFIED** | `~/workspace/litebox/litebox/hostile-tests/receipts/*.json`: all five `verdict: "contained"` — BUT: (a) receipt `ts` fields read **2026-09-10**, predating the claimed 2026-10-09 test run by a month — provenance gap; (b) `hostile-tests/bin/` is **empty** locally (fixture binaries absent, cannot re-verify); (c) local clone is on `main`, with the suite as untracked `?? hostile-tests/` — not on the `lucidota` fork branch locally |
| Upstream `cargo test -p litebox --lib` | **MIXED** | Assessment records 108 passed, **24 failed** upstream (main@9e8155f) |
|liteboxd daemon running + healthy | **EXISTING AND VERIFIED** | Live health check this session (above) |
| Generation gate live in production (governor actually routing work through LiteBox today) | **UNKNOWN** | PROVENANCE-ENFORCEMENT.md mandates it (§2 gate 1), but no evidence found that any production lane currently executes through liteboxd |

## 5. Evidence of tension (must not be smoothed over)

1. **Claim vs boundary:** `PROVENANCE-ENFORCEMENT.md` §2 says "Work executes inside the sandbox… An agent cannot produce an output without the sandbox witnessing how it was produced." The source-level assessment says linux_userland is NO-GO as a hostile-agent boundary. These coexist only if "sandbox" means *witnessed execution + receipts for cooperative workloads*, not *malicious-agent containment*. The stronger reading is unsupported.
2. **Adapter-never-fork vs working tree:** the local clone has **uncommitted modifications to upstream LiteBox sources** — `M litebox_shim_linux/Cargo.toml`, `M litebox_shim_linux/src/lib.rs`, `M litebox_shim_linux/src/syscalls/file.rs`, `?? litebox_shim_linux/src/telemetry.rs` — plus untracked `hostile/` and `hostile-tests/`. Whatever the intent, the local tree is currently NOT a pristine upstream + adapter arrangement.
3. **Receipt provenance gap:** the hostile-test receipts' own timestamps (2026-09-10) contradict the claimed test date (2026-10-09). They assert containment without binding to the run that allegedly produced them.

## 6. Key file index

- Trait + manifest + policy: `~/workspace/goals/litebox-library-os-organelle-execution-substrate/build/execution-backend/execution-backend-core/src/{backend,manifest,personality,policy,canon}.rs`
- Launcher (real LiteBox): `.../build/execution-backend/execution-backend/src/litebox/{launcher,adapter,policy,probe,receipt}.rs`
- Governor-side enforcer: `.../build/execution-backend/execution-backend/src/enforcer.rs` (+ `enforcer_shim` helper binary)
- Receipt wiring: `.../build/execution-backend/execution-backend/src/receipt.rs`; adversarial harness: `.../build/adversarial-harness/src/{backend,guest,case,scenario,runner,receipt,mock}.rs`
- Tests: `.../build/execution-backend/execution-backend/tests/{litebox_real,litebox_assess,lifecycle_receipt,enforcer,canon_parity}.rs`; guests: `.../build/execution-backend/guests/{noop,netsock,netconnect,udpsend,memtouch}.S`
- Daemon: `.../build/liteboxd/{src/main.rs,run.sh,guest-store/,state/}`
- Fork/spec docs: `~/workspace/forks/{FORK-STRATEGY.md,DEV-NOTES.md,specs/litebox-SPEC.md}`; goal doctrine: `~/workspace/goals/litebox-library-os-organelle-execution-substrate/GOAL.md`, `hidden_files/{LITEBOX-SPEC-2026-10-08.md,assessment-2026-10-08.md}`, `files/LITEBOX-DEEP-RESEARCH-2026-10-08.md`
- Provenance role: `~/workspace/proof-ledger/PROVENANCE-ENFORCEMENT.md` (§2 gate 1, §3 envelope `execution:` field)
- Honest security characterization: `~/workspace/goals/graph-hacks-2026-context-forge-falkordb-agent/hidden_files/research/net-litebox.md` (+ `net-litebox-usecase2.md`)

## 7. Findings summary (state per finding)

1. **EXISTING AND VERIFIED** — `ExecutionBackend` trait + `ExecutionManifest` + `lucidota-receipt/1` receipt schema implemented in Rust; LiteBox is one implementor behind the trait (adapter-never-fork honored on the production path — subprocess spawn, not linked; experiment crates `path-fuzz`, `dogfood`, `litebox-organelle-host` do link the upstream `litebox` crate as a path dep, with the organelle-host wrapping it in an outer Linux sandbox).
2. **EXISTING AND VERIFIED** — Real launcher runs guests in the actual `litebox_runner_linux_userland` binary (wave-2 evidence); liteboxd daemon live with bearer token + mandatory enforcer (health-verified this session).
3. **EXISTING AND VERIFIED** — Governor-owned host-side enforcement (rlimit + seccomp-BPF) exists precisely because wave-3 proved LiteBox config alone did not enforce the resource envelope.
4. **DISPROVEN as security claim** — linux_userland as a hostile-agent containment boundary. The only characterized boundary is cooperative-guest witnessing + receipts.
5. **EXISTING BUT UNVERIFIED** — The 5 "contained" hostile-fixture receipts (provenance gap + absent binaries).
6. **UNKNOWN** — Whether the provenance generation gate is live on production work today; whether the local `litebox_shim_linux` working-tree modifications are experimental or headed for the fork.
