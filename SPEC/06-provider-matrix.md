# 06 — Provider Quota + Capability Matrix (§12.6)

**Mission §3/§11 support deliverable · SPEC §12.6.** Specification only — no code, no deploys.
Evidence base: `evidence/f3-airoouter-lanes.md`, `evidence/f8-quota-measurements.md`,
`~/workspace/compute/adapters/*.py`, `~/workspace/{nvidia,gemini}-usage/`.

## 0. Reading guide

- Each cell is tagged **MEASURED** (wire/file-observed, exact source) /
  **DECLARED** (config-stated, never observed) / **UNKNOWN** (no evidence).
- RPM ceilings of 39 (NVIDIA) and 10 (Gemini) are **adapter-enforced policy**,
  not provider-published limits. The scheduler paces **below** them.
- TPM in/out and concurrency are **UNKNOWN for every provider** — the matrix
  says so explicitly; no quota is invented to complete any arithmetic.
- DeepSeek is **disqualified from code generation** by the CoT-leak defect
  (`~/TOOLS.md`, 2026-10-09) regardless of its quota row.
- Cap'n Maps has **no role** in the execution engine (f7/f6: identity/purpose do
  not support this workflow).

## 1. Direct provider adapters

| Field | NVIDIA NIM — nemotron-3-super-120b-a12b | NVIDIA NIM — nemotron-3-ultra-550b-a55b | NVIDIA NIM — openai/gpt-oss-20b |
|---|---|---|---|
| Endpoint | `integrate.api.nvidia.com` — MEASURED (`adapters/nvidia.py`) | same | same |
| RPM | **39 — MEASURED policy ceiling** (`compute/nvidia_rpm.py`: `DEFAULT_RPM=39`; `nvidia_rpm_state.json`: `rpm_limit:39`). Provider's true limit **UNKNOWN** (no 429/402 ever; one transient 503 on 2026-10-07 — `adapters/nvidia.py:86` `"rate_limit": "unverified"`) | 39 — same adapter ceiling (policy); provider limit UNKNOWN | 39 — same adapter ceiling (policy); provider limit UNKNOWN |
| TPM in | UNKNOWN | UNKNOWN | UNKNOWN |
| TPM out | UNKNOWN | UNKNOWN | UNKNOWN |
| Concurrency | UNKNOWN (burn pacer: single pooled cadence 1.62 s — MEASURED cadence, not a limit) | UNKNOWN | UNKNOWN |
| Context window | **524,288 — MEASURED** observed hosted max (`nvidia-usage/capability.json`; sentinel-echo verified, HTTP 200 at 524,288) | **393,216 — MEASURED** observed hosted max (`nvidia-usage/quality/models.json`; probe at 524,288 → 503, `probe-phase2.json`) | `serving_default` 131,072 (`quality/models.json`); observed max null — **UNKNOWN** |
| Max output | **32,000 — MEASURED** accepted and delivered (`nvidia-usage/output_ceiling.json`, 2026-10-07: 3000 requested lines → 3054 produced, 32000 completion tokens) | UNKNOWN | UNKNOWN |
| Latency | **MEASURED** (`probe-phase1/2.json`, HTTP 200): 8K→1.57 s · 16K→2.19 s · 32K→2.71 s · 65K→4.32 s · 131K→6.71 s · 262K→11.92 s · 524K→26.67 s. Aggregate p50 **20.1 s** / p95 **41.9 s** (`executions.jsonl`, n=2543) | 524,288 → 503 at 3.6 s (MEASURED, `probe-phase2.json`); aggregate shares the 20.1/41.9 s pool stats | UNKNOWN |
| Reliability | **61.9% — MEASURED** (1576 success / 2543; 550 invalid empty-text, 416 error, 1 adapter-refused — `executions.jsonl`) | shares pool stats | UNKNOWN |
| Cost ceiling | **5000 calls — UNVERIFIED_ESTIMATE** (`nvidia-usage/budget.json`: "NOT verified against the account. The account dashboard shows no meter. Treat as estimate until the API demonstrates the limit (first 402/429)"). Used 2926 → util 0.5852 (2026-10-09). Bands MEASURED (`compute/budget.py:19-27`): normal_ops [0,0.60) · catastrophic [0.60,0.80) · final_arch [0.80,0.90) · capability [0.90,1.00]; fail closed at 1.00. Burn guard MEASURED (`compute/burn.py:90`): pause ≥ 0.55, resume < 0.50 → **lane currently PAUSED**. $0 money | same account-shared 5000-call estimate pool (not per-model) | same account-shared pool |

| Field | Gemini direct — gemini-3.8-flash |
|---|---|
| Endpoint | `https://generativelanguage.googleapis.com/v1beta` — MEASURED (`adapters/gemini.py`) |
| RPM | **10 — MEASURED policy ceiling** (`adapters/gemini_rpm.py`: `DEFAULT_RPM=10`; `gemini_rpm_state.json`). Probe 2026-10-08: 5 rapid calls @2 s spacing → 4×200 then 503 overloaded (`gemini-usage/probe-2026-10-08.json`). Brochure nominal 15 RPM NOT demonstrated. Operational pace ~9 RPM (ledger ~5252, policy not measurement) |
| TPM in | UNKNOWN (operational diagnostic only: ~600–700K tok/10 min then 429; sustainable ~27K tok/min w/ 240 s pacing — ledger seq 5185; **not a schedulable limit**) |
| TPM out | UNKNOWN |
| Concurrency | UNKNOWN (burn pacer synchronous 7.06 s cadence — MEASURED cadence, not a limit) |
| Context window | **DECLARED** 1,048,576 (`gemini-usage/models-list.json`); **MEASURED** ≥ 7,020 processed @ HTTP 200 |
| Latency | **MEASURED** (`gemini-usage/probe-2026-10-08.json`; `executions.jsonl` n=1121): typical 2–7 s; aggregate p50 **2.6 s** / p95 **12.3 s** |
| Reliability | **MEASURED** (`executions.jsonl`, n=1121): success 18, error 16, invalid 4, **rate_limited 1083** (adapter's own 10-RPM bucket refusing — policy working, zero provider cost). Provider-attempt success excl. refusals: 18/38 = 0.4737. Pro models DISPROVEN on this key (gemini-3.1-pro-preview → 429); gemini-2.5-flash → 404 (new-user cutoff) |
| Cost ceiling | **20 generateContent requests/day — MEASURED hard floor** (ledger seq 5215). $0 |

| Field | DeepSeek direct | Mistral direct | OpenRouter direct |
|---|---|---|---|
| Endpoint | `api.deepseek.com` — MEASURED (`skills/deepseek/SKILL.md`) | scaffolding only (`skills/mistral/SKILL.md`, no `bin/` CLI) | scaffolding only (`skills/openrouter/SKILL.md`, no `bin/` CLI) |
| Credential health | **MEASURED** (dogfood 2026-10-07): `/v1/models` lists `deepseek-flash`, `deepseek-v4-pro`; `deepseek-chat` probe → HTTP 200 in 1482 ms | UNKNOWN | UNKNOWN |
| RPM / TPM in / TPM out / Concurrency / Context / Latency / Reliability / Cost | **UNKNOWN — all** (no adapter in `compute/`, no probe data) | **UNKNOWN — all** | **UNKNOWN — all** |
| Blocking caveat | **CoT-leak defect: `deepseek-chat` (both `deepseek-v4-pro` and `deepseek-flash`) leaks chain-of-thought into stdout instead of clean code — unusable for code generation** (`~/TOOLS.md`, 2026-10-09). Route generation through non-reasoning models or implement directly; record `direct` fallback in receipts | — | — |

---

## 2. ai-router lanes (live 2026-10-09T18:39:16Z, `https://ai-router.cutecity.workers.dev`)

Adapter: `compute/adapters/ai_router.py` (`SOURCE_ID="ai-router-free"`). The adapter's
protocol **forbids promoting declarations to measurements** (ai_router.py:3-6).
Lane *inventory*: EXISTING AND VERIFIED (live /health). All `rpmLimit` values:
**DECLARED only, never measured**. TPM in/out, concurrency, per-lane latency,
token windows: **UNKNOWN for all 13 lanes**.

| pri | lane | tier | configured | healthy | rpmLimit (DECLARED) | model | lifetime success/fail (MEASURED, observed) |
|---|---|---|---|---|---|---|---|
| 1 | gemini | keyed | false | false | 15 | gemini-2.5-flash | 0/0 — lane dead; critique resolves to `gemini-direct` (f3 §0) |
| 2 | groq | keyed | false | false | 30 | llama-3.3-70b-versatile | 0/0 |
| 3 | mistral | keyed | false | false | 60 | mistral-small-latest | 0/0 |
| 4 | zai | keyed | false | false | 10 | glm-4.7-flash | 0/0 |
| 5 | **nvidia** | keyed | **true** | **true** | 40 | openai/gpt-oss-20b | **152/16** (weekly 166 req / 150,947 tokens) |
| 6 | openrouter | keyed | false | false | 20 | openrouter/free (+5 free-model sub-lanes) | 0/0 |
| 7 | sambanova | keyed | false | false | 15 | Meta-Llama-3.3-70B-Instruct | 0/0 |
| 8 | deepseek | keyed | false | false | 30 | deepseek-flash | 0/0 |
| 9 | github-models | keyed | false | false | 10 | openai/gpt-4o-mini | 0/0 |
| 10 | **pollinations** | keyless | **true** | **true** | 30 | openai | **6/31** (19% — flake under load) |
| 11 | **kilo** | keyless | **true** | **true** | 10 | kilo-auto/free | **46/28** (62%) |
| 12 | **ovh** | keyless | **true** | **true** | 2 | Qwen3.5-9B | **4/26** |
| 13 | **llm7** | keyless | **true** | **true** | 2 | default | **0/15** (429ing live) |

Aggregate router-path latency (**MEASURED** end-to-end only, `executions.jsonl`,
source `ai-router-free`, n=108): p50 **10.8 s** / p95 **19.1 s**; success 104/108
(**96.3%**), error 4. Per-lane latency: UNKNOWN.
Live failure evidence (ledger, redteam wave 10, 2026-10-09T16:31Z): router 502 with
"nvidia timeout, kilo empty, llm7 429, pollinations 402, ovh timeout" — keyless
lanes flake under load; llm7 already 429ing.

**Scheduler rules for router lanes:**
1. Never pace off a DECLARED `rpmLimit`; pace off measured end-to-end behavior only.
2. The `nvidia` lane's `rpmLimit=40` (DECLARED) is **not** the 39-RPM operator ceiling;
   different enforcement points — do not conflate. Its traffic debits the same
   account-shared 5000-call estimate pool (§1 shared-pool rule).
3. Derate lane eligibility by measured reliability (`q·r`); lanes at 0% lifetime
   success (llm7) are ineligible until a successful probe.

## 3. Burn-engine run evidence (2026-10-08 → 2026-10-09)

From `compute/burn.log` + `compute/burn.STATUS.json` — MEASURED run data:
start 2026-10-08T20:18:34Z, shutdown 2026-10-09T04:52:32Z; corpus nvidia=119, gemini=26.
Pacing: nvidia 1.62 s pooled, gemini 7.06 s synchronous.
Final: nvidia_ok=5, nvidia_fail=4, gemini_ok=1, gemini_fail=0, verify_ok=2,
verify_fail=0, overrides=65, blocked=0, **rate_limited=64** (adapter-bucket gating,
not provider 429s), queue_pending=839 at shutdown. NVIDIA paused: band utilization
0.584 ≥ guard 0.55 (consistent with 2926/5000 = 0.5852). Provider 429s during run:
**zero** (NVIDIA); Gemini preflight rate_limited once at start. ai-router was
DOWN(0) (Cloudflare outage) → `ai-router-free` OFF.

## 4. Routing policy benchmarks (context for tier planning)

`compute/bench_results.json` (`router-differential-001`, 200 tasks, 2026-10-09T09:11:56Z)
— MEASURED: policies `random_feasible`, `cheapest_first`, `always_nvidia`, `governor`
all deterministic; governor policy: scarce_selection_rate 0.51, trivia_burn_rate 0.0,
mean_effective_quality 0.6885, decision latency p99 113 ms. The 200-task corpus is
the measured scale anchor for the worked example (`15-worked-example.md`).

## 5. Classification rollup

- **EXISTING AND VERIFIED:** direct NVIDIA adapter + 39-RPM Governor bucket;
  direct Gemini adapter + 10-RPM bucket; NVIDIA input/output capacity numbers;
  Gemini availability/context/latency; ai-router lane inventory + live health;
  credential health (deepseek, nvidia-nim); routing symbols + quota plumbing;
  budget bands + burn guard; execution latency/reliability histories.
- **EXISTING BUT UNVERIFIED:** all ai-router per-lane `rpmLimit` (declared);
  NVIDIA 5000-call estimate; mistral/openrouter scaffolding; keyless-lane failure
  modes (single incident).
- **UNKNOWN:** provider-published RPM for NVIDIA/DeepSeek; TPM in/out and
  concurrency for every provider; DeepSeek/Mistral/OpenRouter quotas of any kind;
  per-lane latency/token windows; true NVIDIA credit balance (no account meter).
- **DISPROVEN (this account):** Gemini pro models (429); gemini-2.5-flash via this
  key (404); ai-router gemini lane as critique path (`configured=false`).

---

## Provider use

No provider generation or critique was used in authoring this file. It is a
transcription of the forensic evidence bundle (f3/f8) into matrix form; every
cell traces to an exact source file. (NVIDIA NIM generation and Gemini critique
were authorized but not needed — this is judgment/verification work.)
