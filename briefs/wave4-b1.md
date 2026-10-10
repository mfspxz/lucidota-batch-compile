# WAVE-4 LANE B1 — PIPE-001 prompts registry, then PIPE-005 worker envelopes

## Task
Implement the next batch slice in dependency order: PIPE-001 first, then PIPE-005
(which depends on PIPE-001). Production code, named as the real thing.

## Inputs
- `~/workspace/batch-compile/SPEC/12-implementation-backlog.md`: PIPE-001 (§59–77),
  PIPE-005 (§201–229), dependency graph (§346–351).
- Existing modules: `~/workspace/compute/pipeline/{workorder,partition,allocate,checks,goaltypes}.py`
  (read them; match their conventions: i64 guards, fail-closed, deterministic ids).
- `partition.py::_t3_assignment` sets `"prompt_ref": None  # Pinned by PIPE-001` —
  after prompts.py exists, wire it to the pinned default prompt (see below).

## Deliverables
1. **PIPE-001**: NEW `~/workspace/compute/pipeline/prompts.py` —
   `PROMPTS_VERSION = "prompts/1"`, `register(prompt_id, version, text, sha256)`,
   `get(prompt_id, version) -> str`, `pin(prompt_id) -> (version, sha256)`.
   NEW `~/workspace/compute/pipeline/prompts_test.py`.
   NEW `~/workspace/compute/pipeline-prompts/` — content-addressed prompt entries.
   Rules: prompts are developer-defined/supplied; the module DISTRIBUTES pinned
   `(prompt_id, version, sha256)` — it never authors, rewrites, judges, or selects
   prompt text (test asserts this via static check: grep for model-call imports → empty).
   Immutable once registered; re-register of same id+version with different text → rejected.
   Register one clearly-marked DEFAULT placeholder prompt (e.g. `default-tier-rules`,
   text = the four development rules from the §13 example work order) and document
   in-module that production prompts are developer-supplied replacements.
   Acceptance: register→get roundtrip byte-identical; text change under same
   id+version → rejected; `pin()` resolves latest; pytest green.
2. **PIPE-005**: NEW `~/workspace/compute/pipeline/worker.py` —
   `t3_envelope(unit, prompt_text)`, `t2_envelope(bundle, t3_results, prompt_text)`,
   `t1_envelope(kit, prompt_text)`, `run_unit(envelope, allocation) -> AttemptRecord`
   (thin wrapper: envelope → `dispatch.create_dispatch` → fake-adapter `execute()`
   → artifact + receipt → `dispatch.complete_dispatch`/`fail_dispatch`; tier on the attempt).
   NEW `~/workspace/compute/pipeline/worker_test.py` (fake adapters; 0 provider calls).
   Rules: context breadth monotonic T3 < T2 < T1 (asserted); a worker response can
   never self-accept, raise its own budget, authorize a tool, or change policy
   (10 adversarial responses → named violations, mirroring
   `indy-reads/src/governor.rs` `AiProposal::sanitize`); deterministic timeout from
   the work order; prompts distributed from the registry, never authored here.
   Wire `prompt_ref` in partition assignments to the pinned default prompt.
   Acceptance: T3 envelope has zero out-of-allowlist refs; ref-count monotonic;
   10 adversarial → rejected with named violation; timeout → `fail_dispatch`;
   every attempt emits an envelope-sealed receipt; pytest green.

## Acceptance (lane)
- `cd ~/workspace/compute/pipeline && python3 -m pytest -q` → all green (existing 147 + new).
- One commit per PIPE task, same-turn, message `PIPE-001: ...` / `PIPE-005: ...`.

## Constraints
- 0 provider calls. Local-only.
- Write scope: `~/workspace/compute/pipeline/` + `~/workspace/compute/pipeline-prompts/` only.
- Existing modules are read or called, never rewritten.
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
