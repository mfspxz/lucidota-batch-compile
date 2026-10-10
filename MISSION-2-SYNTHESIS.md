# MISSION 2 — SYNTHESIZE THE EVIDENCE INTO AN EXECUTABLE MULTI-TIER SCHEDULER SPECIFICATION

Run only after Mission 1 has produced its evidence bundle. This mission forces
engineering synthesis, not another inventory or high-level plan.

## Inputs
The complete forensic inventory, source references, quota measurements,
architecture maps, test evidence, and unresolved-unknowns report from Mission 1.

## Objective
Produce the exact implementation specification for a rate-limit-aware,
multi-tier LLM task execution engine integrated with the existing
CANON / Governor / LUCIDOTA Exchange / ai-router / Validator / Verifier / PL /
graph / sandbox stack.

## Mode
Specification and verification design only. Do not modify code, deploy services,
change quotas, or mutate production state.

## 1. Evidence reconciliation
Read the entire evidence bundle; inspect source directly for every architectural
assumption that materially affects the design. Build the evidence-to-design
matrix: Requirement | Existing implementation | Evidence | Gap |
Proposed enforcement | Test. Preserve actual project boundaries. Reuse existing
components when their behavior is proven. Never create a second governor,
router, ledger, scheduler, graph store, or validator because the design wants
that capability. Classify every decision: Reuse as-is / Extend existing /
Add narrowly-scoped component / Blocked pending evidence. For each blocked
decision, name the exact missing fact and why it changes the design.

## 2. Execution DAG
Task graph, dependency rules, tier transitions, resource constraints:
objective -> task manifest -> manifest validation (CANON/scope/policy/acceptance)
-> partition -> provider assignment -> quota-constrained scheduling -> immediate
validation pipeline -> accept/reject/repair-at-tail -> Tier 2 integration ->
final glue + independent verification -> deterministic test suite -> isolated
worktrees -> merge compatible+authorized only -> final commit + evidence-bound
completion receipt. Draw the dependency graph; overlap independent stages.

## 3. Scheduling mathematics
Formal per-provider/model/endpoint quota-pool model: request rate limits +
window semantics, input/output token quotas, context/max-output constraints,
concurrency limits, per-task estimated/actual usage, shared pools, retry/timeout
budgets, cooldowns + reset times, cost/free-credit ceilings, dependency
readiness, contention + merge locks. Vector of constraints, not one scalar RPM.
Scheduler atomically reserves all resources before dispatch; specify reservation
expiry, reconciliation with actuals, crash recovery, distributed coordination.
Derive: (A) homogeneous throughput λ from binding request/token/latency/
concurrency limits; (B) heterogeneous scheduling with token variability +
model profiles; (C) per-tier expected + conservative makespan; (D) retry
overhead: expected attempts, quota consumed, bounded worst case, assumptions
stated; (E) end-to-end time incl. validation overlap, Tier 2, glue, checks,
merges, recovery; (F) cost: projected + maximum per task/tier/provider/run,
incl. failures + integration calls; (G) sensitivity: which parameter is the
bottleneck and how throughput moves when it changes; (H) replanning: when to
adjust rates, switch providers, defer, or halt; failover preserves policy,
constraints, evidence. Use MEASURED values. Unknown = symbolic formula labeled
unquantified. Never invent a quota.

## 4. Task and artifact contracts
Versioned machine-readable schemas: execution run, task manifest, task
dependency, model/provider profile, quota pool + reservation, attempt record,
worker request envelope, worker response envelope, artifact manifest,
validation result, retry/dead-letter record, integration result, patch/merge
request, acceptance decision, evidence receipt, final run summary. Required
fields, types, constraints, permitted state transitions, validation rules,
compatibility policy. Task identity stable across attempts; attempt identity
unique; artifacts bound to originating task + exact input + base revision +
validation evidence. A model response must never self-accept, raise its own
budget, authorize a tool, change policy, or fabricate a test result.

## 5. Scheduler/governor boundary
Exact division: task planner, deterministic scheduler, provider router, quota
coordinator, governor, worker runtime, artifact validator, independent verifier,
PL + witnesses, graph services, sandbox, integration/glue workers, merge
controller. Per boundary: request contract, response contract, authorization
check, state mutation, timeout, retry semantics, receipt. Use existing CANON
authority hierarchy + current policy. Scheduler chooses eligible work and
manages resources; governor authorizes; validators inspect; independent
verification establishes evidence; ledger records evidence (recording != truth).
Fail-closed when authorization, evidence, policy state, or validation services
are unavailable.

## 6. Retries, repair, termination
Explicit failure taxonomy tied to operational behavior. Per failure class:
detection, retryable?, same-budget?, backoff/cooldown, max attempts, alternate
provider eligible?, repair model allowed?, revalidation required?, terminal
state, evidence retained. Queue keeps processing independent work on failure;
retries to tail; dependency-blocked stays blocked. Cancellation + kill-switch
semantics: running requests, reserved quota, partial artifacts, completed side
effects. Prove retry loops terminate and every task reaches accepted / rejected /
blocked / cancelled / explicitly-unresolved under stated fairness + availability.

## 7. Tier-specific behavior
Tier 1: task sizing, envelopes, output contracts, provider selection,
concurrency, pacing, validation, retries. Optimize for independent verified
artifacts, not raw response count. Tier 2: exact inputs (artifact manifests,
interfaces, dependency edges, source snapshots, test results, conflicts);
glue proposes changes WITHOUT merge authority. Final glue: minimal sufficient
integration context, interface reconciliation, unresolved-issue handling,
required verification. Never feed full transcripts by default — bounded,
task-relevant evidence + versioned contracts. Deterministic acceptance: exact
required checks per artifact class (source validation, compile, unit,
integration, adversarial, security, final-tree). Successful response !=
successful artifact; passing unit test != system correctness.

## 8. Stack integration
FalkorDB: which graph structures are authoritative/derived/experiential; queries
+ identifiers for task discovery, dependencies, provenance, coordination — only
where the implementation supports them. LiteBox: sandbox interface +
resource/isolation requirements from PROVEN capabilities; presence != secure
boundary. Cap'n Maps: use discovered canonical identity + actual purpose; role
only if its contract supports the workflow. CANON, Governor, Exchange,
ai-router, Validator, Verifier, PL, Cloudflare services: source-backed interface
contracts + exact ownership of state and authority. Prefer existing interfaces;
new interfaces need migration + compatibility plans.

## 9. Executable pseudocode
Manifest validation; DAG construction + readiness; quota reservation + dispatch;
completion handling; artifact validation; retry scheduling; provider cooldown +
failover; tier advancement; budget enforcement; integration conflict detection;
patch staging + merge gates; receipt generation + final acceptance; crash
recovery + reconciliation. Mark deterministic decisions vs model proposals.
Every state-changing op: explicit preconditions + recoverable failure path.

## 10. Hostile verification suite
Distinguish actual enforcement from superficial compliance: scheduler-math +
quota-accounting unit tests; property tests (state transitions, idempotency,
reservation invariants); simulated-clock rate-limit/cooldown tests; load sims
at 1/5/50/100/150 workers; mixed-provider + shared-quota; variable token/latency
distributions; 429s, timeouts, partial outputs, outages; duplicate delivery +
crash recovery; malformed/task-mismatched artifacts; forged/stale/replayed
receipts; unauthorized actions + budget-escalation attempts; conflicting
patches + merge regressions; validator/verifier/ledger unavailability;
kill-switch under load; end-to-end acceptance on final tree. Fake providers +
virtual time for load tests — never burn real free quota to simulate scale.
Per test: invariant, setup, expected result, failure signal, evidence artifact.

## 11. Numerical worked example
Measured quotas + measured task distributions, representative run: task counts
by tier, provider/model assignments, RPM + token ceilings, effective
concurrency, estimated/actual token usage, tier-by-tier expected + conservative
makespan, validation overlap, retry allowance + dead-letter assumptions,
projected + max cost, queue depth + bottleneck, test + merge overhead. Show the
arithmetic; reproducible by another engineer. Hypotheticals marked separately
from measured production facts.

## 12. Implementation-ready specification
1. Architecture + data-flow diagrams. 2. Component ownership + interfaces.
3. Versioned data schemas. 4. State-transition tables. 5. Scheduler equations +
algorithm. 6. Provider quota + capability matrix. 7. Pseudocode. 8. Test +
adversarial verification plan. 9. Observability + operational runbook.
10. Failure/recovery matrix. 11. Migration plan preserving existing services +
data. 12. Dependency-ordered implementation backlog: task IDs, concrete
file/symbol targets, acceptance predicates, test commands, estimates.
13. Unresolved facts blocking safe implementation. 14. Traceability matrix:
every requirement -> implementation point -> test. Classify each capability:
EXISTING AND VERIFIED / EXISTING BUT UNVERIFIED / REQUIRES EXTENSION /
NEW WORK / BLOCKED. Never claim implementation-ready while critical
interfaces, quota constraints, authorization boundaries, or acceptance criteria
are UNKNOWN.

## 13. Completion criterion
An engineer can implement without guessing: how many requests can run; when
requests may launch; how token/concurrency limits interact; task flow through
tiers; failure retry/termination; governor authority enforcement; artifact
validation; graph/sandbox participation; safe merges; final proof. Finish with
the exact first implementation batch dispatchable independently — each task's
inputs, deliverables, acceptance tests, dependency declarations.
