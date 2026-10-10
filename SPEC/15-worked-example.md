# 15 — Numerical Worked Example (mission §11)

**Mission §11 deliverable.** Specification only — no code, no deploys.
Inputs: `05-scheduler-math.md` (equations), `06-provider-matrix.md` (numbers),
`evidence/f3-airoouter-lanes.md`, `evidence/f8-quota-measurements.md`.

**Tier model (owner directive 2026-10-09 — replaces Mission 2 tier language;
numbering INVERTED: Tier 1 is the TOP; N=3 fixed; no fourth tier).** Tiers
defined by **context/responsibility scope, NOT model capability**:
- **Tier 3** — single-check workers (ONE checklist item + inputs/context +
  output + completion condition; max independent parallelism, minimal context).
- **Tier 2** — check-group workers (GROUP of related items + relevant Tier 3
  results + shared context + group output + completion condition).
- **Tier 1** — full-context developer (complete rules + checklist + objective +
  specs/constraints + Tier 2 results + evidence; owns coherence and final
  integration via deterministic Compare merge; bounded regeneration on conflict).

Scheduler ops: **Partition → Group → Assign → Schedule → Record → Repeat**
(fixed retries). **Partitioning rule (structural):** an item goes to Tier 3
ONLY if performable with its supplied context alone; related/dependent checks
stay at Tier 2. Prompts are developer-defined/supplied; the scheduler
distributes, never authors or judges.

## 0. What is measured vs hypothetical

- **MEASURED production facts** (traced to exact files): N=200 corpus scale,
  all RPM ceilings, latencies, reliabilities, budget bands, burn guard,
  context-window capacities.
- **HYPOTHETICAL** (marked `[H]`): the partition split, group size, λ shares,
  Tier-1 latency, context estimates. The arithmetic is fully reproducible;
  swapping any `[H]` value re-derives cleanly.

## 1. Partition

200 checklist items → typed work units. **N = 200 — MEASURED scale anchor**:
`compute/bench_results.json`, `router-differential-001`, 200 tasks,
2026-10-09T09:11:56Z. Applying the structural partitioning rule **[H]**:
- **160 items** performable with their supplied context alone → **Tier 3**
- **40 items** related/dependent (stay together) → **Tier 2**

## 2. Group

The 40 Tier-2 items form **[H] 8 groups of 5** related checks. Each group
bundle carries: its 5 items + relevant Tier-3 results + shared context +
group output contract + completion condition.

## 3. Assign

- **T3 ← 160** single-check units (minimal context each)
- **T2 ← 8** group bundles
- **T1 ← 1** complete kit (full context; context-gate check below)

Allocator shares **[H]** (policy; work-conserving): `x_3 = 0.70`, `x_2 = 0.25`,
`x_1 = 0.05`, summing to 1. Effective per-tier dispatch rates
(`λ_pol = 35/60 = 0.583333/s` sustainable under the 39 RPM policy ceiling):
- `λ_3 = 0.70 × 0.583333 = 0.408333/s`
- `λ_2 = 0.25 × 0.583333 = 0.145833/s`
- `λ_1 = 0.05 × 0.583333 = 0.029167/s`

Constants from evidence (all MEASURED): `p = 1576/2543 = 0.6197`,
`E[A] = 1.6136`, `A_95 = 4` (same measured pool reliability applied to all
tiers — no per-tier reliability measured; stated assumption). Tier-1 latency
`L̄_1 = 60 s`, `L_95,1 = 90 s` **[H]** (full-context pass; probe anchor:
524K input → 26.67 s measured, plus output generation and merge).

**Tier-1 context gate (hard, MEASURED capacity):** the complete kit must fit
`ctx = 524,288` tokens (nemotron-3-super-120b-a12b, `nvidia-usage/capability.json`).
`[H]` kit estimate ≈ 100K tokens (rules + checklist + 8 group outputs + specs +
evidence) → **fits with 5× headroom**. If a future kit exceeds `ctx_m`, Tier 1
cannot schedule on that model — the gate fails closed, never silently truncates.

## 4. Schedule — per-tier makespan

Formulas (`05` §B2–C): `T_3 = N_3·E[A]/(x_3·λ_pol)`,
`T_2 = G·E[A]/(x_2·λ_pol)`, `T_1 = N_1·E[A]·L̄_1` (latency-bound).

| Tier | Units | λ share (req/s) | Expected makespan | Conservative makespan | Binding constraint |
|---|---|---|---|---|---|
| **Tier 3** | 160 | 0.408333 | 160×1.6136/0.408333 = **632.3 s = 10.54 min** | 160×4/0.408333 = **1567.3 s = 26.12 min** | **pace share** `x_3·λ_pol` (request-rate term); token terms UNQUANTIFIED |
| **Tier 2** | 8 groups | 0.145833 | 8×1.6136/0.145833 = **88.5 s = 1.48 min** | 8×4/0.145833 = **219.4 s = 3.66 min** | **pace share** `x_2·λ_pol` **+ dependency gating** (group starts when its Tier-3 results are accepted — streaming) |
| **Tier 1** | 1 | 0.029167 (non-binding) | 1×1.6136×60 = **96.8 s = 1.61 min** | 1×4×90 = **360.0 s = 6.00 min** | **latency** (single task; the 5% rate share would allow a task/34 s — irrelevant for N_1=1) **+ context hard gate** (fits: ~100K [H] ≤ 524,288 measured) |

**Where the binding constraint lands per tier:** Tier 3 → the allocated pace
share (this is the max-parallel throughput term: 632 s of the 818 s expected
total). Tier 2 → pace share plus dependency gating on Tier-3 results.
Tier 1 → latency and the context-window gate; rate is structurally non-binding
for a single integration pass. If Tier 3's share rises, the bottleneck follows
it — see §7.

**E2E (sequential sum — conservative, reproducible):**
expected = 632.3 + 88.5 + 96.8 = **817.6 s = 13.63 min**;
conservative = 1567.3 + 219.4 + 360.0 = **2146.8 s = 35.78 min**.
Streaming overlap (Tier-2 groups starting as their Tier-3 deps land; Tier 1
starting as Tier-2 outputs land) only reduces this.

Deterministic checks (Compare: schema/hash/limit/test + policy gates) overlap
execution and keep pace per `05` §C (`v/v̄ ≥ λ_pol`; `v̄` UNMEASURED → symbolic).
Tier 1's final integration is deterministic Compare merge over the 8 Tier-2
group outputs; on conflict it issues bounded regeneration work orders back
through the Allocator (each with its own K=8 budget) — no judge layer.

## 5. Retry allowance + dead-letter assumptions

- Per-task attempt cap K=8 (MEASURED, Exchange defer ceiling); retries to queue
  tail; queue keeps processing independent work.
- Expected dead-letters: 169 × (1−0.6197)^8 = 169 × 0.00043 = **0.074 → ~0 tasks**.
- Dead-letter: quarantined with full attempt evidence; operator review; never
  silently dropped (accepted / rejected / blocked / cancelled /
  explicitly-unresolved).
- Cooldowns `2^(n−1)` min cap 60 (MEASURED, `worker.js`:67) — not triggered in
  the expected case.

## 6. Cost: projected + maximum (quota units; money $0)

NVIDIA estimate pool: used 2926/5000 = 0.5852 (2026-10-09, MEASURED).

- Projected run calls = 169 × 1.6136 = **272.70** →
  projected util = (2926 + 272.70)/5000 = 3198.70/5000 = **0.6397** →
  **catastrophic_debugging band** [0.60, 0.80)
- Max run calls (K-bounded) = 169 × 8 = **1352** →
  max util = 4278/5000 = **0.8556** → **final_architecture band** [0.80, 0.90);
  dead-letter-bounded, no unbounded tail; the max case needs explicit band
  authorization — never silent.

**Guard interaction (MEASURED):** burn guard pauses the NVIDIA lane at util ≥ 0.55
(`compute/burn.py:90`); current 0.5852 is **above** the guard → the NVIDIA lane is
paused today. This run executes only after the guard clears (util < 0.50) or an
operator-authorized band exception is recorded; otherwise `05` §H halt applies.

## 7. Sensitivity: where the bottleneck moves

- Tier 3 dominates (632 s of 818 s expected). Raising its share `x_3` 0.70 → 0.85:
  `λ_3` = 0.4958/s → T_3 = 258.18/0.4958 = 520.7 s → E2E = 706.0 s = 11.77 min
  (**−13.6%**) — at the expense of Tier-2 share (work-conserving rebalancing
  bounds the loss while Tier-3 backlog exists).
- Raising sustainable pace 35 → 39 RPM: T_3 = 258.18/(0.70×39/60) = 567.4 s
  (−10.3%) — a policy choice spending the safety margin, not free throughput.
- Tier-1 latency `[H]` (60 s) is the second lever; Tier 2 is negligible at this
  group count. Token/concurrency terms remain UNQUANTIFIED: if a TPM probe later
  shows `λ_Tin,3 < 0.4083/s`, Tier 3's binding constraint moves there — the
  equation already contains the term.

## 8. End-to-end rollup

| Stage | Expected | Conservative |
|---|---|---|
| Manifest validation (200 × 113 ms p99, MEASURED) | 0.38 min | 0.38 min |
| Tier 3 — 160 single checks @ 0.4083/s | 10.54 min | 26.12 min |
| Tier 2 — 8 group bundles @ 0.1458/s (streaming) | 1.48 min | 3.66 min |
| Tier 1 — 1 full-context pass (latency-bound) | 1.61 min | 6.00 min |
| Ledger receipts (append-only fold, MEASURED) | ≈ 0 | ≈ 0 |
| **End-to-end (sequential; streaming overlap reduces)** | **≈ 14.0 min** | **≈ 36.2 min** |

## 9. Reproducibility checklist

Another engineer reproduces every number above from:
1. `evidence/f8-quota-measurements.md` — RPM ceilings, latencies, budget bands,
   burn guard, context capacities.
2. `evidence/f3-airoouter-lanes.md` — reliability counts (1576/2543), shared-pool facts.
3. `compute/bench_results.json` — N=200 corpus anchor, 113 ms p99 decision latency.
4. `05-scheduler-math.md` §A–C — the equations (λ split, per-tier makespan);
   `06-provider-matrix.md` — the inputs.
5. `[H]` values restated in §0–§3 — substitute and re-derive.

No number in this file was invented to complete the arithmetic; every UNKNOWN
appears as a labeled `[H]` assumption or a symbolic term, never a filled quota.

---

## Provider use

No provider generation or critique was used in authoring this file. All
arithmetic was computed directly from the evidence bundle and the equations in
`05-scheduler-math.md`; every input traces to an exact source file.
(NVIDIA NIM generation and Gemini critique were authorized but not needed —
this is judgment/verification work.)
