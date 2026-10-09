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

