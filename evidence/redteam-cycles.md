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

---

## CYCLE 5 (2026-10-09)

**New attacks** (not repeating cycles 1-4 or wave 5): governor
receipt verification edges (forged cited receipts, cross-run replay,
policy-version mismatch, malformed oracle verdicts incl.
`verdict=1`, hostile ref paths incl. FIFOs + 32MiB sparse files,
oracle raising BaseException); tier-2 bundle merge gates (exact
within-bound boundary probe, dangling t3_result_refs, zero-member
bundles, duplicate member refs, 10k-ref bundles, wrong-typed evidence,
group_related adversarial incl. 5000-goal groups); driver `--adapter`
recorded-defect fixes + run-dir containment (traversal, absolute
outside cwd, symlink chain attacks, file collision, uncreatable
paths, non-writable dirs, symlink planted inside run dir, foreign
run-receipt).

**150-fixture battery**: 151/151, 3x green (unchanged).

**Confirmed defects FIXED (12)**:

### C4A-001 — SystemExit escaping --adapter instantiation [HIGH]
`driver.py`: `except Exception` around `cls()` let a hostile
`__init__` (e.g. `--adapter sys:exit`) exit the process 0 — silent
success on the `--live` path. Now `except BaseException` ->
`AdapterSpecError`, exit 1, plain stderr. The 2 documenting tests now
assert the fixed behavior.

### C4A-003 — raw provider exception, no usage log [MEDIUM]
`live_adapters.py`: wrapped `_call_provider` -> usage-log line with
status `"error"`, then `AdapterError`. Deliberately `Exception` not
`BaseException`: SystemExit/KeyboardInterrupt still reach
`worker.run_unit` (C4A-002 owns that contract).

### C4A-004 — non-dict provider payload raw AttributeError [LOW]
`live_adapters.py`: isinstance check -> usage-log `"error"` line +
`AdapterError`.

### C5B-001 — cited governor_receipt_ref never verified [HIGH]
`checks.py`: an oracle verdict citing a fabricated/nonexistent
receipt passed on verdict alone. Now a cited ref MUST verify (bounded
read -> JSON -> schema -> `integrity.verify_seal` -> task_id binding
-> `policy_version == router.POLICY_VERSION`) before True is honored.

### C5B-002 — BaseException from oracle escaped raw [HIGH]
`checks.py`: hostile oracle `SystemExit` unwound the interpreter.
Now named failed CheckResult (`oracle_system_exit`); KeyboardInterrupt
-> failed record attached via `exc.add_note`, then re-raised.

### C5B-003 — malformed oracle outputs slipped guards [MEDIUM]
`checks.py`: `verdict=1` slipped `in (True,False,None)`; bad
evidence_refs/measured raised ValueError; unknown keys silently
ignored. Now strict identity verdict check, closed key set, all
malformed shapes -> deterministic failed CheckResults.

### C5B-004 — hostile ref paths [MEDIUM]
`checks.py`: regular-file gate (no open() on FIFOs/devices), chunked
reads capped at 1 MiB, OSError -> named failure.

### C5C-001 — zero-member bundle vacuous pass [HIGH]
`checks.py`: `item_ids=[]` with artifacts consumed -> `passed=True`.
Now fail-closed False, agreeing with
`driver_guards.t2_check_ready`.

### C5C-002 — non-serializable artifact content raw TypeError [MEDIUM]
`checks.py`: now named ValueError.

### C5C-003 — non-dict artifact measured raw AttributeError [MEDIUM]
`checks.py`: now named ValueError ("measured: dict required").

### C5C-004 — within with zero present values crashed [MEDIUM]
`checks.py`: `max([])` ValueError -> degrades to `unknown`
("unmeasurable").

### C5C-005 — group_related silently dropped dangling depends_on [HIGH]
`partition.py`: targets resolving to neither T3 unit nor bundle were
dropped; T2 could pass without the dependency's evidence. Now raises
ValueError naming the dangling targets. Also updated the stale
cycle-2 pin that had locked the old accidental ValueError.

**Run-dir hardening** (`driver.py`, new `_open_run_dir` +
`RunDirError`, wired into run_exec + run_dry_run; write-time symlink
guard in `_write_run_files`): `..` traversal, absolute-outside-cwd,
symlink anywhere in the chain, file collision, uncreatable paths,
non-writable dirs, symlinks planted inside the run dir, foreign
run-receipts -> all plain exit-1 errors, never followed, never
clobbered; same-work-order re-run allowed. 18 driver tests adjusted
(chdir to tmp under pytest). Note: absolute --run-dir outside the
invocation cwd is now a plain error by design (cd there first).

**Recorded (design, not patch)**:
- **R9 [HIGH]**: no authority signature on governor receipts — a
  local file-write attacker can mint a fully-bound, freshly-sealed
  receipt for any task under the current policy. Seal proves
  integrity-since-sealing, not sealer identity (authority-key custody
  still outstanding). Trust boundary = receipt dir
  governor-writable-only, enforced outside this region.
- **R10 [MED]**: cross-run replay undetectable — `router.decide`
  receipts carry no `run_id`; a genuine receipt verifies in any run.
  Needs `run_id` stamped at issuance + binding here. Pinned by a
  documenting test asserting the replay passes.
- R11 [LOW]: FIFO-swap TOCTOU between isfile gate and open();
  accepted residual.
- R12 [LOW]: `decision_hash`/`policy_hash` taken at face value, not
  recomputed (folds into R9).
- R9b [LOW]: `bundle_id`/`unit_id` collide when `work_order_id`
  absent in both orders — content-derived by contract; degenerate
  input.
- R1-R8 (cycles 1-4) still open.

**Behavior locks**: every malformed `--adapter` spec -> plain error,
exit 1, no traceback, no run dir; `--live` without adapter -> plain
error, never fake downgrade; import-time side effects proven to
execute (documented, by design); within-bound boundary pinned
exactly (spread == bound passes, bound+1 fails); duplicate member
refs deduped deterministically; 10k refs in 0.02s; 5000-goal group
-> 1 bundle in 0.01s.

**Suite**: 817 passed + 2 skipped (chmod/read-only probes skip as
root), 3 consecutive full runs. Battery 151/151 x3. 0 provider calls.

---

## CYCLE 6 (2026-10-09)

**New attacks** (not repeating cycles 1-5 or wave 5): deterministic
grammar fuzz over the parser (5000 fixed-seed hostile cases + 300
valid-biased + 300 manifest-conflict + 2000 regex-differential);
hostile artifact content (traversal strings, 10MB, exact-cap/cap+1,
null bytes, lone surrogates, receipt-shaped JSON confused-deputy,
non-string types); artifact write-path containment (`..`,
symlink-to-outside, file-where-dir, pre-planted symlink at target);
retry termination under always-retryable faults + 1000-task retry
storm; AttemptRecord fuzz (21 lookalikes incl. Cyrillic/fullwidth/
zero-width, 7 non-str types, str subclasses).

**Deferred, not executed**: lane 6A (multi-process envelope writers,
byzantine prev_hash, SIGKILL lock release) stopped on its
pre-condition — `shadow.py` had uncommitted PIPE-010 work from a
concurrent lane. Zero attacks run, zero edits; re-dispatch
recommended once shadow.py settles. (Cycle-2 precedent: observed,
not mine, do not touch.)

**150-fixture battery**: 151/151, 3x green (unchanged).

**Confirmed defects FIXED (9)**:

### C6B-001 — spaced-colon trailer raised raw AttributeError [HIGH]
`workorder.py`: `"Group : x"` / `"Done-When : x"` escaped
`parse_workorder` via `# type: ignore[union-attr]` lines. New
`_trailer_value()` splits on first colon — total, never raises.

### C6B-002 — lone surrogate raised UnicodeEncodeError [MED]
`workorder.py`: on the success path at `text.encode("utf-8")`.
Now fail-closed plain error up front.

### C6B-003 — quadratic regex backtracking [MED]
`workorder.py`: two competing `\s*` around the optional `[type]`
group (`"Goal 1"` + 20KB spaces took 0.75s; 10MB would never
finish). `\s*` moved inside the optional group — linear, proven
language-equivalent by 2000-header differential test.

### C6B-004 — unbounded input echo in errors [MED]
`workorder.py`: a 10MB hostile line produced a 10,485,800-char
error string. New `_clip_echo()` (80 chars + `[...truncated]`) on
every attacker-controlled echo in parse/manifest/validate paths.

### C6C-001 — lone-surrogate artifact_text raw UnicodeEncodeError [HIGH]
`worker.py`: escaped `run_unit` (no sealed receipt, no
`fail_dispatch`). Now named failed attempt (`adapter_malformed`).

### C6C-002 — artifact write OSError escaped raw [MED]
`worker.py`: now named failed attempt (`artifact_write_error`)
with sealed receipt.

### C6C-003 — artifact_dir .. wrote outside named dir [MED]
`worker.py`: new `_contained_artifact_path()` resolves the base
first; writes stay inside the resolved base.

### C6C-004 — pre-planted symlink at target followed [HIGH]
`worker.py`: predictable filename (`att-`+12 hex), no symlink
check — proven "PWNED" clobber of an outside file. Now symlink at
target -> `WorkerError` before any dispatch is created.

### C6C-005 — unhashable terminal_state raw TypeError [LOW]
`worker.py`: now fail-closed ValueError for all invalid states.

**Fuzz result**: pre-fix exploratory run found 3166 defects (807
raises, 2359 unbounded echoes) in the 5000-case corpus; post-fix: 0.
Generator + seed (`0xC60B`) embedded in the test file for
reproducibility.

**Recorded (design, not patch)**:
- R13 [LOW]: spaced-colon trailers accepted (completing the old
  key-regex's evident intent); alternative was a plain error. Locked.
- R14 [LOW]: surrogates rejected rather than surrogatepass-encoded
  (keeps source_sha256 over strict UTF-8 bytes).
- R15 [LOW]: no length cap on goal title / group / done_when (spec
  caps objective/body/rules/type-id only) — a 10MB title is valid by
  contract; spec lane may want a cap.
- R16 [LOW]: lowercase `depends-on:` falls through as body line
  while `Note:` -> unknown-trailer error (pre-existing
  inconsistency, unchanged).
- `elapsed_seconds=NaN` sails through the timeout gate
  (`nan > timeout` is False) — inert here; candidate for a
  non-finite-elapsed reject.
- Symlink swapped between containment check and write = accepted
  TOCTOU residual (same class as cycle-5 R11).
- R1-R12 (cycles 1-5) still open; R4 (terminal-vocabulary
  unification) still scheduler-lane work.

**Behavior locks**: spaced-colon trailers parse as trailers;
surrogates -> plain error; regex linear (differential-proven);
error echoes clipped at 80 chars; artifact writes contained;
symlink-at-target -> WorkerError pre-dispatch; retry loop
terminates at dead-letter under always-retryable faults (all
attempt classes x tiers); 1000-task retry storm -> all terminal,
all dead-letters readable; AttemptRecord lookalikes rejected.

**Environment note**: one full-suite run showed 1 failure that never
reproduced (935 green on re-run); a concurrent lane was editing
`live_adapters_test.py` mid-run (test counts varied 928 -> 935
across runs). Verification runs are only meaningful when no other
lane is mid-edit; counts must be stable across the 3x.

**Suite**: 928-935 passed + 3 skipped (root/chmod probes), 3
consecutive full runs green at final count. Battery 151/151 x3.
0 provider calls.

---

## CYCLE 7 (2026-10-09)

**New attacks** (not repeating cycles 1-6 or wave 5): lane 6A
multi-process envelope writers (8 procs x 25 locked appends; writers
SIGKILLed mid-append; byzantine fork/replay/splice/tamper/garbage
prev_hash; SIGKILL while holding LOCK_EX; torn-tail fail-closed);
run-dir isolation under concurrent runs (same-second same-workorder
collision, 4-proc id uniqueness, concurrent dry-runs); falsification
chain (verify racing concurrent appender, truncation, mid-file corrupt
line, caller chain-field injection, legacy-prefix tamper, full rewrite).

**Confirmed defects FIXED (1)**:

### C7B-001 — same-second run_id collision -> run-dir clobber [MED]
`driver.make_run_id` used a second-granularity stamp: two runs of the
same work order starting in the same second got the same run_id -> the
same run dir -> silent last-writer-wins clobber of run-receipt.json /
report.json (the foreign-receipt check passes: same work_order_sha256).
Now microseconds + pid; run_id identifies a RUN, not a work order.
Dead `_utc_stamp()` removed (no other users, grep-proven).

**Confirmed defect, UNPATCHED (out of lane write scope)**:

### C7C-001 — verify_chain torn-read race [MED]
`integrity.verify_chain` reads without the sidecar inter-process lock
while `append_chained` writes under `<name>.lock` LOCK_EX: a verifier
racing an appender can observe a torn tail and report spurious
corruption on a file that verifies clean once appends stop (proven by
intermittent xfail in `test_7c_verify_under_concurrent_append` -- the
final file always verifies). Fix: take LOCK_SH on the sidecar lock in
verify_chain/_read_chunks. integrity.py is outside this lane's write
scope (pipeline/ + evidence only); flagged for a follow-up lane.

**Recorded (design, not patch)**:
- R17: unkeyed hash chains cannot detect truncation (prefix verifies);
  needs an external length anchor.
- R18: mid-file corrupt line bricks verify_chain forever even as valid
  appends continue (fail-closed wins over availability; repair manual).
- R19: full rewrite with recomputed hashes verifies -- unkeyed chains
  are tamper-evident, not tamper-proof; defense is append-only file
  control + external manifests.
- Lane-6A deferred item now EXECUTED: shadow.py locked-I/O layer held
  all 9 attacks (no fork under 8-way writers, byzantine prev_hash
  fails closed at the exact envelope, SIGKILL releases flock via the
  kernel, torn tail skips at tail-read / fails closed at verify).
- compute/queue.py shadows stdlib `queue` under pytest: mp.Queue() is
  unusable in tests (parent breaks at context.py); file-based IPC used.
- Explicit --run-dir reuse across modes with the same work order is
  allowed by design (user asked for that dir); only the accidental
  same-second default-dir collision was a defect.

**Behavior locks**: run_ids unique across processes/microseconds;
two concurrent dry-runs of one work order -> two dirs, both receipts
verify; byzantine prev_hash always fails closed naming the envelope;
caller-supplied _seq/_prev_hash/_record_hash ignored by append_chained;
legacy-prefix tamper detected via genesis anchor.

**150-fixture battery**: 151/151, 3x green (unchanged).

**Suite**: 953 passed + 3 skipped, 3 consecutive full runs green
(1 xfail: C7C-001 race, intermittent). 0 provider calls.

---

## CYCLE 8 (2026-10-09)

**New attacks** (not repeating cycles 1-7 or wave 5): DeepSeek adapter
hostile inputs (5MB prompt cost bomb, cap boundary exact/+1, hostile
envelope shapes, NaN pacing clock, empty-success lock); provider/pool
wiring (mismatch, alias normalization, unknown provider, override
plan); quota crash-recovery (kill with in-flight deepseek reservations,
torn tail, 7 byzantine log lines, double replay, expired-at-replay).
Worktree/tree-edit patch validation: NO code in pipeline/ (lives in
the organelle factory, out of scope) -- no attacks, not a gap in this
repo.

**Confirmed defects FIXED (4)**:

### C8E-001 — live dispatch spent the wrong provider's quota [MED]
`run_exec` hardcoded `provider=None` at the quota guard, so the
`--provider` override never reached pool resolution: a --live DeepSeek
run silently spent the NVIDIA tier pool's quota while calling DeepSeek's
API. Compounded by no DeepSeek pool being seeded at all. Now: canonical
provider namespace (`PROVIDER_CANON`: "gemini-direct"->"gemini" etc.),
`pool_for` normalizes and fails closed on mismatch, the driver passes
the effective provider (--provider wins, else the adapter's
`provider_id`), --provider builds a real override plan, and the
deepseek pool is seeded (limit 6, provenance "adapter-policy",
mirroring the adapter's own <=6 RPM pacing). Bare adapter/plan
mismatches now abort loudly instead of misaccounting.

### DS-1 — unbounded prompt_text cost bomb [MED]
No prompt-length guard: a multi-MB prompt_text was sent to the provider
unbounded. Now fail-closed at MAX_PROMPT_CHARS (256K) via AdapterError,
before any provider call. Covers both adapters (shared _build_prompt).

### DS-2 — _build_prompt raw escapes [LOW]
Unserializable scope / non-dict envelope leaked raw TypeError /
AttributeError instead of the adapter contract's AdapterError
(worker.py contained them as named attempts, but the contract was
violated). Now AdapterError with the cause named.

### DS-3 — _pace fail-open on NaN clock [LOW]
NaN wait skipped the sleep. Now holds the full interval (fail-closed).
Gemini's pacing lives in adapters/gemini.py (out of scope) -- not
checked.

**Recorded (design, not patch)**:
- R20: `_read_text` honors any `raw_output_ref` path from the ex dict.
  Production ex dicts are adapter-built from uuid paths; the only other
  source is the test-only `_generate` seam. Tightening would break the
  seam contract; contain refs to ADAPTERS_DIR/raw if ex ever goes
  untrusted.
- R21: replay_log silently ignores terminal events for unknown
  reservation ids (defensible: idempotent terminals; the log's threat
  model is crashes, not adversarial writers).
- Bare `--live --adapter X` with no --provider now aborts on
  provider/plan mismatch (loud, by design) -- pass --provider explicitly.

**Behavior locks**: prompt cap exact-boundary pinned; empty-success
still refused (CoT guard intact); alias "gemini-direct"->gemini,
"nvidia-nim"->nvidia; unknown provider fails closed; kill-and-replay
restores exact held/consumed; torn tail skipped + anomaly; double replay
is a no-op; expired-at-replay never re-held; idempotency index rebuilt
across crashes.

**150-fixture battery**: 151/151, 3x green (unchanged).

**Suite**: 968-969 passed + 3 skipped (+1 xfail: C7C-001 race),
3 consecutive full runs green. 0 provider calls.

---

## CYCLE 9 (2026-10-09)

**New attacks** (not repeating cycles 1-8 or wave 5): receipt schema
compat (non-dict/missing seal, old schema, extra fields, hostile
attempt entries, wrong-type digest, non-dict receipt); partition
boundary fuzz (seeded 60-trial property fuzz over counts 0..100 +
boundary counts incl. 1000, malformed pw shapes); shadow comparator
adversarial (duplicate actual ids, order-diff games, provider-spoof
matrix, stream-slot collision, unplanned/unexecuted, 500-scale).

**Confirmed defects FIXED (3)**:

### 9B-2 — duplicate singleton bundle ids [HIGH]
`_t2_bundle` keyed singleton ids on `single:{goal_n}`: a subdivided
dependent goal produced one singleton bundle per sub-unit, ALL sharing
a single bundle_id (proven: 5 bundles, 1 id). `schedule_order` indexes
bundles by bundle_id (allocate.py:869), so 4 bundles' t3_result_refs
were lost and inter-bundle ordering broke silently. Now keyed on
goal_ref ("N.a") with fallback to n for undivided goals (historical
ids stable).

### 9A-1 — verify_run_receipt raw AttributeError [MED]
A non-dict "seal" (str/list/int/bool) escaped `.get` as a raw
AttributeError from the verification function. Now "seal_malformed".

### 9B-1 — partition raw AttributeError on malformed pw [MED]
`partition_checklist`/`group_related` raised raw AttributeError when
goals was not a list (or entries not dicts, or pw not a dict). Now
plain ValueError via `_goals_list` (defense in depth; the driver
validates first).

**Spec/code contradiction resolved (docstring, not code)**:

### R23 — PROVIDER_DIFF "both sides" vs fail-loud
`_classify`'s docstring said "PROVIDER_DIFF fires only when both sides
name a provider"; the code fires when the actual names one that
differs (including a silent plan). Contradiction is original (both
written in 79c795f). For a divergence detector the fail-loud direction
is safer -- a named actual against a silent plan IS a plan/reality
divergence -- so the docstring was corrected to the code and the
behavior pinned by test. Coverage predicate unaffected (PROVIDER_DIFF
counts as planned_for either way).

**Recorded (design, not patch)**:
- R22: receipt sealing is O(n^2) (`_append_with_tail` re-reads the
  whole file per receipt): 10k receipts >6 min, 2k >100s. Fine for
  Phase-1 volumes (tens/hundreds); a tail-cache would fix it if
  volumes grow.

**Behavior locks**: old-schema receipts fail closed (schema_mismatch,
never silent verify); extra fields ignored; duplicate actual task_ids
dedupe deterministically; stream slot collision -> first allocation
wins; actuals key stream slots via `slot_id` (not `stream_slot`);
partition invariants hold over the fuzz corpus (unique unit/bundle
ids, no dropped goals, dependents never T3, determinism).

**150-fixture battery**: 151/151, 3x green (unchanged).

**Suite**: 985-986 passed + 3 skipped (+1 xfail: C7C-001 race),
3 consecutive full runs green. 0 provider calls.
