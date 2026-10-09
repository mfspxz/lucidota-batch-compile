# Queue hygiene lane — 2026-10-09

Scope: `~/workspace/compute/queue.jsonl`. ABSOLUTE PRESERVATION: no deletion,
no mutation, no history rewriting. Append-only tombstoning.

## 1. The "duplicates" — finding: ID collision, not duplication

`task-99721824` appears ×11 (queue lines 1–11), all `created_at`
`2026-10-07T19:02:01Z`, all status `queued`. They are **11 distinct tasks**,
not copies:

| line | objective (falsification fix task) |
|------|-------------------------------------|
| 1 | Close RT-A7: NaN quality score breaks total-order assumption |
| 2 | Close RT-C1: Zero integrity on trust files |
| 3 | Close RT-C2: Registry is self-attestation |
| 4 | Close RT-C3: Provenance is decoration |
| 5 | Close RT-C6: war_room is a label |
| 6 | Close RT-C7: OperatorDispatch unsupervised handoff |
| 7 | Close RT-C8: cross_check raises away the evidence |
| 8 | Close RT-C12: No cascade strategy / anti-loop guards |
| 9 | Close RT-C13: Unknown reliability scored as perfect |
| 10 | Close RT-C14: Inconsistent corrupt-input handling |
| 11 | Close RT-C15: Dispatched != completed |

## 2. Duplicate code path (root cause)

Writer: `queue.add()` in `~/workspace/compute/queue.py` (the only appender;
opens `queue.jsonl` in `"a"` mode).

Pre-RT-C16 mint (no longer in repo history — predates the factory-merge
baseline commit `2c51780`): `task_id = f"task-{int(time_ms) % 10**8}"`
— an 8-digit millisecond-timestamp mint. A burst of 11 `add()` calls inside
one millisecond on 2026-10-07T19:02:01Z produced the same id `99721824`
eleven times. Documented at `queue.py:46`:
`# RT-C16: uuid4-hex ids — ms-timestamp mod 1e8 collided under burst.`

The collision class is **already fixed**: current mint is
`f"task-{uuid.uuid4().hex[:12]}"` (same line). No new collisions possible
through `queue.add()`.

Operational impact of the 11-way collision (pre-existing, unchanged):
- `queue.mark(task_id, …)` marks **all** matching rows (no break) → the 11
  are mutually conflated on any status transition.
- `burn.py:486` `by_id = {r["task_id"]: r for r in recs}` collapses them to
  one (last wins) → 10 silently dropped from that view.
- Proper repair (re-minting 10 ids) requires **mutating existing records**,
  which is forbidden. Left for a future explicitly-authorized migration.

## 3. Tombstoning — deviation from "superseded-by", with reason

The task prescribed tombstones marking lines 2–11 "superseded-by" the line-1
record. That premise was disproved in §1: they are distinct work items, so
supersession would be a **false statement in a trust file**
(`queue.jsonl` is an `integrity.py` TRUST_FILE). Instead, 10 **collision
tombstones** were appended (same file, append-only), each recording the
collision fact honestly. Line 1 kept as canonical (per "beyond the first").

Tombstone schema: full task-record shape (loader-safe: `pending()` needs
`r["classification"]`; `shadow.py` uses `r.get("task_id","")`), unique
`tombstone-<12hex>` ids (never swept by `mark("task-99721824",…)`),
`status: "tombstoned"` (invisible to `pending()`/`drain()`; not in
`QUEUE_STATUSES` so `mark()` can never be called with it), `extra` carries
`{tombstone_for_line, tombstone_for_task_id, tombstone_for_sha256,
tombstone_for_objective, canonical_line: 1, reason, lane}`.

| tombstone id | documents line | original line sha256[:16] |
|---|---|---|
| tombstone-9699336c5e53 | 2 | 896e3e07d43cbdb1 |
| tombstone-39e86fd172b9 | 3 | 6892c748776047e6 |
| tombstone-4cced85821a4 | 4 | 02bbca7d52fe3441 |
| tombstone-b3bb190fc646 | 5 | 19d66527687ad7b8 |
| tombstone-294cf8d77e7c | 6 | f0c90d29ae509b83 |
| tombstone-b6ffa8890c99 | 7 | 5398aef8c21c6a8e |
| tombstone-289040dafea7 | 8 | 61bf671ec61e0bc9 |
| tombstone-a3a763e1f627 | 9 | 6ef36416bc129ed9 |
| tombstone-d1d45a78c28a | 10 | c885fd69972d5174 |
| tombstone-873a97456c67 | 11 | c293b77f757b4705 |

## 4. Counts before / after (by status)

| status | before | after |
|---|---|---|
| queued | 1933 | 1933 |
| failed | 734 | 734 |
| completed | 587 | 587 |
| blocked | 15 | 15 |
| tombstoned | 0 | 10 |
| **total records** | **3269** | **3279** |

## 5. Append-only verification

- Before: 1549624 bytes, sha256
  `63d9f6637c8bad2067e341b60e815d2ddc692a90d7d05a789900cbd1ee3b5f36`.
- Tombstones written via `O_APPEND` single-syscall writes (atomic; concurrent
  burn-window appends interleave safely).
- After: 1560118 bytes (+10494), 3279 records, sha256
  `c13980a92807482e5728efaa5dbf8207d078e33d0d3e26fc5de75b8c8dfeaecf`.
- **Prefix proof:** sha256 of the first 1549624 bytes of the post-append
  file == the before-hash. Zero original bytes deleted or altered; all 11
  collision records present verbatim (line-sha cross-checked before append).
- Loader smoke test: `queue._load()` → 3279, `queue.pending()` → 1933
  (unchanged), no `tombstoned` record in the drain path, tombstone ids unique.

## 6. Notes / follow-ups

- `queue.jsonl` was left **uncommitted** in the compute repo: it carries live
  appends from concurrently running burn windows; committing would attribute
  another lane's rows to this lane.
- Growth note: ~1933 queued vs ~0 completing per window is a separate
  scheduler-liveness issue, not a hygiene issue — flagged, not touched.
- If a future authorized migration re-mints the 10 collided ids, these
  tombstones (`tombstone_for_sha256`) are the join keys.
