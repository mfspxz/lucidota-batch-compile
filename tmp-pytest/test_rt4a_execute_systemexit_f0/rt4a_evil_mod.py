"""Synthetic hostile adapter module (red-team 4A)."""
COUNT_FILE = '/home/hatch/workspace/batch-compile/tmp-pytest/test_rt4a_execute_systemexit_f0/count.txt'

def _bump():
    try:
        n = int(open(COUNT_FILE).read().strip())
    except (OSError, ValueError):
        n = 0
    open(COUNT_FILE, "w").write(str(n + 1))

_bump()  # import-time side effect: proves module code runs on import


class Good:
    def execute(self, envelope):
        return {"artifact_text": "rt4a synthetic",
                "response": {}, "elapsed_seconds": 0.1}


class NeedsArgs:
    def __init__(self, x):
        self.x = x

    def execute(self, envelope):
        return {}


class NoExec:
    execute = 42


class ExitInit:
    def __init__(self):
        raise SystemExit(7)


class SysExitExec:
    def execute(self, envelope):
        raise SystemExit(3)


class NoneExec:
    def execute(self, envelope):
        return None


class StrExec:
    def execute(self, envelope):
        return "not a dict"
