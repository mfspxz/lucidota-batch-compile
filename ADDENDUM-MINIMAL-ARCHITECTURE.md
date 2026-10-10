# ADDENDUM — MINIMAL ARCHITECTURE (Zack, Oct 9 2026 ~11:48 PDT, steering the synthesis wave)

Overengineering correction. No semantic judge, no hierarchy of validators, no
LLM debating another LLM's instructions. The human and authoring LLM decide
what work is wanted; the computer performs deterministic information operations.

## Minimal architecture
- Prompts — reusable instructions for authoring a work order / executing a unit.
- Typed work order — work, units, relationships, outputs, resource limits.
- Partitioner — splits work into typed units by simple explicit rules.
- Allocator — assigns eligible units to LLMs under actual capacity/rate limits.
- Workers — bounded generation strictly within assignment.
- Ledger — inputs, allocations, outputs, attempts, results.
- Retry — fixed rules, no judgment.

## The computer's operations (implementation categories, collapsible)
Read, Write, Copy, Transform, Compare, Calculate, Route, Track, Stop.
A schema check is ordinary deterministic logic — it does not judge wisdom.

## The essential distinction
Structural integrity = cheap + deterministic (keep). Semantic judgment =
human + authoring LLM (leave there). A faithfully-executed bad objective is a
human/work-order problem, not an excuse for an artificial judge.
Everything beyond typed information + a handful of ops + deterministic
scheduling + bounded generation + ledger must justify its existence.

## Three tiers — scope of responsibility, not model capability (Zack, ~11:51 PDT)
- Tier 3: one checklist item + basic rules + specific inputs → defined output. Max parallelism, minimal context.
- Tier 2: related checklist group + Tier 3 results + shared context → group output. Local deps, bounded inconsistencies.
- Tier 1: full rules + whole checklist + objective + specs/constraints + Tier 2 results/evidence → owns coherence + final integration.
- Partitioning rule (structural): Tier 3 only if performable with supplied context alone; dependents stay grouped. Not a judge.
- Prompts are developer-defined; scheduler distributes, never authors/judges.
- N=3 fixed. More tiers = more context-translation boundaries = plot loss.

## Work-order input spec (Zack, ~11:54 PDT) — THE interface
- A work order = plain-text prompt: objective + development rules + individually numbered goals.
- Human-written or LLM-generated; equally valid; no authoring pipeline.
- Scheduler: explicit goal boundaries + registered goal types → work graph. Deps/metadata inline or simple manifest.
- Numbered goal = default unit. Split only if the goal's type permits subdivision.
- Related goals → Tier 2 groups; Tier 1 gets the whole work order.
- No LLM authors/normalizes/validates the work order. Malformed → plain error. Ambiguous intent → never reinterpreted.
- The work order defines the requested work; the scheduler defines its allocation and execution.
