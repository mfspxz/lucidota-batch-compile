import os, sys
sys.path.insert(0, '/home/hatch/workspace/compute')
from pipeline.allocate import QuotaCoordinator
log = sys.argv[1]
c = QuotaCoordinator(log_path=log)
pid = next(iter(c.pools))
c._append_log = lambda rec: os._exit(0)
c.reserve(pid, {"task_id": 't-kill1', "attempt_id": "a",
                "units": 3, "minter": "x"})
os._exit(99)  # must never be reached
