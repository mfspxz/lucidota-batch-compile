# batch-compile — organelle mapping decisions

Mission-control repo (`~/workspace/batch-compile`): work orders, briefs, SPEC,
evidence for driving batch-compile missions through the compute pipeline.
The computation lives in `~/workspace/compute/pipeline/`; this repo's
capability is *invoking* that pipeline over its work orders.

## Consolidation (corrects the prior wave-5 pass)

The prior pass created three manifests — pipeline-driver / plan-partitioner /
workorder-parser — all dispatching to the SAME command
(`../compute/pipeline/driver.py` with no op distinction): three ops, one
identical invocation, and one shared codon `bb`. That was blind splitting.

The code's actual seam (DRIVER.md + `pipeline/driver.py` argparse): ONE
driver with three modes — `--dry-run` (parse→partition→plan, no dispatch),
`--shadow` (full loop through the fake adapter, 0 provider calls),
`--live` (full dispatch through an injected provider adapter). Parse and
partition are not separately invocable via CLI (`workorder.py` /
`partition.py` have no `__main__`); the observable stage boundary is the
mode flag. Per the ledger-graph precedent (one organelle where the core is
indivisible), this repo is ONE organelle with three mode-ops. The two
superseded manifests were `git rm`'d (never registered anywhere; the
consolidation is recorded here, not silent).

## Capability units

| Unit | Entry | Organelle ops | Decision |
|---|---|---|---|
| batch-compile-driver (`bd`) | `python3 -m pipeline.driver` (cwd `~/workspace/compute`) | `dry_run`, `shadow_run`, `live_run` | **Bespoke.** Mission-specific work-order execution (Goals 1–8, `driver.work-order.txt`). No ref organelle runs a DAG pipeline. Cross-repo note: when compute registers `compute-pipeline` (`cp`), these ops delegate to it; until then the adapter shells to the driver module directly (documented invocation from DRIVER.md). |

`live_run` is ExternalEffect (real provider calls, quota spend) and requires
capability `batch-compile.driver:live`; `dry_run`/`shadow_run` are ReadOnly.

## Reference-organelle check (all 12 considered, none adopted)

A pipeline driver is none of the 12 primitives (kv/http-fetch/text-transform/
json-validate/hash-seal/time-oracle/geo-point/ledger-append/notify/
scrape-extract/model-call/file-cas). The driver *calls* model-call-shaped
adapters internally, but the unit's contract is work-order execution.

## Deliberate exclusions

- `SPEC/`, `briefs/`, `*.work-order.txt`, `MASTER-DIRECTIVE.md`,
  `MISSION-*.md`, `ADDENDUM-*.md`: mission inputs/docs, not capabilities.
- `evidence/`: run evidence (data).
- `tmp-pytest/`: scratch.
- `pipeline-driver.manifest.json`, `plan-partitioner.manifest.json`,
  `workorder-parser.manifest.json`: superseded by consolidation (see above).

## Execution facts

- Valence: Candidate (shells to another repo's driver; live mode spends quota).
- fs: `~/workspace/batch-compile` (work orders), `~/workspace/compute`
  (driver; read+execute only via the module invocation).
- network: none for dry/shadow; live inherits the driver's provider egress.
- kill: driver is checkpoint-resume safe; suspend drains, kill = SIGTERM,
  final receipt from the adapter.
