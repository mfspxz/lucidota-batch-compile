# WAVE-4 LANE B2 — PIPE-008 ledger contract pin, then PIPE-009 fixed retry rules

## Task
Implement two independent PIPE tasks in order: PIPE-008 (tests existing code, no
dependency), then PIPE-009 (depends on PIPE-007, already committed). Production
code, named as the real thing.

## Inputs
- `~/workspace/batch-compile/SPEC/12-implementation-backlog.md`: PIPE-008 (§283–300),
  PIPE-009 (§301–323).
- Existing: `~/workspace/compute/ledger.py` (`record()`), `~/workspace/compute/envelope.py`
  (`wrap`/`verify`/`verify_chain`), `~/workspace/compute/pipeline/checks.py`.

## Deliverables
1. **PIPE-008**: NEW `~/workspace/compute/pipeline/ledger_contract_test.py` — pins the
   pipeline's ledger contract: every pipeline action recorded via `ledger.record()`;
   every receipt sealed with `envelope.wrap` / verified by `envelope.verify_chain`;
   tier + unit/bundle/kit refs carried on attempt records; corrections are new
   entries (never edits).
   NEW `~/workspace/compute/pipeline/LEDGER-CONTRACT.md` — one page: symbols,
   fields, guarantees.
   Rules: NO code changes to `ledger.py`/`envelope.py` (KEEP — the test passing
   against the current tree verifies this); test failure blocks the pipeline —
   the contract is not "fixed" by the pipeline.
   Acceptance: pytest green against the unmodified tree; tamper fixture →
   `verify_chain` raises.
2. **PIPE-009**: NEW `~/workspace/compute/pipeline/retry.py` —
   `FAILURE_CLASSES` (maps to the worker.js taxonomy: RETRYABLE / PERMANENT /
   POLICY / AUTH / QUOTA / CAPABILITY / PROVIDER / VERIFICATION_FAILURE),
   `next_action(class, attempt, tier) -> retry_at_tail | dead_letter | blocked | failed`,
   `MAX_ATTEMPTS = 5`, per-class deterministic backoff table.
   Tier note: T1-kit failure → `blocked` (never silently re-run the full-context
   developer; a failed integration is a human-visible event); T3/T2 follow the
   standard table. Dead-letter path: `~/workspace/compute/pipeline/dead-letter.jsonl`
   (note: backlog text says `~/workspace/compute/pipeline-dead-letter.jsonl` —
   use the pipeline-local path and record the correction in your commit message).
   NEW `~/workspace/compute/pipeline/retry_test.py` — fault injection:
   200 synthetic tasks × 8 failure classes × 3 tiers → 100% terminal, 0 lost,
   0 exceeding MAX_ATTEMPTS; T1 failure → `blocked`, never auto-retried.
   Simulated clock; 0 provider calls.
   Rules: retries to the queue tail, never head-of-line; dependency-blocked stays
   blocked; every task terminates in `done | failed | blocked | dead_letter |
   explicitly_unresolved` — liveness by bounded attempts.
   Acceptance: pytest green.

## Acceptance (lane)
- `cd ~/workspace/compute/pipeline && python3 -m pytest -q` → all green.
- One commit per PIPE task, same-turn, message `PIPE-008: ...` / `PIPE-009: ...`.

## Constraints
- 0 provider calls. Local-only. Simulated clock for retry tests.
- Write scope: `~/workspace/compute/pipeline/` only.
- `ledger.py` / `envelope.py` are read-only — never modified.
- Consult `~/ledger` via grep for context; don't dump it.
- No deletions — archive safely only. Production naming throughout.

## FORBIDDEN GIT OPS
NEVER run `git reset` (any mode) — destroys uncommitted work tree-wide.
NEVER run `git stash` — parks work where concurrent lanes can lose it.
NEVER run `git clean -f` — deletes untracked fixtures/evidence.
NEVER run `checkout`/`switch --force` (or `-f`) — overwrites without asking.
NEVER run `push --force` (or `-f`) — rewrites shared history.
NEVER rewrite history (`rebase`, `commit --amend`, `filter-branch`, `filter-repo`, BFG).
Stage selectively (`git add <paths>`); commit same-turn. If in doubt, stop and report.
