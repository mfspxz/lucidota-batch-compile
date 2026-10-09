# F8 — Measured Quota / Cost / Latency Evidence

Forensic extraction, read-only, 2026-10-09. Every number below was read from a file listed in the Source column. Anything not evidenced is marked UNKNOWN. No value was invented to complete the table. Adapter-enforced policy ceilings (10/39 RPM) are NOT provider rate limits; the table distinguishes them.

## Master table

| Provider / Model / Endpoint | RPM | Input TPM | Output TPM | Concurrency | Context window | Measured latency | Cost / credit ceiling | Source file + line |
|---|---|---|---|---|---|---|---|---|
| Gemini / gemini-3.8-flash / generativelanguage.googleapis.com (v1beta) | **10 — adapter-enforced hard ceiling (policy, measured)**. 5 rapid calls @2s spacing: 4×HTTP 200 then 503 overloaded (2026-10-08). Nominal brochure 15 RPM was NOT demonstrated. | No TPM limit measured. **Observed rolling window (operational):** ~600–700K tokens per ~10 min then 429; sustainable ~27K tokens/min with 240s pacing | UNKNOWN | UNKNOWN (burn pacer ran gemini synchronously, 7.06s cadence) | Declared 1,048,576 (models.list). **Measured processed input: 7,020 tokens @ HTTP 200** | basic_flash: 12,538 ms (200, tiny prompt); context_10k (7,020 tok): 2,673 ms (200); rapid-fire: 19,100 / 7,306 / 6,878 / 2,135 ms (200s), 6,657 ms (503). Typical ~2–7s | $0. Free-tier quota (operational diagnostics): **20 generateContent requests/day** for gemini-3.8-flash; rolling token window above. Pro models DISPROVEN on this key (gemini-3.1-pro-preview → 429). gemini-2.5-flash → 404 (cut off for new users) | adapters/gemini.py:12-17 (probe notes); adapters/gemini.py:92-110 (measured caps); adapters/gemini_rpm.py:1-8 (10 RPM ceiling); adapters/gemini_rpm_state.json (rpm_limit:10); gemini-usage/probe-2026-10-08.json (raw latencies); ledger seq 5185 (~600-700K/10min, ~27K tok/min); ledger seq 5215 (20 req/day) |
| NVIDIA NIM / nemotron-3-super-120b-a12b / integrate.api.nvidia.com | **39 — adapter-enforced hard ceiling (policy, "not a target")**. Provider rate limit: **UNVERIFIED**. No 429/402 observed 2026-10-07; one transient 503 | UNKNOWN | UNKNOWN | UNKNOWN (burn pacer "pooled", 1.62s cadence; adapter default timeout 300s, max_tokens default 512) | **observed_hosted_max 524,288** (sentinel-echo verified; HTTP 200 at 524,288) | 8,192→1,573 ms; 16,384→2,188 ms; 32,768→2,713 ms; 65,536→4,319 ms; 131,072→6,711 ms; 262,144→11,922 ms; 524,288→26,670 ms (all HTTP 200, measured 2026-10-07) | **provider_budget_estimate = 5,000 calls — UNVERIFIED_ESTIMATE** ("community-documented, NOT verified"; ToS confirms a Credits mechanism, publishes no numbers; account dashboard shows no meter). **Used: 2,926** (calls.jsonl line count, 2026-10-09) → remaining ≈ 2,074 *by estimate only*. Bands: normal_ops [0,0.60), catastrophic_debugging [0.60,0.80), final_architecture [0.80,0.90), capability_research [0.90,1.00). Expiry: UNKNOWN (none published). Money: $0 | adapters/nvidia.py:86 (rate_limit "unverified"); adapters/nvidia.py:109-111 (39 RPM ceiling); compute/nvidia_rpm.py:1-8; nvidia_rpm_state.json (rpm_limit:39); nvidia-usage/budget.json (5000 UNVERIFIED_ESTIMATE); nvidia-usage/calls.jsonl (2926 lines); compute/budget.py:19-27 (bands); nvidia-usage/capability.json (observed_hosted_max); nvidia-usage/probe-phase1.json + probe-phase2.json (latencies) |
| NVIDIA NIM / nemotron-3-ultra-550b-a55b / integrate.api.nvidia.com | 39 — same adapter ceiling (policy); provider limit UNVERIFIED | UNKNOWN | UNKNOWN | UNKNOWN | **observed_hosted_max 393,216** (quality/models.json); probe at 524,288 → HTTP 503 | 524,288 → 503 at 3,615 ms | Same 5,000-call UNVERIFIED estimate pool (shared account quota, not per-model) | nvidia-usage/quality/models.json (393,216, temp 1.0, top_p 0.95, serving_default 256,000); nvidia-usage/probe-phase2.json (503 @ 524288) |
| NVIDIA NIM / openai/gpt-oss-20b / integrate.api.nvidia.com | 39 — same adapter ceiling (policy) | UNKNOWN | UNKNOWN | UNKNOWN | serving_default 131,072; observed max: null (UNKNOWN) | UNKNOWN | Same 5,000-call UNVERIFIED estimate pool | nvidia-usage/quality/models.json |
| ai-router / openrouter/free + lanes / ai-router.cutecity.workers.dev | UNKNOWN — per-lane `rpmLimit` values exist on /health but are **DECLARED ONLY, never measured**; adapter protocol forbids promoting them. Status NOT_TESTED | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | $0 money; "per-lane rpm limits (declared)" | adapters/ai_router.py:3-6 (declared-only doctrine), 38-58 (lane caps), 71-77 (4/13 lanes healthy keyless per /health 2026-10-07) |
| DeepSeek (api.deepseek.com) | UNKNOWN — no adapter in compute/, no probe data | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | doctrine only (PROVIDER ROUTING, AGENTS.md); no measured evidence in workspace |
| Mistral / OpenRouter (direct) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | doctrine only; no measured evidence in workspace |
| local-subprocess | UNKNOWN (no limit) — **observed** 1.0 req/60s in burn window (rate, not ceiling) | n/a | n/a | n/a | n/a | Router decision latencies (local, not API): p50 0.002–12.5 ms, p99 up to 113 ms by policy | n/a | compute/burn.STATUS.json (rpm_60s); compute/bench_results.json (decision_latency_ms) |

## Gemini "~9 RPM critique lane" — evidenced?

Partially. The **measured** ceiling is **10 RPM** (adapter-enforced, probe-proven 2026-10-08). The figure "**~9RPM**" appears in ledger entries (e.g. "Gemini ~9RPM + NVIDIA 39RPM" parallelization notes, ledger seq ~5252 era) as Zackary's **operational target pace** — i.e. ~90% of the measured 10 RPM ceiling, not an independent measurement. There is no 9-RPM measurement in any probe or state file. Correct statement: Gemini critique lane runs at ~9 RPM by policy under a measured 10 RPM adapter ceiling, with a free-tier hard floor of 20 generate requests/day.

## NVIDIA 39 RPM — measurement or policy?

Policy. `compute/nvidia_rpm.py` documents it as "a HARD MAXIMUM, not a target... a Governor resource primitive, not a prompt instruction." Zackary's order ("maximum NVIDIA generation at 39 RPM pace", ledger seq 5252) matches this existing ceiling; it is an operational pace under a self-imposed gate. The **provider** rate limit remains UNVERIFIED — no 429/402 has ever been observed, so the true provider RPM is unknown.

## Burn-engine run evidence (2026-10-08 → 2026-10-09)

From `compute/burn.log` (1,169 lines) and `compute/burn.STATUS.json`:

- Start 2026-10-08T20:18:34Z, shutdown 2026-10-09T04:52:32Z. Corpus: nvidia=119, gemini=26 tasks.
- Pacing config: nvidia pacer cadence **1.62 s (pooled)**, gemini pacer **7.06 s (synchronous)**.
- Final counts: nvidia_ok=5, nvidia_fail=4, gemini_ok=1, gemini_fail=0, verify_ok=2, verify_fail=0, overrides=65, blocked=0, **rate_limited=64** (rate_limited events are adapter-bucket gating, not provider 429s), queue_pending=839 at shutdown.
- nvidia paused: band utilization 0.584 ≥ guard 0.55 (consistent with 2,926/5,000 = 0.5852).
- Observed provider 429s during run: **zero** (NVIDIA), and Gemini preflight reported rate_limited once at start.
- Cloudflare endpoints (ai-router, lucidota-exchange, ctcc-router) were DOWN(0) during the run → ai-router-free OFF.

## Explicitly NOT measured (do not use in scheduling math)

- Input/output token-per-minute limits for NVIDIA (no TPM probes exist).
- Concurrency limits for any provider (adapters run single-flight pacers; no parallel-load probe).
- Per-provider request windows / reset semantics / cooldowns.
- ai-router lane rpmLimits (declared on /health only — NOT_TESTED per adapter protocol).
- NVIDIA provider rate limit (UNVERIFIED — adapter rate_limit field says so).
- NVIDIA budget 5,000 (UNVERIFIED_ESTIMATE; governance only, never capacity).
- Any DeepSeek / Mistral / OpenRouter-direct numbers.
- Cost in dollars for NVIDIA (only the unverified call-count estimate exists).

## Files read (read-only)

- `~/workspace/compute/bench_results.json` (router policy benchmarks only — no provider quotas)
- `~/workspace/compute/budget.py` (bands, UNVERIFIED estimate doctrine)
- `~/workspace/compute/budget.lock` (0 bytes — lock placeholder)
- `~/workspace/compute/burn.log` (run telemetry)
- `~/workspace/compute/burn.STATUS.json` (final counters)
- `~/workspace/compute/campaigns/nvidia-production-001.json` (policy, no numbers)
- `~/workspace/compute/adapters/{gemini,gemini_rpm,nvidia,ai_router}.py` + `gemini_rpm_state.json` + `nvidia_rpm_state.json`
- `~/workspace/gemini-usage/probe-2026-10-08.json`, `models-list.json`
- `~/workspace/nvidia-usage/{budget.json,calls.jsonl,capability.json,quality/models.json,output_ceiling.json,probe-phase1.json,probe-phase2.json}`
- `~/ledger/ledger-0001.jsonl` via grep (context: Gemini rolling token window ~600–700K/10min, ~27K tok/min sustained; 20 req/day; ~9RPM operational pace; 39 RPM order)
- `~/workspace/skills/{ai-router,deepseek,nvidia-nim}/SKILL.md` (no measured quota numbers; nvidia-nim skill has no limit docs)

**Not run:** burn scripts, probes, or any API calls. Zero quota consumed. No files modified.

## Addendum 2026-10-09 ~13:15 PDT — DeepSeek quota probe (minimal, 3 calls)

Method: `~/workspace/skills/deepseek/bin/deepseek-chat` (surrogate credential
`custom.deepseek`, entry `access_token`; raw key never handled). 1× GET
/v1/models + 2× tiny prose completions (NOT code — CoT-in-stdout defect stands),
~30s spacing. Stopped after 2 prose calls: sufficient for a first measurement;
no 429/402/503 observed, no reason to spend more.

Results (model `deepseek-flash`):
- Auth: OK. /v1/models HTTP 200 in 1.29s. Models: `deepseek-flash`,
  `deepseek-v4-pro` (no context_length / max_tokens fields exposed).
- Call 1: HTTP 200 in 1.97s. usage prompt=43 / completion=64 (all 64 were
  reasoning_tokens; content empty; finish_reason=length — max_tokens=64 eaten
  by reasoning). system_fingerprint `aeb56401ca74e127821c4f9126dcb669`.
- Call 2: HTTP 200 in 2.41s. usage prompt=43 / completion=61 (31 reasoning +
  30 visible prose); finish_reason=stop; visible content present.
- CoT behavior confirmed on both calls (reasoning_content populated) — for
  prose request max_tokens well above expected reasoning; codegen remains
  unusable per standing defect note.
- Throttling: none observed at ~2 RPM pace. No 429/402/503.

Scheduler-usable numbers:
- Measured latency: ~2.0–2.4s per tiny prose call (deepseek-flash).
- Usage accounting: prompt/completion/reasoning token split reported per call.
- RPM ceiling: UNKNOWN (unmeasurable with 2 calls; do not schedule on it).
- TPM in/out, concurrency, reset/cooldown semantics: UNKNOWN.
- Cost / credit balance / expiry: UNKNOWN (no cost fields in API responses;
  no balance endpoint probed).
- Context window observed: UNKNOWN (43-token prompts; no limit evidence).

Quota consumed by this probe: 3 API calls (1 models-list + 2 completions,
~211 total tokens). Evidence: raw JSON responses in /tmp (ds1/ds2), not retained.
