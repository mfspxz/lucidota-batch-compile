# MASTER DIRECTIVE — filed 2026-10-09 ~11:41 PDT (Zackary's steering prompt, verbatim source of record)

Governing execution directive. Priority over both missions. Mode: autonomous
engineering and remediation. Duration: continuous until he explicitly stops it.

Objective: working, measured, tested, secure, self-operating, rate-limit-aware
multi-tier engineering execution system integrated with CANON / Governor /
LUCIDOTA Exchange / ai-router / Validator / Verifier / Proof Ledger /
FalkorDB / LiteBox / Cap'n Maps and related stack. Execution, not another plan.

## Adopted deltas (corrections to prior setup)

1. **39 RPM is a hypothesis, not a fact.** Pace NVIDIA at the VERIFIED limit,
   sustainable below it, accounting for burst behavior + token quotas. Never let
   independent agents each assume they own the whole shared quota. Reserve before
   dispatch; reconcile actuals; persist accounting across restarts.
2. **Preservation invariant is absolute and procedural:** before ANY operation
   that could overwrite/discard/truncate/prune/reset/clean/force-push/migrate
   destructively — identify affected state, backup outside the affected location,
   verify backup complete + readable, record location/revision/hashes/recovery,
   confirm restoration possible, then proceed only if authorized and safe.
   Archive is not delete. Canonicalize is not erase.
3. **Measure accepted artifacts, not agent count.** Track: accepted tasks/min,
   artifact yield, queue age/depth, provider utilization, token consumption,
   retry/rejection rates, validation throughput, cost per accepted artifact.
4. **Event-triggered continuation must be real.** Completion handoffs chain the
   waves (sanctioned shape: wake on completion events, never timer polls).
   Never claim persistent operation that isn't actually configured + observed.
5. **Reporting: compact, evidence-based.** Surface only: material verified
   milestones, critical security/correctness findings, real blockers, significant
   architectural conflicts, completion evidence. No routine interruptions.

## The loop (until he says stop)

Inspect backlog+state → highest-value executable work → compute quota capacity →
dispatch all eligible independent tasks → validate immediately → requeue
eligible failures / isolate terminal → adversarial + gardening in parallel →
tier integration → deterministic acceptance + independent verification →
safe apply/merge → receipts → next batch automatically. Recover durable task
ledger each cycle; never restart from zero.

## Definition of done (evidence-required)

Real quotas represented correctly; concurrent execution under constraints;
state survives restarts + duplicate delivery; invalid outputs rejected; retry
queues terminate; provider failures don't stop independent work; tier
transitions preserve identity/contracts/evidence; governor enforces authority;
validation + independent verification operational; merge gates hold;
adversarial regressions tested; final tree passes acceptance; canonical
implementation unambiguous; existing work recoverable; event continuation
actually configured + observed; cost/throughput/defects measured and reported.

Full prompt text retained in chat history (side chat d0152cac, 2026-10-09).
