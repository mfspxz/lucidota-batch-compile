# RED-TEAM CYCLES — continuous hardening vs ~/workspace/compute/pipeline/

Coordinator: red-team cycle coordinator, dispatched 2026-10-09 ~12:47 PDT.
0 real provider calls in every cycle (fake providers / virtual time only).
Each cycle: new attacks -> bugfix same-cycle -> harden -> full suite 3x ->
commit. The 150-fixture malformed work-order battery
(`redteam_wo_battery_test.py`) runs 3x per cycle.

Prior work: `redteam-wave5.md` (wave-5 lane: 8 fixed, 4 recorded).

---

## CYCLE 1 (2026-10-09)

**New attacks** (not repeating wave 5): parser unicode/encoding surface
(BOM, zero-width space, arabic-indic + fullwidth digits, fullwidth header,
nbsp), allocator numeric contract (0/-1/1.5/True/"3"/2^63/2^63-1),
retry closed-vocabulary edges, shadow receipt taxonomy, measured-value JSON
validity, partitioner adversarial inputs (200KB single paragraph, 3000-goal
group, unresolvable context refs), 200-deep schedule chain, 10MB line perf.

**150-fixture battery**: 150/150 reject with the exact offending field
named, no exceptions, no guessing. Ran 3x green. (151 tests incl.
hostile-types; 3 runs.)

**Confirmed defects FIXED (2)**:

### C1-001 — non-finite floats in CheckResult.measured emit invalid JSON [MEDIUM]
`measured` only i64-checked `int` values; `float('inf'/'nan')` sailed
through, and `json.dumps` (allow_nan=True) emits `Infinity`/`NaN` —
invalid JSON, corrupting the append-only JSONL receipt contract on
read-back. Fix (checks.py): reject non-finite floats in `__post_init__`;
finite floats still accepted (valid JSON).

### C1-002 — corrupt shadow receipt line escapes as raw JSONDecodeError [MEDIUM]
`shadow.verify_receipts` let `json.loads` raise unwrapped, while
`_read_actuals` in the same module skips-and-counts corrupt lines.
A corrupt receipt line IS a verification failure: it now raises
`ShadowError(ValueError)` naming the line — fail-closed with a
verification verdict, never a codec accident. (Skipping would be wrong
here: a tampered file must not verify its intact remainder silently.)

**Dead code removed**: workorder.py's `if current is None:` stray-line
branch in the goals loop was PROVEN unreachable (the rules loop breaks
only on a `_RE_GOAL` match without consuming it, so the goals loop
always processes a valid goal header first; every gm-branch path assigns
`current`). Stray lines before the first goal surface as "malformed rule
line" from the rules loop — the battery locks this. 7 lines removed,
proof in commit message.

**Behavior locks** (verified deterministic, must keep holding): unicode
digits accepted as goal numbers; BOM -> missing-Objective; `Note:` body
line -> unknown trailer key; duplicate depends-on values preserved;
out-of-order goals accepted + sorted; CRLF valid; allocator numeric
edges (0/-1/1.5/True/"3" -> HARD_CONSTRAINT; 2^63 -> HARD_CONSTRAINT;
2^63-1 -> BUDGET_EXCEEDED); next_action closed vocabulary raises;
huge attempt -> dead_letter (bounded).

**Recorded (design, not patch)**:
- R1 [LOW]: BOM-prefixed input fails as "missing Objective" — consider
  utf-8-sig stripping for human-authored files.
- R2 [LOW]: duplicate depends-on values preserved verbatim — consider
  dedup in the partitioner.
- R3 [LOW]: non-ASCII decimal digits accepted as goal numbers
  (deterministic via int()); document or restrict to ASCII.

**Suite**: 563 passed, 3 consecutive full runs. Commits: battery (150),
cycle-1 attacks (31), fixes C1-001/C1-002, dead-code removal.

---

## CYCLE 2 (2026-10-09)

**New attacks** (not repeating cycle 1 or wave 5): adapter contract edges
(6 malformed variants + mid-run raise), circular bundle dependencies,
self-dep bundle, unknown pool refusal, reconcile-unknown silent noop,
idempotent re-delivery (no double-spend), sweep_expired with virtual time,
non-rpm kind refusal, t2/t3 gate edges, unknown goal type fallback, shadow
govern-crash recording, latest_plan missing file, verify_chain bad
signature.

**150-fixture battery**: 151/151, 3x green (unchanged since cycle 1).

**Confirmed defects FIXED (1)**:

### C2-001 — AttemptRecord accepted any terminal_state string [MEDIUM]
`terminal_state` was a free string field; `"GARBAGE"` was accepted
silently. Downstream, driver.py's `== "completed"` comparisons would
then never match, misrouting a completion as a failure (retry or
dead-letter) with the garbage string as the "failure reason". Fix
(worker.py): `__post_init__` validates against the closed vocabulary
`{running, completed, failed, timeout, dead_letter, blocked}` — derived
from all three producers (worker seal paths, driver_guards "running",
ATTEMPT_TERMINAL values), not invented. driver_guards.apply_terminal_state
already validated its input; the hole was only direct construction.

**Behavior locks**: adapter malformations -> `adapter_malformed` failed
(never a guess, never a crash); circular bundle deps block both, no hang;
unknown pool -> UNAVAILABLE; reconcile unknown id -> silent idempotent
noop; same idempotency key -> same reservation, quota spent once;
sweep_expired frees capacity under virtual-time jump; tpm kind ->
NO_MEASURED_EVIDENCE; govern_fn crash -> per-proposal refusal with the
exception named (better than the crash-evidence path); unknown goal type
-> normal unit (parser can never emit one anyway).

**Recorded (design, not patch)**:
- R4 [MED]: terminal-state vocabularies are inconsistent across layers
  (worker AttemptRecord "completed" vs retry.TERMINAL_STATES "done" vs
  driver_guards values vs queue states). C2-001 closed the constructor
  hole; unifying the vocabularies is design work for the scheduler lane.
- R1-R3 from cycle 1 still open (LOW).

**Observed, not mine (do not touch)**: 2 pre-existing failures in
driver_laneA_test.py (test_shadow_stub_exits_1, test_live_stub_exits_1:
stub driver returns 0 where the test expects exit 1) — proven failing on
HEAD before my change; a driver lane is in-flight (driver.py modified,
driver_test.py + runs/ untracked). Left alone.

**Suite**: 619 passed + 2 pre-existing driver failures, 3 consecutive runs.
Battery 3x green. Commits: cycle-2 attacks (28), fix C2-001.

---

## CYCLE 3 (2026-10-09)

**New attacks** (not repeating cycles 1-2 or wave 5): cross-module
property fuzz (30 seeded trials: parse -> partition -> assign -> schedule),
64-thread reserve race + 16-thread idempotency race, kill-and-replay crash
recovery, idempotency surviving the crash, determinism (stable
work_order_id), double-release, sweep-noop, driver-guard edges, retry-loop
exhaustion, prompt-registry tamper surface (version ordering, tamper,
unknown pin, wrong sha, latest-pin), parser self-dependency/empty-group,
envelope tamper.

**150-fixture battery**: 151/151, 3x green (unchanged since cycle 1).

**Confirmed defects**: NONE. Every attack held. Notable near-misses that
turned out to be my harness bugs (code correct): govern_fn verdict needs
{"allowed": True, "governor_receipt_ref"} (my first fuzz was vacuous --
assertion now requires non-empty allocs); dependent goals correctly route
to tier-2 bundles, not tier-3 units (can_standalone by design); replay
restores seeded pool limits (accounting, not config, by design); a live
reservation re-delivered across a crash keeps held=3 (no double-spend).

**Behavior locks**: 64 threads vs limit-1 -> exactly 1 winner, held never
exceeds 1; idempotency race -> 1 reservation; replay restores held/consumed
exactly; idempotency index survives crash; double-release returns False
without double-free; tampered envelope chain -> EnvelopeError; tampered
prompt re-register rejected; wrong sha at register rejected; unknown
prompt pin -> KeyError; self-depends-on and empty group rejected;
RetryLoop: RETRYABLE@5 -> dead_letter, PERMANENT -> failed.

**Recorded (design, not patch)**: R1-R4 still open (R1 BOM, R2 dup
depends-on, R3 unicode digits, R4 terminal-state vocabulary unification).

**Suite**: 640 passed, 0 failed, 3 consecutive full runs. The 2
driver_laneA failures from cycle 2 are gone -- the driver lane fixed its
own in-flight work; not touched by this cycle. Commits: cycle-3 attacks
(19). 0 provider calls across all 3 cycles.



---

## CYCLE 4 (2026-10-09)

**New attacks** (not repeating cycles 1-3 or wave 5): driver `--live`
`--adapter MODULE:CLASS` injection surface (14 malformed specs, CLI
exit-code/stderr locks, import-time side-effect proof, sys.modules
cache poisoning, fake-seam malformations); quota coordinator crash
recovery (kill -9 in narrowest window via os._exit probes, torn last
line, in-flight holds across restart, double replay, log
deleted/swapped, corrupt middle line); append-only stores under
crash/kill (16-thread concurrent writers incl. 100KB payloads,
envelope chain fork, torn-write kill vs every reader, empty/whitespace
files, reader-racing-writer, wrong-schema/unknown-field receipts).

**150-fixture battery**: 151/151, 3x green (unchanged).

**Confirmed defects FIXED (7)**:

### D4B-001 — replay_log crashed on torn/corrupt log lines [HIGH]
`allocate.py`: `JSONDecodeError`/`KeyError` on any torn/corrupt line
made crash recovery impossible after a mid-append kill. Now
skip-and-count with line numbers in `replay_anomalies`.

### D4B-002 — replay re-held time-expired reservations [MEDIUM]
`allocate.py`: overstated `held` (false `BUDGET_EXCEEDED`) until a
sweep ran. Now TTL-aware at replay; dead holds rebuild as `"expired"`.

### D4B-003 — missing log / unknown-pool reservations silent [LOW]
`allocate.py`: now surfaced via `replay_anomalies` (empty on clean logs).

### C4A-002 — SystemExit/KeyboardInterrupt escaped run_unit [MEDIUM]
`worker.py`: hostile `execute()` raising bare `SystemExit` exited the
process 0 (silent success), no sealed receipt. Now: `SystemExit` ->
named failed attempt (`adapter_system_exit`); `KeyboardInterrupt` ->
attempt recorded failed + `fail_dispatch`, then re-raised (operator
interrupt still aborts, no zombie "executing").

### C4-001 — raw codec exceptions escaping shadow readers [MEDIUM]
`shadow.py`: non-dict JSON -> `AttributeError`, 100k-deep nesting ->
`RecursionError`, invalid UTF-8 -> `UnicodeDecodeError`. Now
`_loads_line()` (ValueError + RecursionError -> corrupt-line signal),
non-dict JSON treated as corrupt, snapshot decode `errors="replace"`;
data readers skip deterministically, verifiers fail closed naming the line.

### C4-002 — authentic-but-wrong-schema receipts verified True [MEDIUM]
`shadow.py`: `verify_receipts` checked authenticity but not schema.
Now `_check_receipt_schema` after `verify_chain`: payload `schema`
must equal `RCPT_SCHEMA`, no unknown top-level fields, `class` in
`DIVERGENCES` — else `ShadowError` naming receipt index + value.

### C4-003 — envelope chain fork under concurrent writers [MEDIUM]
`shadow.py`: two writers sealing onto the same stale `prev_hash`
forked the chain (detection existed, prevention did not). Now
`_append` is a single `os.write` under process-wide thread lock +
advisory `LOCK_EX` (fsync preserved); `_append_with_tail` makes
read-tail->seal->append one critical section; readers snapshot under
`LOCK_SH`.

**Recorded (not patched — file owned by concurrent lane, patch provided)**:
- **C4A-001 [HIGH]**: `_load_cli_adapter`'s `cls()` wrapped in
  `except Exception`; a spec whose `__init__` raises `SystemExit`
  (e.g. `--adapter sys:exit`) escapes raw -> process exits 0 on the
  `--live` path (silent success, inverse of fail-closed). Pinned by 2
  documenting tests. Proposed patch: `except BaseException` around
  `cls()` -> `AdapterSpecError`.
- **C4A-003 [MEDIUM]**: provider exception mid-call escapes
  `GeminiDirectAdapter.execute()` raw (not `AdapterError`), no
  usage-log line (violates "one JSON line per call"). Proposed: wrap
  `_call_provider`, log status `"error"`, raise `AdapterError`.
- **C4A-004 [LOW]**: non-dict provider payload -> raw
  `AttributeError`, no log. Fold into C4A-003 with isinstance check.

**Recorded (design, not patch)**:
- R5 [MED]: no plan-chain verifier — `plans.jsonl` chains
  prev_hash/seal but nothing verifies it.
- R6 [LOW]: crash-recovery contract pinned — tail-read skips torn
  tail, but `verify_receipts` fails closed on the torn line until
  manually removed (auto-skip would let an attacker delete a receipt
  by truncation; repair stays manual by design).
- R7 [LOW]: `claim_id` uniqueness not enforced; concurrent
  `compare_shadow` with identical (window_id, cycle) mints duplicate
  claim IDs.
- R8 [LOW]: advisory `flock` coordinates cooperating writers only; a
  foreign process appending raw bytes can still tear/fork (verify
  fails closed).
- Adapter R5 [MED]: `--adapter` executes arbitrary import-time code
  by design (proven with counter file); consider allowlist or
  adapters-dir restriction.
- Adapter R6 [LOW]: no adapter-side output cap (`MAX_OUTPUT_TOKENS`
  is request-side); enforcement is `worker.MAX_ARTIFACT_CHARS=1M`.
- Adapter R7 [LOW]: `_read_text` follows provider-supplied
  `raw_output_ref` with no size cap (trust boundary = provider).
- R1-R4 (cycles 1-2) still open.

**Behavior locks**: 16 threads x 8 receipts -> zero torn lines
(O_APPEND line atomicity holds empirically); fork DETECTED by
verify_chain; reader-racing-writer -> clean monotone verified
prefixes; kill-in-narrowest-window -> exact replay restore;
TTL-1 sweeps nothing / exactly-TTL expires; double replay is a
no-op; every malformed `--adapter` spec -> plain AdapterSpecError,
exit 1, no traceback, no run dir; `--live` without `--adapter` ->
plain error, never fake-adapter downgrade; import-time side effects
proven to execute (documented, by design).

**Environment note**: `/tmp` is a 512MB tmpfs shared across lanes;
repeated full-suite runs filled it -> phantom ENOSPC failures
(59 failed, pytest INTERNALERROR), none reproducible with space.
Verification used `--basetemp` on real disk. Lanes: route pytest
tmp off /tmp.

**Suite**: 741 passed, 3 consecutive full runs. Battery 151/151 x3.
Commits: cycle-4 attacks + 7 fixes. 0 provider calls.
