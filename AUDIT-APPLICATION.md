# AUDIT-APPLICATION

- **Repo:** `~/workspace/batch-compile`
- **Date:** 2026-10-10
- **Auditor:** brutal-audit rollout slice 7/8 (parent orchestrator)
- **Repo type:** SPEC/DOCS repo — no production code of its own

## Disposition

| Finding | Applies? | Where / How |
|---|---:|---|
| R-1 | Applies | `evidence/redteam-wave5.md` has instance-only “FIXED” claims without dedicated re-attack sign-off |
| R-2 | Applies | Guardrail docs lack explicit “catches / cannot catch” bounds |
| R-3 | N/A | No hash-chained log in this repo |
| R-4 | Applies | `evidence/redteam-wave5.md` has explicit 4-item backlog |
| R-5 | N/A | No signature/denylist/strip games in this repo |
| R-6 | N/A | No detectors in this repo |
| R-7 | N/A | No tracked test suite; `tmp-pytest/` scratch untracked |
| R-8 | Applies | Unsigned evidence/ docs may be misread as provenance |
| R-9 | Applies | `evidence/redteam-wave5.md` and `redteam-cycles.md` act as claim/falsification logs without frozen verdict schema |
| R-10 | Applies | Work logs and red-team records are archival, not same-motion |
| R-11 | Applies | Explicit UNKNOWN list required |
| R-12 | Applies | Unsourced narrative claims require `UNVERIFIED` label |

---

## R-1 — Fix-verification claims require dedicated re-attack sign-off

**Applies.**

`evidence/redteam-wave5.md` states “FIXED in this lane (regression tests added, committed same turn)” for 8 findings. These are instance-only claims. No dedicated re-attack result is present.

Until a dedicated re-attack signs off, the 8 “FIXED in this lane” entries are `UNKNOWN`, not `PROVEN` or `FIXED`.

Claims and defeats must live in one book with one verdict per claim. Current records are split across `redteam-wave5.md` and `redteam-cycles.md`; that is not a compliant single book.

No `PROVEN/FIXED` status without a re-attack result.

---

## R-2 — Document honest bounds on every guardrail

**Applies.**

Guardrail documentation in `SPEC/` and `evidence/` does not currently state, in each case:

- what the guardrail catches;
- what it cannot catch;
- the boundary of its claimed effect.

Any guardrail statement without such bounds is `UNKNOWN`.

Hardening must freeze at the documented bound. No new hardening claims beyond the documented bound are accepted.

---

## R-3 — Hash-chained log out-of-band head copy

**N/A — this repo has no hash-chained log.**

No log in this repo is hash-chained and no log here should be called tamper-evident. If any existing document uses “tamper-evident” language, it must be corrected to `UNVERIFIED` or removed.

---

## R-4 — Triage backlogs

**Applies.**

`evidence/redteam-wave5.md` contains the explicit section:

> `RECORDED for the next build wave (not fixed — need design, not patches)`

This is a standing backlog. The four recorded-not-fixed items need complexity budgets or explicit `WONT-FIX` dispositions.

See **Wont-fix / backlog triage** below. The backlog must not grow unbounded.

---

## R-5 — Signature/denylist/strip games

**N/A — no signature, denylist, or strip games in this repo.**

This is a SPEC/DOCS repo. There are no signature-based actuators, denylists, or strip games here.

---

## R-6 — No detector without named consumer + enforcement gate

**N/A — no detectors in this repo.**

There is no detector code or detector configuration here.

---

## R-7 — Property tests vs change-detection tests

**N/A — no tracked test suite in this repo.**

`tmp-pytest/` scratch is untracked and is not part of the repo. It is excluded from audit.

If a tracked test suite is later added, R-7 policy must apply: property tests and change-detection tests separated, and property test expectations may not be rewritten without adversarial sign-off.

---

## R-8 — Unsigned provenance must be honestly-unsigned

**Applies.**

Existing `evidence/` documents are unsigned. They must not be read as provenance.

All unsigned evidence in this repo is `UNKNOWN` assertion material, labeled `honestly-unsigned`, with no verification power unless signed or anchored.

`f5-proof-ledger.md` describes a subsystem in `~/workspace/proof-ledger`, a different repo. It is not evidence from this repo and does not establish claims in this repo.

---

## R-9 — Claim/falsification log schema

**Applies.**

`evidence/redteam-wave5.md` and `evidence/redteam-cycles.md` act as claim/falsification logs.

They do not currently have a frozen verdict schema.

Allowed verdicts:

- `PROVEN`
- `DISPROVEN`
- `UNKNOWN`
- `SUPERSEDED-BY-BYPASS`

Existing verdict-less entries must be backfilled or marked `UNKNOWN`. Until backfill happens, treat all current entries as `UNKNOWN`.

---

## R-10 — Record-keeping same-motion or archival

**Applies.**

`WORK-LOG.md`, `evidence/redteam-wave5.md`, and `evidence/redteam-cycles.md` are records of events. Existing entries are archival, not same-motion.

New records must be written in the same motion as the event or explicitly declared `ARCHIVAL`.

No retroactive edits to archival records except with an archival note.

---

## R-11 — Explicit UNKNOWN list

**Applies.**

See **UNKNOWN list** below.

No “probably” passes as `PROVEN`. Uncertain items are `UNKNOWN`.

---

## R-12 — No unsourced oral footnotes

**Applies.**

Any claim not backed by an evidence doc or source is `UNVERIFIED`.

Do not cite oral footnotes as evidence. Existing narrative without source must be marked `UNVERIFIED`.

---

## Changes made today

None — document-only pass.

No code, SPEC, evidence, WORK-LOG, or backlog edits were made. This `AUDIT-APPLICATION.md` is the only deliverable.

---

## Commits

- Commit for this document: `b0352f1` (brutal-audit: R-1..R-12 application pass, docs-only repo)
- Other commits today: none

---

## Test counts

- Tracked test suite: none
- Tracked test count: `0`
- `tmp-pytest/` scratch: untracked, excluded from audit

---

## UNKNOWN list

- Whether the 8 “FIXED in this lane” findings in `evidence/redteam-wave5.md` would survive a dedicated re-attack: `UNKNOWN`
- Whether the batch-compile fixed-task-envelope claims hold against a hostile builder: `UNKNOWN` — never evidenced
- Whether the four recorded-not-fixed backlog items are still valid or exploitable: `UNKNOWN` — recheck required
- Whether `f5-proof-ledger.md` accurately describes the proof-ledger subsystem in `~/workspace/proof-ledger`: `UNKNOWN` — outside this repo, no verifiable evidence here
- Whether all `evidence/` documents are current and complete: `UNKNOWN`
- Whether any guardrail has a bounded, honest “cannot catch” statement: `UNKNOWN` — not yet documented

No item in this repo is currently `PROVEN`.

---

## Wont-fix / backlog triage

The backlog is the four items in `evidence/redteam-wave5.md` under:

> `RECORDED for the next build wave (not fixed — need design, not patches)`

Required disposition per R-4:

| Backlog item | Disposition |
|---|---:|
| Recorded-not-fixed item 1 | `TBD` complexity budget or explicit `WONT-FIX` |
| Recorded-not-fixed item 2 | `TBD` complexity budget or explicit `WONT-FIX` |
| Recorded-not-fixed item 3 | `TBD` complexity budget or explicit `WONT-FIX` |
| Recorded-not-fixed item 4 | `TBD` complexity budget or explicit `WONT-FIX` |

Until a complexity budget or explicit `WONT-FIX` is assigned, each item remains `OPEN UNKNOWN`.

New backlog additions require a same-motion triage note and a budget or `WONT-FIX`. Backlog must not grow unbounded.
