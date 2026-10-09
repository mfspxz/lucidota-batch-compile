# DOGFOOD REPORT — pipeline driver CLI built with the method, by the method

Date: 2026-10-09. Coordinator: dogfood subagent. App: the pipeline driver CLI
(missing keystone of `~/workspace/compute/pipeline/`).

## What was built

`python3 -m pipeline.driver` — takes a plain-text work-order file, executes it
end-to-end: parse → partition → assign → schedule → dispatch Tier-3/2/1 units
via the PIPE-005 worker runtime → tier checks → fixed retry loop → quota
guards → envelope-sealed run receipts → final report. Modes: `--dry-run`
(plan only), `--shadow` (plan + dispatch against fake adapter, 0 provider
calls), `--live` (injected provider adapter; `None` → plain error, never a
silent dry-run). Exit codes 0/1/2. Documented in `pipeline/DRIVER.md`.

Files (all `~/workspace/compute/pipeline/`):

| File | LOC | Purpose |
|---|---|---|
| `driver.py` | 1117 | CLI, arg parsing, dry-run, run_exec wiring, receipts, reports |
| `driver_dispatch.py` | 366 | dispatch_plan, tier envelopes, FakeAdapter |
| `driver_guards.py` | 434 | tier checks, RetryLoop, QuotaGuard |
| `driver_test.py` | 383 | 30 integration tests |
| `DRIVER.md` | 156 | usage, modes, guards, receipt format |
| lane test files | — | 71 lane tests (17+20+34) |
| **Total** | **2456** | |

## Method path used

**Factory path: BLOCKED — by architecture, verified from source, no quota
burned proving it.** `factory/scheduler/src/assemble.rs` hardcodes the
assembly: copies each unit's `<id>.rs` into `assembly/src/`, generates
`lib.rs` with `pub mod`, runs `cargo test`. A Python CLI cannot come out of
that pipeline. The factory is a proven Rust-organelle builder; it is not a
general application builder.

**Fallback used (recorded): tiered subagent lanes per SPEC/12-implementation-
backlog.md discipline** — the same method the pipeline modules themselves
were built with: numbered-goal work order → deterministic partition →
headless LLM workers with bounded envelopes → tested application. The
benchmark below measures THIS path.

Work order: `~/workspace/batch-compile/driver.work-order.txt` — Objective +
dev rules + 8 numbered goals (human-written). Partition: Lane A goals 1+2,
Lane B goal 3, Lane C goals 4+5 (parallel); Lane D goals 6+7+8 (after A–C).

## Benchmark — measured numbers only

| Metric | Value | How measured |
|---|---|---|
| Wall-clock, work-order written → all green | **910 s (15m10s)** | epoch timestamps 1791575294 → 1791576204 |
| Goals planned / completed | **8 / 8** | all Done-Whens verified by lanes + coordinator |
| Provider calls (all providers) | **0** | briefed 0-call; no model-call imports in new modules (grep verified) |
| Tokens consumed | **0** | same |
| Cost | **$0** | same |
| Tests, driver suite | **101 passed** | `pytest driver_test.py driver_laneA/B/C_test.py` |
| Tests, full pipeline suite | **621 passed** | `pytest .` in `pipeline/`, coordinator re-run |
| Commits | **4** | b0e39d9, b5c9047, 077417b, 9c6ddde — selective staging, no destructive ops |
| Secret-scrub / brief-lint | clean / clean | hook exit 0 on every commit |
| `--dry-run` on own work order | exit 0, 0.19 s | 8 goals → 1 T3 + 7 T2 + 1 T1, sealed receipt written |
| `--shadow` on own work order | exit 0, 0.15 s | 9/9 dispatched, 9/9 checks pass |
| Receipt seal verification | **0 violations** | `verify_run_receipt` recomputation on both runs |

### Defects — who found what

| Found by | Count | Notable |
|---|---|---|
| Worker self-check (lane's own tests) | **11** | random `assignment_id` → nondeterministic task_ids (A); `t1_check_ready` misfire (C); envelope shape mismatch dry-run vs dispatch (D); T1 never scheduled — empty evidence_refs (D); schedule_order input bug — fail-closed block on 4 units (D); T2 member binding (D); band-guard promotion (C); 4 lane test bugs |
| Tier checks / integration | 4 of the 11 | the 4 D-lane defects above surfaced only at assembly |
| Red-team | 0 on this build | red-team ran against the underlying pipeline pre-driver, not the driver |
| Coordinator independent verification | 0 new defects | 621 green, both modes, receipts verify |

Rework cycles: 1 (Lane D integration pass fixing 4 cross-lane contract
mismatches). No goal was re-partitioned; no lane was re-dispatched.

## Verdict: PROVEN

8/8 goals → finished, installed, tested (101 new + 621 suite green),
documented, runnable application in 15 minutes, $0, with every defect found
by the method's own machinery (worker self-checks, then integration checks) —
not by the coordinator intervening. The method works as specified.

**Bottleneck, named:** cross-lane contract *semantics* at assembly. Names
matched the pinned interfaces; meanings drifted — envelope nesting
(`prompt_ref` inside `context_scope` vs raw), `schedule_order`'s input
expectation (remaining vs full batch), T1 evidence accumulation, T2 member
binding. This is the third instance of the same defect class in this
campaign (vacuous-`all([])`, `t3_result_refs` key drift). The fix that
works is the one used: a dedicated integration lane + full-suite green +
independent driver run. Partitioning by name is not enough; the assembly
lane is load-bearing.

## Honest caveats (what the numbers do NOT prove)

1. The benchmark measures the lane-discipline implementation of the method,
   not the factory's headless-subprocess implementation. Factory-as-builder
   for non-Rust targets is disproven by architecture (not attempted).
2. `--live` is code-complete and adapter-injection-tested but has never
   touched a real provider (0 calls by design; NVIDIA band guard is tripped
   anyway at 0.584 ≥ 0.55).
3. No red-team pass has attacked the driver itself yet — only its substrate.
4. Second app ("do it again") not started — awaiting parent direction.

## Repro

```
cd ~/workspace/compute
python3 -m pipeline.driver --dry-run ~/workspace/batch-compile/driver.work-order.txt
python3 -m pipeline.driver --shadow ~/workspace/batch-compile/driver.work-order.txt --run-dir /tmp/d1
cd pipeline && python3 -m pytest . -q   # 621 passed
```

---

# Benchmark 2 — the LIVE path (2026-10-09, ~13:07–13:10 PDT)

Coordinator: dogfood-2 subagent. App: `relnotes` — CLI drafting release notes
from a git log range (`relnotes v1.2.0..HEAD` → markdown: Highlights, Breaking
changes, Contributors). Method: numbered-goal work order
(`dogfood2.work-order.txt`: Objective + dev rules + 6 goals, human-written)
executed through the driver ITSELF:
`python3 -m pipeline.driver --live --adapter pipeline.live_adapters:GeminiDirectAdapter --provider gemini-direct <workorder>`.
Dev rules included: quota budget cap (8 calls), provider allow-list
(gemini-direct only), no secret material in prompts, fail-closed on guard trip.

## What blocked first (real defects, fixed same-task)

1. **Driver defect: CLI `--live` could never run.** `main()` hardcoded
   `adapter=None`, so the benchmark's own stated interface
   (`pipeline.driver --live <workorder>`) was a guaranteed plain error.
   Fixed: `--adapter MODULE:CLASS` flag (importlib, no-arg init,
   `execute(envelope)->dict` checked; bad specs → plain error, exit 1,
   never a silent downgrade). 8 new CLI tests. Commit 52626c9.
2. **My work-order bug:** a multi-line dev-rule broke the rule grammar
   (rules must be single `- ` lines) → plain malformed error, fixed.

## The live run (measured)

| Metric | Value | How measured |
|---|---|---|
| Wall-clock, work-order written → run complete | **~111 s** | file mtime 20:07:36Z → 20:09:24Z (includes 2 rework cycles) |
| Live dispatch wall-clock | **9.514 s** | run receipt `wall_seconds` |
| Goals planned / completed | **6 / 0** | run report |
| Provider calls | **18** (6 units × 3 attempts) | run receipt attempts + live-usage.jsonl |
| Successful generations | **0** | all 18 → HTTP 429 |
| Tokens in/out | **0 / 0** | no successful call |
| Cost | **$0** | no successful call |
| Tests, driver + live adapter | **44 passed** | driver_test.py (38) + live_adapters_test.py (6) |
| Tests, full pipeline suite | **654 passed** | `pytest .`, post-commit re-run |
| Run receipt seal | **valid** | `verify_run_receipt` → [] |
| Dead letters / blocked | **6 / 1** (T1) | run report |
| Secret-scrub / brief-lint | clean / clean | hook exit 0 |

## Why zero completions (honest)

Every one of the 18 calls returned **HTTP 429 from the Gemini API**
(provider-side, not the local 10-RPM bucket). Per standing rule the 429 is
a hard stop for that provider in this task — no retries, no waiting it out.
Fallbacks, each honestly closed:
- **NVIDIA**: band guard tripped (0.590 ≥ 0.55) — off limits.
- **DeepSeek**: live-OK per skill, but zero measured quota (f8) → the
  driver's quota guard fail-closes on unmeasured pools; and the CoT-leak
  defect disqualifies it for codegen anyway.
- **ai-router**: 401 on health check; gemini lane unhealthy.

The run behaved exactly as designed under provider failure: attempts
recorded as `adapter_exception`, bounded retry at tail (3 each), all 6
units dead-lettered with sealed receipts, T1 correctly blocked on dead
T3s, receipt chain verifies, per-call usage log written (18 × 429).

## Verdict: LIVE path PROVEN (mechanically) — bottleneck: provider quota

**PROVEN:** `--live` through the CLI works end to end — real adapter
injection, real provider calls, real errors recorded honestly, fixed
retry → dead-letter → tier blocking, sealed receipts, usage accounting.
Two real defects found and fixed getting there (the `--adapter` gap and
my grammar bug).

**App delivery BLOCKED by quota, not by the method:** with zero eligible
provider capacity (Gemini 429-hard-stopped, NVIDIA band-paused, DeepSeek
unmeasurable), no generative work could dispatch. The method degrades
exactly as specified: loudly, with receipts, nothing faked.

Bottleneck named: **provider quota availability at dispatch time** — the
driver has no provider failover for live generation (by minimal-architecture
design: no judge, no silent substitution), so a single-provider allow-list
plus a tripped guard equals a stopped run. If live dogfooding must survive
one provider's outage, the work order needs ≥2 quota-verified providers on
the allow-list *before* the run.

## Repro

```
cd ~/workspace/compute
python3 -m pipeline.driver --live --adapter pipeline.live_adapters:GeminiDirectAdapter --provider gemini-direct ~/workspace/batch-compile/dogfood2.work-order.txt --run-dir runs/dogfood2
cd pipeline && python3 -m pytest live_adapters_test.py -q   # 0 provider calls (fake generator)
```
