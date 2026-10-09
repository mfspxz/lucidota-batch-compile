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
