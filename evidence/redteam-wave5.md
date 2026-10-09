# RED-TEAM WAVE 5 — adversarial battery vs ~/workspace/compute/pipeline/

Date: 2026-10-09. Lane: red-team. 0 real provider calls (fake adapters,
fake clocks, in-memory coordinators). Suite: 293 passed + 52 new
red-team tests (`redteam_wave5_test.py`: 51 passed, 1 strict-xfail).

## FIXED in this lane (regression tests added, committed same turn)

### RT5-001 — int() ValueError escapes the work-order parser [HIGH]
Repro: `parse_workorder("Objective: x\n\nDevelopment rules:\n- r\n\nGoal " + "9"*5000 + ": T\nbody\n")`
raises `ValueError: Exceeds the limit (4300 digits) for integer string
conversion` — uncaught, violating the module's "no exceptions leak" contract.
Same escape via `Depends-On: <5000 digits>` (`_parse_depends_on`) and via
`can_standalone` with `context_refs=["goal:"+"9"*5000]` (partition.py).
Fix: 19-digit i64 pre-check at all three sites → plain error strings /
fail-closed False. Never an exception.

### RT5-002 — worker-named minter bypass [MEDIUM]
Repro: `reserve(pool, {..., "minter": "Worker-evil"})` → RESERVED;
`"WORKER"`, `None`, `123` also RESERVED. Only lowercase `worker*` was refused.
Fix: case-insensitive prefix check + non-string minters refused
(AUTHORITY_VIOLATION). Legit minters (`allocator`, `pipeline-allocator`,
`governor`) unaffected.

### RT5-003 — raising adapter escapes run_unit, dispatch left zombie [HIGH]
Repro: adapter whose `execute()` raises → `RuntimeError` propagates out of
`run_unit`; no AttemptRecord, no `fail_dispatch`, dispatch stuck "executing".
Fix: `adapter.execute` wrapped → `fail("adapter_exception: ...")` with
fail_dispatch + envelope-sealed receipt. Fail-closed.

### RT5-004 — str artifact_dir crashes run_unit [MEDIUM]
Repro: `run_unit(..., artifact_dir="/tmp/xyz")` → `TypeError: unsupported
operand type(s) for /: 'str' and 'str'` (operator precedence: `or` binds
looser than `/`). Signature promises `str | Path | None`.
Fix: normalize `str` → `Path` before joining.

### RT5-005 — tampered/transplanted receipts undetectable [HIGH]
Finding: the anti-transplant property ("a receipt can never be transplanted
to another envelope") was asserted in docstrings but no verification
function existed anywhere in the tree.
Fix: added `worker.verify_receipt(receipt, envelope, artifact_bytes)` →
list of violations (empty = valid); checks schema, envelope_sha256,
envelope_id, tier, prompt pin, artifact_sha256. Tests: valid verifies;
tampered artifact/seal and cross-envelope transplant all reported.

### RT5-006 — kill-switch refused from unknown state [MEDIUM]
Repro: `route_track_stop({"state": None}, {"op":"stop",...,"to_state":"failed"})`
→ passed=False ("unknown current state"), contradicting the docstring:
"stop is the kill-switch: always permitted into the domain's terminal
states, fail-closed halt." A kill-switch that cannot fire is the dangerous
direction.
Fix: stop → terminal states allowed regardless of current state; all other
ops still fail closed on unknown state. Strengthens, never weakens.

### RT5-007 — CheckResult tri-state hole [LOW]
Repro: `CheckResult(..., passed=1, ...)` accepted (`1 == True` passes the
`in (True, False, None)` membership test). Fix: identity checks
(`is True / is False / is None`).

### RT5-008 — prompt disk-index path traversal [HIGH]
Repro: INDEX.json entry `"path": "../prompts-evil/f.txt"` (or
`"../prompts2/f.txt"`) passed the audit — the containment check was
`str(target).startswith(str(base))`, bypassable by sibling-prefix
("prompts-evil".startswith("prompts")). An attacker-controlled index could
point the audit at bytes matching the registry sha elsewhere, masking a
tampered prompt file in the real dir.
Fix: `target.is_relative_to(base)`.

## VERIFIED (attacked, held — no defect)

- **Quota double-spend race**: 64 threads vs limit-39 pool → exactly 39
  reservations, max held 39. The single-lock claim holds.
- **Reservation expiry mid-flight**: reserve → clock+121s → sweep → expired,
  held freed; late `reconcile` → None, `release` → False (safe no-ops);
  capacity re-reservable. Designed behavior confirmed.
- **Tier 4**: rejected in allocate (`TierViolation`), worker, checks,
  retry, schedule_order; bad values (0, -1, True, "3", 2^63) rejected.
- **Forged bare-boolean evidence**: `CheckResult(passed=True,
  evidence_refs=[True])` → ValueError; policy stub fails forged bare-True.
- **Stale terminal refs**: a forged ref in `schedule_order`'s
  `terminal_results` affects ORDERING only (documented); the downstream
  `check_t2_consistency` still fails closed on missing artifacts. Test locks
  this defense-in-depth.

## RECORDED for the next build wave (not fixed — need design, not patches)

### RT5-R1 — assign_tiered is not idempotent; duplicate delivery double-spends [HIGH]
Repro: `assign_tiered([env], [], None, {}, ...)` twice with the same envelope
→ 2 allocations, `held == 2`, identical `task_id` (stable derivation).
At-least-once delivery of an assignment silently double-spends quota.
Needs idempotency-key support in `reserve()`/assignment flow (design item,
not a one-line patch). Regression test present as strict-xfail:
`test_rt5_duplicate_delivery_single_spend` — it MUST start XPASS-failing
once the fix lands.

### RT5-R2 — rate-1m window never rolls over [MEDIUM]
The pool is seeded `window_kind="rate-1m"` but `QuotaCoordinator` has no
window tracking: it enforces max-39-outstanding-held, not 39/minute.
Reserve+reconcile in a tight loop can exceed 39 "requests" per wall minute.
Pacing currently lives in `nvidia_rpm.py` / driver loops, not here.
Next wave: decide whether the coordinator owns window rollover or the
"rate-1m" label is renamed to what it enforces (outstanding-held ceiling).

### RT5-R3 — t2_envelope binds result keys, not values [MEDIUM]
Repro: `t2_envelope(bundle, {"t3-abc123": {"task_id": "WRONG-UNIT", ...}}, text)`
is accepted — keys must be ⊆ `t3_result_refs`, but a result belonging to a
different unit under the right key is not detected. The Tier-2 worker (an LLM)
then integrates mismatched data; `check_t2_consistency` only re-verifies
declared comparisons. Needs a result↔ref binding field in the result
contract (design item).

### RT5-R4 — terminal_results not run-scoped; stale dict replays completions [LOW]
`schedule_order(allocs, terminal_results)` trusts any present ref key.
A stale dict from a previous run (unit_ids are content-derived, hence
identical across runs) marks T2 bundles schedulable before any worker ran.
Blast radius limited to premature scheduling — check ops still gate —
but the next wave should scope refs by run_id or require result records
carrying run identity.

## Hygiene notes
- No destructive git ops used. Selective staging only (pipeline/ +
  this file); unrelated tree state (envelopes.jsonl modification, untracked
  burn outputs) untouched.
- Write scope honored: `~/workspace/compute/pipeline/` + this file.
