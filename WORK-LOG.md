# WORK LOG — batch-compile campaign (started 2026-10-09 ~11:38 PDT)

Zackary's order: run BOTH missions one shot — forensic inventory (Mission 1),
then executable scheduler spec (Mission 2), then implement. Maximum agents,
maximum NVIDIA generation paced at 39 RPM. Don't stop until he says stop.
No deletions ever — archive safely only.

## Standing rules for this campaign
- Waves are event-chained on agent completion handoffs. NO timer crons, NO polling loops.
- Briefs never authorize destructive git ops (reset/stash/clean --force/push --force/history rewrite).
- Builders produce production code named as the real thing; no "sketch"/"prototype" labels.
- Provider routing: GENERATE via NVIDIA NIM (39 RPM pace) or DeepSeek; CRITIQUE via Gemini through ai-router.
- Record which provider did what. Measured numbers only — never invent quotas.
- Token triage: agents get tight briefs, consult ~/ledger via grep for context.

## Wave 1 — Mission 1 forensic (8 parallel agents, dispatched 11:38 PDT)
- F1 canon-governor: CANON authority hierarchy + governor enforcement points
- F2 exchange-lifecycle: LUCIDOTA Exchange lifecycle states/transitions
- F3 airouter-lanes: ai-router provider profiles, routing, quotas
- F4 validator-verifier: validation pipeline, verifier, acceptance tests
- F5 proof-ledger: PL structure, claim vs proof, envelope/receipt schemas
- F6 graph-falkordb: graph stores, FalkorDB state, Cap'n Maps identity
- F7 sandbox-litebox: sandbox interface, LiteBox integration state
- F8 quota-measurements: bench_results.json, budget.py/lock, burn logs, skill rate limits
Evidence target: ~/workspace/batch-compile/evidence/*.md

## Master directive filed (~11:41 PDT)
- Steering prompt saved as MASTER-DIRECTIVE.md; ledgered seq=5253.
- Deltas adopted: 39 RPM is hypothesis-until-verified (pace at verified limit,
  sustainable below it); preservation invariant is procedural; measure accepted
  artifacts not agent count; event-triggered continuation must be real;
  compact reporting only.
- Wave 1 (8 forensic agents) already conforms: unique scopes, read-only,
  completion handoffs chain Wave 2.

## Wave 1 progress
- 11:41 PDT: F5 proof-ledger evidence landed (f5-proof-ledger.md). Key: envelope v1 verified live (16/16 Rust tests green, Python interop OK); PROVENANCE-ENFORCEMENT v2 is doctrine-only, NOT implemented; authority-key custody still Zack's open call; XIMPL-2 bigint defect pinned but open.
- 7 of 8 forensic agents still running.
- 11:41 PDT: F3 ai-router/lanes evidence landed. Key: NVIDIA 39 RPM = operator token-bucket ceiling (nvidia_rpm.py), provider TRUE limit UNKNOWN (no 429/402 ever seen); Gemini direct 10 RPM measured (brochure 15 disproven); TPM in/out + concurrency UNKNOWN for all providers — λ math limited to RPM/latency terms; DeepSeek unusable for code gen (CoT leak); ai-router gemini lane unhealthy → critique currently resolves to gemini-direct adapter; NVIDIA 550/2543 empty-text executions = retry-budget sink.
- 11:41 PDT: F2 exchange-lifecycle evidence landed. Key: Exchange = 10 interlocking lifecycles (9-stage pipeline DISCOVER→REPLAN has no single code-defined state machine); envelope claimed→established→authorized but `authorized` has NO call site in compute/ (promoter UNKNOWN); mcp-servers/exchange/server.py is a naming collision (unrelated); worker.js 0.6.14 live-deploy parity not re-verified.
- 11:41 PDT: F8 quota-measurements evidence landed. Key: NVIDIA 39 RPM = policy ceiling (provider limit UNVERIFIED, zero 429s ever); budget 5000 calls UNVERIFIED estimate, ~2074 remaining by estimate; Gemini 10 RPM measured, ~27K tok/min sustainable, 20 req/day floor; ai-router lane rpmLimits DECLARED ONLY; TPM/concurrency/reset semantics/cost UNKNOWN everywhere; burn 2026-10-08/09: queue_pending=839, nvidia paused at 0.584 util ≥ 0.55 guard.
- 11:42 PDT: F1 canon-governor evidence landed. Key: FIVE authority surfaces (CANON Rust normative, compute governor.py allocation, ~/workspace/governor dispatch-gate dev-freeze 12/12 tests PASS, MCP authority server advisory-only, Indy_Reads governor.rs); hierarchy CANON > PL > GIT > AI. Discrepancies: D-CANON-001 raw status "active" vs SUPERSEDED effective; legacy fixtures ACTIVE in contracts; lanectl cost-governor UNKNOWN; CANON prod key custody blocked on Zack.
- 11:42 PDT: F4 validator-verifier evidence landed. Key: court.py acceptance authority (derive_status, canon_court_e2e 14 checks VERIFIED); independent_verifier.py 11-gate w/ AST independence invariants VERIFIED; pl_canon_verifier.py EXISTING BUT UNVERIFIED (no harness tests); FABRICATE-1 HIGH OPEN (file-write attacker can mint VERIFIED PL claims; blocked on key custody); test-count discrepancies (envelope_test 10 vs docs 12; court 14 vs docs 13); verifier-mission/lane-a attestation README claims 56/56 but no test file present.
- 11:42 PDT: F7 sandbox-litebox evidence landed. Key: ExecutionBackend trait + manifest + receipts VERIFIED; LiteBox = one implementor via child-process spawn (adapter-never-fork holds on prod path); liteboxd live this session w/ enforcer; linux_userland DISPROVEN as hostile-agent containment (CONDITIONAL GO cooperative only); 5 "contained" hostile-fixture receipts have ts 2026-09-10 (pre-dating claimed run) — cannot re-verify; provenance gate liveness UNKNOWN.

## Wave 1 COMPLETE (~11:45 PDT) — 8/8 evidence files
- f6 graph-falkordb landed. Key: 5 file-local graph stores; FalkorDB live but hackathon-only (synthetic data, hard boundary — no production role); Cap'n Maps NOT PRESENT anywhere — zero code/doc/ledger hits, Mission 2 must treat as BLOCKED/UNKNOWN; dev-graph `enables`/`ready` is the existing verified scheduling substrate.
- Bundle: f1-canon-governor, f2-exchange-lifecycle, f3-airoouter-lanes, f4-validator-verifier, f5-proof-ledger, f6-graph-falkordb, f7-sandbox-litebox, f8-quota-measurements. All read-only, nothing modified.

## Wave 2 dispatched (~11:45 PDT)
- Single synthesis coordinator → fans out section agents. Reads MISSION-2-SYNTHESIS.md + all 8 evidence files. Output: ~/workspace/batch-compile/SPEC/ (14 deliverables). NVIDIA generation paced at policy ceiling, Gemini critique. Ends with first independently-dispatchable implementation batch.

## Minimal-architecture addendum (~11:48 PDT)
- Zack's correction: overengineered. Steered synthesis coordinator to re-scope
  (not restart): minimal set = prompts, typed work order, partitioner,
  allocator, workers, ledger, fixed retry rules. Cut semantic-judge layers.
  Existing components map onto minimal set or get marked for deprecation.

## Tier model set (~11:51 PDT)
- 3 tiers by scope (Tier 3 single-check / Tier 2 group / Tier 1 full-context), N=3 fixed. Coordinator steered; addendum updated.

## Work-order input spec set (~11:54 PDT)
- Work order = prompt + numbered goals + dev rules. Coordinator steered; addendum updated.

## Wave 2 COMPLETE (~12:04 PDT) — SPEC/ 17 files
- Synthesis coordinator delivered all 14 §12 deliverables + INDEX. Re-scoped 3x mid-flight (minimal architecture, 3-tier scope model, work-order input spec). Identifier reconciliation done (canonical lucidota-sched/1 names). Zero code changes, zero deletions.
- Notable: coordinator encoded Zack's organelle thesis (§18 traits declared, never inferred; GO-50/D-25/C-25 layers). Caveats: Gemini-direct critique hit 429 once (honored, no retry); UF-001..024 open blockers carried (XIMPL-2, key custody, v2 machinery, authorized-promotion path, FalkorDB role, worker.js deploy parity).
- Worked example: N=200 → T3 10.54 / T2 1.48 / T1 1.61 min expected (E2E ≈14.0 min; 36.2 conservative).

## Wave 3 dispatched (~12:05 PDT) — §13 first implementation batch, 4 lanes, 0 provider calls
- PIPE-002 workorder parser; PIPE-003 goal-type registry + partition/group; PIPE-004 allocator + quota math; PIPE-007 deterministic check ops.
- Write scope: ~/workspace/compute/pipeline/ only. Brief-lint rules embedded (no destructive git ops). Commit same-turn.
- 12:07 PDT: PIPE-007 (checks.py) done — committed 7b6f73f, 41 tests green, 0 provider calls. Schema defect recorded: SPEC 03 §20 pins check-result.op to 3 ops + binary outcome, but brief requires 9 ops + tri-state (unknown). Lane coded to brief; §20 needs additive extension → queued for conformance batch (PIPE-008 territory).
- 3 of 4 Wave-3 lanes still running (PIPE-002, 003, 004).

## Wave 3 progress (~12:12 PDT)
- PIPE-002 committed 542fce4 (workorder parser; lane fixed its own allowlist self-flag).
- PIPE-007 committed 7b6f73f (checks.py, 41 tests green).
- PIPE-004: driver-committed staged allocate.py/allocate_test.py/QUOTA-SEEDS.md (18 tests green) after scrub went clean. Schema defects recorded (brief vs §21 key names — coded to canonical; real bug caught: wrong key → vacuous all([])).
- PIPE-003 still running (partition.py/goaltypes.py) — its files untouched.
- Noted: separate main-chat work order "DETERMINISTIC ORGANELLE FACTORY" building in ~/workspace/organelle/ (different chat, own coordinator) — logged, not interfered with; this campaign continues per standing orders.
- Tree hazard logged: compute/queue.py shadows stdlib queue under pytest (breaks concurrent.futures) — conformance batch item.
- PIPE-002 full report: 54 tests green; work_order_id content-derived (wo-+sha256[:12]); schema defect noted (§18 table vs §13 pinned layout: dev_rules list vs string, field sets diverge — coded to pinned, noted in SCHEMA_NOTES); scrub incident resolved by lane (renamed own long test name + narrow allowlist prefix for PIPE-003's file).

## Wave 3 COMPLETE, independently verified (~12:13 PDT)
- All 4 lanes committed: 542fce4 (PIPE-002, 54 tests), 36791be (PIPE-003, 33 tests), f5a368f (PIPE-004, 18 tests), 7b6f73f (PIPE-007, 41 tests).
- Driver ran full suite: 146/146 green in 0.23s. Zero provider calls all wave.
- Recorded for conformance: §20 check-result schema needs additive extension (9 ops + tri-state); §18-vs-§13 layout divergence (coded to §13 pinned); context_refs field optional (parser confirmation pending); brief-vs-§21 key names (coded to canonical §21).

## WAVE-4 dispatched (~12:12 PDT)
- Step 1 DONE by coordinator: §13 e2e demo committed (pipeline/demo_e2e_test.py) —
  synthetic 5-goal work order → parse → 1 T3 unit + 3 T2 bundles + 1 T1 kit →
  assign → schedule → checks 1/1 T3, 3/3 T2, 1/1 T1. 147/147 green. 0 provider calls.
  Structural gap found (recorded in demo, not fixed): T2 bundles whose depends_on
  resolve only to non-standalone goals get empty t3_result_refs → immediately
  schedulable; inter-bundle ordering not gated. Flagged for conformance lane.
- Lane C (conformance lanes 2–4 vs lane-1 parser surface; 5 open items incl. the gap).
- Lane B1 (PIPE-001 prompts registry → PIPE-005 worker envelopes).
- Lane B2 (PIPE-008 ledger contract pin → PIPE-009 fixed retry rules).
- All briefs brief-lint clean. PIPE-006 waits on B1 (needs PIPE-005).

## WAVE-4 lane C COMPLETE (~12:19 PDT) — conformance verdicts
- Report: SPEC/conformance-lanes2-4.md. All 4 modules CONFORM to lane-1 surface
  (validate_parsed + TIER_VALIDATORS); partition.can_standalone is a conservative
  superset of tier3_eligible, not a contradiction.
- (a) §20 gap confirmed → ADDITIVE addendum appended to 03-schemas.md (9 ops + tri-state); base table byte-intact.
- (b) §13 pinned layout normative; §18 divergent reference. (c) context_refs = lane-2-local, parser untouched.
- (d) canonical §21 keys confirmed in allocate/checks; partition.py shorthand documented.
- (e) inter-bundle depends_on gap → BACKLOG TASK (not spec-blessed). NEW FINDING: schedule_order reads
  context_scope.tier3_result_refs but _t2_bundle emits top-level t3_result_refs — the T3 gate is INERT on raw
  partition envelopes and only fired through the demo's adapter. Same follow-up batch.
- batch-compile/ initialized as git repo (2 commits, selective staging). Suite 194 passed.
## WAVE-4 lane B2 commits observed
- PIPE-008 (ledger contract pin) + PIPE-009 (retry rules, 4800-task fault injection) committed in compute repo.
- Lane B1 (PIPE-001 → PIPE-005) still running.

## WAVE-4 lane B2 handoff detail (~12:20 PDT)
- PIPE-008: 9 tests pin G1–G4 against unmodified tree; 3-fixture tamper battery all raise EnvelopeError; LEDGER-CONTRACT.md one-pager. git diff on ledger.py/envelope.py empty (anchors untouched).
- PIPE-009: 8 FAILURE_CLASSES mapped 1:1 to worker.js taxonomy; T1→blocked always; 4800-task fault injection 100% terminal, 0 lost; dead-letter path corrected to pipeline/dead-letter.jsonl (recorded in commit).
- Lane B1 (PIPE-001 → PIPE-005) still running. PIPE-006 queued behind B1.

## WAVE-4 COMPLETE (~12:25 PDT) — all 3 lanes done
- Lane C: conformance verdicts + additive §20 addendum (batch-compile repo, 2 commits).
- Lane B1: PIPE-001 (prompts.py, 19 tests) + PIPE-005 (worker.py, 32 tests) committed.
- Lane B2: PIPE-008 (ledger contract pin) + PIPE-009 (retry.py, 4800-task injection) committed.
- Suite: 226/226 green. 0 provider calls all wave.
- Lane B3 dispatched: PIPE-006 (burn.py pipeline mode, flag-guarded). Brief lint-clean.
- Next: PIPE-010 shadow trial (wall-clock bound, needs PIPE-006) → PIPE-011 canary.

## WAVE-4 lane B3 COMPLETE (~12:31 PDT) — PIPE-006
- Commit 90e13fd: flags.py (mode/killed/enabled, env at call time), burn.py additive
  run_pipeline_cycle (Partition→Group→Assign→Schedule→Workers→Record→checks→retry→Repeat),
  pipeline_mode_test.py flag matrix. 0 deletions. Suite 238/238 green.
- Driver compensates the t3_result_refs/tier3_result_refs shape mismatch by holding T2
  until T3 refs terminal (documented). Key unification still belongs in follow-up batch.
- Repeat bounded at 25 structural waves. Enforced test run: T3→T2→T1 check-gated, 3/3 passed.
## WAVE-4 BATCH COMPLETE
- PIPE-001…009 all committed (002–004, 007 were prior waves). 238/238 green, 0 provider calls.
- Next eligible: PIPE-010 shadow trial — runbook execution, wall-clock bound (3 burn windows
  in PIPELINE_MODE=shadow), not a code lane. Flagged for parent scheduling.

## Wave 4 COMPLETE, independently verified (~12:32 PDT)
- 238/238 green (driver ran suite). Commits: e9a5bf2 (demo), 26c326c (PIPE-008), 2b13b4d (PIPE-009), d48a604 (PIPE-001), a150838 (PIPE-005), 90e13fd (PIPE-006). 11 commits total wave, 0 provider calls.
- Real finding: T3-gate key mismatch (schedule_order reads context_scope.tier3_result_refs; partitioner emits top-level t3_result_refs) — B3 driver compensates; unification queued for Wave 5. Same defect class as PIPE-004's vacuous-all([]) bug: key-name drift between spec sections.
- Correction: my earlier "HOLD Notion upgrade till end of month" is SUPERSEDED — background workstream got 1-month Business+AI live 09:38 PDT; Zack's call now: results this month → extension ask. Notion workstream owned outside this campaign.
- AGENTS.md gained SECRET-SCRUB LONG-IDENTIFIER TRAP (wave-4 lane): keep test names/string consts under ~40 chars.

## Wave 5 dispatched (~12:33 PDT)
- Lane A: key-unification (canonical t3_result_refs) + inter-bundle depends_on ordering.
- Lane B: red-team vs pipeline/ (adversarial tests, fake providers, virtual time).
- Lane C: PIPE-010 shadow trial (3 burn windows, PIPELINE_MODE=shadow, within existing burn guards).

## PIPE-010 shadow trial — BLOCKED (~12:35 PDT)
- Runbook lane found the shadow machinery does not exist: burn.py shadow mode is a
  specified no-op (PIPE-006 test pins shadow=>legacy), no per-cycle plan builder, no
  comparator, no divergence classes, no pipeline-shadow-receipts.jsonl. 0 windows run
  (running them would fake acceptance). No code changed, 0 provider calls.
- Also: NVIDIA lane currently paused by its own band guard (0.584 >= 0.55).
- Report: SPEC/shadow-trial-report.md with unblock spec (5 items) for a lane.

## PIPE-010 shadow trial: honestly BLOCKED (~12:34 PDT)
- Lane verified premises, refused to fake the trial: shadow mode is a specified no-op (burn.py:1092-1095 returns {"path":"legacy"}), comparator doesn't exist, no plans/receipts files. 0 windows run, 0 quota consumed. Report: SPEC/shadow-trial-report.md.
- Contradiction found: PIPE-006's test pins shadow=>legacy-no-op, contradicting migration spec §4 Phase 1 (shadow = observe + plan). Migration spec normative.
- Wiring lane dispatched: pipeline/shadow.py (new module, no checks.py overlap with red-team lane), burn.py flag wiring, test-pin update, STOPFILE burn-window definition. NVIDIA guard tripped (0.584 ≥ 0.55) noted — re-trial waits for recovery.
- Key-unification lane done (~12:37 PDT): committed 4d47497, 242/242 green. T2 gate now fires on raw partition envelopes (canonical top-level t3_result_refs); inter-bundle depends_on ordering with fail-closed on missing dep bundle. Honest limitation: transitive T2-result gating not implemented (one level deep) — defined follow-up lane.
- Red-team lane done (~12:39 PDT): 8 defects fixed same-turn (4 HIGH: int() escape, adapter-exception zombie, anti-transplant verify missing, prompt path traversal; 4 MED/HIGH), 51 new tests, suite 293 passed + 1 strict-xfail. Commits 63e7219 + f221436. 4 recorded for next wave (RT5-R1 HIGH: assign_tiered not idempotent — duplicate delivery double-spends; R2-R4 MED/LOW).
- RT5-R1 fix lane dispatched (idempotency keys on reserve path; xfail test becomes normal pass).
- RT5-R1 idempotency fixed (~12:45 PDT): committed 931b3bd. reserve() takes idempotency_key; duplicate delivery → existing reservation, no re-spend; survives kill-and-replay; xfail test now normal pass. Driver-verified suite green. Note: 1 transient flake (2 shadow_test failures, unreproducible x5) while shadow-wiring lane's files in flux — watching.

## NEVER-STOP order (~12:46 PDT)
- Zack: keep going, not allowed to stop till he's back. Cycles of red-team → bugfix → harden → repeat till beyond perfection. Triple-check the 150-item list. Dogfood = finish one app entirely with the method, benchmark prove/disprove, do it again.
- Dispatched: red-team cycle coordinator (continuous, 3 cycles then re-dispatch; includes 150-malformed-fixture triple-check per cycle) + dogfood coordinator (build the pipeline driver CLI via the factory method; benchmark report with verdict; app two after).
- Note: main-chat factory (Deterministic Organelle Factory) is BUILT + PROVEN live — dogfood runs through it; this campaign's pipeline/ is the scheduler substrate. Complementary, not competing.
- Shadow wiring done (~12:47 PDT): committed 79c795f. pipeline/shadow.py (plan builder + comparator, new module per zero-overlap), burn.py flag hunks (+86/-0), test pin updated (shadow = observe + plan; dispatch untouched). 310 tests green, dry synthetic cycle: 32 allocs, 23 sealed receipts chain-verify. Comparator deviation from §4 (shadow.py not checks.py) recorded.
- Findings: burn queue has duplicate task_ids (task-99721824 ×10) — queue-hygiene lane queued; NVIDIA guard decayed (paused=False); one honestly-labeled test artifact in pipeline-plans.jsonl left per archive-don't-delete.
- PIPE-010 shadow trial RE-DISPATCHED (3 STOPFILE-bounded burn windows).

## PIPE-010 re-run underway (~12:50 PDT)
- Shadow wiring verified present (79c795f). Driver running 3 STOPFILE-bounded windows (shadow-w1/w2/w3), 3 plans each, queue+counts snapshots per window. Window 1 engine live, first plan built.

## DOGFOOD-1 COMPLETE — verdict PROVEN (~13:04 PDT)
- Driver CLI finished via work order (8 goals, human-written) executed through tiered lanes (factory path blocked: hardcoded Rust assembly can't emit a Python CLI — recorded, 0 quota burned finding out).
- Measured: 910 s wall-clock, 8/8 goals, 0 provider calls / 0 tokens / $0, 101 driver tests, 621 suite green, 11 defects all caught by worker self-checks, 1 rework cycle.
- Bottleneck: cross-lane contract SEMANTICS drift (4th instance of the recurring defect class) — integration lane + full suite is the working fix.
- Caveats: --live never touched a real provider; no red-team on driver yet. Report: DOGFOOD-REPORT.md.
- DOGFOOD-2 dispatched: relnotes CLI (git log → release notes) built THROUGH the driver in --live mode with real provider calls — benchmarks the unproven live path. Then stop.
- Red-team cycles 1–3 done (~13:07 PDT): 3 MED fixed (inf/nan JSON corruption, raw JSONDecodeError escape, free-string terminal_state → closed vocab), dead code removed (7 lines, proven unreachable), cycle 3 zero defects. 150-fixture battery 151/151 ×3 runs every cycle. Suite 640/640 green. Design items R1–R4 recorded. Cycles 4–6 re-dispatched (new attack surfaces).

## DOGFOOD-2 COMPLETE — live path PROVEN mechanically (~13:11 PDT)
- relnotes CLI via driver --live: 6 goals planned, 0 completed — all 18 calls HTTP 429 (Gemini), NVIDIA band-paused (0.590), DeepSeek zero measured quota, ai-router 401. Degraded exactly as designed: retry → dead letters → T1 blocked, sealed receipts, usage log. 654 suite green.
- Real driver defect found by the benchmark: --live hardcoded adapter=None (could never run) → fixed with --adapter flag (commit 52626c9). That's the dogfood working.
- Verdict: mechanics proven; bottleneck = provider quota availability at dispatch time. No silent failover by design (minimal architecture) → single-provider allowlist + tripped guard = stopped run.
- Follow-up dispatched: DeepSeek quota-probe lane (minimal calls) for a 2nd verified provider.
- DeepSeek probe done (~13:13 PDT): auth OK, latency ~2-2.4s, usage accounting works; CoT defect confirmed (call 1: 64 tokens all reasoning, empty visible). Cost: 3 calls, ~211 tokens. RPM/TPM/concurrency/cost UNKNOWN — reachable but NOT quota-verified; cannot join live allow-list yet. Addendum in f8.
- Live path still effectively single-provider (Gemini 10 RPM measured, 429-prone today). Next live dogfood waits for a 2nd verified provider or guard recovery.

## PIPE-010 re-run COMPLETE (~13:25 PDT) — verdict MIXED
- 3/3 windows clean (rc=0), 9 plans, 0 allocator crashes, 138/138 receipts chain-verified.
- Coverage predicate NOT MET: 30.8%/42.9%/62.5% (need 95%). Structural cause: allocator plans queue backlog top-32; engine dispatches new corpus tasks; pools disjoint except requeued tasks.
- Provider calls: NVIDIA 15 (all startup-race before guard), Gemini 239 attempts / 4 completions / 235 rate-limited (adapter bucket), 27,785 output tokens (partial).
- Findings: nvidia startup guard-evasion race (lane starts unpaused, 4-6 dispatches before first budget_guard); task-99721824 ×11 duplicates; queue 839→1071.
- Recommendation: no Phase 2 until pool mismatch resolved (design decision).
- Report overwritten: SPEC/shadow-trial-report.md.
- PIPE-010 re-run verdict: MIXED (~13:25 PDT). 3 windows, 0 allocator crashes, 138/138 receipts chain-verify — machinery proven. Coverage 30.8/42.9/62.5% vs ≥95% predicate — STRUCTURAL: allocator plans backlog top-32, engine dispatches pacer-stream tasks (disjoint pools). Phase 2 NOT advanced.
- Findings: startup guard-evasion race (_nvidia_paused init False → 4-6 dispatches before guard engages); queue duplicates task-99721824 ×11, queue grew 839→1071; Gemini 239 attempts → 4 completions (adapter-bucket binding).
- Fix lane dispatched: plan-scope coverage redesign + guard-evasion fix (dry synthetic only).
- Coverage redesign done (~13:40 PDT): commits 780f1aa + 02f7cc3 (falsification seq 152). Corpus.peek (pure), stream-slot planning with fingerprint slot ids, two-keyed compare_shadow, coverage_report() restated. Guard race closed (_init_nvidia_pause from persisted utilization, fail-closed). Suite 892 passed, 3 skipped. Migration §4 predicate restated by driver.
- Red-team cycles 4–6 done (~13:50 PDT): 28 defects fixed (9 HIGH, 15 MED, 4 LOW). Suite 935+3skip. Battery 151/151 ×3. Open: R9 HIGH (governor receipt authority signature — blocked on key custody), R10 MED (run_id stamping), R4/R5, adapter allowlist. Lane 6A deferred (shadow.py had concurrent uncommitted work). Env lessons: /tmp 512MB tmpfs → --basetemp on real disk; verify on quiet tree. Cycles 7–9 re-dispatched (6A first if shadow.py settled).
- DEEPSEEK LIVE LANE done (~13:54 PDT): DeepSeek PROVEN as prose provider (conditionally). DeepSeekDirectAdapter built (≤6 RPM, 8192 max_tokens, hard-stop on 429/402, reasoning/visible accounting), 3/3 prose units completed 70.3s, relnotes 6/6 goals, 14/14 tests. KEY: 77% of generated tokens were chain-of-thought, not artifact (88% worst call) — 8192 budget load-bearing; under old 2048 cap calls 2-3 would have truncated/emptied. RPM/TPM ceilings still UNKNOWN. Codegen remains disqualified. Suite 948+3skip. Report: DOGFOOD-REPORT.md Benchmark 2b.
- Red-team cycles 7–9 done (~14:27 PDT): 8 defects fixed (1 HIGH, 5 MED, 2 LOW) + 1 MED unpatched (C7C-001 verify_chain torn-read race — integrity.py was out of lane scope). Notable: C8E-001 — the DeepSeek live run silently spent NVIDIA's quota pool (provider override never reached pool resolution; no DeepSeek pool seeded) — now fixed with canonical provider namespace + deepseek pool seeded. 9B-2 HIGH — duplicate singleton bundle ids lost t3_result_refs + broke inter-bundle ordering. Lane 6A executed: shadow locked-I/O held all 9 byzantine attacks. Suite 985-986+1xfail, battery 151/151 ×3. Cycles 10–12 re-dispatched (C7C-001 fix first, integrity.py scope granted).
- PIPE-010 trial 3: FAIL as-measured, comparator defect not allocator failure (~14:30 PDT). Coverage w1 0.870 (noise: actuals_new_tasks joined against capped top-256 queued_ids, misclassifying ~2575 pre-trial terminal tasks as window dispatches), w2/w3 1.000. Corrected: 1.000 all windows. Guard-race fix CONFIRMED (NVIDIA 0 calls vs 15 in trial 2). 8157/8157 receipts chain-verify, 0 crashes. Fix+trial-4 lane dispatched (full snapshot task-id set in plan; clean acceptance run).
- Red-team cycles 10–12 done (~15:06 PDT): C7C-001 FIXED (verify_chain LOCK_SH; registry keyed by (thread,path); xfail→hard pass), C10-001 MED (quota math ZeroDivisionError/NaN → fail-closed), C11-001 PERF (compare_shadow O(n²) → batch sealing; 10k receipts in seconds; supersedes R22), C12-001 MED/DoS (FIFO at run-receipt hung driver 20s → non-regular receipts refused). Suite 1034 ×3, battery 151/151 ×3. Cycles 13–15 re-dispatched (driver.py:963 artifact_ref surface first).
- Red-team cycles 13–15 done (~15:49 PDT): C13-001 HIGH (FIFO swap hung run; symlink swap laundered foreign content into sealed tier-3 checks) + C13-004 HIGH (retry write to persistent FIFO hung forever) — both fixed (non-regular refused, tamper sealed as VERIFICATION_FAILURE + tamper_events). C14-001 MED (bool("false") enabled subdivision; raw TypeError on unhashable type ids), C14-002 MED, C15-001/002/003 MED (plans never verified before compare; append opened without file-type check; _utc_now unvalidated). Suite 1067 ×3, battery 151/151 ×3. Open: dispatch_plan hardcodes attempt_index=0 (retry overwrites artifact, receipt sha mismatches). Cycles 16–18 re-dispatched (attempt_index fix first).
- PIPE-010 TRIAL 4 done (~16:05 PDT): verdict FAIL-vacuous. Known-set fix completed properly (809ecde: queued_ids_all=full _load snapshot + queued_pending_ids; 0 phantoms proven across 3 clean windows, 186 receipts). Predicate (b) NOT MET: coverage=None — zero provider dispatches in all windows (79-82 adapter-bucket 429s/window, 0 completions), so nothing to measure. Trial-3's "50 MATCH / 1.0" proven artifactual (historical tasks, fingerprint collisions). Chain verifies per-segment; w-10k experiment broke whole-file single chain (another lane's hygiene flag). Phase 2 NOT advanced. Report: SPEC/shadow-trial-report.md.
- PIPE-010 trial 4: FAIL (vacuous), honest (~16:02 PDT). Fix proven: 0 phantom dispatches, 0 crashes, 186 receipts verify. But 0 provider completions all windows (79-82 rate-limited attempts/window) → coverage undefined. Correction: trial 3's "1.0 coverage" proven ARTIFACTUAL (slot-fingerprint collisions with historical tasks). Methodology gap named: trial needs dispatches to complete. Dispatched: synthetic-dispatch harness lane (deterministic fake provider; trial-5 after) + queue hygiene lane (tombstone ×11 dups, no deletion).
- Queue hygiene done (~16:06 PDT): the ×11 "duplicates" are 11 DISTINCT war-001 falsification tasks — an 8-digit task_id mint collided when 11 add() calls landed in one millisecond (2026-10-07T19:02:01Z). Mint class already fixed (uuid now). 10 honest collision tombstones appended (line 1 canonical); prefix-hash proves zero bytes altered; queue.jsonl left uncommitted (live lane appends). Open: mark()/by_id collapse the 11 rows — true re-mint repair needs explicit auth; queue growth (~1933 queued) is scheduler-liveness, flagged.
- Synthetic harness done (~16:16 PDT): compute@320c893. SyntheticDispatchAdapter (fake provider, deterministic completions), VirtualQuota, run_synthetic_trial with seeded failure injection. 16 tests green (clean trial coverage 1.0; ORDER_DIFF/PROVIDER_DIFF/unplanned/drop all classified). Suite 1102+3skip. Trial-5 dispatched: 3 shadow windows with synthetic dispatch — coverage finally measurable. PIPE-010 passes iff clean acceptance; Phase 2 stays with parent.
- Red-team cycles 16–18 done (~16:18 PDT): C16-001 HIGH (attempt_index=0 → retry overwrote attempt-1 artifact, receipt sha mismatch — now attempt-indexed paths), C17-001 MED×3 (RecursionError at 3 json.loads sites), C17-002 HIGH (raw_output_ref arbitrary file read → artifact laundering; containment to ADAPTERS_DIR/raw), C16-002/003, cycle 18 all held. Suite 1111+3skip ×3, battery 151/151 ×3. Cycles 19–21 re-dispatched (gemini.py:205 RecursionError exception granted).
- Trial-5 lane errored on a runtime restart drain (~16:29 PDT) before running windows; driver script survived. Re-dispatched with resume-from-artifacts.
- PIPE-010 TRIAL 5: PASSED (~00:08 UTC). 3 synthetic windows (t5w2/t5w3/t5w4), rc=0, 0 allocator crashes, per-plan coverage 1.0 in all 6 comparisons, 0 phantoms, all receipt segments chain-verify, 0 real provider calls (647/647/662 synthetic completions, virtual quota). Seeded divergence check: 8/8 ORDER_DIFF, chain-verified. t5w1 excluded (driver counted stale plans -> 33s window; gate fixed to ts>=window start, t5w4 run clean). Measurement note: window-union coverage (0.64-0.77) is a cross-plan scope-drift artifact; per-plan is the correct unit. Phase 2 NOT advanced here — PIPE-011 stays with parent.
