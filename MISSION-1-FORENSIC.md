# MISSION 1 — FORENSIC INVENTORY (read-only)

Mode: discovery only. Do NOT modify code, deploy services, change quotas, or mutate production state.
Do NOT delete, move, or rename anything. If something looks wrong, record it — never fix it in place.

## Objective
Produce the complete evidence bundle the synthesis mission needs:

1. Forensic inventory of the actual stack: CANON authority boundary, Governor,
   LUCIDOTA Exchange lifecycle, ai-router provider lanes, Validator, Verifier,
   Proof Ledger (PL), graph services / FalkorDB, sandbox / LiteBox, Cap'n Maps.
2. Source references: exact file paths, symbols, interface contracts.
3. Quota measurements: actual measured RPM / token / latency / concurrency
   numbers from bench results, budget files, burn logs, skill docs.
4. Architecture maps: how the pieces connect today, as implemented.
5. Test evidence: which tests enforce which acceptance behavior, by symbol/file.
6. Unresolved-unknowns report: facts needed by the design that could not be verified.

## The one rule
Evidence discovery and implementation share the same identifiers and contracts.
If you discover an existing validator, identify the ACTUAL symbol and test that
enforces acceptance. The implementation plan must reference that same symbol and
test — never invent a new abstraction with a similar name.

## Verification standard
Re-verify present state. Do NOT treat historical reports, ledger summaries, or
memory notes as current truth. Read the source. Every claim is labeled:

- EXISTING AND VERIFIED (read the code + found the enforcing test)
- EXISTING BUT UNVERIFIED (code seen, no test found)
- NEW WORK (does not exist)
- BLOCKED (missing fact — state exactly what fact and why it changes the design)

Prior context identifies the CANON authority boundary, the Exchange lifecycle,
the ai-router provider lanes, and the PL distinction between recorded claims and
independent proof. Re-verify all of it against the tree as it stands now.

## Output
One evidence file per component in `~/workspace/batch-compile/evidence/<name>.md`,
each with: component, file paths, key symbols + signatures, interface contracts,
enforcing tests, measured numbers (never invented), state labels, gaps, unknowns.
