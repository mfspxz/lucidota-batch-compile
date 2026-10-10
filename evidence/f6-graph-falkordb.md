# F6 — Graph services, FalkorDB, Cap'n Maps: forensic inventory

Forensic mission 1, evidence bundle. Read-only investigation conducted 2026-10-09 ~11:38–11:50 PDT.
Method: filesystem inventory, source reads, live socket verification (PING/MODULE/GRAPH.LIST/RO_QUERY only),
SQLite row counts, ledger grep. Nothing modified, nothing deleted.

## 1. Summary

| Area | Verdict |
|---|---|
| Graph stores in production use | **5 distinct stores**, all file-local: SQLite entity graph (canonical), per-goal dev-graph.json files (58), Kuzu entity index, SQLite lifelog graph, SQLite exchange evidence graph |
| FalkorDB | **LIVE and verified** — Redis 8.10.2 + falkordb.so on 127.0.0.1:6379 (pid 2100), 10 graphs present, `devgraph` graph queryable. Role today: hackathon practice/dogfood harness only (Graph Hacks, Oct 15–18). **Not wired into any production pipeline.** |
| Entity-graph visit matcher | **EXISTS as code** — `~/workspace/lifelog/matcher.py` with adversarial tests. Staged; live data blocked on phone location permission. |
| Graph MCP server | **EXISTS AND VERIFIED** — v0.2.0, 29/29 selftest green (2026-10-07 dogfood report), typed domain ops over the SQLite entity graph, fail-closed raw SQL. |
| Graph memory pipeline (reader/writer) | **EXISTS** — Gemini reader (trinary judgments) → deterministic writer (validated apply), with unit tests on throwaway Kuzu. |
| Cap'n Maps | **NOT PRESENT in the workspace.** No code, docs, contracts, or ledger entries for anything named "Cap'n Maps". See §8. |

## 2. Graph stores in use (measured)

### 2a. Entity graph — SQLite (canonical operational graph)
- Path: `~/workspace/entity-graph/graph.db` (245,760 bytes, modified 2026-10-09 16:17 PDT)
- Front page: `~/workspace/entity-graph/GRAPH.md` (human-readable; DB is what is queried)
- Tables (verified via `.tables`): `nodes`, `edges`, `attributes`, `observations`, `hunches`, `typed_edges`
- Row counts (measured 2026-10-09): **82 nodes, 90 edges, 7 observations, 0 hunches, 0 typed_edges**
- Node identifiers: integer PK `id`, `name TEXT UNIQUE NOT NULL`, `type`, `notes`, `first_seen`
- Rules (from GRAPH.md): codenames are final and never replaced with real identities; record only what Zackary says; his-language attributes (Friend/Enemy/Fuckhead/Hero/Protected); trinary Verdict attribute on nodes
- State: **EXISTING AND VERIFIED** (live DB read directly)

### 2b. Dev-graphs — per-goal JSON (planning/scheduling graphs)
- Pattern: `~/workspace/goals/<slug>/hidden_files/dev-graph.json` — **58 files present** (measured)
- Manager: `~/workspace/bin/devgraph.py` — CLI (`init`, `add-node`, `add-edge`, `set-status`, `ready`, `blocked`, `stats`, `validate`); status forward-only (open → in_progress → done); `ready` computes `enables`-predecessor completion
- Schema: `~/workspace/dev-graph/SCHEMA.md` — closed node types (goal/epic/task/track/feature/research/design/plan/practice/ktest/benchmark/query/demo_beat/schema_label/decision/risk/deliverable/milestone); closed edge vocabulary (`part_of`, `informs`, `enables`, `tests`, `demos`, `targets`, `mitigates`, `decides`, `scheduled_for`); `enables` is the scheduling edge
- Enrichment scripts: `~/workspace/bin/enrich-graphs.py` (idempotent merge-by-id, never regresses status), `~/workspace/goals/graph-hacks-2026-context-forge-falkordb-agent/hidden_files/expand-graph.py`
- Graph Hacks reference graph: 147 nodes / 200 edges (84 done / 42 in_progress / 21 open — measured)
- Convention: "No secrets in the graph. Ever."
- State: **EXISTING AND VERIFIED**

### 2c. Kuzu entity index — derived from hypertimeline
- Builder: `~/workspace/graph-fabric/build_graph.py` — docstring: "Deterministic, $0, no LLM. Log stays dumb: hypertimeline.jsonl is source of truth, this DB is a derived index, rebuildable from scratch." Entity sources: agent-extract `entities[]` arrays + name mining. Fellegi-Sunter typing resolves unknowns.
- DB: `~/workspace/graph-fabric/zack.db` (22,241,280 bytes, modified 2026-10-09 18:03 PDT)
- Reported scale (reader README, doc-reported not re-measured): 15,250 entities, 28,353 events, 166K MENTIONED_IN, 108K CO_OCCURS
- State: **EXISTING AND VERIFIED** (file + builder source read; exact counts doc-reported)

### 2d. Lifelog temporal graph — SQLite
- Path: `~/workspace/lifelog/lifelog-graph.db`
- Schema: `~/workspace/graph-recalibration/lifelog-temporal-schema.sql`
- Written by the visit matcher (§4)
- State: **EXISTING BUT UNVERIFIED** (file presence not re-checked this run; schema + writer code read)

### 2e. Exchange evidence graph — SQLite
- Paths: `~/workspace/exchange/evidence-graph.db`, `~/workspace/exchange/evidence-graph-sync.py`
- State: **EXISTING BUT UNVERIFIED** (not opened; files present)

## 3. FalkorDB integration state

**Live server (verified by socket this run):**
- `redis-server` pid 2100 listening on `0.0.0.0:6379` (verified via `ss`)
- Module loaded: log `~/workspace/falkordb-local/falkordb.log` shows `<graph> Created new data type 'graphdata'`, "Module 'graph' loaded from /home/hatch/workspace/falkordb-local/img/layers/rootfs/var/lib/falkordb/bin/falkordb.so" (2026-10-09 17:23:21); RDB loaded with 20 keys; "Ready to accept connections"
- `MODULE LIST` responds (2 modules); `PING` → PONG; `DBSIZE` → 20 keys
- `GRAPH.LIST` returns **10 graphs**: `vectest4`, `constrainttest`, `vectest3`, `devgraph`, `test`, `sanity`, `moneytest`, `idxtest`, `vectest2`, `verify`
- `GRAPH.RO_QUERY devgraph "MATCH (t) RETURN count(t)"` → **106 nodes**, 0.025 ms internal execution

**Code:**
- `~/workspace/falkordb-local/fb.py` — minimal dependency-free RESP client (`class FalkorDB`, `q(graph, cypher)` → `GRAPH.QUERY`), sanity query `RETURN 1 AS one`
- `~/workspace/falkordb-prac/dogfood.py` — the verification harness: loads the Graph Hacks `dev-graph.json` into graph `devgraph` with INDEX-FIRST binding rule, UNWIND bulk-load (the "K1 pattern"), then runs Q1 blast-radius, Q2 WHY-chain, Q3 aggregations, PROFILE, and adversarial checks (bare-path RETURN, duplicate aliases, RO_QUERY write rejection). Documents engine realities: `allShortestPaths()` non-functional on the 6.0.2 engine; `shortestPath()` only in WITH/RETURN; reliable WHY = variable-length + min(length) aggregation ("E3-proven").
- Install: `~/workspace/falkordb-prac/falkordb.so` (50 MB), `redis-stable` source dir, venv — assembled 2026-10-08
- No Rust `falkordb` crate usage anywhere in workspace (grep of `*.rs`/`Cargo.toml` — zero hits). The dev-graph decision node `dec-falkordb-rs` ("falkordb-rs v0.10.x picked (embedded harness)") is a **hackathon pre-event decision**, not an implemented integration.

**Role:** practice/dogfood for Graph Hacks 2026 (goal `graph-hacks-2026-context-forge-falkordb-agent`, event Oct 15–18). Goal hard boundaries: INDEPENDENT from the main project, synthetic data only (fictional NORTHSTAR company), pre-event work MUST NOT become FalkorDB integration or submission code. **No production pipeline reads or writes FalkorDB.** 
- State: **EXISTING AND VERIFIED** (live server + harness source); production integration: **UNKNOWN / not present**

## 4. Entity-graph visit matcher

- Code: `~/workspace/lifelog/matcher.py` (Python stdlib only)
- Pipeline: tracklog points → sanitize → stay-point clustering (**150 m / 30-min gaps**, `STAY_MAX_GAP_S=1800`, `STAY_MAX_DIST_M=150`, `MIN_STAY_POINTS=2`) → visit nodes → `VISITED` edges to places, `VISITED_BY` edge to Zackary, `AT_KNOWN_PLACE` edges to known place entities
- Properties: ADD-only, deterministic ids, idempotent re-runs, append-only watermark on `tracklog.db`; every inferred edge carries **provenance, confidence 0–1, trinary verdict**; geocoder failures degrade to lat/lon labels, never cached; `--self-test` mode
- Bootstrap: `~/workspace/graph-recalibration/lifelog-temporal-schema.sql` onto `lifelog-graph.db` + one-time additive migration of `entity-graph/graph.db`
- Tests: `~/workspace/adversarial/test_matcher_adversarial.py` (plus a mirror copy under `~/workspace/cutecity-git/lucidota/`)
- Goal: `nightly-entity-graph-visit-matcher` (goal_30cc1d60a256) — description explicitly says "Verify whether any matcher was ever built; if not, spec and stage it."
- Live-data status: blocked on phone location permission (goal + standing memory)
- State: **EXISTING BUT UNVERIFIED** (code read, self-test not executed this run)

## 5. Graph MCP server (model-facing interface)

- `~/workspace/mcp-servers/graph/server.py` — stdio JSON-RPC 2.0, pure stdlib, `{"name": "graph", "version": "0.2.0"}`
- Backend: `~/workspace/entity-graph/graph.db` **READ-ONLY**; observations live in a separate `observations` table; observation status always `OBSERVED`; contradictions surfaced, never resolved; no tool invents state
- Domain tools: `entity.get`, `relationship.get`, `path.find`, `observation.record`, `temporal.query`, `provenance.trace`, `contradictions.find`
- `sql.raw`: maintenance-only, disabled by default (`GRAPH_MCP_ALLOW_RAW=1` to enable; SELECT/WITH only, writes rejected even when enabled)
- Doctrine (v0.2.0): "Graphical Intuition" — hunches as typed statements, a VIEW not a new graph machine; `RESEMBLES != CAUSES` enforced in query
- Test evidence: `DOGFOOD-REPORT.md` (2026-10-07) — `python3 server.py --selftest` → **29 pass, 0 fail**; live stdio drive against real DB (24 nodes at the time); one code-only bug found and fixed (hardcoded `relation.assert_typed` note); dogfood rows deleted afterward, zero residue verified
- State: **EXISTING AND VERIFIED**

## 6. Graph memory pipeline (reader → writer)

- Reader: `~/workspace/graph-memory/reader/` — whole-graph analysis over Gemini 1M-token context (`serialize.py`, `gemini.py` using `gemini-3.8-flash` verified live 2026-10-09, `prompts.py`, `run.py`); privacy doctrine binding (person names → synthetic IDs, `.anon-map.json` 0600 never leaves machine)
- Contract: `~/workspace/graph-memory/writer/JUDGMENT-SCHEMA.md` — reader NEVER writes; drops judgment JSON files; writer ingests ONLY through deterministic validation. **"Gemini proposes, deterministic machinery disposes."**
- Judgment fields: `judgment_id` (unique, reruns are duplicate no-ops), `ts`, `model`, `verdict` ∈ {proven|disproven|unknown} (trinary), `facts` (ops), `evidence` (EventT `vid`s), `rationale` (free text, never trusted/ingested)
- Verdict gating: `proven` requires non-empty evidence with every `vid` existing in live EventT table (else whole-judgment `no_evidence` reject); `disproven` → no graph changes, sealed negative receipt; `unknown` → quarantined
- Writer: `~/workspace/graph-memory/writer/writer.py`; tests `test_writer.py` run against **throwaway Kuzu DB in workspace scratch** (live `zack.db` never touched)
- State: **EXISTING BUT UNVERIFIED** (sources read; test suite not executed this run)

## 7. FalkorDB-adjacent research (not integrations)

- `~/workspace/goals/graph-hacks-2026-context-forge-falkordb-agent/hidden_files/research/` — agent1-falkordb-graphrag.md, net-falkordb-docs.md, net-rust-falkordb.md, prac-falkordb-local.md, prac-dogfood.md, q1/q2/q3 query sketches, killgate-report-schema.md, RECONCILIATION-2026-10-08.md — pre-event research only
- Ledger mentions of "falkordb": one chat_verbatim about the public `FalkorDB/falkordb-rs` GitHub repo (recon target list), no integration records
- State: research artifacts, **EXISTING BUT UNVERIFIED** for currency

## 8. Cap'n Maps — canonical identity finding

**Measured result: "Cap'n Maps" does not exist anywhere in the workspace or ledger.**
- Greps for `Cap'n Maps` / `CapnMaps` / `capn-maps` across all `*.md` return only the two batch-compile mission documents and the WORK-LOG line for this exact forensic task ("F6 graph-falkordb: graph stores, FalkorDB state, Cap'n Maps identity"). Zero ledger hits. Zero code hits.
- The mission docs ask for "discovered canonical identity + actual purpose" — the discovery is that the component is **not present**; there is no discovered contract to use. Per the mission's own rule, inventing one is forbidden.
- Closest existing identities, recorded only to prevent confusion:
  - **Cap'n Web** (`capnweb` npm package, Cloudflare open-source object-capability RPC) — researched in `~/workspace/cloudflare-os-research/notes/2026-10-08-capnweb-rpc-boundary.md` (cycle 01, confirmed from `cloudflare/cloudflare-os` source) and cycle20; fork spec `~/workspace/forks/specs/capnweb-SPEC.md` (mfspxz/capnweb, capability patterns: membrane/caretaker/receipt wrapper). This is an **RPC/capability library**, not a maps product.
  - CuteCity GIS / pedicab mapping facet — separate mapping work under `cutecity`/`tricycle-corp`, no "Cap'n" naming found.
- Scheduler implication (for Mission 2): Cap'n Maps must be treated as **BLOCKED / UNKNOWN** — no role may be assigned to it in the DAG until an actual contract is discovered. If the intended referent was Cap'n Web, its proven capability is cross-boundary object-capability RPC, and that contract should be referenced by its real name.
- State: **UNKNOWN** (term originates in the mission docs only)

## 9. Authoritative / derived / experiential — measured mapping

| Layer | What | Source of truth | Evidence |
|---|---|---|---|
| **Authoritative** | Append-only ledger `~/ledger/ledger-0001.jsonl` | The ledger itself | Trinary epistemics, UTC timestamps, append-only (standing doctrine) |
| **Authoritative** | hypertimeline JSONL | `~/workspace/hypertimeline/hypertimeline.jsonl` | build_graph.py docstring: "Log stays dumb: hypertimeline.jsonl is source of truth" |
| **Authoritative** | Entity-graph semantic content | `~/workspace/entity-graph/graph.db` | GRAPH.md rules: codenames final, record only what Zackary says; server never upgrades semantic status |
| **Derived** | Kuzu `graph-fabric/zack.db` | Rebuildable from hypertimeline | build_graph.py: "this DB is a derived index, rebuildable from scratch" |
| **Derived** | Dev-graph JSON files | Authored via `devgraph.py` CLI | SCHEMA.md; forward-only status; idempotent merges |
| **Derived** | GRAPH.md front page | Rendered from graph.db | Header states DB is what is queried |
| **Derived** | Exchange evidence graph | Synced by `evidence-graph-sync.py` | File + sync script present |
| **Experiential** | Observations | `observations` table in entity-graph (status always OBSERVED) | graph MCP server docstring; 7 rows measured |
| **Experiential** | Hunches (Graphical Intuition view) | `hunches` table (0 rows measured) | server.py v0.2.0 docstring: "a VIEW, not a new graph machine" |
| **Experiential** | Graph-memory reader slices | "Connected experience" vs "Ordered operational record" (ledger) | reader README: "the model is the 5% judgment layer, never the store" |

Ontology note: the GO-50/O-25/C-25 framework doc (`~/workspace/user/files/GO_ONTOLOGY_FRAMEWORK_10_bsn6.md`) claims a `go-ontology` crate at `PALANTOUR/crates/go-ontology/` with 5 passing tests. **The crate path was not found in the workspace** — framework doc EXISTS, code verification BLOCKED on the missing path (possibly in the private PALANTOUR checkout / cutecity-git; not verified).

## 10. Queries / identifiers supported (measured)

**Entity graph (SQLite, via graph MCP server v0.2.0):**
- `entity.get` (by name; missing entity → honest REJECTED), `relationship.get`, `path.find` (1-hop demonstrated), `observation.record` (→ OBSERVED terminal), `temporal.query`, `provenance.trace`, `contradictions.find`
- Node identity: integer `id` PK + `name UNIQUE`; edges carry provenance per the server's posture

**Dev-graphs (via `devgraph.py`):**
- `ready` (open nodes with all `enables`-predecessors done), `blocked`, `stats`, `validate`
- Node identity: kebab-case string ids (type-prefixed by convention)

**FalkorDB (Cypher, verified live on `devgraph`):**
- Proven patterns from dogfood.py: index-first then UNWIND bulk load; blast-radius `MATCH p=(t)-[rels*1..6]->(imp)` with min-hop ordering; WHY-chain incoming provenance; `algo.SPpaths` for known-endpoint trails; `GRAPH.EXPLAIN` index-scan proof; `GRAPH.RO_QUERY` for reads
- Engine realities (documented in dogfood.py): `allShortestPaths()` non-functional; `shortestPath()` WITH/RETURN only

**Lifelog matcher:** deterministic stay-point → visit edges; all edges carry provenance + confidence + trinary verdict

## 11. Per-finding state table

| # | Finding | State |
|---|---|---|
| F6-01 | SQLite entity graph, 82 nodes / 90 edges / 7 observations | EXISTING AND VERIFIED |
| F6-02 | 58 per-goal dev-graph.json + devgraph.py CLI + SCHEMA.md | EXISTING AND VERIFIED |
| F6-03 | Kuzu zack.db derived index (22 MB) + build_graph.py | EXISTING AND VERIFIED (counts doc-reported) |
| F6-04 | Lifelog lifelog-graph.db + temporal schema | EXISTING BUT UNVERIFIED |
| F6-05 | Exchange evidence-graph.db + sync script | EXISTING BUT UNVERIFIED |
| F6-06 | FalkorDB live on 127.0.0.1:6379, 10 graphs, devgraph 106 nodes | EXISTING AND VERIFIED |
| F6-07 | FalkorDB in any production pipeline | UNKNOWN — none found; role is hackathon practice only |
| F6-08 | falkordb-rs embedded integration | UNKNOWN — decision node exists, zero code hits |
| F6-09 | Visit matcher code + adversarial tests | EXISTING BUT UNVERIFIED (self-test not run) |
| F6-10 | Graph MCP server v0.2.0, 29/29 selftest | EXISTING AND VERIFIED |
| F6-11 | Graph-memory reader/writer + judgment schema | EXISTING BUT UNVERIFIED (tests not run) |
| F6-12 | Cap'n Maps canonical identity | UNKNOWN — term exists only in mission docs; no artifact |
| F6-13 | GO-50/O-25/C-25 ontology crate | EXISTING BUT UNVERIFIED — doc exists, code path not found |

## 12. Unresolved unknowns (blockers for Mission 2 design)

1. **Cap'n Maps**: no contract exists. Any DAG role for it is BLOCKED until a real contract is produced. If the intended referent is Cap'n Web, Mission 2 should name it correctly and use the RPC-boundary contract from `cloudflare-os-research/notes/2026-10-08-capnweb-rpc-boundary.md`.
2. **Which graph is authoritative for task discovery/dependencies in the batch-compile DAG?** Candidates are dev-graph.json (`enables` edges, `ready` computation — the natural fit) vs FalkorDB (currently hackathon-only). The dev-graph system is the existing, verified scheduling substrate.
3. **FalkorDB production readiness**: server is live and dogfooded, but no pipeline consumes it; the Graph Hacks goal's hard boundary forbids mixing it with the main project.
4. **graph-memory writer test currency**: tests exist but were not executed this run; the `receipts/` dir has content (not inspected).
5. **lifelog-graph.db and evidence-graph.db**: presence not re-verified this run.
