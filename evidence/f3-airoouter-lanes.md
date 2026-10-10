# F3 — ai-router provider lanes + provider quotas: forensic inventory

**Investigator:** subagent (forensic, read-only) · **Date:** 2026-10-09 11:40 PDT
**Method:** code + config + ledger + live read-only health check. No mutations, no deletions.
**Sources consulted:** `~/ledger/ledger-0001.jsonl` (grep), `~/workspace/skills/ai-router/SKILL.md` (+`bin/router-call.py`, `DOGFOOD-REPORT.md`), `~/workspace/skills/deepseek/SKILL.md` (+dogfood), `~/workspace/skills/nvidia-nim/SKILL.md` (+dogfood), `~/workspace/skills/mistral/SKILL.md`, `~/workspace/skills/openrouter/SKILL.md`, `~/workspace/compute/router.py`, `~/workspace/compute/budget.py`, `~/workspace/compute/burn.py`, `~/workspace/compute/bench_results.json`, `~/workspace/compute/adapters/{ai_router,nvidia,gemini,gemini_rpm}.py`, `~/workspace/compute/nvidia_rpm.py`, `~/workspace/compute/executions.jsonl`, `~/workspace/nvidia-usage/{budget,capability,output_ceiling,probe-phase1,probe-phase2}.json`, `~/workspace/gemini-usage/{probe-2026-10-08,models-list}.json`, live `GET /health` on the router (2026-10-09T18:39:16Z).

**Status taxonomy used below:** EXISTING AND VERIFIED · EXISTING BUT UNVERIFIED · UNKNOWN. Per the project's own epistemology, declared-but-unmeasured values are never promoted to measured.

---

## 0. Executive summary

Three execution paths exist, with distinct quota regimes:

1. **Direct provider adapters** (`~/workspace/compute/adapters/`): `nvidia.py` (SOURCE_ID `nvidia-nim-hosted`) and `gemini.py` (SOURCE_ID `gemini-direct`). These carry the **measured** rate data. EXISTING AND VERIFIED.
2. **The ai-router worker** (`https://ai-router.cutecity.workers.dev`): an OpenAI-compatible free failover router with **13 declared lanes**. Only 5/13 are currently healthy. Its per-lane `rpmLimit` values are router-config DECLARED values, never measured. Lane inventory: EXISTING AND VERIFIED (live /health). Quota numbers: EXISTING BUT UNVERIFIED (declared).
3. **Skill-level direct CLIs** (`~/workspace/skills/{deepseek,nvidia-nim,mistral,openrouter}/bin/`): credential-verified working for deepseek and nvidia-nim; mistral/openrouter CLIs are scaffolding only. No quota measurements. EXISTING BUT UNVERIFIED (quota) / EXISTING AND VERIFIED (credential health, deepseek+nvidia only).

**Provider routing doctrine (Zack's standing order, AGENTS.md; confirmed in ledger 2026-10-09):** builders GENERATE via DeepSeek or NVIDIA NIM APIs, CRITIQUE via Gemini through ai-router. NOTE: the ai-router `gemini` lane is currently `configured=false, healthy=false` — so the working Gemini critique path today is the **direct** adapter (`gemini-direct`), not the router lane. A ledger critic report (2026-10-09) records: "Gemini unreachable via ai-router, failed over to gpt-oss-20b then 403."

**The 39 RPM figure is an operator pacing directive, not a provider-published limit.** Zackary ordered "maximum NVIDIA calls ... generate their prompts 39 RPM." It is implemented as a deterministic Governor primitive — a token-bucket hard ceiling in `~/workspace/compute/nvidia_rpm.py` (capacity 39, refill 39/min, fcntl-locked, disk-persisted). The provider's true RPM limit has never been observed (no 429/402 ever; one transient 503 on 2026-10-07).

---

## 1. Provider profiles

### 1.1 NVIDIA NIM (direct) — `nvidia-nim-hosted`

- **Adapter:** `~/workspace/compute/adapters/nvidia.py` — symbols: `SOURCE_ID="nvidia-nim-hosted"`, `PROVIDER_ID="nvidia"`, `CLI=/home/hatch/workspace/skills/nvidia-nim/bin/nvidia-nim`, `register_nvidia()`, `execute(model, prompt, max_tokens=512, ...)`, `_measured_caps()`, `_provenance_for()`. EXISTING AND VERIFIED.
- **Endpoint:** `integrate.api.nvidia.com`. Auth: `custom.nvidia-nim` credential surrogate. Skill: `~/workspace/skills/nvidia-nim/SKILL.md`. EXISTING AND VERIFIED.
- **Models measured** (from `~/workspace/nvidia-usage/capability.json`, evidence `probe-phase1.json` + `probe-phase2.json` both present):
  - `nvidia/nemotron-3-super-120b-a12b` — observed hosted input max **524,288 tokens** (measured); `model_max` declared=None (not published in probe). 6/6 phase-1 sizes HTTP 200.
  - `nvidia/nemotron-3-ultra-550b-a55b` — observed hosted input max **393,216 tokens** (measured); `model_max` declared=None. 5/5 phase-1 sizes HTTP 200.
- **Output ceiling (measured):** 32,000 max_tokens accepted and delivered on nemotron-3-super-120b-a12b (`~/workspace/nvidia-usage/output_ceiling.json`, 2026-10-07; 3000 requested lines → 3054 produced, 32000 completion tokens). EXISTING AND VERIFIED.
- **RPM:** 39 hard ceiling via `~/workspace/compute/nvidia_rpm.py` (`DEFAULT_RPM=39`, `acquire()` returns `(False, retry_after_s)` past ceiling; `set_rpm_limit()` obeys a lower discovered limit). `execute()` gates on the bucket: over-ceiling calls record a `rate_limited` Execution, never dispatched. EXISTING AND VERIFIED. **The provider's actual RPM limit is UNVERIFIED** — adapter records `"rate_limit": "unverified"`, "no 429/402 observed 2026-10-07; one transient 503".
- **Budget:** `provider_budget_estimate=5000` calls — **UNVERIFIED community estimate** (`~/workspace/nvidia-usage/budget.json`: "NOT verified against the account. The account dashboard shows no meter. Treat as estimate until the API demonstrates the limit (first 402/429)."). Governor only, never capacity. EXISTING BUT UNVERIFIED.
- **Spend bands** (`~/workspace/compute/budget.py`): normal_operations <0.60 · catastrophic_debugging <0.80 · final_architecture <0.90 · capability_research ≤1.00 of the estimate; fail closed at the full estimate. Burn engine uses a **stricter guard**: `NVIDIA_BAND_GUARD = 0.55` (`~/workspace/compute/burn.py:90`, `budget_guard()` pauses the NVIDIA lane; resumes at <0.50). EXISTING AND VERIFIED.
- **Measured execution history** (`~/workspace/compute/executions.jsonl`, source `nvidia-nim-hosted`, n=2543): success 1576 (**61.9%**), invalid 550 (empty/no-extractable text — adapter marks these `invalid`, not success), error 416, rate_limited 1. Latency: p50 **20.1s**, p95 **41.9s**. EXISTING AND VERIFIED (measured).
- **Concurrency:** UNKNOWN — never measured. Burn pacer used a pooled cadence of 1.62s (~37/min, under the 39 ceiling). Single in-flight at a time is NOT established; multi-concurrency behavior untested.
- **TPM (input/output):** UNKNOWN — never measured.

### 1.2 Gemini (direct) — `gemini-direct`

- **Adapter:** `~/workspace/compute/adapters/gemini.py` — symbols: `SOURCE_ID="gemini-direct"`, `PROVIDER_ID="gemini"`, `BASE=https://generativelanguage.googleapis.com/v1beta`, `KEY_PATH=~/workspace/keys/GEMINI_KEY` (read transiently, never logged), `DEFAULT_MODEL="gemini-3.8-flash"`, `register_gemini()`, `execute()`. EXISTING AND VERIFIED.
- **RPM (measured):** 10 RPM adapter ceiling (`~/workspace/compute/adapters/gemini_rpm.py`, `DEFAULT_RPM=10`). Evidence (`~/workspace/gemini-usage/probe-2026-10-08.json`): 5 rapid calls at 2s spacing to gemini-3.8-flash → **4× HTTP 200 then 1× HTTP 503 (model overloaded)**; the brochure nominal free-tier 15 RPM is NOT what the wire demonstrated, so the ceiling is set conservatively at 10. EXISTING AND VERIFIED (measured).
- **Context window:** declared 1,048,576 tokens per `models.list` (`~/workspace/gemini-usage/models-list.json`); **measured 7,020 tokens** processed at HTTP 200. EXISTING AND VERIFIED (both the declared value and the measured lower bound).
- **Latency (measured):** typical 2000–7000ms per completion. EXISTING AND VERIFIED.
- **Availability:** 50 models listed; `gemini-2.5-flash` → 404 for this key (new-user cutoff, API redirects to `gemini-3.8-flash`) — DISPROVEN. `gemini-3.1-pro-preview` → 429 quota-exceeded — pro models DISPROVEN on this free key. EXISTING AND VERIFIED (measured).
- **Measured execution history** (`executions.jsonl`, source `gemini-direct`, n=1121): success 18, error 16, invalid 4, **rate_limited 1083** (the adapter's own 10-RPM bucket refusing — consistent with the ceiling, not provider 429s). Latency: p50 **2.6s**, p95 **12.3s**. EXISTING AND VERIFIED.
- **TPM (input/output):** UNKNOWN. **Concurrency:** UNKNOWN.

### 1.3 DeepSeek (direct)

- **Skill:** `~/workspace/skills/deepseek/SKILL.md` — `custom.deepseek` credential, authenticated requests restricted to `api.deepseek.com`. EXISTING AND VERIFIED.
- **Credential health (measured):** dogfood 2026-10-07 — `/v1/models` listed `deepseek-flash, deepseek-v4-pro`; probe on `deepseek-chat` → **HTTP 200 in 1482ms**, reply 'OK'. EXISTING AND VERIFIED.
- **OPERATOR CAVEAT (TOOLS.md, 2026-10-09):** `deepseek-chat` (both `deepseek-v4-pro` and `deepseek-flash`) leaks chain-of-thought reasoning into stdout instead of emitting clean code — **unusable for code generation** as of 2026-10-09; route generation through non-reasoning models or implement directly.
- **RPM / TPM in/out / concurrency / context window:** UNKNOWN — no measurements in bench_results.json, burn logs, or skill docs.

### 1.4 Mistral (direct) / OpenRouter (direct)

- Skills exist (`~/workspace/skills/mistral/SKILL.md`, `~/workspace/skills/openrouter/SKILL.md`) as credential scaffolding; no `bin/` CLIs populated, no dogfood reports with measured calls. **No quota measurements anywhere.** UNKNOWN for all rate/token fields. EXISTING BUT UNVERIFIED (scaffolding only).

---

## 2. ai-router lane registry (live, 2026-10-09T18:39:16Z)

Endpoint: `https://ai-router.cutecity.workers.dev` · CLI: `~/workspace/skills/ai-router/bin/router-call.py` (`router-call.py <METHOD> <PATH> [--data @file] [--header K:V] [--full]`) · Adapter: `~/workspace/compute/adapters/ai_router.py` (`SOURCE_ID="ai-router-free"`, `describe()`, `register_ai_router()`, `execute(model="openrouter/free", ...)`).

The adapter marks every lane capability **DECLARED, never measured** ("the protocol forbids promoting declarations to measurements"). The `rpmLimit` column below is the router's configured per-lane limit from `/health` — **DECLARED, not a provider-measured limit.** Lane inventory itself: EXISTING AND VERIFIED (live).

| pri | lane | tier | configured | healthy | rpmLimit (DECLARED) | model | lifetime success/fail |
|---|---|---|---|---|---|---|---|
| 1 | gemini | keyed | false | false | 15 | gemini-2.5-flash | 0/0 |
| 2 | groq | keyed | false | false | 30 | llama-3.3-70b-versatile | 0/0 |
| 3 | mistral | keyed | false | false | 60 | mistral-small-latest | 0/0 |
| 4 | zai | keyed | false | false | 10 | glm-4.7-flash | 0/0 |
| 5 | **nvidia** | keyed | **true** | **true** | 40 | openai/gpt-oss-20b | **152/16** (weekly 166 req / 150,947 tokens) |
| 6 | openrouter | keyed | false | false | 20 | openrouter/free (+5 free models sub-lanes) | 0/0 |
| 7 | sambanova | keyed | false | false | 15 | Meta-Llama-3.3-70B-Instruct | 0/0 |
| 8 | deepseek | keyed | false | false | 30 | deepseek-flash | 0/0 |
| 9 | github-models | keyed | false | false | 10 | openai/gpt-4o-mini | 0/0 |
| 10 | **pollinations** | keyless | **true** | **true** | 30 | openai | **6/31** |
| 11 | **kilo** | keyless | **true** | **true** | 10 | kilo-auto/free | **46/28** |
| 12 | **ovh** | keyless | **true** | **true** | 2 | Qwen3.5-9B | **4/26** |
| 13 | **llm7** | keyless | **true** | **true** | 2 | default | **0/15** |

Notes:
- 5/13 lanes healthy. Matches the adapter's own note ("4/13 lanes healthy (keyless) per /health 2026-10-07" — nvidia keyed lane has since become healthy).
- The nvidia lane's `rpmLimit=40` (DECLARED) is **not** the 39-RPM operator ceiling; the 39 ceiling is enforced in `adapters/nvidia.py` via `nvidia_rpm.acquire()` on the *direct* adapter path. They are different enforcement points — do not conflate.
- Live failure evidence (ledger, redteam wave 10, 2026-10-09T16:31Z): ai-router 502 with "nvidia timeout, kilo empty, llm7 429, pollinations 402, ovh timeout" — keyless lanes flake under load; llm7 already 429ing.
- ai-router execution history (`executions.jsonl`, source `ai-router-free`, n=108): success 104, error 4; latency p50 **10.8s**, p95 **19.1s**. EXISTING AND VERIFIED (measured end-to-end latency only — per-lane latency UNKNOWN).
- TPM per lane: UNKNOWN. Concurrency per lane: UNKNOWN. Token windows per lane model: UNKNOWN (except via the lane's `model` name string).

---

## 3. Routing logic (exact symbols)

- **Decision point:** `~/workspace/compute/router.py` — `route()` (wrapper, reads quota ONCE) → `_route_impl(task, policy, eval_time, quota, exclude=())` ("The actual routing. quota is read ONCE by the caller"). EXISTING AND VERIFIED.
- **Quota plumbing:** `_quota_state(snapshot)` → `budget.py::quota_state()`; full decision receipt via `route_with_receipt()` certifies the exact quota the decision was made under (`"quota_before"`, `"quota_used"`). EXISTING AND VERIFIED.
- **Gates (in order):** budget gate (scarce sources only; `budget.py::check()`), scarce-resource trivia gate (quota never consumed for trivia without value), ranking via `_rank_key()`. EXISTING AND VERIFIED.
- **Model selection (NVIDIA):** `_nvidia_models_for(task, source)` — eligible = models with `input_capacity_tokens:` capability whose **measured** value ≥ `task.input_size`; deterministic order = measured quality desc, then model_id ASC. EXISTING AND VERIFIED.
- **Reliability handling:** `_reliability(model_id)` returns measured `successful_execution_rate` or `(False, None)`; unmeasured sources get `UNKNOWN_RELIABILITY_FACTOR = 0.7` (capped, flagged — never assumed perfect). Effective quality = measured quality × measured reliability (e.g. "0.93 quality × 0.59 reliability = 0.55 expected"). EXISTING AND VERIFIED.
- **Routing policies benchmarked:** `~/workspace/compute/bench_results.json` (`router-differential-001`, 200 tasks, 2026-10-09T09:11:56Z): `random_feasible`, `cheapest_first`, `always_nvidia`, `governor` — all deterministic; governor policy: scarce_selection_rate 0.51, trivia_burn_rate 0.0, mean_effective_quality 0.6885, decision latency p99 113ms. EXISTING AND VERIFIED.
- **Burn engine:** `~/workspace/compute/burn.py` — supervisor cycles with `budget_guard()` (0.55 pause / 0.50 resume), per-source pacers (nvidia cadence **1.62s**, gemini cadence **7.06s** — measured pacer rates from burn.log), adapter RPM buckets as the hard enforcement. Last burn (2026-10-09T04:52:31Z, `burn.STATUS.json`): nvidia_ok=5, nvidia_fail=4, gemini_ok=1, gemini_fail=0, rate_limited=64, queue_pending=839, ai_router_live=false, shutdown=true. EXISTING AND VERIFIED (measured run data).

---

## 4. Quota matrix (measured vs declared vs unknown)

| Provider | RPM | TPM in | TPM out | Concurrency | Context window | Source |
|---|---|---|---|---|---|---|
| NVIDIA direct | **39** — operator-set hard ceiling (token bucket, fcntl, disk-persisted); provider's real limit UNVERIFIED | UNKNOWN | UNKNOWN | UNKNOWN | **524,288** in (super, measured) / **393,216** in (ultra, measured); **32,000** out (super, measured) | nvidia_rpm.py, capability.json, output_ceiling.json |
| Gemini direct | **10** — adapter ceiling (measured 4×200+503 at 2s spacing; brochure nominal 15) | UNKNOWN | UNKNOWN | UNKNOWN | declared 1,048,576; measured ≥7,020 | gemini_rpm.py, probe-2026-10-08.json |
| ai-router lanes | per-lane rpmLimit **DECLARED only** (15/30/60/10/40/20/15/30/10/30/10/2/2) — never measured | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | live /health (DECLARED) |
| DeepSeek direct | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | — |
| Mistral / OpenRouter direct | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | scaffolding only |

**Measured end-to-end latencies** (from `executions.jsonl`): nvidia-nim-hosted p50 20.1s / p95 41.9s · gemini-direct p50 2.6s / p95 12.3s · ai-router-free p50 10.8s / p95 19.1s. These bound the λ (sustainable requests/min) via the latency term; the RPM ceilings above are the binding request-rate term for nvidia and gemini.

**Measured reliability (success rate, from executions.jsonl):** nvidia-nim-hosted 61.9% (1576/2543; 550 "invalid" empty-text, 416 error) · gemini-direct 18 success vs 1083 adapter-refusals (bucket working as designed) · ai-router-free 96.3% (104/108).

---

## 5. The 39 RPM directive — recorded as operator directive, NOT measured fact

- Zackary's order (2026-10-09, chat): "Maximum NVIDIA calls as well generate their prompts 39 RPM."
- Status: **OPERATOR DIRECTIVE (pacing target)**. Implemented as a hard ceiling — never exceeded, may run under it (burn pacer ran ~37/min).
- Implementation: `~/workspace/compute/nvidia_rpm.py` — `DEFAULT_RPM = 39`, `acquire()` / `peek()` / `set_rpm_limit()`; state in `~/workspace/compute/nvidia_rpm_state.json`; cross-process safe via `fcntl`. Docstring: "39 requests/minute is a HARD MAXIMUM, not a target. ... If the endpoint reports a lower limit, obey the lower limit."
- Enforcement point: `~/workspace/compute/adapters/nvidia.py::execute()` — calls `nvidia_rpm.acquire()` before dispatch; refusal records a `rate_limited` Execution (observed exactly once in 2543 executions).
- **It is not NVIDIA's published limit.** No 429/402 has ever been observed on this endpoint; the true provider ceiling is UNKNOWN.

---

## 6. Classification rollup

- **EXISTING AND VERIFIED:** direct NVIDIA adapter + 39-RPM Governor bucket; direct Gemini adapter + 10-RPM bucket (measured); NVIDIA input/output capacity numbers; Gemini availability/context/latency measurements; ai-router lane *inventory* (13 lanes, live health, per-lane success/fail); ai-router skill CLI + dogfood; DeepSeek/NVIDIA credential health; routing symbols and quota plumbing; budget bands + burn guard; benchmark policies; execution-latency/reliability histories.
- **EXISTING BUT UNVERIFIED:** all ai-router per-lane `rpmLimit` values (declared by router config, never measured); NVIDIA `provider_budget_estimate=5000` (community estimate; no account meter); mistral/openrouter skill scaffolding (no live calls); the redteam-observed keyless-lane failure modes (single incident, not a measurement).
- **UNKNOWN:** provider-published RPM for NVIDIA and DeepSeek; TPM in/out for every provider; concurrency for every provider; DeepSeek/Mistral/OpenRouter quotas of any kind; per-lane latency/token windows on the router; the account's true NVIDIA credit balance (dashboard shows no meter).
- **DISPROVEN (for this account):** Gemini pro models (429), gemini-2.5-flash via this key (404); the ai-router gemini lane as a working critique path (configured=false — use `gemini-direct`).

## 7. Gaps for the scheduler spec (what remains UNKNOWN)

1. No provider has measured TPM in/out — the λ equation's token terms cannot be filled from measurement today.
2. No provider has measured concurrency — λ's C·μ term is unquantified for all lanes.
3. NVIDIA's true rate limit and true credit balance are both UNKNOWN; the 5000-estimate and 39-ceiling are governance choices, not capacity facts.
4. ai-router lane `rpmLimit` values are router-side config, not wire measurements — pacing the scheduler off them assumes the router enforces them.
5. DeepSeek has zero quota measurements despite being a designated generation lane; its CoT-leak defect (TOOLS.md) disqualifies it for code generation regardless.
