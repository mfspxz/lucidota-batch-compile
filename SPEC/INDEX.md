# SPEC INDEX — Batch-Compile Multi-Tier Scheduler Specification

**Status:** DRAFT index.
**Re-scoped 2026-10-09 per OWNER DIRECTIVE — ARCHITECTURE SIMPLIFICATION,**
as amended by the **TIER MODEL UPDATE** and the **WORK-ORDER INPUT SPEC**
(same day).

Minimal architecture: **Prompts → Typed work order → Partition / Group →
tiered Assign → Schedule → tiered Workers (T3 → T2 → T1) → Ledger →
fixed retry rules → repeat**, with deterministic check ops
(Compare/Calculate, Compare-against-policy, Calculate, Route/Track/Stop).

Tier model (numbering INVERTED — Tier 1 is the TOP; context/responsibility
scope, NOT model capability; N=3, fixed; no fourth tier):
- **Tier 3:** single-check workers (ONE checklist item + inputs/context + output + completion condition)
- **Tier 1:** full-context developer (entire checklist + objective + specs/constraints + Tier 2 results + evidence; owns coherence + final integration)

Scheduler ops: **Partition, Group, Assign, Schedule, Record, Repeat**.
Structural rule: Tier 3 ONLY if performable with supplied context alone;
related/dependent checks stay at Tier 2. Prompts developer-defined/supplied;
scheduler distributes, never authors/judges.

Cut: semantic-judge LLM, validator hierarchies, LLM-debates-LLM,
autonomous objective reinterpretation, LLM glue / LLM merge authority.

---

## 1. The work order is THE interface

**Governing line: the work order defines the requested work; the scheduler
defines its allocation and execution.**

Shape (plain-text prompt; human-written or any-LLM-written, both equally valid):
- **Objective** — one or more lines, verbatim, immutable, never reinterpreted.
- **Development rules** — bulleted rules the workers must follow.
- **Individually numbered Goals** — `Goal 1 [type]: title` + free body;
  each numbered goal is the DEFAULT unit of work. Inline metadata trailers:
  `Depends-On:`, `Group:`, `Done-When:` — or a simple sidecar manifest
  (`<workorder>.manifest.json`); inline↔manifest conflict is a plain error.

Scheduler behavior is deterministic ONLY:
(a) explicit goal boundaries + registered goal types (`pipeline/goaltypes.py`)
construct the work graph; (b) dependencies/metadata inline or sidecar;
(c) the partitioner may split a goal ONLY when its type explicitly permits
subdivision (`maybe_subdivide`, encoded rule); (d) related goals may be grouped
for Tier 2; Tier 1 receives the entire work order; (e) the scheduler NEVER uses
an LLM to author, normalize, or semantically validate the work order —
structural parsing (`pipeline/workorder.py::parse_workorder`) + deterministic
ops only; (f) malformed structure is reported plainly as an error; ambiguous
intent is NEVER silently reinterpreted by a judge model.

Full interface contract: 12-implementation-backlog.md §13 (pinned format +
`lucidota-sched/1#typed-work-order`); requirements R-WO-05…R-WO-11 in 14-traceability.md.

---

## 2. File map — every SPEC file → mission section(s)

Actual files on disk (sibling set landed ~18:48–18:53 UTC; this index
reconciled ~18:55 UTC):

| SPEC file | Mission §12 deliverable (+ related sections) | Author | Tier / work-order relevance |
|---|---|---|---|
| `00-architecture.md` | §12.1 architecture + data-flow diagrams (+§2 DAG) | Sibling | Must show T3→T2→T1 data flow + six scheduler ops |
| `01-evidence-reconciliation.md` | §1 evidence reconciliation | Sibling | — |
| `02-ownership-interfaces.md` | §12.2 component ownership + interfaces (+§5 boundaries) | Sibling | Tier envelope interfaces (T3/T2/T1 scope contracts) |
| `03-schemas.md` | §12.3 versioned data schemas (+§4 contracts) | Sibling | `lucidota-sched/1#typed-work-order`, `lucidota-sched/1#worker-assignment-envelope` (tiers 3/2/1), `lucidota-sched/1#check-result`, `lucidota-sched/1#attempt-record`, `lucidota-sched/1#prompt-record`, `lucidota-sched/1#partitioner-rules` |
| `04-state-transitions.md` | §12.4 state-transition tables (+§2, §6) | Sibling | Tier states + tier boundary gates (T3-pass → T2, T2-pass → T1) |
| `05-scheduler-math.md` | §12.5 scheduler equations + algorithm (+§3) | Sibling | Tiered Assign/Schedule; λ with UNMEASURED symbolic terms labeled |
| `06-provider-matrix.md` | §12.6 provider quota + capability matrix (+§3) | Sibling | Measured-only seeds (f8); no invented quotas |
| `07-pseudocode.md` | §12.7 pseudocode (+§9) | Sibling | Partition/Group/Assign/Schedule/Record/Repeat; deterministic vs model-proposed marked |
| `08-verification-plan.md` | §12.8 test + adversarial verification plan (+§10) | Sibling | Per-tier hostile cases; fake providers + virtual time; never burn real quota |
| `09-observability-runbook.md` | §12.9 observability + operational runbook | Sibling | Tier-tagged events; terminal-state trail replay |
| `10-failure-recovery.md` | §12.10 failure/recovery matrix (+§6) | Sibling | Tier-aware retry table (T1 failure → blocked) |
| `11-migration.md` | §12.11 migration plan | **This lane — DRAFT** | Additive-only; keep/extend/deprecate verdicts; tier-aware module map |
| `12-implementation-backlog.md` | §12.12 backlog + **§13 first dispatchable batch** | **This lane — DRAFT** | PIPE-001…011; goal-type registry; subdivision rule; batch-1 builds the 3-tier working slice |
| `13-unresolved-facts.md` | §12.13 unresolved facts | **This lane — DRAFT** | UF-001…UF-024; unknowns unchanged by re-scope |
| `14-traceability.md` | §12.14 traceability matrix | **This lane — DRAFT** | Tier requirements R-PT/R-AL/R-WK/R-CK; interface requirements R-WO-05…11; D-01…D-08 justified; B-01…B-08 blocked |
| `15-worked-example.md` | §11 numerical worked example | Sibling | Should use measured quotas + tiered flow |
| `INDEX.md` | §13 completion-criterion checklist | **This file** | — |

**Reconciliation notes for siblings:** RESOLVED 2026-10-09 19:05 UTC (coordinator): 12's §13 batch now references the canonical `lucidota-sched/1#<contract>` identifiers from 03-schemas.md §§18/21/20/6/5 — no invented schema names remain in 12 or 14; every emitted record carries `"schema": "lucidota-sched/1#<contract>"`;
05-scheduler-math should respect 14's R-AL-03 (UNMEASURED symbolic terms);
07-pseudocode's Partition/Group/Assign/Schedule/Record/Repeat should match
12's PIPE-003/004/006 and 14's §8 op coverage.

---

## 3. §13 completion-criterion checklist — "an engineer can implement without guessing"

Per-item status under the minimal + tier-model + work-order-spec architecture.

| # | §13 item | Status | Where specified |
|---|---|---|---|
| 1 | **How many requests can run** | SPECIFIED (with labeled unknowns) | Allocator quota math (12: PIPE-004): measured ceilings NVIDIA 39 / Gemini 10 RPM; TPM + concurrency symbolic `UNMEASURED` (UF-007); ai-router caps advisory (UF-009) |
| 2 | **When requests may launch** | SPECIFIED | Reservation (atomic, TTL 120s) → `govern()` consult → adapter bucket acquisition; tier ordering T3→T2→T1 structural (14: R-AL-02) |
| 3 | **How token/concurrency limits interact** | PARTIAL — symbolic | Unmeasured for all providers (UF-007); pacing stays on request-rate ceilings + measured latency bounds; no invented interaction model |
| 4 | **Task flow through tiers** | SPECIFIED | Numbered goals → Partition (T3 single-check, subdivision only by type permission) → Group (T2 check-group, consumes T3 results) → T1 full-context developer (entire work order + T2 results + evidence; owns coherence + final integration); six scheduler ops (12: PIPE-003/004/005; 14: §8) |
| 5 | **Failure retry/termination** | SPECIFIED | Fixed retry table, `MAX_ATTEMPTS=5`, tail requeue, dead-letter; T1 failure → `blocked`; terminal exhaustiveness proven by bound (12: PIPE-009; 14: R-RT-01–03) |
| 6 | **Governor authority enforcement** | SPECIFIED — EXISTING AND VERIFIED | Allocator proposes, `governor.govern()` disposes (11: §2a); compare-against-policy check op (14: R-CK-06); `governor_tests.py` A–R |
| 7 | **Artifact validation** | SPECIFIED — no LLM judge | Deterministic check ops per tier: T3 completion, T2 bounded consistency, T1 coherence + work-order acceptance; goal `Done-When` commands (12: PIPE-007; 14: R-CK-01–05, R-WO-11) |
| 8 | **Graph/sandbox participation** | SPECIFIED — optional | dev-graph `enables` conventions inform (not required by) the partitioner; LiteBox cooperative-witnessing only, never a gate (f7); FalkorDB BLOCKED (B-02); Cap'n Maps BLOCKED (B-01) |
| 9 | **Safe merges** | SPECIFIED | Integration = typed work orders; T1 owns coherence; merge = deterministic checks (tests green) + authorized scope (dispatch-gate); no LLM merge authority (D-05, D-06) |
| 10 | **Final proof** | SPECIFIED — EXISTING AND VERIFIED | Ledger receipts via `ledger.record()` + v1 envelopes (`envelope.wrap`/`verify_chain`); acceptance via `court.derive_status`; `authorized` promotion BLOCKED (B-03) so acceptance stops at `established` + verdict |

**Overall:** items 1, 2, 4, 5, 6, 7, 9, 10 implementable without guessing from
this SPEC set. Item 3 is partial by measurement reality (unknowns labeled, not
papered over). Item 8 is specified-as-optional with blockers named. Per mission
§12: no claim of implementation-readiness where interfaces, quotas,
authorization boundaries, or acceptance criteria are UNKNOWN — those are listed
in 13-unresolved-facts.md, not assumed.

---

## 4. Reading order for an implementer

1. **`INDEX.md`** (§1–§2) — the work-order interface (THE contract) and the map.
2. **`13-unresolved-facts.md`** — what is UNKNOWN/BLOCKED before designing around it.
3. **`11-migration.md`** — what changes, what stays; keep/extend/deprecate
   verdicts; shadow rollout; rollback; worktree rules.
4. **`12-implementation-backlog.md`** — PIPE-001…011 in dependency order;
   then the **§13 first dispatchable batch** (pinned plain-text format +
   `lucidota-sched/1#typed-work-order` + 4 parallel lanes building the 3-tier working slice).
5. **`14-traceability.md`** — requirement → symbol → test for everything
   (R-WO-05…11 for the interface); deprecation candidates with justifications;
   blocked items.
6. **Sibling files 00–10, 15** — architecture, interfaces, schemas, state
   transitions, scheduler math, quota matrix, pseudocode, test plan,
   observability, failure/recovery, worked example. Reconcile per §2 notes.

---

## 5. Standing rules bound to this SPEC set

- Exact discovered symbols only — never invent a second governor / router /
  ledger / scheduler / validator / prompter / partitioner / allocator.
- Measured numbers only (f8). Unknown = symbolic + labeled (UNMEASURED), never invented.
- Migration is additive-only; archive-don't-delete absolute; no destructive git
  ops anywhere (brief-lint gate).
- Cap'n Maps: BLOCKED, no role (B-01 / UF-001).
- The work order defines the requested work; the scheduler defines its allocation
  and execution. Scheduler distributes prompts; never authors/judges (R-PRM-02, R-WO-10).
- No fourth tier (R-WO-04).

---

## Provider use

None — direct synthesis from evidence bundle f1–f8 (no NVIDIA NIM generation,
no Gemini critique), to preserve exact symbol grounding. Fallback per task
authorization ("record `direct` fallback in receipts").
