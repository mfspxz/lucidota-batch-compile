import os, sys
sys.path.insert(0, '/home/hatch/workspace/compute')
from pipeline.allocate import QuotaCoordinator
log = sys.argv[1]
c = QuotaCoordinator(log_path=log)
pid = next(iter(c.pools))
orig = c._append_log
def _killer(rec):
    orig(rec)
    os._exit(0)
c._append_log = _killer
c.reserve(pid, {"task_id": 't-kill2', "attempt_id": "a",
                "units": 3, "minter": "x"})
os._exit(99)  # must never be reached
