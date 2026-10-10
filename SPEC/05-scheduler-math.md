# 05 — Scheduler Mathematics: quota-pool model, reservation semantics, derivations A–H

**Mission §3 deliverable · SPEC §12.5.** Status: specification only — no code, no deploys.
Evidence base: `evidence/f3-airoouter-lanes.md`, `evidence/f8-quota-measurements.md`,
`evidence/f2-exchange-lifecycle.md`, `~/workspace/compute/adapters/*.py`,
`~/workspace/compute/{nvidia_rpm,budget,burn}.py`, `~/workspace/exchange/worker.js`.

## 0. Conventions

- **MEASURED** — a wire- or file-observed value with an exact source citation.
- **DECLARED** — a config/protocol-stated value never observed on the wire. Never promoted to MEASURED.
- **UNKNOWN** — no evidence; appears only as a symbolic term labeled **UNQUANTIFIED**.
- Adapter-enforced RPM ceilings (39 NVIDIA, 10 Gemini) are **policy**, not provider limits.
  The scheduler always paces **below** ceilings (sustainable target ≈ 90% of ceiling).
- The NVIDIA 5000-call figure is an **UNVERIFIED_ESTIMATE** (`nvidia-usage/budget.json`):
  governance band only, never capacity.
- Money cost is $0 on every path in scope (free tiers / keys / keyless lanes).
  "Cost" in this document means **quota units consumed** (calls, requests, tokens).
- **Minimal architecture (owner directive 2026-10-09, takes precedence):**
  Prompts → Typed work order → Partitioner → Allocator → Workers → Ledger →
  fixed retry rules → repeat. Integration is **deterministic merge (Compare)**
  plus **bounded Worker regeneration** on conflict. The Allocator assigns
  eligible units to **Workers only** — no capacity planning for "Tier 2 /
  final glue judging model tiers". CUT: semantic-judge LLM, hierarchy of
  validators, LLM-debates-LLM layers, autonomous reinterpretation of the
  human's objective. Deterministic ops vocabulary used throughout:
  **Compare** = schema/hash/limit/test checks, governor/CANON policy gates,
  deterministic merge; **Calculate** = quota accounting, λ math, band
  utilization; **Route/Track/Stop** = routing decisions, dispatch tracking,
  kill-switch.
- **Tier model (owner directive 2026-10-09 — replaces Mission 2 tier language;
  numbering INVERTED: Tier 1 is the TOP; N=3 fixed; no fourth tier).**
  Tiers are defined by **context/responsibility scope, NOT model capability**:
  - **Tier 3** — single-check workers: ONE checklist item + its inputs/context +
    output + completion condition. Maximize independent parallel work, minimal context.
  - **Tier 2** — check-group workers: GROUP of related items + relevant Tier 3
    results + shared context + group output + completion condition. Combines
    results, local dependencies, bounded in-group inconsistencies.
  - **Tier 1** — full-context developer: complete rules + entire checklist +
    objective + specs/constraints + Tier 2 results + evidence. Owns coherence
    and final integration (deterministic Compare merge over Tier-2 outputs;
    on conflict issues bounded regeneration work orders back through the
    Allocator), cross-group concerns.
  Scheduler ops: **Partition** (checklist → typed units) → **Group** (related
  items → Tier 2 bundles) → **Assign** (T3 ← single checks, T2 ← groups,
  T1 ← complete kit) → **Schedule** (dependencies, capacity, quotas) →
  **Record** → **Repeat** (fixed retries).
  **Partitioning rule (structural):** an item goes to Tier 3 ONLY if performable
  with its supplied context alone; related/dependent checks stay at Tier 2.
  Prompts are developer-defined/supplied; the scheduler distributes, never
  authors or judges.

---

## 1. Quota-pool model: a vector of constraints

A **quota pool** `p` is the unit of contention: `(provider, model, endpoint, credential/account)`.
Pools are never scalars. For each pool the scheduler tracks the constraint vector below.

**Dim 1 — Request rate + window semantics** (`R_p`, `W_p`).
Max requests per window; window semantics: fixed window, sliding window, or token bucket
`(capacity, refill)`.
- NVIDIA direct: `R=39/min` token bucket, `capacity=39`, `refill=39/min`, fcntl-locked,
  disk-persisted — **MEASURED policy** (`compute/nvidia_rpm.py`, `nvidia_rpm_state.json`).
  Provider's true limit **UNKNOWN**.
- Gemini direct: `R=10/min` bucket — **MEASURED policy** (`adapters/gemini_rpm.py`,
  `gemini_rpm_state.json`; probe `gemini-usage/probe-2026-10-08.json`: 4×200 then 503
  at 2 s spacing; brochure 15 RPM NOT demonstrated).
- ai-router lanes: per-lane `rpmLimit` **DECLARED only** (live `/health`:
  15/30/60/10/40/20/15/30/10/30/10/2/2); never measured → **UNVERIFIED**.

**Dim 2 — Input token rate** (`Tin_p`, tok/min). Rolling input-token throughput ceiling.
- NVIDIA: **UNKNOWN — UNQUANTIFIED**.
- Gemini: operational diagnostic only, not a safe limit: ~600–700K tok/10 min then 429;
  sustainable ~27K tok/min with 240 s pacing (ledger seq 5185). **Not a declared limit —
  scheduling treats it as UNKNOWN.**
- ai-router: **UNKNOWN — UNQUANTIFIED**.

**Dim 3 — Output token rate** (`Tout_p`, tok/min). **UNKNOWN — UNQUANTIFIED** for every provider.

**Dim 4 — Context / max-output** (`ctx_p`, `outmax_p`). Per-request hard caps.
- NVIDIA: **MEASURED**: `ctx`: super 524,288 / ultra 393,216
  (`nvidia-usage/capability.json`, `quality/models.json`); `outmax`: 32,000 delivered
  on super (`nvidia-usage/output_ceiling.json`). gpt-oss-20b: `serving_default`
  131,072, observed max null (**UNKNOWN**).
- Gemini: **DECLARED** 1,048,576 (`gemini-usage/models-list.json`); **MEASURED**
  ≥ 7,020 processed @ HTTP 200.
- ai-router: **UNKNOWN** (lane `model` name string only).

**Dim 5 — Concurrency** (`C_p`). Max in-flight requests before provider backpressure.
**UNKNOWN — UNQUANTIFIED** for every provider (burn pacers ran single-flight:
nvidia 1.62 s pooled cadence, gemini 7.06 s synchronous — cadences MEASURED,
concurrency limit never probed).

**Dim 6 — Per-task usage** (`(î_t, ô_t)` estimated / `(i_t, o_t)` actual).
Estimate: task manifest `input_size` vs model's measured `input_capacity_tokens`
gates routing — **MEASURED mechanism** (`compute/router.py::_nvidia_models_for`).
Actual: from the adapter attempt receipt — **MEASURED per attempt**.

**Dim 7 — Shared pools** (`S`). Pools drawing from one account/key budget.
The 39-RPM bucket **and** the 5000-call estimate pool are **account-shared across
super/ultra/gpt-oss-20b** on the direct adapter — **MEASURED** (f3 §1.1).
The ai-router `nvidia` lane (rpmLimit 40, DECLARED) is a *separate enforcement point*
hitting the same provider account → its traffic must be debited against the same
estimate pool (§2.5 coordination rule).

**Dim 8 — Retry / timeout budgets** (`K`, `τ_p`, `B_p`).
Max attempts, per-attempt timeout, per-run retry quota.
`K=8` (mirrors Exchange defer ceiling, `worker.js`:1035 — **MEASURED**);
`τ=300 s` adapter default, NVIDIA (`adapters/nvidia.py` — **MEASURED**).

**Dim 9 — Cooldowns + reset times** (`cd(n)`, `ρ_p`).
`cd(n) = 2^(n-1)` min, cap 60 min (**MEASURED**, `worker.js`:67 THROTTLED);
provider reset semantics **UNKNOWN**.

**Dim 10 — Cost / credit ceiling** (`Q_p`, bands).
- NVIDIA: `Q = 5000` calls **UNVERIFIED_ESTIMATE** (`nvidia-usage/budget.json`).
  Bands **MEASURED** (`compute/budget.py:19-27`): normal_ops `[0, 0.60)` ·
  catastrophic_debugging `[0.60, 0.80)` · final_architecture `[0.80, 0.90)` ·
  capability_research `[0.90, 1.00]`; fail closed at 1.00.
  Burn guard **MEASURED** (`compute/burn.py:90`): pause lane at `≥ 0.55`,
  resume at `< 0.50`. Used 2926/5000 = **0.5852** (2026-10-09,
  `nvidia-usage/calls.jsonl` line count) → above burn guard → **NVIDIA lane
  currently PAUSED**.
- Gemini: **20 `generateContent` requests/day — MEASURED hard floor** (ledger seq 5215).
- ai-router: $0 money; per-lane declared rpm only.

**Dim 11 — Dependency readiness + merge locks** (`deps(t)`, `M`).
`deps(t)` all-accepted before dispatch — **MEASURED** mechanism
(`compute/queue.py`, `compute/router.py`). Merge lock: single writer per
integration branch; merge latency **UNMEASURED → symbolic**.

**Per-task eligibility (measured mechanism, `compute/router.py`):**
model `m` eligible for task `t` iff measured `input_capacity_tokens(m) ≥ t.input_size`;
deterministic order = measured quality desc, then `model_id` ASC.
Unmeasured sources get `UNKNOWN_RELIABILITY_FACTOR = 0.7`, capped and flagged —
never assumed perfect.

---

## 2. Reservation semantics

### 2.1 Atomic reserve-before-dispatch
A dispatch reserves **all** of the following across every pool it touches, atomically:
one request slot, estimated input+output tokens, one concurrency unit, one
attempt-credit draw against `K`, one cost-unit against `Q_p` bands. If any pool
refuses, **all** reservations are released (no partial holds). Over-ceiling calls
are recorded as `rate_limited` executions and **never dispatched** — measured
mechanism (`adapters/nvidia.py::execute()` → `nvidia_rpm.acquire()`; observed
exactly once in 2543 executions, f3 §5).

### 2.2 Reservation expiry
Reservations are leases, mirroring the Exchange: **60 s expiry** (`createLease`,
`worker.js`:767–775 — MEASURED). A reservation not converted to a dispatch within
60 s is released. Execution leases are swept as zombies after **10 min** without a
receipt (`worker.js`:2814–2822 — MEASURED).

### 2.3 Reconciliation with actuals
Reserve on the **estimate** `(î_t, ô_t)`; reconcile on the **actual** `(i_t, o_t)`
from the attempt receipt, releasing the over-reserve. Accounting is written from
**measured cost, never worker assertion** (W6 invariant, f2 lifecycle C — MEASURED).
Routing decisions certify the exact quota they were made under via
`route_with_receipt()` (`"quota_before"`, `"quota_used"` — MEASURED, `compute/router.py`).

### 2.4 Crash recovery
- Fold state (`compute/dispatch.py::_fold_state()`, append-only `dispatches.jsonl` —
  MEASURED) is the source of truth for in-flight work; `executing` reachable only
  from `dispatched` (transition guard, dispatch.py:142–143).
- On restart: expired-lease reservations are released; executions with no receipt
  past the 10-min sweep become **UNCERTAIN** — the provider *may* have executed,
  so the task is **verified before replanned, never blindly retried**
  (W10 invariant — MEASURED).
- Quota buckets are disk-persisted and cross-process safe via `fcntl`
  (`nvidia_rpm.py` — MEASURED); bucket state survives the crash.

### 2.5 Distributed coordination for shared quotas
- The 39-RPM bucket and 5000-call estimate pool are shared across all direct-NVIDIA
  models **and** must absorb ai-router `nvidia`-lane traffic (separate enforcement
  point, same account). Rule: the direct adapter's bucket is the account-wide
  governor; router-lane calls debit the same estimate pool and count toward
  `S`-shared utilization.
- Routing reads quota **ONCE** per decision (`router.py`: "quota is read ONCE by the
  caller" — MEASURED); concurrent dispatchers serialize on the `fcntl`-locked
  bucket files. No second scheduler, router, ledger, or validator is created —
  these reuse the existing Governor/registry/queue/dispatch components.

---

## 3. Derivations

### (A) Homogeneous throughput λ

For homogeneous tasks with mean input `ī`, mean output `ō` (tokens), mean latency
`L̄` (s), on pool `p` with window 60 s:

```
λ_R    = R_p / 60                         (request-rate term, req/s)
λ_Tin  = Tin_p / (ī · 60)                  (input-token term — UNQUANTIFIED)
λ_Tout = Tout_p / (ō · 60)                 (output-token term — UNQUANTIFIED)
λ_C    = C_p / L̄                          (latency/concurrency term — UNQUANTIFIED)
λ_pol  = R_pol / 60                        (policy pace: R_pol < R_p)
λ      = min(λ_R, λ_Tin, λ_Tout, λ_C, λ_pol)
```

Reduction to measured terms (token and concurrency terms stay symbolic):

| Pool | λ_R (measured policy) | λ_pol (sustainable) | λ_Tin, λ_Tout, λ_C | Binding (measured) |
|---|---|---|---|---|
| NVIDIA direct | 39/60 = **0.6500/s** | 35/60 = **0.5833/s** (pace < ceiling; burn pacer observed 1/1.62 s = 0.6173/s — **MEASURED**) | symbolic UNQUANTIFIED | **pacing** — the observed 1.62 s pacer, not latency, bound the last burn |
| Gemini direct | 10/60 = **0.1667/s** | 9/60 = **0.1500/s** (operational pace ~9 RPM, ledger ~5252) | symbolic UNQUANTIFIED | **pacing** per minute; **20 req/day floor** binds sustained campaigns (§F) |
| ai-router lanes | rpmLimit/60 **DECLARED only** → λ_R flagged UNVERIFIED (nvidia lane: 40/60) | pace off measured end-to-end latency only | symbolic UNQUANTIFIED | **reliability** of keyless lanes (pollinations 6/31, llm7 0/15 — MEASURED lane stats, live /health) |

Measured latencies bounding the in-flight window: NVIDIA p50 **20.1 s** / p95 **41.9 s**;
Gemini p50 **2.6 s** / p95 **12.3 s**; ai-router end-to-end p50 **10.8 s** / p95 **19.1 s**
(all from `executions.jsonl`, f3 §4 — MEASURED).

### (B) Heterogeneous scheduling with token variability + model profiles

Model profile `m ∈ {nemotron-3-super-120b-a12b, nemotron-3-ultra-550b-a55b, openai/gpt-oss-20b}`:

```
profile(m) = (L̄_m, r_m, q_m, ctx_m, outmax_m)
```

- `L̄_super`: input-size-dependent, **MEASURED** (`probe-phase1/2.json`): 8K→1.57 s,
  65K→4.32 s, 131K→6.71 s, 262K→11.92 s, 524K→26.67 s (all HTTP 200).
- `r_m`: super/ultra share measured **0.6197** (1576/2543, `executions.jsonl` —
  MEASURED); unmeasured sources use 0.7 capped/flagged (`UNKNOWN_RELIABILITY_FACTOR`
  — MEASURED).
- `q_m`: measured-quality-desc ordering (`router.py` — MEASURED mechanism);
  effective quality = `q_m · r_m` (e.g. 0.93 × 0.59 = 0.55 — MEASURED example, f3 §3).
- Shared-pool constraint: `Σ_m λ_m ≤ R_shared/60`, `R_shared = 39` (policy).
  Fractions `x_m` assigned by deterministic eligibility order;
  per-model rate `λ_m = x_m · λ_pol`.

Token variability: per-task `î_t` from the manifest distribution; the scheduler
reserves at the **p95 estimate** `î_95` and reconciles to actual `i_t` on receipt
(§2.3). The input-token term uses `î_95`:

```
λ_Tin^cons = Tin_p / (î_95 · 60)          — UNQUANTIFIED (Tin unknown, formula only)
```

Context gate is hard, not statistical: `î_t ≤ ctx_m` or the model is ineligible
(measured gate, §1 dim 6).

### (B2) Tiered assignment: how λ splits across tiers

The Allocator assigns the shared pool rate across the three context-scope tiers
with shares `x_3 + x_2 + x_1 = 1` (policy; work-conserving — idle share
redistributes to backlogged tiers). Per-tier throughput:

```
λ_j = min( x_j · λ_R , λ_Tin,j^u , λ_Tout,j^u , λ_C,j^u , x_j · λ_pol )    j ∈ {3,2,1}
```

- **Tier 3** (N_3 single-check units, minimal context): the max-parallel term.
  Binding = the allocated pace share `x_3 · λ_pol` (request-rate term).
  Token footprint smallest; token terms UNQUANTIFIED.
- **Tier 2** (G group bundles; group g consumes its Tier-3 results):
  binding = the pace share `x_2 · λ_pol`, **plus dependency gating** — group g
  starts only when its Tier-3 dependencies are accepted (streaming, not
  batch-gated). Larger per-task input (shared context + Tier-3 results);
  token terms symbolic.
- **Tier 1** (N_1 full-context passes, N_1 small — typically 1): binding =
  **latency, not rate** — for N_1 = 1 the rate share is non-binding; the task
  takes `E[A]_1 · L̄_1`. Plus the **context hard gate**: `î_1 ≤ ctx_m`
  (measured: 524,288 for nemotron-3-super-120b-a12b) — the full kit
  (rules + checklist + objective + specs + Tier-2 results + evidence) must fit,
  or the run cannot schedule Tier 1 on that model. Tier 1 owns coherence and
  final integration: deterministic Compare merge over Tier-2 outputs; on
  conflict it issues bounded regeneration work orders back through the
  Allocator (to Tier 3 or Tier 2 as appropriate), each with its own K-attempt
  budget — no unbounded loops, no judge layer.

### (C) Per-tier expected + conservative makespan

```
T_3^exp  = N_3 · E[A]_3 / (x_3 · λ_pol)        T_3^cons = N_3 · A_95,3 / (x_3 · λ_pol)
T_2^exp  = G · E[A]_2 / (x_2 · λ_pol)          T_2^cons = G · A_95,2 / (x_2 · λ_pol)
T_1^exp  = N_1 · E[A]_1 · L̄_1                 (latency-bound; L̄_1 [H] — UNMEASURED)
T_1^cons = N_1 · A_95,1 · L_95,1              (L_95,1 [H] — UNMEASURED)
```

Deterministic checks (Compare: schema/hash/limit/test + policy gates) overlap
execution: with `v` parallel checkers each taking `v̄` s/artifact, checks keep
pace iff `v / v̄ ≥ λ_pol`. `v̄` is **UNMEASURED** → symbolic. E2E makespan is the
sequential sum `T_3 + T_2 + T_1` (conservative, reproducible); streaming overlap
(Tier-2 groups starting as their Tier-3 deps land; Tier 1 starting as Tier-2
outputs land) only reduces it. Regeneration allowance: conflicts re-enter as
fresh work orders inside the same tiered terms. (Numerics in
`15-worked-example.md`.)

### (D) Retry overhead

**Measured reliability** (`executions.jsonl` — MEASURED):

| Source | n | success | invalid (empty text) | error | adapter-refused |
|---|---|---|---|---|---|
| nvidia-nim-hosted | 2543 | 1576 → **p = 0.6197** | 550 (retryable BAD_RESPONSE) | 416 | 1 |
| gemini-direct | 1121 | 18 | 4 | 16 | **1083** (bucket working, zero provider cost) |
| ai-router-free | 108 | 104 → **p = 0.9630** | — | 4 | — |

Gemini provider-attempt success (excluding adapter refusals, which never dispatch):
`p_g = 18/(18+16+4) = 0.4737`.

**Assumptions (stated):** attempts independent with constant `p`; `invalid`
(empty/no-extractable text) is **retryable** (BAD_RESPONSE → RETRYABLE_FAILURE,
f2 taxonomy); adapter refusals consume **zero** provider quota (queue time only);
max attempts `K = 8` (Exchange defer ceiling — MEASURED); per-attempt timeout
`τ = 300 s` (NVIDIA adapter default — MEASURED).

```
E[A]   = 1/p                                    (geometric, unbounded)
E[A|K] = (1 − (1−p)^K) / p                      (capped at K attempts)
A_95   = ceil( ln(0.05) / ln(1−p) )             (attempts covering 95% of tasks)
Quota consumed (expected) = E[A|K] × (1 request slot + î_t + ô_t est. tokens)
Worst case per task       = K attempts → K × (slot + tokens)   (bounded)
Dead-letter probability   = (1−p)^K            (task dead-letters after K)
```

Numerics:

| Source | p | E[A] | E[A\|K=8] | A_95 | Dead-letter prob (1−p)^8 |
|---|---|---|---|---|---|
| NVIDIA | 0.6197 | **1.6136** | 1.6129 | **4** | 0.00043 (0.04%) |
| Gemini (provider) | 0.4737 | **2.1111** | 2.0985 | **5** | 0.0059 (0.6%) |
| ai-router | 0.9630 | **1.0384** | 1.0384 | **2** | ≈ 0 |

Expected added latency per task from retries (E[A] × p50):
NVIDIA 1.6136 × 20.1 s = **32.4 s**; Gemini 2.1111 × 2.6 s = **5.5 s**;
ai-router 1.0384 × 10.8 s = **11.2 s**.
Conservative (A_95 × p95): NVIDIA 4 × 41.9 = 167.6 s; Gemini 5 × 12.3 = 61.5 s;
ai-router 2 × 19.1 = 38.2 s.
Cooldowns add `cd(n) = 2^(n−1)` min (cap 60) per consecutive provider-class failure —
MEASURED mechanism (`worker.js`:67); consecutive-failure counter per pool, reset on success.

### (E) End-to-end time with validation overlap

```
T_e2e = T_manifest + Σ_j T_j + T_glue + T_verify + T_merge + T_recovery
        − overlap(dispatch, validation) − overlap(tier_j, tier_{j+1} prep)
```

- `T_manifest`: manifest validation (CANON/scope/policy/acceptance) — deterministic,
  bounded by decision latency p99 **113 ms**/decision (MEASURED, `bench_results.json`).
- `overlap(dispatch, validation)`: validation starts on first artifact, not at tier
  end; net validation cost = `max(0, T_val,j − T_dispatch,j)` (Little's-law bound).
- Tier-2 groups start when their Tier-3 dependencies are accepted; Tier 1 starts
  when Tier-2 group outputs are accepted — streaming, not batch-gated.
- `T_recovery`: zombie sweep (10 min) + UNCERTAIN verification + replan — budgeted as
  `P(zombie) × 600 s`; `P(zombie)` **UNMEASURED** → symbolic.

### (F) Cost: projected + maximum

Quota-unit accounting (money $0 everywhere):

**NVIDIA** — `Q = 5000` calls UNVERIFIED_ESTIMATE; used 2926 → remaining ≈ 2074
**by estimate only**; utilization 0.5852.

```
projected_run_calls = Σ_j N_j · E[A|K=8]_nvidia
max_run_calls       = Σ_j N_j · K            (dead-letter bounded)
projected_util      = (2926 + projected_run_calls) / 5000
max_util            = (2926 + max_run_calls) / 5000
```

Band enforcement: scheduler refuses NVIDIA dispatch when `projected_util ≥ 0.60`
(normal_ops ceiling) unless the run's band authorization explicitly covers a higher
band; **hard fail-closed at 1.00** (estimate exhausted). Burn guard is stricter:
pause at `≥ 0.55`, resume `< 0.50` (**MEASURED**, `burn.py:90`) — current 0.5852 is
**above** the guard: the NVIDIA lane is paused until the guard clears or an
operator-authorized band exception is recorded.

**Gemini** — 20 req/day **hard floor** (MEASURED): `max_provider_calls/day = 20`.
Adapter refusals cost 0. Sustained campaigns: `days ≥ ceil(total_calls / 20)`.

**ai-router** — $0 money; declared per-lane rpm (UNVERIFIED); live lane reliability
stats from `/health` (MEASURED as observed: nvidia 152/16, kilo 46/28,
pollinations 6/31, ovh 4/26, llm7 0/15).

### (G) Sensitivity: the bottleneck parameter

Binding term per pool (from (A) with measured values):

1. **NVIDIA direct**: binding = **policy pace** `λ_pol = 0.5833/s` (35/min sustainable
   under the 39 ceiling). Sensitivity: `dλ/dR_pol = 1/60`; raising sustainable pace
   35 → 39 RPM cuts dispatch makespan ~10.3% but burns the safety margin the ceiling
   exists for — **policy decision, not free throughput**. Token/concurrency terms are
   UNQUANTIFIED: if a TPM probe later shows `λ_Tin < 0.5833/s`, the bottleneck moves
   there — the equation already contains the term; only the number is missing.
2. **Gemini direct**: binding = **20 req/day floor** for any campaign > 20 calls;
   per-minute binding = 10-RPM adapter ceiling. `d(days)/d(calls) = 1/20`.
3. **ai-router**: binding = **lane reliability** (keyless lanes: pollinations 19%
   lifetime success, llm7 0%) and DECLARED-not-measured caps — derate by measured
   reliability (`q·r`); never pace off `rpmLimit`.

Throughput moves 1:1 with the binding term until the next constraint binds —
that is the whole content of the `min(...)` in (A).

### (H) Replanning + failover rules

| Trigger (measured signal) | Action | Preserved |
|---|---|---|
| Adapter refusal rate rising / first provider 429 | `set_rpm_limit()` to the lower discovered limit (**MEASURED** mechanism, `nvidia_rpm.py`); pool → THROTTLED, `cd(n)=2^(n−1)` min cap 60 | Policy snapshot, quota receipts, evidence chain |
| Pool EXHAUSTED (band ≥ 1.00, Gemini 20/day spent) | Fail over to next eligible pool per deterministic order; suspend pool until recheck (5 min — MEASURED, `worker.js`:67) | `route_with_receipt()` quota_before/quota_used; attempt history; task identity stable across attempts |
| Lane `healthy=false` (ai-router precedent: gemini lane `configured=false`) | Lane removed from eligibility; in-flight tasks → UNCERTAIN → verify-before-replan (W10) | Claim/lease binding; no blind retry of possibly-executed work |
| Utilization ≥ 0.55 (burn guard) | Pause NVIDIA lane; resume < 0.50 | Queue keeps processing independent work on other pools; retries go to tail |
| Governor/ledger/validator unavailable | **Fail closed** — no dispatch, no self-accept (mission §4: a response must never self-accept, raise its own budget, or authorize a tool) | Nothing dispatched on missing authority |
| Kill-switch | Running requests cancelled; reserved quota released; partial artifacts retained as evidence, never merged | Receipts for every state change |

Replanning never invents quota: every rate change is a **measured** response
(429 seen, refusal rate measured, band computed from the estimate) or a **policy**
choice recorded with its authorization — never a filled-in UNKNOWN.

---

## Provider use

No provider generation or critique was used in authoring this file. The mathematics
were derived directly from the evidence bundle (f2/f3/f8) and the cited source files;
every number traces to an exact file. (NVIDIA NIM generation and Gemini critique
were authorized but not needed — this is judgment/verification work, and
provider-generated prose risks unattributed numbers.)
