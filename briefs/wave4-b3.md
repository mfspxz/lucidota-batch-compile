# WAVE-4 LANE B3 — PIPE-006 burn.py minimal pipeline mode (EXTEND, flag-guarded)

## Task
PIPE-006 is now unblocked (PIPE-004 and PIPE-005 are committed). Extend burn.py
with the minimal pipeline mode. Production code, named as the real thing.

## Inputs
- `~/workspace/batch-compile/SPEC/12-implementation-backlog.md`: PIPE-006 (§230–249).
- `~/workspace/batch-compile/SPEC/11-migration.md` §3 (PIPELINE_MODE semantics).
- Existing: `~/workspace/compute/burn.py` (read it; extend, never rewrite),
  `~/workspace/compute/pipeline/{workorder,partition,allocate,checks,worker,prompts,retry}.py`.

## Deliverables
1. NEW `~/workspace/compute/pipeline/flags.py` — `mode()`, `killed()`.
   Env vars read at call time, NEVER cached.
2. EXTEND `~/workspace/compute/burn.py` — additive function
   `run_pipeline_cycle(workorder_path)` implementing the loop:
   Partition → Group → tiered Assign → Schedule → tiered Workers → Record →
   checks → retry → Repeat, using the committed pipeline modules.
   Called ONLY when `PIPELINE_MODE=enforced`.
3. NEW `~/workspace/compute/pipeline/pipeline_mode_test.py` — flag matrix
   (off / shadow / enforced × kill) → correct path each; legacy path untouched.

## Rules
- Additive hunk only. NO existing burn.py symbol's signature changes.
- Mode `off`/unset/kill ⇒ legacy path; a reference dry-run must reproduce the
  pre-change `burn.STATUS.json` counter shape.
- No second driver loop (hard rule) — this is the one pipeline entry point.
- Heads-up from lane B1: the secret-scrub pre-commit hook flags long
  high-entropy identifiers (LONG_PAT + Shannon entropy) — keep test names and
  string constants under ~40 chars or expect scrub blocks.

## Acceptance
- `cd ~/workspace/compute/pipeline && python3 -m pytest -q` → all green.
- `cd ~/workspace/compute && git diff --stat` shows only the additive hunk + import
  in burn.py, plus the two new files.
- One commit, same-turn: `PIPE-006: ...`.

## Constraints
- 0 provider calls. Local-only.
- Write scope: `~/workspace/compute/burn.py` (additive only) +
  `~/workspace/compute/pipeline/` (flags.py, pipeline_mode_test.py).
- Consult `~/ledger` via grep for context; don't dump it.
- No deletions — archive safely only.

## FORBIDDEN GIT OPS
NEVER run `git reset` (any mode) — destroys uncommitted work tree-wide.
NEVER run `git stash` — parks work where concurrent lanes can lose it.
NEVER run `git clean -f` — deletes untracked fixtures/evidence.
NEVER run `checkout`/`switch --force` (or `-f`) — overwrites without asking.
NEVER run `push --force` (or `-f`) — rewrites shared history.
NEVER rewrite history (`rebase`, `commit --amend`, `filter-branch`, `filter-repo`, BFG).
Stage selectively (`git add <paths>`); commit same-turn. If in doubt, stop and report.
