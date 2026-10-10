import os, sys
sys.path.insert(0, '/home/hatch/workspace/compute')
from pipeline.allocate import QuotaCoordinator
log = sys.argv[1]
c = QuotaCoordinator(log_path=log)
pid = next(iter(c.pools))
os.fsync = lambda fd: os._exit(0)
c.reserve(pid, {"task_id": 't-kill3', "attempt_id": "a",
                "units": 2, "minter": "x"})
os._exit(99)  # must never be reached
